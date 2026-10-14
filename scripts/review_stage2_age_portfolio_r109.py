"""Independent raw identity and register-hazard audit; imports no project code."""
import hashlib
import json
import re
import time
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PROJECT = ROOT / 'projects/18-isa-scheduler'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def fingerprint(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':'),
                                    ensure_ascii=False).encode()).hexdigest()


def distance(token):
    assert isinstance(token, str) and re.fullmatch(r't#[1-9][0-9]*', token)
    return int(token[2:])


def read_lines(path):
    return [json.loads(line) for line in path.read_text(encoding='utf-8').splitlines()]


def review(folder, count, copies):
    directory = PROJECT / 'experiments' / folder
    report = json.loads((directory / 'report.json').read_text(encoding='utf-8'))
    for name, field in [('inputs.jsonl', 'corpus_sha256'),
                        ('optimized_outputs.jsonl', 'optimized_outputs_sha256'),
                        ('original_orders.jsonl', 'original_orders_sha256')]:
        assert sha(directory / name) == report[field]
    input_rows = read_lines(directory / 'inputs.jsonl')
    inputs = {fingerprint(row['input']): row['input'] for row in input_rows}
    assert len(inputs) == len(input_rows) == report['case_count']
    orders = {(row['input_sha256'], row['variant']): row['original_order']
              for row in read_lines(directory / 'original_orders.jsonl')}
    records = {(row['sha256'], row['variant']): row for row in report['records']}
    statuses = {}
    for variant in ('phase_r102', 'age_portfolio'):
        rows = [r for r in report['records'] if r['variant'] == variant]
        statuses[variant] = Counter(row['status'] for row in rows)
        assert dict(statuses[variant]) == report['summary'][variant]['statuses']
    assert statuses['phase_r102'] == statuses['age_portfolio']
    improved = equal = regressed = 0
    for key in inputs:
        before, after = (records[key, variant] for variant in ('phase_r102', 'age_portfolio'))
        assert before['status'] == after['status']
        if after['status'] == 'verified':
            change = after['inserted_copies'] - before['inserted_copies']
            improved += change < 0
            equal += change == 0
            regressed += change > 0
    assert regressed == 0
    checks = []
    for saved in read_lines(directory / 'optimized_outputs.jsonl'):
        key = saved['input_sha256'], saved['variant']
        assert key[1] == 'age_portfolio'
        data, order = inputs[key[0]], orders[key]
        original = data['instructions']
        assert len({node['id'] for node in original}) == len(original)
        assert sorted(order) == list(range(len(original)))
        original_positions = {node: position for position, node in enumerate(order)}
        last_write, reads = {}, {}
        hazard_edges = set()
        for index, node in enumerate(original):
            for token in node.get('inputs', []):
                parent = index - distance(token)
                assert 0 <= parent < index and original[parent]['op'] != 'SET'
            if node['op'] == 'GET':
                register = node['reg']
                if register in last_write:
                    hazard_edges.add((last_write[register], index))
                reads.setdefault(register, []).append(index)
            elif node['op'] == 'SET':
                register = node['reg']
                if register in last_write:
                    hazard_edges.add((last_write[register], index))
                hazard_edges.update((reader, index) for reader in reads.get(register, []))
                last_write[register], reads[register] = index, []
        assert all(original_positions[a] < original_positions[b] for a, b in hazard_edges)
        output = saved['output']
        assert output['block_id'] == data['block_id']
        slots, cursor, inserted = [], 0, 0
        width = 2 ** data['bit_width']
        for instruction in output['optimized_instructions']:
            position = len(slots)
            assert instruction['id'] == position
            if instruction['op'] == 'COPY':
                assert set(instruction) == {'id', 'op', 'source'}
                offset = distance(instruction['source'])
                assert 1 <= offset <= min(width, position)
                identity = slots[position - offset]
                assert original[identity]['op'] != 'SET'
                slots.append(identity)
                inserted += 1
                continue
            identity = order[cursor]
            cursor += 1
            node = original[identity]
            assert {k: v for k, v in instruction.items() if k not in ('id', 'inputs')} == {
                k: v for k, v in node.items() if k not in ('id', 'inputs')}
            expected = [identity - distance(token) for token in node.get('inputs', [])]
            actual = []
            for token in instruction.get('inputs', []):
                offset = distance(token)
                assert 1 <= offset <= min(width, position)
                actual.append(slots[position - offset])
            assert actual == expected
            slots.append(identity)
        assert cursor == len(original)
        record = records[key]
        assert record['status'] == 'verified' and record['inserted_copies'] == inserted
        checks.append(dict(input_sha256=key[0], original_nodes=len(original),
                           copies=inserted, window=width, hazard_edges=len(hazard_edges)))
    assert len(checks) == count and sum(row['copies'] for row in checks) == copies
    return dict(folder=folder, passed=True, all_inputs=len(inputs), verified=count,
                copies=copies, improved=improved, equal=equal, regressed=regressed,
                statuses=dict(statuses['age_portfolio']),
                hazard_bearing_verified=sum(row['hazard_edges'] > 0 for row in checks),
                checks=checks, evidence={name: sha(directory / name) for name in (
                    'report.json', 'inputs.jsonl', 'optimized_outputs.jsonl', 'original_orders.jsonl')})


def main():
    reviews = [review('r107-age-portfolio-336', 272, 192929),
               review('r108-age-portfolio-heldout', 62, 15538)]
    provenance_path = PROJECT / 'experiments/r109-age-validation/source-provenance.json'
    provenance = json.loads(provenance_path.read_text(encoding='utf-8'))
    for relative, expected in provenance['core_manifest'].items():
        frozen = PROJECT / provenance['snapshot'] / Path(relative).name
        assert sha(frozen) == expected
    for relative, expected in provenance['evidence_sha256'].items():
        assert sha(PROJECT / relative) == expected
    result = dict(reviewed_unix=time.time(), passed=True, reviews=reviews,
                  verified=334, frozen_core_sha256=provenance['core_aggregate_sha256'],
                  source_provenance_sha256=sha(provenance_path),
                  method='No project imports: raw original-index identities through all physical output slots; complete original-node permutation, exact ordered operands and registers; original RAW/WAR/WAW edges rebuilt from GET/SET register accesses and checked against every output order. Verifies all statuses and paired COPY changes including failures; hashes every frozen core source and evidence artifact.',
                  guarantee='For these saved outputs and deterministic primitive semantics, identity induction plus preserved register hazards proves value and memory-access semantics for every initial register state. This does not prove arbitrary input acceptance, optimal COPY counts, or any official level.',
                  limitation='Synthetic complete408-input corpus retains47 model-scoped certificates and27 budget/heuristic failures across the two batches. No official evaluation distribution or denominator is available; successful-subset percentages are not level acceptance.')
    destination = ROOT / 'outputs/stage2-root-age-portfolio-review-r109.json'
    destination.write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({k: result[k] for k in ('passed', 'verified', 'frozen_core_sha256')}))
    for review_result in reviews:
        print(json.dumps({k: v for k, v in review_result.items() if k not in ('checks', 'evidence')}))


if __name__ == '__main__':
    main()
