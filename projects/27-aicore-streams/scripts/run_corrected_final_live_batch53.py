"""Authorized fixture correction only, original binaries; no recompile/12/full."""
from pathlib import Path
import hashlib,json,os,subprocess,time
P=Path('research/batch53/corrected');sha=lambda f:hashlib.sha256(Path(f).read_bytes()).hexdigest()
plan=json.loads((P/'revision-map.json').read_text())
for f in plan['frozen_files']:assert sha(f['path'])==f['sha256'],f['path']
env=os.environ.copy();temp=Path('research/batch53/compiler-temp').resolve()
for k in ('TEMP','TMP','TMPDIR'):env[k]=str(temp)
statuses=[]
def run(label,cmd):
    t=time.perf_counter();r=subprocess.run(cmd,capture_output=True,text=True,env=env)
    Path(f'reports/final-live-{label}-corrected-batch53.stdout.txt').write_text(r.stdout,encoding='utf-8');Path(f'reports/final-live-{label}-corrected-batch53.stderr.txt').write_text(r.stderr,encoding='utf-8')
    statuses.append(dict(label=label,command=cmd,actual_exit_code=r.returncode,shared_functional_wall_seconds=time.perf_counter()-t))
    (P/'execution-status.json').write_text(json.dumps(dict(revision_map_sha256=sha(P/'revision-map.json'),statuses=statuses),indent=2)+'\n',encoding='utf-8');print(label,'actual exit',r.returncode,flush=True);assert r.returncode==0
run('generation',['C:/Users/admin/miniconda3/python.exe','scripts/correct_final_live_fixtures_batch53.py'])
for label,cmd in [('gcc',['research/batch53/gold-gcc.exe',str(P/'driver-input.json'),'reports/final-live-gcc-corrected-batch53.json']),('ubsan',['research/batch53/gold-ubsan.exe',str(P/'driver-input.json'),'reports/final-live-ubsan-corrected-batch53.json']),('fixed-ubsan',['research/batch53/fixed-ubsan.exe',str(P/'fixed-gold.json'),'reports/final-live-fixed-ubsan-corrected-batch53.json']),('verify',['C:/Users/admin/miniconda3/python.exe','scripts/verify_corrected_final_live_batch53.py'])]:run(label,cmd)
for f in plan['frozen_files']:assert sha(f['path'])==f['sha256'],f['path']
paths=[str(P/x) for x in ('revision-map.json','qualification-remediation.json','gold.json','fixed-gold.json','driver-input.json','execution-status.json')]+[f'reports/final-live-{x}-corrected-batch53.json' for x in ('gcc','ubsan','fixed-ubsan')]+['reports/final-live-corrected-summary-batch53.json']
out=dict(status='CORRECTED_QUALIFICATION_AND_ACTUAL_GATE_TERMINAL_EXIT0',revision_map_sha256=sha(P/'revision-map.json'),files=[dict(path=f,sha256=sha(f)) for f in paths],statuses=statuses,candidate_source_changed=False,default_changed=False,initial_files_preserved=True,selected12_not_repeated=True,no_compile_or_remaining63_full_or_performance=True)
(P/'completion.json').write_text(json.dumps(out,indent=2)+'\n',encoding='utf-8');print('Corrected R53 small gate actual terminal',flush=True)
