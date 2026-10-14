"""Bounded post-promotion research on all 41 unresolved records; no default edits."""
from pathlib import Path
import datetime,hashlib,json,subprocess,time
ROOT=Path(__file__).resolve().parents[1];OUT=Path('G:/Hackathon-stage2-artifacts/project27/20261013/post-r64');OUT.mkdir(exist_ok=True)
EXE=OUT.parent/'r62/selected-driver.exe';sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
rows=json.loads((OUT.parent/'r63/remaining63-helper.json').read_text())['cases'];failed={r['name'] for r in rows if not r['helper']['valid']}
original=ROOT/'research/batch52/remaining63-input-only.json';cases=[c for c in json.loads(original.read_text())['cases'] if c['name'] in failed];assert len(cases)==41
src=OUT/'remaining41-input-only.json';src.write_text(json.dumps({'format':'aicore-local-v1','cases':cases}))
jobs=[(w,s,128000000) for w in (4,8,16) for s in (1,2,3)]+[(32,0,512000000),(64,0,512000000),(128,0,512000000)]
report={'default_changed':False,'original_records':41,'sha256':{str(p):sha(p) for p in [original,src,EXE,Path(__file__)]},'jobs':[]};deadline=datetime.datetime(2026,10,13,5,53,tzinfo=datetime.timezone.utc)
for w,style,budget in jobs:
    remaining=(deadline-datetime.datetime.now(datetime.timezone.utc)).total_seconds()
    if remaining<120:report['stopped_for_deadline']=True;break
    dst=OUT/f'w{w}-s{style}-b{budget}.json';start=time.perf_counter()
    run=subprocess.run([str(EXE),str(src),str(dst),'helper-only',str(budget),str(w),str(style)],capture_output=True,text=True,timeout=min(remaining-60,240))
    assert run.returncode==0,(run.returncode,run.stderr)
    rs=json.loads(dst.read_text())['cases'];assert len(rs)==41;h=[r['helper'] for r in rs]
    entry={'width':w,'style':style,'budget':budget,'recovered':[r['name'] for r in rs if r['helper']['valid']],
           'cpu_us':sum(x['cpu_us'] for x in h),'wall_us':sum(x['wall_us'] for x in h),'elapsed_seconds':time.perf_counter()-start,'output':str(dst),'sha256':sha(dst)}
    report['jobs'].append(entry);(OUT/'report.partial.json').write_text(json.dumps(report,indent=2));print(json.dumps(entry),flush=True)
report['complete']=True;(OUT/'report.json').write_text(json.dumps(report,indent=2))
