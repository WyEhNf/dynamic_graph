"""Append max evidence and current docs without rewriting small acceptance."""
import hashlib,json,shutil
from pathlib import Path
p=Path(__file__).resolve().parents[1];stage=p/'artifacts/stage2-vm-proved-budget';root=stage/'maximum-shape';out=root/'final-evidence';out.mkdir(exist_ok=False)
def sha(x):return hashlib.sha256(Path(x).read_bytes()).hexdigest()
plan=json.loads((root/'run-plan.json').read_text(encoding='utf-8'));report=json.loads((root/'report.json').read_text(encoding='utf-8'))
assert report['passed']and report['status']=='complete'and len(report['runs'])==3 and report['plan_sha256']==sha(root/'run-plan.json')
assert report['default_failure']['actual_exit_code']==1 and report['default_failure']['unpublished_output']and not(root/'fixed-default-rejected.bin').exists()and not(root/'fixed-default-rejected.bin.partial').exists()
assert report['large_SHA_verified']and not report['ordinary_fixed_default_maximum_passed']and report['optin_proved_policy_maximum_passed']
accept=stage/'runtime-integration/acceptance/manifest.json';assert sha(accept)==plan['acceptance_manifest_sha256']
evidence={}
for x in [root/'run-plan.json',root/'report.json',*sorted(root.glob('*.stdout')),*sorted(root.glob('*.stderr'))]:
    target=out/x.name;shutil.copyfile(x,target);evidence[x.name]=sha(target)
files=[p/'README.md',p/'docs/stage2-vm-proved-budget-integration.md',p/'tools/test_vm_proved_budget_maximum_stage2.py',p/'tools/windows_resource_probe.py',p/'tools/evaluate_source.py',Path(__file__)]
source={}
for x in files:
    relative=x.relative_to(p);target=out/'source'/relative;target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(x,target);source[relative.as_posix()]=sha(target)
for name,digest in plan['script_sha256'].items():assert sha(p/'tools'/name)==digest
for binary in plan['binaries'].values():assert sha(binary['path'])==binary['sha256']
ordinary=sha(p/'build/cholesky_runtime.exe');memory=sha(p/'build-memory/cholesky_runtime.exe');assert ordinary=='99a87d135378406a15efd930d58941291683ca799f91bd5dcc0ca77ceadef448'and memory=='7da06bbd96b711f08283c1df2379741f70d8fb2be6727feae586f6c00aaad947'
assert all(g['passed']and g['available_ram_bytes']>=2684354560 for g in report['resource_gates'])
summary=[]
for row in report['runs']:
    assert row['actual_exit_code']==0 and row['bytes']==800000008 and row['byte_identical']and row['sha256']==plan['historical_sha256']['oracle.bin']and row['vm_steps']==row['vm_budget_bound_peak']==row['vm_effective_step_limit_max']==1700000012 and not row['explicit_vm_step_limit']
    summary.append({key:row[key]for key in ['backend','vm_backend','output','actual_exit_code','bytes','sha256','vm_steps','vm_budget_bound_peak','vm_effective_step_limit_max','vm_budget_work','vm_budget_proof_ms','vm_prepare_ms','compute_ms','input_read_ms','output_write_ms','metadata_read_ms','wall_ms','sha_validation_ms','whole_file_comparison_ms','process_peak_working_set_bytes','process_peak_commit_bytes','available_ram_before_bytes','host_available_ram_min_bytes','host_busy_percent_during_process']})
manifest={'passed':True,'scope':'three sequential opt-in proved N10000 full-file functional/resource cases, fixed default rejection; no promotion/performance','tool_session':10759,'actual_outer_exit_code':0,'plan_sha256':sha(root/'run-plan.json'),'report_sha256':sha(root/'report.json'),'small_acceptance_sha256':sha(accept),'source_sha256':source,'evidence_sha256':evidence,'actual_runs':summary,'full_C_reference':plan['original_C_reference'],'C_reference_reexecuted':False,'large_source_input_ref_bin_SHA_verified_by_original_runner':True,'final_freezer_rehashes_large_files':False,'ordinary_sha256':ordinary,'memory_sha256':memory,'proved_CMake_default':False,'published_budget_policy':'fixed1e9','ordinary_default_maximum_passed':False,'optin_proved_maximum_passed':True,'native_FP_and_Metadata_unchanged':True,'performance_claim':False,'remaining_general_loop_scope':'Unknown/nested/irreducible/data-controlled or unsupported cycles retain fixed1e9; this is not a universal C/N10000 guarantee.'}
(out/'manifest.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8');print(json.dumps({'passed':True,'manifest':str(out/'manifest.json'),'manifest_sha256':sha(out/'manifest.json'),'actual_case_count':len(summary),'ordinary_default_unchanged':True,'optin_proved_maximum_passed':True}),flush=True)
