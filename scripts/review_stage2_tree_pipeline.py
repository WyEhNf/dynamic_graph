"""Independent original-identity replay and exhaustive local interleaving gold."""
import json
import time
from pathlib import Path
from review_stage2_spine_extensions import replay, fingerprint, read_lines, sha, distance

ROOT = Path(__file__).resolve().parents[1]
P = ROOT/'projects/18-isa-scheduler'
E = P/'experiments'


def local_gold(data):
    """Enumerate raw original DAG orders, independently emit only due COPYs."""
    rows = data['instructions']; window = 2**data['bit_width']
    deps = [set(i-distance(a) for a in row.get('inputs', [])) for i, row in enumerate(rows)]
    users = [set(j for j, required in enumerate(deps) if i in required) for i in range(len(rows))]
    best = None; total = 0

    def count(order):
        live = {}; position = copies = 0; completed = set()
        for i in order:
            consumed = {a for a in deps[i] if users[a] <= completed | {i}}
            relays = 0
            while live and position-min(live.values()) == window:
                oldest = min(live, key=live.get)
                if oldest in consumed:
                    break
                relays += 1
                if relays > window:
                    return None
                live[oldest] = position; position += 1; copies += 1
            if any(a not in live or not 1 <= position-live[a] <= window for a in deps[i]):
                return None
            for a in consumed:
                del live[a]
            if users[i]:
                live[i] = position
            position += 1; completed.add(i)
        return copies

    def visit(order, done):
        nonlocal best, total
        if len(order) == len(rows):
            total += 1; cost = count(order)
            if cost is not None and (best is None or cost < best):
                best = cost
            return
        for i in range(len(rows)):
            if i not in done and deps[i] <= done:
                visit(order+[i], done | {i})
    visit([], set())
    return total, best


def main():
    evidence = {}; suites = {}; replayed = 0
    def load(path):
        evidence[path.relative_to(ROOT).as_posix()] = sha(path)
        return json.loads(path.read_text())
    def saved(data, path):
        nonlocal replayed
        value = load(path)
        value.setdefault('input_sha256', fingerprint(data))
        cost = replay(data, value); replayed += 1
        return cost
    for name in ('r145-tree-age-sources', 'r147-tree-age-probe-sources', 'r152-tree-pipeline-final-sources'):
        d = E/name; manifest = load(d/'source-provenance.json')
        for file, digest in manifest['source_sha256'].items():
            assert sha(d/'src'/file) == digest
        suites[name] = dict(frozen_source_files=len(manifest['source_sha256']))
    for name in ('r146-tree-age-audit', 'r148-tree-age-old48', 'r149-tree-age-heldout36',
                 'r150-tree-dfs-diagnosis', 'r153-tree-pipeline-gold', 'r154-tree-pipeline-old120',
                 'r155-tree-pipeline-old48', 'r156-tree-pipeline-heldout36'):
        d = E/name
        manifest = load(d/'evidence-provenance.json')
        for file, digest in manifest['evidence_sha256'].items():
            assert sha(P/file) == digest
    for name, count in [('r146-tree-age-audit', 120), ('r154-tree-pipeline-old120', 120)]:
        d = E/name; report = load(d/'report.json')
        cases = {fingerprint(r['input']): r['input'] for r in read_lines(d/'inputs.jsonl')}
        assert len(cases) == len(report['records']) == count
        total = 0
        for r in report['records']:
            assert r['status'] == 'verified'
            cost = saved(cases[r['sha256']], d/(r['sha256'][:16]+'-output.json'))
            assert cost == r['copies']; total += cost
        suites[name] = dict(records=count, actual_outputs=count, copies=total)
    for name, n, legal, before_expected, after_expected in (
        ('r148-tree-age-old48', 48, 36, 10153, 10153),
        ('r149-tree-age-heldout36', 36, 29, 1348, 1348),
        ('r155-tree-pipeline-old48', 48, 36, 10153, 10149),
        ('r156-tree-pipeline-heldout36', 36, 29, 1348, 1342),
    ):
        d = E/name; report = load(d/'report.json')
        cases = {fingerprint(r['input']): r['input'] for r in read_lines(d/'inputs.jsonl')}
        assert len(cases) == len(report['records']) == n
        assert report['before_statuses'] == report['after_statuses']
        before = after = completed = improved = actual_legal = 0; outcomes = {}
        for r in report['records']:
            assert r['before_status'] == r['after_status']
            outcome = r['attempt']['outcome']; outcomes[outcome] = outcomes.get(outcome, 0)+1
            if r['after_status'] != 'verified':
                continue
            data = cases[r['sha256']]; key = r['sha256'][:16]
            b = saved(data, d/(key+'-baseline-output.json'))
            a = saved(data, d/(key+'-output.json'))
            assert b == r['before_copies'] and a == r['after_copies'] and a <= b
            before += b; after += a; improved += a < b; actual_legal += 1
            candidate = d/(key+'-candidate-output.json')
            if candidate.exists():
                assert saved(data, candidate) == r['attempt']['copies']; completed += 1
        assert (actual_legal, before, after) == (legal, before_expected, after_expected)
        assert improved == report['improved'] and report['recovered'] == 0
        suites[name] = dict(records=n, legal=legal, before_copies=before, after_copies=after,
                           improvements=improved, all_saved_candidates_replayed=completed,
                           retained_outcomes=outcomes, unchanged_statuses=report['after_statuses'])
    d = E/'r153-tree-pipeline-gold'; report = load(d/'report.json')
    cases = {fingerprint(data): data for data in read_lines(d/'inputs.jsonl')}
    assert len(cases) == len(report['records']) == 100
    orders = 0
    for r in report['records']:
        data = cases[r['sha256']]; key = r['sha256'][:16]
        c = saved(data, d/(key+'-output.json'))
        assert saved(data, d/(key+'-gold-output.json')) == c
        count, optimum = local_gold(data)
        assert count == r['all_interleavings'] and optimum == c == r['gold_copy_count'] == r['candidate_copy_count']
        orders += count
    assert orders == report['total_interleavings'] == 3648
    suites['r153-tree-pipeline-gold'] = dict(records=100, independent_exhaustive_orders=orders,
        scope='All topological original orders with deadline-only COPY on isolated two chains; no external roles or early COPY.')
    d = E/'r150-tree-dfs-diagnosis'; report = load(d/'report.json')
    cases = {fingerprint(r['input']): r['input'] for r in read_lines(d/'inputs.jsonl')}
    for r in report['records']:
        data = cases[r['sha256']]; key = r['sha256'][:16]
        assert saved(data, d/(key+'-baseline-output.json')) == r['baseline']['copies']
        assert saved(data, d/(key+'-DFS-output.json')) == r['DFS']['copies']
    data = load(d/'two-chains-input.json')
    assert saved(data, d/'two-chains-DFS-output.json') == 1
    assert saved(data, d/'two-chains-pipeline-output.json') == 0
    result = dict(passed=True, reviewed_unix=time.time(), actual_replay_instances=replayed,
                  suites=suites, evidence=evidence,
                  scope='Raw original identities, physical COPY/window, ordered operands and rebuilt register hazards checked for all saved legal outputs and all completed pipeline candidates, including worse candidates. Root independently enumerated all3648 local original interleavings. Budget/proof statuses retained; historical exact-global oracle not rerun, local candidate not global optimality. Default/global336 and official Levels unchanged.')
    (ROOT/'outputs/stage2-root-tree-pipeline.json').write_text(json.dumps(result, indent=2)+'\n')
    print(json.dumps({k:v for k,v in result.items() if k != 'evidence'}))


if __name__ == '__main__':
    main()
