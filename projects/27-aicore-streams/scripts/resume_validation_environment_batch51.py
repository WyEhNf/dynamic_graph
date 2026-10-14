"""Launch frozen validation script with process-local F-drive temporary files.

No global environment mutation or deletion of user files. Preserve first
actual ENOSPC failure; that attempt ran no CTest or Clang compilation.
"""
import hashlib,json,os,shutil,subprocess,sys
from pathlib import Path
root=Path.cwd().resolve();p=root/'research/batch51';tmp=p/'compiler-temp';tmp.mkdir(exist_ok=True)
assert tmp.resolve().is_relative_to(root)
log=root/'reports/validation-build-batch51.txt';archive=root/'reports/validation-build-initial-enospc-batch51.txt'
if not archive.exists():
    text=log.read_text(encoding='utf-8')
    assert 'No space left on device' in text
    shutil.copyfile(log,archive)
sha=lambda f:hashlib.sha256(Path(f).read_bytes()).hexdigest()
env=os.environ.copy()
for key in ('TEMP','TMP','TMPDIR'):env[key]=str(tmp)
record=dict(initial_actual_session=3354,initial_actual_exit=1,initial_error='GCC solution.obj failed writing assembly in C: default TEMP: No space left on device',initial_tests_started=False,initial_failure_log_sha=sha(archive),unchanged_source_sha=sha(p/'solution.cpp'),unchanged_frozen_validation_script_sha=sha(root/'scripts/run_validation_build_batch51.py'),process_only_environment={k:env[k] for k in ('TEMP','TMP','TMPDIR')},global_environment_modified=False,user_files_deleted=False,wrapper_sha=sha(__file__),status='Retry original frozen script under F: process-only TEMP')
(p/'environment-repair.json').write_text(json.dumps(record,indent=2),encoding='utf-8')
cmd=[sys.executable,'scripts/run_validation_build_batch51.py']
with (root/'reports/validation-environment-retry-batch51.txt').open('w',encoding='utf-8') as output:r=subprocess.run(cmd,env=env,stdout=output,stderr=subprocess.STDOUT)
record['retry_actual_exit']=r.returncode;record['retry_output_sha']=sha(root/'reports/validation-environment-retry-batch51.txt');record['status']='Actual retry completed'
(p/'environment-repair.json').write_text(json.dumps(record,indent=2),encoding='utf-8');print('Validation environment retry actualexit',r.returncode,flush=True);raise SystemExit(r.returncode)
