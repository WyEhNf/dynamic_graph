"""Root verify promoted default, complete prior rollback, and actual smoke heaps."""
import json
import time
from review_stage2_acceptance_r48 import ROOT, PROJECT, sha, read
from review_stage2_functional_plans_r44 import simulate


def main():
    evidence={}
    def load(path):
        evidence[path.relative_to(ROOT).as_posix()]=sha(path)
        return read(path)
    mp=PROJECT/'reports/final-checkpoint-batch51.json'
    manifest=load(mp)
    assert mp.read_bytes()==(PROJECT/'research/batch51/provenance.json').read_bytes()
    rbp=PROJECT/manifest['rollback_manifest_path'];rollback=load(rbp)
    assert sha(rbp)==manifest['rollback_manifest_sha']
    for row in rollback['snapshots'].values():
        assert sha(PROJECT/row['snapshot'])==row['sha']
    old=load(PROJECT/manifest['old_R48_freeze'])
    for group in ('compile_inputs','test_inputs','generation_inputs'):
        for name,digest in old[group].items():
            assert name in rollback['snapshots'],name
            assert rollback['snapshots'][name]['sha']==digest,name
    assert rollback['source_sha']==old['source_sha256']==manifest['old_default_R48_source_sha']
    assert rollback['exe_sha']==old['default_exe_sha256']==manifest['old_default_R48_exe_sha']
    checked=0
    for group in ('compile_inputs','test_inputs','generation_inputs','reports'):
        for name,digest in manifest[group].items():
            assert sha(PROJECT/name)==digest,name
            checked+=1
    for name,flags in manifest['release_flags'].items():
        assert (PROJECT/name).read_text()==flags,name
    for name,digest in [('solution/solution.cpp',manifest['source_sha256']),
        (manifest['default_exe_path'],manifest['default_exe_sha256']),
        (manifest['default_archive'],manifest['default_exe_sha256']),
        (manifest['measured_exe_path'],manifest['measured_exe_sha256']),
        (manifest['performance_baseline_exe_path'],manifest['performance_baseline_exe_sha']),
        ('reports/project27-research.tex',manifest['old_frozen_R31_tex_sha'])]:
        assert sha(PROJECT/name)==digest,name
    accepted=load(PROJECT/'research/batch51/acceptance-checkpoint.json')
    assert sha(PROJECT/'research/batch51/acceptance-checkpoint.json')==manifest['candidate_acceptance_sha']
    assert accepted==manifest['candidate_acceptance']
    assert sha(PROJECT/'research/batch51/paired-completion.json')==manifest['paired_completion_sha']
    assert sha(PROJECT/'research/batch51/paired-plan.json')==manifest['paired_plan_sha']
    assert '100% tests passed, 0 tests failed out of 14' in (PROJECT/'reports/ctest-default-batch51.txt').read_text()
    assert '#include "../solution/solution.cpp"' in (PROJECT/'tests/test_release_cut.cpp').read_text()
    assert 'solution/solution.cpp' in (PROJECT/'build/CMakeCache.txt').read_text()
    smoke=manifest['default_smoke'];ip=PROJECT/'data/default-smoke-batch51.json';op=PROJECT/'reports/default-smoke-batch51.json'
    assert sha(ip)==smoke['input_sha'] and sha(op)==smoke['report_sha']
    cases,outputs=load(ip)['cases'],load(op)['cases']
    assert len(cases)==len(outputs)==10
    candidate={family:load(PROJECT/f'reports/paired-{family}-batch51-1-after.json')['cases'] for family in ('hard','heldout')}
    passing=0
    for case,row,(family,index) in zip(cases,outputs,smoke['selection']):
        assert not any('witness' in k or 'generation' in k for k in case)
        reference=candidate[family][index]
        assert all(row[k]==reference[k] for k in ('name','pass','valid','T','peak_memory','models_equal'))
        assert case['name']==row['name']
        if row['pass']:
            assert simulate(case,row['plan'])==(row['T'],row['peak_memory'])
            passing+=1
    assert passing==smoke['passing']==7 and smoke['unresolved']==3 and smoke['actual_exit_code']==1
    assert manifest['hard_legal']==145 and len(manifest['unresolved'])==57 and len(manifest['heldout_unresolved'])==6
    assert manifest['known_witness_unresolved']==63 and manifest['total_records']==1349
    assert manifest['total_passed_according_to_expectation']==1286 and manifest['total_expected_infeasible']==1
    result=dict(passed=True,reviewed_unix=time.time(),source_sha256=manifest['source_sha256'],
        default_exe_sha256=manifest['default_exe_sha256'],measured_exe_sha256=manifest['measured_exe_sha256'],
        checked_inputs=checked,rollback_snapshots=len(rollback['snapshots']),ctest=14,actual_default_cases=10,
        independent_heap_replays=passing,explicit_unresolved=3,hard_legal=145,hard_unresolved=57,fresh48_legal=42,fresh48_unresolved=6,
        evidence=evidence,scope='Actual c491 default source/EXE/archive/Release flags/full R48 rollback and14CTest verified; seven actual smoke heaps replayed independently, three known feasible failures explicit. c491 is distinct from25ac used for all paired costs. Full1099 regressions/625 numeric candidate controls were not rerun on this default. Original open TeX intact; 63 local known feasible failures remain, no official score/universal feasibility claim.')
    (ROOT/'outputs/stage2-root-default-r51.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({k:v for k,v in result.items() if k!='evidence'}))


if __name__=='__main__':main()
