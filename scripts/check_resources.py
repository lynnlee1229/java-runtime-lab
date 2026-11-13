#!/usr/bin/env python3
"""Opt-in official URL verification. Response bodies are temporary and never republished."""
import concurrent.futures
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import subprocess
import tempfile
from urllib.parse import urlparse
from curriculum import ROOT, validate

def check(row):
    url=row['url']
    assert urlparse(url).hostname in {'ocw.mit.edu','openjdk.org','docs.oracle.com','www.dre.vanderbilt.edu'}
    with tempfile.TemporaryDirectory(prefix='java-curriculum-') as tmp:
        body=Path(tmp)/'body'
        result=subprocess.run(['curl','-fsSL','--retry','2','--retry-all-errors','--max-time','30',url,'-o',str(body)],capture_output=True,timeout=100)
        if result.returncode: raise RuntimeError('Could not verify '+row['id'])
        content=body.read_bytes();assert len(content)>500
        return {'id':row['id'],'url':url,'publicRead':True,'bytes':len(content),'sha256':hashlib.sha256(content).hexdigest()}

if __name__ == '__main__':
    d=validate(json.loads((ROOT/'docs/curriculum.json').read_text()))
    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
        results=list(executor.map(check,d['resources']))
    output={'checkedAt':datetime.now(timezone.utc).isoformat(),'method':'Anonymous HTTP GET; no registration/cookies/credentials; bodies discarded','resources':results}
    (ROOT/'records/resource-checks.json').write_text(json.dumps(output,indent=2)+'\n')
    print('PASS: anonymous official resource reads:',len(results))
