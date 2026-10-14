"""Independent bounded-buffer comparison of actual raised-budget max outputs."""
import json
import time
from pathlib import Path
from review_stage2_vm_proved_integration import ROOT,P,sha,header,compare_files


def main():
    d=P/'artifacts/stage2-vm-proved-budget/maximum-shape'
    pp,rp=d/'run-plan.json',d/'report.json'
    plan,report=map(lambda p:json.loads(p.read_text()),(pp,rp))
    assert report['passed'] and report['status']=='complete' and report['large_SHA_verified']
    assert sha(pp)==report['plan_sha256']
    assert not report['ordinary_fixed_default_maximum_passed'] and report['optin_proved_policy_maximum_passed']
    assert not report['C_reference_reexecuted'] and not report['performance_claim']
    old=Path(plan['input']).parent
    for name,digest in plan['historical_sha256'].items():assert sha(old/name)==digest,name
    for name,digest in plan['script_sha256'].items():assert sha(d/name)==digest
    for record in plan['binaries'].values():assert sha(Path(record['path']))==record['sha256']
    assert len(report['runs'])==3 and [r['backend'] for r in report['runs']]==plan['backend_order']
    files=[Path(plan['original_C_reference'])]+[Path(r['output']) for r in report['runs']]
    size,hashes=compare_files(files)
    assert size==800000008 and len(set(hashes))==1 and hashes[0]==plan['historical_sha256']['oracle.bin']
    assert all(header(path)==[10000] for path in files)
    resources=[]
    for row in report['runs']:
        command=row['command'];mode=row['backend']
        assert sha(Path(command[0]))==plan['binaries'][mode]['sha256']
        assert '--vm-step-limit' not in command and command[command.index('--vm-budget')+1]=='proved'
        actual=json.loads((d/(mode+'.stdout')).read_text())
        assert (d/(mode+'.stderr')).read_bytes()==b''
        for key,value in actual.items():assert row[key]==value,key
        assert row['actual_exit_code']==0 and row['bytes']==size and row['sha256']==hashes[0]
        assert row['vm_steps']==row['vm_budget_bound_peak']==row['vm_effective_step_limit_max']==1700000012
        assert row['vm_budget_proved_matrices']==1 and row['vm_budget_unknown_matrices']==0
        assert row['vm_backend']=={'GNUauto':'decoded-threaded','GNUdecoded':'decoded','portableauto':'decoded-fallback'}[mode]
        assert row['selected_engine']=='vm' and row['vm_budget_mode']=='proved'
        assert 0<=row['vm_budget_proof_ms']<=row['compute_ms'] and row['vm_budget_work']<=250000
        assert row['available_ram_before_bytes']>=2684354560 and row['resource_samples']>0
        assert row['process_cpu_time_ms']==row['process_kernel_cpu_ms']+row['process_user_cpu_ms']
        resources.append({k:row[k] for k in ('backend','vm_backend','vm_steps','vm_budget_bound_peak','vm_effective_step_limit_max',
            'vm_budget_work','vm_budget_proof_ms','compute_ms','available_ram_before_bytes','process_peak_working_set_bytes',
            'process_peak_commit_bytes','host_available_ram_min_bytes','host_busy_percent_during_process')})
    assert all(r['passed'] and r['available_ram_bytes']>=2684354560 and r['free_F_bytes']>=r['minimum_remaining_disk_bytes'] for r in report['resource_gates'])
    negative=report['default_failure']
    assert negative['actual_exit_code']==1 and negative['stderr']=='error: VM instruction limit exceeded\n' and negative['stdout']==''
    assert (d/'fixed-default.stdout').read_bytes()==b''
    assert (d/'fixed-default.stderr').read_text()==negative['stderr']
    assert negative['effective_fixed_limit']==1000000000 and '--vm-budget' not in negative['command']
    assert not (d/'fixed-default-rejected.bin').exists() and not (d/'fixed-default-rejected.bin.partial').exists()
    fp=d/'final-evidence/manifest.json'
    final=json.loads(fp.read_text())
    assert final['passed'] and final['actual_outer_exit_code']==0 and final['tool_session']==10759
    assert final['plan_sha256']==sha(pp) and final['report_sha256']==sha(rp)
    for name,digest in final['source_sha256'].items():assert sha(fp.parent/'source'/name)==digest
    for name,digest in final['evidence_sha256'].items():assert sha(fp.parent/name)==digest
    for frozen,actual in zip(final['actual_runs'],report['runs']):
        for key,value in frozen.items():assert actual[key]==value,key
    result=dict(passed=True,reviewed_unix=time.time(),plan_sha256=sha(pp),actual_report_sha256=sha(rp),
        n=10000,actual_original_C_rerun=False,complete_files_stream_compared=4,full_bytes_per_file=size,
        automatic_proved_backends=resources,actual_explicit_limit_used=False,fixed_default_budget_passed=False,
        optin_proved_budget_passed=True,final_freeze_sha256=sha(fp),final_frozen_sources=len(final['source_sha256']),
        evidence={p.relative_to(ROOT).as_posix():sha(p) for p in (pp,rp,fp)},
        scope='Root streamed full frozen originalC plus three actual800000008byte output files; SHA/header and source/Metadata/oracle/harness/exe rechecked. Each backend executed original1700000012steps with exactly derived1700000012 effectivecap, no explicitlimit. Fresh>=2.5GiB gates/negative fixed1e9 refusal/hostresources and actualstdout verified. OriginalC reused, not rerun. This proves one N10000 copy source under opt-in policy, not arbitraryC/default installation/paired performance.')
    (ROOT/'outputs/stage2-root-vm-proved-maximum.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({k:v for k,v in result.items() if k not in ('evidence','automatic_proved_backends')}))


if __name__=='__main__':main()
