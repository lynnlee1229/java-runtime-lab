#!/usr/bin/env python3
import hashlib,json,pathlib,re,sys
from html.parser import HTMLParser
from urllib.parse import urljoin,urlparse,unquote
from verify import verify
from verify_bulkhead import verify as verify_bulkhead
from curriculum import validate as validate_curriculum
ROOT=pathlib.Path(__file__).resolve().parent.parent;OUT=ROOT/'dist';BASE='https://lynnlee1229.github.io/'
class Page(HTMLParser):
 def __init__(self):super().__init__();self.links=[];self.h1=0;self.lang='';self.alt=set()
 def handle_starttag(self,t,attrs):
  a=dict(attrs)
  if t=='h1':self.h1+=1
  if t=='html':self.lang=a.get('lang','')
  if t=='link' and a.get('hreflang'):self.alt.add(a['hreflang'])
  for key in ['href','src']:
   if a.get(key):self.links.append(a[key])
for f in (OUT/'java-runtime-lab').rglob('*'):
 if not f.is_file():continue
 assert f.suffix in ['.html','.json','.xml','.css','.mjs'],f'Unexpected export: {f.name}'
 s=f.read_text()
 # Canonical owner identity and GitHub URLs are public. Other local paths/credentials/contacts are forbidden.
 for pattern in [r'/Users/',r'/home/',r'(?i)[a-z]:\\',r'(?i)(?:sk-proj-|ghp_|github_pat_|BEGIN.*PRIVATE KEY)',r'(?i)mailto:|tel:',r'(?i)password\s*[=:]',r'(?i)(?:localhost|127\.0\.0\.1):\d+']:
  assert not re.search(pattern,s),f'Privacy pattern in {f.name}'
 if f.suffix=='.html':
  p=Page();p.feed(s)
  assert p.lang in ['en-US','zh-CN']
  if f.parent.name!='java-runtime-lab':assert p.h1==1 and p.alt=={'en-US','zh-CN','x-default'}
  for link in p.links:
   u=urlparse(urljoin(BASE+str(f.relative_to(OUT)),link))
   if u.netloc!='lynnlee1229.github.io':continue
   if u.path.startswith('/assets/') or u.path in ['/','/zh/','/websites/','/zh/websites/']:continue
   target=OUT/unquote(u.path).lstrip('/')
   if target.is_dir():target=target/'index.html'
   assert target.exists(),f'Broken link: {f.name} -> {link}'
for i in range(1,4):verify(json.loads((OUT/f'java-runtime-lab/assets/run-{i}.json').read_text()))
for i in range(1,4):verify_bulkhead(json.loads((OUT/f'java-runtime-lab/assets/bulkhead-{i}.json').read_text()))
registry=validate_curriculum(json.loads((OUT/'java-runtime-lab/assets/curriculum.json').read_text()))
receipts=json.loads((OUT/'java-runtime-lab/assets/resource-checks.json').read_text())
assert {r['id'] for r in receipts['resources']}=={r['id'] for r in registry['resources']}
assert all(r['publicRead'] and r['bytes']>500 for r in receipts['resources'])
m=json.loads((OUT/'java-runtime-lab/manifest.json').read_text())['files']
for name,sha in m.items():assert hashlib.sha256((OUT/'java-runtime-lab'/name).read_bytes()).hexdigest()==sha
assert set(m)=={str(f.relative_to(OUT/'java-runtime-lab')) for f in (OUT/'java-runtime-lab').rglob('*') if f.is_file() and f.name!='manifest.json'}
print('PASS: bilingual pages, static links, actual records, privacy allowlist and complete SHA-256 manifest')
