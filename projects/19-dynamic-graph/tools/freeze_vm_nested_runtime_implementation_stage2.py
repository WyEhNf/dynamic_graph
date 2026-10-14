"""Freeze implemented mirror and exact future runner without compiling anything."""
import ast,difflib,hashlib,json,shutil
from pathlib import Path
P=Path(__file__).resolve().parents[1];R=P/'artifacts/stage2-vm-nested-budget/runtime-integration';I=R/'initial-plan';W=R/'workspace';F=R/'implementation-freeze'
def sha(x):return hashlib.sha256(Path(x).read_bytes()).hexdigest()
def main():
    assert not F.exists();initial=json.loads((I/'plan.json').read_text(encoding='utf-8'));contract=json.loads((R/'contract-supplement/plan.json').read_text(encoding='utf-8'))
    assert sha(I/'plan.json')=='32aafc022a3fe8ad375c36bdbccf66823048847c88bc45a3cd18b20abc867253'and sha(R/'contract-supplement/plan.json')=='7aa25cc3a060cffc700aee41799877346d74dc0999a61d33e78b6a172735b5a3'
    changed=set(initial['source_scope']['anticipated_copied_file_changes']);before={};after={};diffs={}
    for rel,row in initial['frozen_files'].items():
        assert sha(I/rel)==row['sha256'],rel
        if not rel.startswith('baseline-source/'):continue
        relative=rel.removeprefix('baseline-source/');before[relative]=row['sha256'];after[relative]=sha(W/relative)
        if relative not in changed:assert before[relative]==after[relative],relative
    assert {k for k in before if before[k]!=after[k]}==changed
    for relative in ['src/vm_nested_step_bound.cpp','include/cholesky/vm_nested_step_bound.hpp','tests/vm_nested_step_bound_tests.cpp']:
        assert sha(W/relative)==sha(I/'nested-source'/relative),relative
    assert sha(W/'src/vm_nested_step_bound.cpp')=='e4174798ec482c474c4bcf0ef3e602c02e339804c5413594cb5755fb68de7dea'
    assert sha(W/'src/vm_step_bound.cpp')==initial['source_scope']['original_vm_step_bound_cpp_SHA_unchanged']
    runner=P/'tools/run_vm_nested_runtime_stage2.py';builder=P/'tools/implement_vm_nested_runtime_mirror_stage2.py';probe=P/'tools/windows_file_resource_probe_stage2.py'
    for source in [runner,builder,Path(__file__)]:ast.parse(source.read_text(encoding='utf-8'),filename=str(source))
    assert sha(probe)=='03db0678b9063a8af11fb799e2017ba57f1968e6da1bb6cc7f6dc2bf213fc1a6'
    F.mkdir();mirror={}
    for source in sorted(W.rglob('*')):
        if not source.is_file():continue
        rel=source.relative_to(W);target=F/'source'/rel;target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(source,target);mirror[rel.as_posix()]=sha(target)
    tools={}
    for source in [runner,builder,probe,Path(__file__)]:
        target=F/'runner-source/tools'/source.name;target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(source,target);tools[source.name]=sha(target)
    for relative in sorted(changed):
        target=F/'diffs'/(relative.replace('/','__')+'.diff');target.parent.mkdir(exist_ok=True);target.write_text(''.join(difflib.unified_diff((I/'baseline-source'/relative).read_text(encoding='utf-8').splitlines(True),(W/relative).read_text(encoding='utf-8').splitlines(True),fromfile='baseline/'+relative,tofile='isolated/'+relative)),encoding='utf-8');diffs[target.name]=sha(target)
    commands={phase:[str(P/'.venv/Scripts/python.exe'),str(runner),'--phase',phase]for phase in ['build','contracts','functional','ctest','ubsan']}
    ordinary=sha(P/'build/cholesky_runtime.exe');memory=sha(P/'build-memory/cholesky_runtime.exe');assert ordinary==initial['ordinary_sha256']and memory==initial['memory_sha256']
    manifest={'schema':'optional-nested-VM-runtime-implementation-freeze-v1','status':'implementation and runners written; no compile/VM/AST/C run yet','initial_plan_sha256':sha(I/'plan.json'),'static_contract_supplement_sha256':sha(R/'contract-supplement/plan.json'),'mirror_path':str(W),'mirror_source_sha256':mirror,'baseline_before_sha256':before,'four_modified_baseline_files':sorted(changed),'modified_after_sha256':{k:after[k]for k in sorted(changed)},'diff_sha256':diffs,'runner_source_sha256':tools,'runner_sha256':sha(runner),'component_CPP_sha256':sha(W/'src/vm_nested_step_bound.cpp'),'component_original_gold_denominator_unchanged':True,'ordinary_sha256':ordinary,'memory_sha256':memory,'working_original_proof_CPP_sha256':sha(P/'src/vm_step_bound.cpp'),'matching_new_ABI_header_sha256':sha(W/'include/cholesky/runtime.hpp'),'all_four_builds_new_core_runtime_and_callers':True,'link_historical_library':False,'builds':initial['builds'],'commands':commands,'expected_selection_observations':{'gnu-nested':60,'portable-nested':60,'proved-only-compat':60,'disabled':10,'total':190},'selection_auxiliary_checks':{'positive_remaining_despite_work_limit_reason':15,'fixed_exact_and_one_short_executions':60,'zero_remaining_example':'50000 reachable instructions yield first work250000 before final CFG sentinel; nested must skip','large_constant_cap_example':'N3 PROGRAM nested30000x40000 then original negative READ before100VMsteps'},'primary_denominator':contract['denominator_contract']['main_total'],'all_primary_and_compat_denominator':contract['denominator_contract']['all_primary_and_compat_totals'],'work_policy':'unchanged first250000; nested only unknown and positive checked remaining; shared aggregate250000; never treat reason work-limit alone as used250000','bound_policy':'no additional MAX bound rejection introduced; retain any successful first proof exactly','existing_extreme_counter_limitation':'Old fixed explicit UINT64MAX followed by >MAX executed instructions would wrap ++steps; executors unchanged. Actual frozen components reject bound==MAX and ordinary fixed1e9 is safe; no claim of MAX+1 execution verification.','existing_VM_sources_changed':False,'compile_or_VM_started':False,'N10000_or_performance_or_default_changed':False}
    (F/'manifest.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8');print(json.dumps({'frozen':True,'manifest_sha256':sha(F/'manifest.json'),'mirror_files':len(mirror),'changed_baseline_files':4,'selection':190,'build_or_run_started':False}))
if __name__=='__main__':main()
