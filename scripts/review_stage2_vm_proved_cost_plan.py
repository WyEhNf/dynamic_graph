"""Independent review of the immutable same-runtime budget-policy cost cohort."""
import json
import re
import time
from pathlib import Path
from review_stage2_vm_proved_integration import ROOT, P, sha, header


def main():
    d=P/'artifacts/stage2-vm-proved-budget/policy-cost'
    plan=json.loads((d/'run-plan.json').read_text())
    acceptance=P/'artifacts/stage2-vm-proved-budget/runtime-integration/acceptance'
    accepted=json.loads((acceptance/'manifest.json').read_text())
    root=json.loads((ROOT/'outputs/stage2-root-vm-proved-integration.json').read_text())
    assert root['passed'] and root['manifest_sha256']==sha(acceptance/'manifest.json')==plan['acceptance_manifest_sha256']
    assert sha(d/'runtime.exe')==sha(acceptance/'gnu/cholesky_runtime.exe')==plan['binary']['sha256']==root['candidate_sha256']
    assert sha(P/'build/cholesky_runtime.exe')==plan['ordinary_sha256']
    assert sha(P/'build-memory/cholesky_runtime.exe')==plan['memory_sha256']
    for name,digest in plan['source_snapshot_sha256'].items():assert sha(d/name)==digest,name
    assert len(accepted['source_sha256'])==139
    for name,digest in accepted['source_sha256'].items():assert sha(d/'implementation-source'/name)==digest,name
    for name,digest in accepted['build_provenance_sha256']['gnu'].items():assert sha(d/'implementation-build'/name)==digest,name
    flags=(d/'implementation-build/CMakeFiles/cholesky_core.dir/flags.make').read_text()
    assert '-fno-fast-math' in flags and '-ffp-contract=off' in flags
    for name in ('tools/benchmark_vm_proved_policy_stage2.py','tools/windows_resource_probe.py','tools/evaluate_source.py'):
        assert sha(P/name)==plan['source_snapshot_sha256']['plan-source/'+name]
    assert (plan['records'],plan['pairs'],plan['rounds'])==(114,57,3)
    assert (plan['VM_records'],plan['VM_pairs'],plan['native_control_records'],plan['native_control_pairs'])==(90,45,24,12)
    assert plan['sole_command_variation']=='--vm-budget fixed versus proved'
    assert plan['literal_step_limit'] is None and plan['backend_override'] is None
    assert plan['threads']==4 and plan['scheduler']=='parallel'
    assert all(plan[k] for k in ('same_program_and_metadata','proof_and_decode_in_compute','preserve_all_unknown_and_negative','user_apps_untouched','host_not_claimed_idle'))
    assert not plan['new_C_execution'] and not plan['timing_based_case_selection']
    assert plan['small_batch_minimum_launch_RAM_bytes']==plan['minimum_disk_overhead_bytes']==268435456
    cases=plan['cases'];assert len(cases)==len({c['source'] for c in cases})==19
    previous=json.loads((P/'artifacts/stage2-prepared-vm-phase3/performance/run-plan.json').read_text())
    prior={c['source']:c for c in previous['cases']};assert len(prior)==13
    functional=json.loads((P/'artifacts/stage2-vm-proved-budget/runtime-integration/correctness/report.json').read_text())
    wire=json.loads((P/'artifacts/stage2-runtime-release/wire/report.json').read_text())
    assert functional['passed'] and wire['passed']
    roots=[]
    for case in cases:
        folder=d/case['source']
        assert set(case['hashes'])=={'source.c','program.meta','oracle.c','oracle.exe','input.bin','oracle.bin'}
        for name,digest in case['hashes'].items():assert sha(folder/name)==digest,(case['source'],name)
        assert header(folder/'input.bin')==header(folder/'oracle.bin')==case['input_matrix_headers']
        assert len(case['input_matrix_headers'])==case['matrices']
        assert (folder/'oracle.bin').stat().st_size==case['reference_bytes']
        optimized=re.search(r'^optimized=(.+)$',(folder/'program.meta').read_text(),re.MULTILINE)[1]
        assert optimized==case['optimized']
        if case['source'] in prior:
            old=prior[case['source']]
            assert case['kind']=='vm' and optimized=='none'
            assert case['hashes']==old['hashes'] and case['input_matrix_headers']==old['sizes']*old['whole_stream_repeats']
            assert case['matrices']==old['matrices'] and case['expected_vm_steps']==old['original_steps']
            assert case['lineage']['whole_stream_repeats']==old['whole_stream_repeats']
            assert Path(case['lineage']['prior_plan'])==P/'artifacts/stage2-prepared-vm-phase3/performance/run-plan.json'
        elif case['kind']=='vm':
            assert case['source'] in ('heldout-stride2','heldout-disjoint') and optimized=='none'
            assert case['input_matrix_headers']==[7,13,29,53] and case['lineage']['whole_stream_repeats']==1
            original=next(r for r in functional['runs'] if r['source']==case['source'] and r['family']=='dense' and r['mode']=='fixed-auto')
            source=next(r for r in functional['sources'] if r['label']==case['source'])
            for key,oldkey in [('input.bin','input_sha256'),('oracle.bin','reference_sha256'),('program.meta','metadata_sha256')]:assert case['hashes'][key]==original[oldkey]
            assert case['hashes']['source.c']==source['source_sha256'] and case['expected_vm_steps']==original['vm_steps']
            for name in ('oracle.c','oracle.exe'):assert sha(Path(source['folder'])/name)==case['hashes'][name]
        else:
            assert case['kind']=='native' and case['expected_vm_steps']==0 and case['expected_proof_status']=='not-run'
            assert optimized in ('scalar_cholesky_column_dag','rightlooking_cholesky_column_dag','rightlooking_cholesky_column_dag_fma')
            source=next(r for r in wire['sources'] if r['label']==case['lineage']['source'])
            fmt=next(r for r in source['formats'] if r['schema']==2 and r['mode']=='dag')
            original=next(r for r in fmt['runs'] if r['family']==case['lineage']['family'] and r['engine']=='tiled')
            assert case['hashes']['source.c']==source['source_sha256'] and case['hashes']['program.meta']==fmt['sha256']
            assert case['hashes']['oracle.bin']==original['sha256'] and case['block']==7
            originalfolder=P/'artifacts/stage2-runtime-release/wire'/source['label']
            for name in ('oracle.c','oracle.exe'):assert sha(originalfolder/name)==case['hashes'][name]
            assert sha(originalfolder/(case['lineage']['family']+'-input.bin'))==case['hashes']['input.bin']
        roots.append({'source':case['source'],'kind':case['kind'],'actual_shapes':case['input_matrix_headers'],'whole_reference_bytes':case['reference_bytes'],'source_sha256':case['hashes']['source.c']})
    assert sum(c['kind']=='vm' for c in cases)==15
    assert plan['expected_output_bytes_total']==sum(c['reference_bytes'] for c in cases)*6==494057592
    assert not (d/'report.json').exists() and not any(d.glob('*/round-*.bin'))
    result=dict(passed=True,reviewed_unix=time.time(),plan_sha256=sha(d/'run-plan.json'),frozen_implementation_sources=139,
        immutable_binary_sha256=sha(d/'runtime.exe'),cases=roots,records=114,pairs=57,VM_pairs=45,native_pairs=12,
        performance_started=False,ordinary_default_promoted=False,expected_output_bytes=494057592,
        scope='Same accepted binary and strict FP build, six files per originalC cohort member, full original input/reference headers and exact historical/fresh/native lineage independently verified. Alternate fixed/proved only, all unknown/negative/short-task costs retained; proof and decode included in compute, raw host load recorded. No timing or general-C/default claim.')
    (ROOT/'outputs/stage2-root-vm-proved-cost-plan.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({k:v for k,v in result.items() if k!='cases'}))


if __name__=='__main__':main()
