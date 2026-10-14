"""Root full-block replay of the fixed two-subtree diagnostic, all outlets."""
import json
import time
from pathlib import Path
from review_stage2_spine_extensions import replay, fingerprint, read_lines, sha

ROOT = Path(__file__).resolve().parents[1]
P = ROOT/'projects/18-isa-scheduler'
D = P/'experiments/r158-tree-fixed-pair-diagnostic'


def main():
    evidence = {}; replays = 0
    def read(path):
        evidence[path.relative_to(ROOT).as_posix()] = sha(path)
        return json.loads(path.read_text())
    def check(data, path):
        nonlocal replays
        record = read(path); record.setdefault('input_sha256', fingerprint(data))
        cost = replay(data, record); replays += 1
        if 'copies' in record:
            assert record['copies'] == cost
        return cost
    manifest = read(D/'evidence-provenance.json')
    for name, digest in manifest['evidence_sha256'].items():
        assert sha(P/name) == digest
    source = read(D/'source-provenance.json')
    for name, digest in source['source_sha256'].items():
        assert sha(P/name) == digest
    report = read(D/'report.json')
    cases = {fingerprint(r['input']): r['input'] for r in read_lines(D/'inputs.jsonl')}
    evidence[(D/'inputs.jsonl').relative_to(ROOT).as_posix()] = sha(D/'inputs.jsonl')
    assert len(cases) == report['input_count'] == 2 and len(report['records']) == report['count'] == 20
    baselines = {key: check(data, D/(key[:16]+'-baseline-output.json')) for key, data in cases.items()}
    improvements, outlets = [], 0
    for r in report['records']:
        key = r['input_sha256']; data = cases[key]
        assert r['outcome'] == 'verified_complete_candidates'
        before = baselines[key]
        assert before == r['before_copies']
        costs = [check(data, D/(key[:16]+f"-parent{r['parent']}-outlet{i}-output.json"))
                 for i in range(r['completed_outlets'])]
        outlets += len(costs)
        assert min(costs) == r['after_copies']
        if min(costs) < before:
            improvements.append(dict(input_sha256=key, parent=r['parent'], before_copies=before, after_copies=min(costs)))
    assert len(improvements) == 6
    assert min(r['after_copies'] for r in improvements) == 21
    result = dict(passed=True, reviewed_unix=time.time(), full_original_inputs=2, attempts=20,
                  all_completed_outlets_replayed=outlets, raw_full_block_replay_instances=replays,
                  independent_improving_parent_proposals=improvements, evidence=evidence,
                  scope='Every completed outlet replayed as the entire original64-node block with exact original identities/operands/window/COPY/register hazards. Six proposals each compare with same23COPY incumbent, best21; they are not accumulated. Reverse-serial same-context control still required to attribute gains specifically to interleaving. Fixed local diagnostic only; default/global336/official Levels unchanged.')
    (ROOT/'outputs/stage2-root-tree-pair-diagnostic.json').write_text(json.dumps(result, indent=2)+'\n')
    print(json.dumps({k:v for k,v in result.items() if k != 'evidence'}))


if __name__ == '__main__':
    main()
