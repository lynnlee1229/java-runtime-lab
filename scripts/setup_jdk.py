#!/usr/bin/env python3
"""Download the pinned Temurin build into ignored local/. Never changes system Java."""
import hashlib,pathlib,platform,subprocess,sys,tarfile
root=pathlib.Path(__file__).resolve().parent.parent
osname={'Darwin':'mac','Linux':'linux'}.get(platform.system())
arch={'arm64':'aarch64','aarch64':'aarch64','x86_64':'x64','AMD64':'x64'}.get(platform.machine())
if not osname or not arch:raise SystemExit('Supported: macOS or Linux, ARM64 or x64. Use Linux in WSL on Windows.')
local=root/'local';local.mkdir(exist_ok=True)
name=f'OpenJDK25U-jdk_{arch}_{osname}_hotspot_25.0.5_8.tar.gz'
base='https://github.com/adoptium/temurin25-binaries/releases/download/jdk-25.0.5%2B8/'
for suffix in ['', '.sha256.txt']:
 subprocess.run(['curl','-fL','--retry','3','--retry-all-errors','--retry-delay','2','--max-time','240','-o',str(local/(name+suffix)),base+name+suffix],check=True,timeout=260)
expected=(local/(name+'.sha256.txt')).read_text().split()[0]
actual=hashlib.sha256((local/name).read_bytes()).hexdigest()
if actual!=expected:raise SystemExit('JDK checksum mismatch; no extraction performed')
with tarfile.open(local/name) as archive:
 for member in archive.getmembers():
  if pathlib.PurePosixPath(member.name).is_absolute() or '..' in pathlib.PurePosixPath(member.name).parts:raise SystemExit('Unexpected archive member')
subprocess.run(['tar','-xzf',str(local/name),'-C',str(local)],check=True,timeout=60)
print('Temurin 25.0.5+8 checksum verified; installed only under local/. Run python3 scripts/lab.py doctor.')
