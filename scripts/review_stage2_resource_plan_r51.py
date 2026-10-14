"""Verify the predeclared complete-cost experiment before its unique window."""
import json
import time
from pathlib import Path
from review_stage2_acceptance_r48 import sha, read

ROOT = Path(__file__).resolve().parents[1]
P = ROOT/'projects/27-aicore-streams'


def main():
    path = P/'research/batch51/paired-plan.json'; plan = read(path)
    assert sha(path) == 'e59213061bc893488c7a71c3cb9fc0529afdab9a67df0aece90aa268f4e9ad9b'
    assert plan['rounds'] == 3
    for key in ('baseline_source', 'candidate_source', 'baseline_exe', 'candidate_exe'):
        assert sha(P/plan[key+'_path']) == plan[key]
    assert plan['baseline_exe'] == '54fc7e9b2257f1edcd6925126f32e969826a5d6ba93bc2f9b3e8fd5dd5538c10'
    assert plan['candidate_exe'] == '25ac71bc389e62f512d7597d40048e97b88783c21e895524cdba3311c6067742'
    assert sha(P/'research/batch48/provenance.json') == plan['baseline_provenance_sha']
    assert sha(P/'research/batch51/acceptance-checkpoint.json') == plan['acceptance_checkpoint_sha']
    for group in ('scripts', 'datasets'):
        for name, expected in plan[group].items():
            assert sha(P/name) == expected
    for name, expected in plan['candidate_flags'].items():
        assert (P/name).read_text() == expected
    assert [len(read(P/name)['cases']) for name in plan['datasets']] == [202, 48]
    assert sha(P/'solution/solution.cpp') == plan['default_unchanged_sha']
    assert sha(P/'build/aicore_bench.exe') == plan['default_exe_unchanged_sha']
    assert sha(P/'reports/project27-research.tex') == plan['old_tex_unchanged_sha']
    assert not (P/'research/batch51/paired-driver-status.json').exists()
    assert not list((P/'reports').glob('paired-*-batch51-*-before.json'))
    assert not list((P/'reports').glob('paired-*-batch51-*-after.json'))
    result = dict(passed=True, reviewed_unix=time.time(), plan_sha256=sha(path),
                  dataset_sizes=[202, 48], rounds=3, full_CLI_trials=12,
                  original_case_execution_records=1500, baseline_actual_default_sha256=plan['baseline_exe'],
                  candidate_frozen_release_sha256=plan['candidate_exe'],
                  scope='Root checked frozen hashes/Release flags, both full cohorts, alternating order and raw host CPU/RAM monitor. Every success and failure retained. No trial started at review; sole project window does not imply host idle; no default promotion authorized.')
    (ROOT/'outputs/stage2-root-resource-plan-r51.json').write_text(json.dumps(result, indent=2)+'\n')
    print(json.dumps(result))


if __name__ == '__main__':
    main()
