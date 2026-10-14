"""One parent-authorized frozen independent reference materialization only."""
from pathlib import Path
import hashlib,json,os,shutil,subprocess,sys,time
base=Path('research/batch56');sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
generator=Path('scripts/make_causal_deferral_gold_batch56.py')
assert sha(generator)=='495c6d82a877dd111163f2f636ffac657802e08879041791262d65669414f800'
outputs=[base/n for n in ('gold160.json','gold-driver-input.json','literal-charge-gold.json','fixture-qualifier-summary.json')]
assert all(not p.exists() for p in outputs),'Never overwrite/restart first reference execution'
assert not (base/'reference-execution-status.json').exists()
assert shutil.disk_usage(Path.cwd().anchor).free>=1<<27
prior=[base/'source-before-gold-freeze.json',base/'fee-erratum-freeze-revision1.json',base/'literal-hand-trace.json',base/'solution.cpp']
prior_sha={str(p):sha(p) for p in prior}
temporary=(base/'compiler-temp').resolve();temporary.mkdir(exist_ok=True)
env=os.environ.copy();env.update({k:str(temporary) for k in ('TEMP','TMP','TMPDIR')})
command=[sys.executable,str(generator)];start=time.perf_counter()
actual=subprocess.run(command,capture_output=True,env=env)
(base/'reference.stdout.txt').write_bytes(actual.stdout);(base/'reference.stderr.txt').write_bytes(actual.stderr)
status=dict(status='ACTUAL_REFERENCE_TERMINAL',actual_exit_code=actual.returncode,owner_pid=os.getpid(),
            command=command,generator_sha256=sha(generator),shared_reference_wall_seconds=time.perf_counter()-start,
            process_environment_overrides={k:env[k] for k in ('TEMP','TMP','TMPDIR')},
            candidate_executed=False,compiler_executed=False,solver_executed=False,
            prior_files=[dict(path=p,sha256=hs,preserved=(sha(p)==hs)) for p,hs in prior_sha.items()],
            outputs=[dict(path=str(p),sha256=sha(p),bytes=p.stat().st_size) for p in outputs if p.exists()])
(base/'reference-execution-status.json').write_text(json.dumps(status,indent=2)+'\n',encoding='utf-8')
print(actual.stdout.decode('utf-8',errors='replace'));print(actual.stderr.decode('utf-8',errors='replace'))
print(json.dumps(dict(actual_exit_code=actual.returncode,owner_pid=os.getpid(),outputs=len(status['outputs']))))
if actual.returncode:sys.exit(actual.returncode)
assert len(status['outputs'])==4 and all(r['preserved'] for r in status['prior_files'])
summary=json.loads((base/'fixture-qualifier-summary.json').read_text())
literal=json.loads((base/'literal-charge-gold.json').read_text())
derived=[{k:t[k] for k in ('template','first_pair_fields','complete_scan','limits')} for t in literal['templates']]
assert derived[0]['first_pair_fields']==75 and derived[0]['complete_scan']==127
files=[*outputs,base/'reference-execution-status.json',base/'reference.stdout.txt',base/'reference.stderr.txt',
       generator,Path(__file__),*prior,base/'gold-driver.cpp',base/'charged-work-implementation.json',base/'literal-hand-trace-revision1.json']
freeze=dict(status='ACTUAL_INDEPENDENT_REFERENCE_GOLD_FROZEN_BEFORE_CANDIDATE_COMPILE',actual_exit_code=0,
            count=summary['count'],families=summary['families'],summary=summary,derived_literal=derived,
            initial_hand_error_preserved=True,static_hand_revision='first75/complete127; revision BEFORE reference execution',
            candidate_executed=False,compiler_executed=False,default_unchanged=True,old_open_tex_unchanged=True,
            files=[dict(path=str(p),sha256=sha(p),bytes=p.stat().st_size) for p in files])
(base/'pre-compile-gold-freeze.json').write_text(json.dumps(freeze,indent=2)+'\n',encoding='utf-8')
print(json.dumps(dict(freeze_sha256=sha(base/'pre-compile-gold-freeze.json'),derived_literal=derived)))
