#!/usr/bin/env python3
"""Six original exercises. Run a real JVM first, then inspect a focused learning outcome."""
import argparse
import json
import pathlib
import subprocess
import sys
from verify import verify as legacy_verify
from verify_bulkhead import verify as bulkhead_verify

ROOT = pathlib.Path(__file__).resolve().parent.parent
UNITS = ['measure', 'pool', 'capacity', 'cancel', 'retry', 'evidence']


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('unit', choices=UNITS)
    p.add_argument('--record', type=pathlib.Path, help='Inspect a saved real capture instead of rerunning')
    p.add_argument('--requests', type=int, default=12)
    p.add_argument('--capacity', type=int, default=3)
    a = p.parse_args()
    bulk = a.unit in ['capacity', 'cancel', 'evidence']
    if a.record:
        source = a.record
    else:
        command = [sys.executable, 'scripts/lab.py', 'bulkhead' if bulk else 'run', '--requests', str(a.requests)]
        if bulk: command += ['--capacity', str(a.capacity)]
        subprocess.run(command, cwd=ROOT, timeout=40, check=True)
        source = ROOT/('local/bulkhead-1.json' if bulk else 'local/run-1.json')
    d = json.loads(source.read_text())
    (bulkhead_verify if bulk else legacy_verify)(d)
    if a.unit == 'measure':
        print('Observed JFR event counts:', json.dumps(d['jfr']['allowedEventCounts']))
        print('Explain: these are instrumented lifecycle observations, not throughput rankings or a confidence interval.')
    elif a.unit == 'pool':
        print(json.dumps([{k:x[k] for k in ['policy','submitted','completed','rejected','callerRuns']} for x in d['pools']], indent=2))
        print('Explain: CallerRuns changes arrivals because the submitter performs work; overflow is not always rejection.')
    elif a.unit == 'capacity':
        print(json.dumps([{k:x[k] for k in ['policy','virtualTasks','maxActive','maxQueued','completed','rejected']} for x in d['cases'][:3]], indent=2))
        print('Predict first: N tasks, C slots => unbounded peak N; queue peak C, queue N-C; reject completes C, rejects N-C.')
    elif a.unit == 'cancel':
        print(json.dumps([{k:x[k] for k in ['policy','cancelSnapshot','permitsRemaining']} for x in d['cases'][3:]], indent=2))
        print('Explain: cancelling the queued task never enters downstream. The ignoring holder remains active after Future cancellation.')
    elif a.unit == 'retry':
        print(json.dumps([{k:x[k] for k in ['policy','requests','attempts','success','failed']} for x in d['retries']], indent=2))
        print('Explain: count extra downstream work and exposed failures together; this model has finite, predetermined failures.')
    elif a.unit == 'evidence':
        print('Actual JFR virtual starts/ends:', d['jfr']['eventCounts']['jdk.VirtualThreadStart'], d['jfr']['eventCounts']['jdk.VirtualThreadEnd'])
        subprocess.run([sys.executable,'-m','unittest','discover','-s','scripts','-p','test_bulkhead*.py'],cwd=ROOT,timeout=10,check=True)
        print('Explain: corrupt records are negative tests, never engine measurements. Zero pinned events is not proof of impossible pinning.')
    print('PASS original exercise:', a.unit)


if __name__ == '__main__':
    main()
