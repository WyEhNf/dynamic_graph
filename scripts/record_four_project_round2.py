"""Collect completed round2 evidence; never regenerate experiments or overwrite."""
from datetime import datetime, timezone, timedelta
import hashlib
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
G=Path('G:/Hackathon-stage2-artifacts')


def sha(path):
    h=hashlib.sha256()
    with path.open('rb') as stream:
        for chunk in iter(lambda:stream.read(1024**2),b''):h.update(chunk)
    return h.hexdigest()


def main():
    paths={
        '11-model-v1':G/'project11/candidate-gate-paired-20261012/report.json',
        '11-model-v2':G/'project11/candidate-gate-public-prompt-v2-20261012/report.json',
        '11-offline-scoring':G/'project11/candidate-gate-offline-scoring-20261012.json',
        '18-composed':G/'project18/r197-composed-selected7/report.json',
        '18-independent-audit':ROOT/'outputs/composed-mobile-selected7-audit-2026-10-12.json',
        '19-source':G/'project19/load-run4/source-provenance.json',
        '19-functional':G/'project19/load-run4/functional19/report.json',
        '19-performance':G/'project19/load-run4/selected-performance3/report.json',
        '19-ctest':G/'project19/load-run4/build/Testing/Temporary/LastTest.log',
        '19-vm-source':G/'project19/load-run4/workspace/src/load_pair_vm.cpp',
        '19-test-source':G/'project19/load-run4/workspace/tests/load_pair_vm_tests.cpp',
        '19-build-flags':G/'project19/load-run4/build/CMakeFiles/cholesky_core.dir/flags.make',
        '19-core':G/'project19/load-run4/build/libcholesky_core.a',
        '19-runtime':G/'project19/load-run4/build/cholesky_runtime.exe',
        '19-observer':G/'project19/load-run4/observer.exe',
        '19-observer-source':G/'project19/load-pair/functional-plan/vm_load_pair_functional_observer_stage2.cpp',
        '27-source':ROOT/'projects/27-aicore-streams/research/batch57/source-provenance.json',
        '27-summary':ROOT/'projects/27-aicore-streams/reports/necessary-prefix-candidate-r57-2026-10-12.json',
        '27-controls':G/'project27/r57-necessary-prefix/controls-report.json',
        '27-budget-controls':G/'project27/r57-necessary-prefix/budget-controls-receipt.json',
        '27-budget-controls-exe':G/'project27/r57-necessary-prefix/budget-controls.exe'}
    evidence={name:{'path':str(p),'sha256':sha(p),'bytes':p.stat().st_size} for name,p in paths.items()}
    load=lambda name:json.loads(paths[name].read_text())
    for name in ['11-model-v1','11-model-v2','18-composed','19-functional','19-performance']:assert load(name)['completed'],name
    for name in ['18-independent-audit','19-functional','19-performance','27-controls','27-budget-controls']:assert load(name)['passed'],name
    ctest=paths['19-ctest'].read_text(errors='replace');assert ctest.count('Test Passed.')==16 and 'Test Failed.' not in ctest
    src=[]
    for project,files in {
        '11-context-governance':['src/context_governance/public_prompt.py','tests/test_public_prompt.py','scripts/run_candidate_gate_paired.py','scripts/prepare_public_prompt_paired.py','scripts/run_candidate_gate_public_prompt_v2.py','scripts/score_saved_candidate_batches.py'],
        '18-isa-scheduler':['scripts/research_composed_mobile.py','scripts/audit_composed_mobile_result.py'],
        '19-dynamic-graph':['tools/prepare_load_run_candidate.py','tools/validate_load_run_candidate.py','tools/benchmark_load_run_candidate.py'],
        '27-aicore-streams':['research/batch57/necessary_prefix_search.inc','research/batch57/solution.cpp','research/batch57/selected-driver.cpp','scripts/prepare_necessary_prefix_candidate.py','scripts/validate_necessary_prefix_candidate.py','scripts/summarize_necessary_prefix_candidate.py','tests/test_necessary_prefix_r57.cpp']}.items():
        src.extend(ROOT/'projects'/project/p for p in files)
    src += [Path(__file__),ROOT/'docs/four-project-development-round2-2026-10-12.md']
    for p in src:evidence[str(p.relative_to(ROOT))]={'path':str(p),'sha256':sha(p),'bytes':p.stat().st_size}
    eighteen=load('18-independent-audit');twentyseven=load('27-summary')
    summary={'11':{'paired_batches':2,'generated_calls':16,'public_selected':0,'held_back_passes':0,
        'unit_test_terminal_receipt':{'command':'python -m unittest discover -s tests','total':54,'passed':53,'skipped':1,'exit_code':0,'elapsed_seconds':70.038}},
        '18':{k:eighteen[k] for k in ['records','before_copies','after_copies','totals','frontier']},
        '19':{'ctest_passed':16,'fusion_contract_comparisons':8606,'functional_sources':19,'dynamic_removed_dispatches':1280,
            'paired_performance_selected_DEV':load('19-performance')['summary']},
        '27':{k:twentyseven[k] for k in ['before_whole_success','after_whole_success','recoveries','pruned_producer_decisions','controls']}}
    result={'recorded_at':datetime.now(timezone(timedelta(hours=8))).isoformat(),'summary':summary,'evidence':evidence,
        'default_promotions':[],'official_requirements_proved':False,'prior_artifacts_preserved':True,
        'notes':['11 scoring happens only after all generation; neither batch selects rejected candidates',
            '18 selected7 larger budget; full336 missing64 unchanged',
            '19 selected3 vs same binary unfused, not old pair; unstable timing no promotion',
            '27 bounded search failures unknown; existing4 plans equal, new recoveries0']}
    target=ROOT/'outputs/four-project-development-round2-2026-10-12.json'
    with target.open('x',encoding='utf-8') as stream:json.dump(result,stream,ensure_ascii=False,indent=2)
    print(json.dumps({'report':str(target),'evidence_files':len(evidence),'sha256':sha(target)}))


if __name__=='__main__':main()
