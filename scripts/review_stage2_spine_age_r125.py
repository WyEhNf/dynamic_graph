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


def main():
    directory=PROJECT/'experiments/r125-spine-age-cross'
    report=json.loads((directory/'report.json').read_text(encoding='utf-8'))
    assert sha(directory/'inputs.jsonl')==report['corpus_sha256']
    inputs={fingerprint(r['input']):r['input'] for r in read_lines(directory/'inputs.jsonl')}
    assert len(inputs)==16 and report['before_statuses']==report['after_statuses']
    for name,expected in report['source_sha256'].items(): assert sha(PROJECT/name)==expected
    checks=[]
    for record in report['records']:
        assert record['old_status']==record['after_status']
        if record['after_status']!='verified':continue
        key=record['sha256'];data=inputs[key]
        path=directory/(key[:16]+'-output.json')
        saved=json.loads(path.read_text(encoding='utf-8'))
        assert saved['input_sha256']==key
        order=saved['original_order']
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
        assert inserted==record['after_copies']<=record['before_copies']
        checks.append(dict(input_sha256=key,copies=inserted,before=record['before_copies'],output_sha256=sha(path)))
    assert len(checks)==14 and sum(r['copies'] for r in checks)==9739
    assert sum(r['before'] for r in checks)==9755
    freeze=PROJECT/'experiments/r126-spine-age-sources'
    provenance=json.loads((freeze/'source-provenance.json').read_text(encoding='utf-8'))
    for name,expected in provenance['source_sha256'].items():assert sha(freeze/name)==expected
    for name,expected in provenance['evidence_sha256'].items():assert sha(PROJECT/name)==expected
    result=dict(passed=True,reviewed_unix=time.time(),inputs=16,independent_actual_outputs=14,
                before_copies=9755,after_copies=9739,improved=sum(r['copies']<r['before'] for r in checks),
                recovered=0,checks=checks,evidence={str((directory/n).relative_to(ROOT)).replace('\\','/'):sha(directory/n) for n in ('report.json','inputs.jsonl')},
                scope='All16 original cross-group inputs/statuses retained; all14 selected actual outputs checked by raw identity, physical COPY/window, exact ordered args and rebuilt register hazards.6 improvements total16COPY only; no default/whole336 score/official Level/optimality claim. Current and frozen R126 source/evidence SHA verified;14 actual outputs include complete original orders.')
    (ROOT/'outputs/stage2-root-spine-age-r125.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({k:v for k,v in result.items() if k not in ('checks','evidence')}))

if __name__=='__main__':main()
