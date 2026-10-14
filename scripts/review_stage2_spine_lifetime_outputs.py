"""Replay actual saved originals, COPY identities and register hazards."""
import json
import time
from pathlib import Path
from review_stage2_spine_age_r125 import ROOT, PROJECT, sha, fingerprint, distance, read_lines


def replay(data, saved):
    assert saved['input_sha256'] == fingerprint(data)
    rows, order = data['instructions'], saved['original_order']
    assert len({r['id'] for r in rows}) == len(rows)
    assert sorted(order) == list(range(len(rows)))
    positions = {node: position for position, node in enumerate(order)}
    writers, readers, edges = {}, {}, set()
    for index, row in enumerate(rows):
        for token in row.get('inputs', []):
            source = index - distance(token)
            assert 0 <= source < index and rows[source]['op'] != 'SET'
        if row['op'] in ('GET', 'SET'):
            register = row['reg']
            if register in writers:
                edges.add((writers[register], index))
            if row['op'] == 'GET':
                readers.setdefault(register, []).append(index)
            else:
                edges.update((reader, index) for reader in readers.get(register, []))
                readers[register], writers[register] = [], index
    assert all(positions[source] < positions[target] for source, target in edges)
    output = saved['output']
    assert output['block_id'] == data['block_id']
    slots, cursor, copies = [], 0, 0
    window = 2 ** data['bit_width']
    for instruction in output['optimized_instructions']:
        position = len(slots)
        assert instruction['id'] == position
        if instruction['op'] == 'COPY':
            assert set(instruction) == {'id', 'op', 'source'}
            offset = distance(instruction['source'])
            assert 1 <= offset <= min(window, position)
            identity = slots[position - offset]
            assert rows[identity]['op'] != 'SET'
            copies += 1
        else:
            identity = order[cursor]
            cursor += 1
            original = rows[identity]
            assert {k: v for k, v in instruction.items() if k not in ('id', 'inputs')} == {
                k: v for k, v in original.items() if k not in ('id', 'inputs')}
            actual = []
            for token in instruction.get('inputs', []):
                offset = distance(token)
                assert 1 <= offset <= min(window, position)
                actual.append(slots[position - offset])
            assert actual == [identity - distance(token) for token in original.get('inputs', [])]
        slots.append(identity)
    assert cursor == len(rows)
    return copies


def main():
    results, evidence = {}, {}
    configs = [('r138-spine-lifetime-cross', 'r125-spine-age-cross', 14, 9739, 9738),
               ('r139-spine-lifetime-heldout', 'r133-spine-potential-heldout', 15, 1124, 1120),
               ('r140-spine-lifetime-macro-cross', 'r125-spine-age-cross', 14, 9739, 9736),
               ('r141-spine-lifetime-macro-heldout', 'r133-spine-potential-heldout', 15, 1124, 1120)]
    for name, baseline_name, expected_legal, expected_before, expected_after in configs:
        directory = PROJECT / 'experiments' / name
        report = json.loads((directory / 'report.json').read_text())
        assert sha(directory / 'inputs.jsonl') == report['corpus_sha256']
        inputs = {fingerprint(r['input']): r['input'] for r in read_lines(directory / 'inputs.jsonl')}
        assert len(inputs) == len(report['records']) == 16
        assert report['before_statuses'] == report['after_statuses']
        before, after, improved, legal = 0, 0, 0, 0
        for record in report['records']:
            assert record['before_status'] == record['after_status']
            if record['after_status'] != 'verified':
                continue
            key, data = record['sha256'], inputs[record['sha256']]
            before_path = (PROJECT / 'experiments' / baseline_name / (key[:16] + '-output.json')) if baseline_name else directory / (key[:16] + '-baseline-output.json')
            after_path = directory / (key[:16] + '-output.json')
            before_cost = replay(data, json.loads(before_path.read_text()))
            after_cost = replay(data, json.loads(after_path.read_text()))
            assert before_cost == record['before_copies'] and after_cost == record['after_copies'] <= before_cost
            before += before_cost
            after += after_cost
            improved += after_cost < before_cost
            legal += 1
            for path in (before_path, after_path):
                evidence[path.relative_to(ROOT).as_posix()] = sha(path)
        assert (legal, before, after) == (expected_legal, expected_before, expected_after)
        assert improved == report['improved'] and report['recovered'] == 0
        results[name] = dict(inputs=16, legal=legal, independently_replayed_before_after=2 * legal,
                             before_copies=before, after_copies=after, improved=improved, recovered=0,
                             unchanged_statuses=report['after_statuses'])
        for filename in ('report.json', 'inputs.jsonl'):
            path = directory / filename
            evidence[path.relative_to(ROOT).as_posix()] = sha(path)
    freeze = PROJECT / 'experiments/r142-lifetime-sources'
    provenance = json.loads((freeze / 'source-provenance.json').read_text())
    for filename, expected in provenance['source_sha256'].items():
        assert sha(freeze / filename) == expected, filename
    for filename, expected in provenance['evidence_sha256'].items():
        assert sha(PROJECT / filename) == expected, filename
    result = dict(passed=True, reviewed_unix=time.time(), suites=results, evidence=evidence,
                  scope='116 before/after replay instances, some incumbents intentionally shared across rounds; '
                        'raw once-only original identities, exact ordered args, physical window/COPY and rebuilt RAW/WAR/WAW hazards. '
                        'All16 status denominators retained per suite. Improvements are isolated candidates, not default or whole336/official Level results.')
    assert sum(row['independently_replayed_before_after'] for row in results.values()) == 116
    (ROOT / 'outputs/stage2-root-spine-lifetime-outputs.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps({k: v for k, v in result.items() if k not in ('evidence', 'scope')}))


if __name__ == '__main__':
    main()
