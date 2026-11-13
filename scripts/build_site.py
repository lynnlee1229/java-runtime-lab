#!/usr/bin/env python3
"""Portable, allowlisted static export; never reads local/."""
import hashlib,html,json,pathlib,re,shutil,sys
from verify import verify
ROOT=pathlib.Path(__file__).resolve().parent.parent
OUT=ROOT/'dist/java-runtime-lab';BASE='https://lynnlee1229.github.io/java-runtime-lab/'
SOURCE='https://github.com/lynnlee1229/java-runtime-lab'

def inline(s):
 s=html.escape(s);s=re.sub(r'`([^`]+)`',r'<code>\1</code>',s)
 return re.sub(r'\[([^\]]+)\]\((https://[^)]+)\)',r'<a href="\2">\1</a>',s)
def markdown(text):
 lines=text.splitlines();out=[];para=[];code=None;ul=False
 def flush():
  if para:out.append('<p>'+inline(' '.join(para))+'</p>');para.clear()
 for line in lines:
  if line.startswith('```'):
   flush()
   if code is None:code=[]
   else:out.append('<pre><code>'+html.escape('\n'.join(code))+'</code></pre>');code=None
  elif code is not None:code.append(line)
  elif line.startswith('#'):
   flush();n=len(line)-len(line.lstrip('#'));out.append(f'<h{n}>'+inline(line[n:].strip())+f'</h{n}>')
  elif line.startswith('- '):
   flush()
   if not ul:out.append('<ul>');ul=True
   out.append('<li>'+inline(line[2:])+'</li>')
  else:
   if ul:out.append('</ul>');ul=False
   if not line.strip():flush()
   else:para.append(line)
 flush()
 if ul:out.append('</ul>')
 return '\n'.join(out)
def page(lang,kind,body):
 zh=lang=='zh';lc='zh-CN' if zh else 'en-US';other='en' if zh else 'zh'
 route='' if kind=='index' else kind+'/'
 rel='../' if kind=='index' else '../../'
 t=lambda e,c:c if zh else e
 title=t({'index':'Java Runtime Lab','guide':'Run guide · Java Runtime Lab','methods':'Methods · Java Runtime Lab'}[kind],{'index':'Java 运行时实验室','guide':'运行指南 · Java 运行时实验室','methods':'方法与范围 · Java 运行时实验室'}[kind])
 nav=''.join(f'<a href="{"" if kind=="index" else "../"}{"./" if k=="index" else k+"/"}"'+(' aria-current="page"' if k==kind else '')+'>'+label+'</a>' for k,label in [('index',t('Evidence','实测记录')),('guide',t('Run guide','运行指南')),('methods',t('Methods','方法范围'))])
 return f'''<!doctype html><html lang="{lc}"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>{title} · Lynn Lee</title><meta name="description" content="{t('Real JVM experiments: bounded pools, cancellation, retry amplification and audited JFR evidence.','真实 JVM 实验：有界线程池、超时取消、重试放大与经过审计的 JFR 摘要。')}"><meta name="author" content="Lynn Lee"><link rel="canonical" href="{BASE}{lang}/{route}"><link rel="alternate" hreflang="en-US" href="{BASE}en/{route}"><link rel="alternate" hreflang="zh-CN" href="{BASE}zh/{route}"><link rel="alternate" hreflang="x-default" href="{BASE}en/{route}"><link rel="icon" href="https://lynnlee1229.github.io/assets/rick-favicon.ico"><link rel="stylesheet" href="{rel}assets/style.css"><meta property="og:title" content="{title}"><meta property="og:url" content="{BASE}{lang}/{route}"><meta property="og:image" content="https://lynnlee1229.github.io/assets/original-cover.png"></head><body><header><div class="top"><a class="brand" href="https://lynnlee1229.github.io/{'zh/' if zh else ''}"><img src="https://lynnlee1229.github.io/assets/rick-avatar.jpeg" width="32" height="32" alt="Rick">Lynn Lee <small>/ Runtime Lab</small></a><nav aria-label="{t('Main navigation','主导航')}">{nav}<a data-language data-base="{rel}{other}/{route}" href="{rel}{other}/{route}" lang="{other}">{'English' if zh else '中文'}</a></nav></div></header><main>{body}</main><footer>Lynn Lee · {t('Synthetic workloads. Saved real measurements. No live JVM in the browser.','合成负载，真实保存记录；浏览器不运行 JVM。')}<br><a href="{SOURCE}">{t('MIT companion source','MIT 配套实验源码')}</a> · <a href="https://lynnlee1229.github.io/{'zh/' if zh else ''}websites/#learning-labs">{t('All learning Labs','全部学习实验室')}</a></footer>{f'<script type="module" src="{rel}assets/app.mjs"></script>' if kind=='index' else ''}</body></html>'''
def workbench(lang):
 t=lambda e,c:c if lang=='zh' else e
 return f'''<section class="hero"><div><p class="eyebrow">Java Runtime Lab / 01</p><h1>{t('When waiting ends,<br>does work stop?','不再等待，<br>工作就停止了吗？')}</h1><p class="lede">{t('Follow actual task lifecycles through a saturated pool, cancellation and retries. Inspect the evidence, then reproduce it on your own JVM.','沿着真实任务生命周期，查看线程池饱和、超时取消与重试。先读证据，再用自己的 JVM 复现。')}</p></div><aside class="note"><strong>{t('Recorded, not simulated','真实保存，非浏览器模拟')}</strong><p>{t('3 independent JVM runs · Temurin 25.0.5+8 LTS · seed 20261113. All work and failures are synthetic and local.','3 轮独立 JVM 实跑 · Temurin 25.0.5+8 LTS · 种子 20261113。负载和失败均为本地合成。')}</p><a href="guide/">{t('Start from zero →','从零执行 →')}</a></aside></section><div class="toolbar"><label>{t('Saved run','保存轮次')}<select id="run"><option value="1">01</option><option value="2">02</option><option value="3">03</option></select></label><button id="download">{t('Download run JSON','下载整轮 JSON')}</button><button id="share">{t('Copy deep link','复制分享深链')}</button></div><div class="tabs" role="group" aria-label="{t('Scenario','实验场景')}"><button data-view="pool" aria-pressed="true">01 / {t('Pool saturation','线程池饱和')}</button><button data-view="timeout" aria-pressed="false">02 / {t('Timeout & cancel','超时与取消')}</button><button data-view="retry" aria-pressed="false">03 / {t('Retry amplification','重试放大')}</button></div><p id="status" class="status" role="status" aria-live="polite">{t('Loading recorded evidence…','正在加载实测记录…')}</p><section class="workspace" id="workspace"><h2 id="case-title">{t('Actual task evidence','真实任务证据')}</h2><div class="toolbar"><label>{t('Inspect policy','检查策略')}<select id="policy"></select></label><button id="export-case">{t('Export this case','导出当前案例')}</button></div><div id="metrics" class="metrics"></div><div id="chart"></div><p id="explanation" class="lede"></p><div id="comparison"></div><details open><summary>{t('Task lifecycle events','任务生命周期事件')}</summary><div class="toolbar"><label>{t('Task filter','任务筛选')}<select id="task"></select></label><small id="event-count"></small></div><div class="trace" id="events"></div></details><details><summary>{t('Environment & audited JFR summary','环境与审计后的 JFR 摘要')}</summary><pre id="environment"></pre></details></section><noscript><p class="note">{t('The evidence viewer needs JavaScript. Read the guide/methods or download the saved records directly.','查看器需要 JavaScript，可先阅读指南和方法，或直接下载保存记录。')} <a href="../assets/run-1.json">run-1.json</a></p></noscript><div class="cards"><article class="card"><h3>{t('Run the exact experiment','运行同一实验')}</h3><p>{t('One pinned JDK, a checksum-pinned Maven wrapper, hard timeouts and no runtime dependencies. Raw JFR stays on your machine.','固定 JDK、带校验值的 Maven wrapper、硬超时，无额外运行依赖。原始 JFR 保留本机。')}</p><a href="guide/">{t('Open the run guide →','打开运行指南 →')}</a></article><article class="card"><h3>{t('Know the boundary','理解结论边界')}</h3><p>{t('Three repetitions verify lifecycle relationships. These timings are observations under JFR, not a JMH benchmark or a capacity promise.','三轮重复验证生命周期关系。启用 JFR 时的耗时是本机观察，不是 JMH 微基准或容量承诺。')}</p><a href="methods/">{t('Read methods & scope →','阅读方法与范围 →')}</a></article></div>'''

def build():
 if OUT.exists():shutil.rmtree(OUT)
 (OUT/'assets').mkdir(parents=True)
 for name in ['style.css','core.mjs','app.mjs']:shutil.copyfile(ROOT/'site'/name,OUT/'assets'/name)
 for i in range(1,4):
  src=ROOT/f'records/run-{i}.json';d=json.loads(src.read_text());verify(d)
  # Only the explicitly authored record schema is accepted; no raw JVM/JFR fields.
  if set(d)!={'schemaVersion','recordType','recordedAt','seed','environment','config','pools','cancellation','retries','jfr','assertionsPassed'}:raise ValueError('Unexpected top-level field')
  if set(d['environment'])!={'jdk','vendor','os','osVersion','arch','logicalProcessors'}:raise ValueError('Unexpected environment field')
  shutil.copyfile(src,OUT/'assets'/src.name)
 for lang in ['en','zh']:
  for kind in ['index','guide','methods']:
   folder=OUT/lang/('' if kind=='index' else kind);folder.mkdir(parents=True,exist_ok=True)
   body=workbench(lang) if kind=='index' else '<article class="reading">'+markdown((ROOT/f'docs/{kind}.{lang}.md').read_text())+'</article>'
   (folder/'index.html').write_text(page(lang,kind,body))
 (OUT/'index.html').write_text('<!doctype html><html lang="en-US"><head><meta charset="utf-8"><title>Java Runtime Lab</title><meta http-equiv="refresh" content="0;url=en/"><link rel="canonical" href="'+BASE+'en/"></head><body><a href="en/">Java Runtime Lab · English</a></body></html>')
 urls=[BASE+lang+'/'+('' if kind=='index' else kind+'/') for lang in ['en','zh'] for kind in ['index','guide','methods']]
 (OUT/'sitemap.xml').write_text('<?xml version="1.0" encoding="UTF-8"?><urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'+''.join('<url><loc>'+u+'</loc></url>' for u in urls)+'</urlset>')
 manifest={str(p.relative_to(OUT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(OUT.rglob('*')) if p.is_file()}
 (OUT/'manifest.json').write_text(json.dumps({'schemaVersion':1,'files':manifest},indent=2)+'\n')
 print(f'Built audited export: {len(manifest)} files + manifest')
if __name__=='__main__':build()
