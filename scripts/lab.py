#!/usr/bin/env python3
"""Owned subprocesses only; no process-name killing. Python 3.9+, POSIX/macOS/Linux."""
import argparse,json,os,pathlib,subprocess,sys
ROOT=pathlib.Path(__file__).resolve().parent.parent

def java_home():
    configured=os.environ.get('JAVA_LAB_JDK')
    if configured:return pathlib.Path(configured)
    candidates=list((ROOT/'local').glob('jdk-*/Contents/Home'))+list((ROOT/'local').glob('jdk-*'))
    return next((p for p in candidates if (p/'bin/java').is_file()),pathlib.Path(os.environ.get('JAVA_HOME','/missing')))
def run(cmd,timeout=60,**kw):
    return subprocess.run([str(x) for x in cmd],cwd=ROOT,timeout=timeout,check=True,**kw)
def main():
    p=argparse.ArgumentParser();p.add_argument('action',choices=['doctor','build','run','bulkhead','test','stop']);p.add_argument('--repeats',type=int,default=3);p.add_argument('--seed',type=int,default=20261113);p.add_argument('--failures',type=int,default=6);p.add_argument('--requests',type=int,default=12);p.add_argument('--capacity',type=int,default=3);a=p.parse_args()
    if a.action=='stop':
        print('Experiments run in the foreground, terminate their own pools, and leave no service. Ctrl-C stops only the owned foreground run; local/ keeps evidence. No process-name kill is used.');return
    j=java_home();env=dict(os.environ,JAVA_HOME=str(j),PATH=str(j/'bin')+os.pathsep+os.environ['PATH'])
    version=run([j/'bin/java','-version'],capture_output=True,text=True).stderr
    if '25.0.5' not in version or 'Temurin-25.0.5+8' not in version:raise SystemExit('Need Temurin JDK 25.0.5+8; see README. Set JAVA_LAB_JDK or unpack into local/.')
    if a.action=='doctor': print(version.strip());print('Python',sys.version.split()[0]);return
    if a.action=='build':run(['./mvnw','--batch-mode','-q','package','-DskipTests'],timeout=180,env=env);return
    if not (ROOT/'target/classes/lab/RuntimeLab.class').exists():raise SystemExit('Run scripts/lab.py build first')
    if not 1<=a.repeats<=5:raise SystemExit('--repeats must be 1..5')
    for i in range(0 if a.action=='bulkhead' else a.repeats if a.action=='test' else 1):
        out=ROOT/f'local/run-{i+1}.json';jfr=ROOT/f'local/run-{i+1}.jfr'
        try:run([j/'bin/java','-cp','target/classes','lab.RuntimeLab','--out',out,'--jfr',jfr,'--seed',a.seed,'--failures',a.failures,'--requests',a.requests],timeout=25,env=env)
        except subprocess.TimeoutExpired:raise SystemExit('HARD TIMEOUT: owned child killed and reaped by subprocess.run; no other JVM is touched')
        # Independently parse the actual JFR again in a new JVM.
        summary=json.loads(run([j/'bin/java','-cp','target/classes','lab.RuntimeLab','--read-jfr',jfr],timeout=10,capture_output=True,text=True,env=env).stdout)
        assert summary['readable'] and summary['allowedEventCounts']['lab.TaskEvent']>0
        print(f'run-{i+1}: JSON and JFR verified',flush=True)
    if a.action in ['bulkhead','test']:
        for i in range(a.repeats if a.action=='test' else 1):
            out=ROOT/f'local/bulkhead-{i+1}.json';jfr=ROOT/f'local/bulkhead-{i+1}.jfr'
            run([j/'bin/java','-cp','target/classes','lab.BulkheadLab','--out',out,'--jfr',jfr,'--requests',a.requests,'--capacity',a.capacity],timeout=25,env=env)
            summary=json.loads(run([j/'bin/java','-cp','target/classes','lab.BulkheadLab','--read-jfr',jfr],timeout=10,capture_output=True,text=True,env=env).stdout)
            assert summary==json.loads(out.read_text())['jfr'],'separate JVM JFR read differs'
            run([sys.executable,'scripts/verify_bulkhead.py',out])
    if a.action=='test':
        run([sys.executable,'scripts/verify.py',*['local/run-'+str(i+1)+'.json' for i in range(a.repeats)]])
        for bad in [['--failures','999'],['--bogus','1']]:
            result=subprocess.run([str(j/'bin/java'),'-cp','target/classes','lab.RuntimeLab',*bad],cwd=ROOT,capture_output=True,timeout=5)
            assert result.returncode!=0,'invalid configuration accepted'
        print('PASS: invalid parameter tests')
        for bad in [['--capacity','0'],['--capacity','6','--requests','6'],['--requests','41'],['--bogus','1']]:
            result=subprocess.run([str(j/'bin/java'),'-cp','target/classes','lab.BulkheadLab',*bad],cwd=ROOT,capture_output=True,timeout=5)
            assert result.returncode!=0,'invalid bulkhead configuration accepted'
        run([sys.executable,'-m','unittest','discover','-s','scripts','-p','test_bulkhead*.py'])
if __name__=='__main__':
    try:main()
    except (subprocess.CalledProcessError,subprocess.TimeoutExpired,AssertionError) as e:raise SystemExit(f'FAIL: {e}')
