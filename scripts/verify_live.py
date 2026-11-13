#!/usr/bin/env python3
"""Anonymous live HTTP verification; output is JSON, no authentication involved."""
import concurrent.futures,hashlib,json,pathlib,subprocess,tempfile
ROOT=pathlib.Path(__file__).resolve().parent.parent
BASE='https://lynnlee1229.github.io/'

def get(path):
 with tempfile.TemporaryDirectory(prefix='java-lab-live-') as tmp:
  target=pathlib.Path(tmp)/'response'
  r=subprocess.run(['curl','-fsSL','--retry','2','--retry-all-errors','--max-time','25',BASE+path,'-o',str(target)],capture_output=True,text=True,timeout=90)
  if r.returncode:raise RuntimeError(path+': live HTTP failed')
  return target.read_bytes()
def main():
 manifest=json.loads((ROOT/'dist/java-runtime-lab/manifest.json').read_text())['files']
 def check(item):
  name,expected=item;data=get('java-runtime-lab/'+name);assert hashlib.sha256(data).hexdigest()==expected,name+' differs from audited export';return {'path':'/java-runtime-lab/'+name,'sha256':expected,'bytes':len(data)}
 with concurrent.futures.ThreadPoolExecutor(max_workers=4) as ex:files=list(ex.map(check,manifest.items()))
 live_manifest=json.loads(get('java-runtime-lab/manifest.json'));assert live_manifest['files']==manifest
 for path in ['websites/','zh/websites/']:
  text=get(path).decode();assert '/java-runtime-lab/'+('zh/' if path.startswith('zh/') else 'en/') in text,path
 robots=get('robots.txt').decode();assert 'https://lynnlee1229.github.io/java-runtime-lab/sitemap.xml' in robots
 for path in ['agent-reliability-lab/en/','geodata-lab/en/','stream-batch-lab/en/','search-recommendation-ads-lab/']:
  assert len(get(path))>300,path
 result={'status':'passed','anonymousHTTP':True,'manifestMatched':True,'homepageCardsBothLanguages':True,'robotsSitemap':True,'preservedLabsReachable':True,'files':files}
 (ROOT/'local/live-check.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))
if __name__=='__main__':main()
