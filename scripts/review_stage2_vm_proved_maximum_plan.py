"""Review frozen max plan without interpreting math gold as an actual run."""
import json
import time
from pathlib import Path
from review_stage2_vm_proved_integration import ROOT,P,sha,header


def main():
    d=P/'artifacts/stage2-vm-proved-budget/maximum-shape'
    plan=json.loads((d/'run-plan.json').read_text())
    root_accept=json.loads((ROOT/'outputs/stage2-root-vm-proved-integration.json').read_text())
    assert root_accept['passed'] and root_accept['manifest_sha256']==plan['acceptance_manifest_sha256']
    assert plan['strict_sequential'] and plan['default_failure_first'] and plan['default_must_reject']
    assert plan['minimum_free_ram_bytes']==2684354560 and plan['full_output_bytes']==800000008
    assert plan['original_steps']==plan['expected_proved_bound']==plan['effective_proved_limit']==17*10000**2+12
    assert not plan['explicit_vm_step_limit_used'] and not plan['performance_claim'] and not plan['large_SHA_verified']
    for name,digest in plan['script_sha256'].items():
        assert sha(d/name)==sha(P/'tools'/name)==digest
    for mode,row in plan['binaries'].items():
        assert sha(Path(row['path']))==row['sha256']
        assert row['sha256']==root_accept['portable_sha256' if mode=='portableauto' else 'candidate_sha256']
    old=Path(plan['input']).parent
    for name,digest in plan['historical_sha256'].items():
        if name in ('input.bin','oracle.bin'):
            assert header(old/name)==[10000] and (old/name).stat().st_size==800000008
        else:assert sha(old/name)==digest
    assert not (d/'report.json').exists()
    result=dict(passed=True,reviewed_unix=time.time(),plan_sha256=sha(d/'run-plan.json'),
        accepted_runtime_sha256=root_accept['manifest_sha256'],minimum_free_ram_bytes=2684354560,
        executable_cases=4,full_success_cases=3,expected_actual_steps=1700000012,
        scope='Frozen runner/host helpers and scoped integration hashes verified; historical originalC small source/Metadata/oracle/harness and large headers/sizes verified. Large hashes to be verified by actual launch; N10000 proof mathgold does not claim execution. Plan fixeddefault refusal then three opt-in raised-budget whole outputs, each freshRAM gate/sequential and fullC comparison; no performance or ordinarydefault promotion.')
    (ROOT/'outputs/stage2-root-vm-proved-maximum-plan.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result))


if __name__=='__main__':main()
