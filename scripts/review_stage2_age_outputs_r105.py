"""Root original-identity replay for saved age-cache outputs; no scheduler imports."""
import hashlib
import json
import re
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DIR = ROOT / 'projects/18-isa-scheduler/experiments/r105-age-budget250'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def fingerprint(data):
    return hashlib.sha256(json.dumps(data,sort_keys=True,separators=(',', ':'),
                                    ensure_ascii=False).encode()).hexdigest()


def lines(name):
    return [json.loads(s) for s in (DIR/name).read_text(encoding='utf-8').splitlines()]


def distance(token):
    assert isinstance(token,str) and re.fullmatch(r't#[1-9][0-9]*',token)
    return int(token[2:])


inputs = {fingerprint(r['input']):r['input'] for r in lines('inputs.jsonl')}
orders = {(r['input_sha256'],r['variant']):r['original_order'] for r in lines('original_orders.jsonl')}
report = json.loads((DIR/'report.json').read_text(encoding='utf-8'))
assert sha(DIR/'inputs.jsonl') == report['corpus_sha256']
assert sha(DIR/'optimized_outputs.jsonl') == report['optimized_outputs_sha256']
assert sha(DIR/'original_orders.jsonl') == report['original_orders_sha256']
records = {(r['sha256'],r['variant']):r for r in report['records']}
checks = []
for saved in lines('optimized_outputs.jsonl'):
    if saved['variant'] != 'age_fast':
        continue
    key = saved['input_sha256'],saved['variant']
    data,order = inputs[key[0]],orders[key]
    original = data['instructions']
    assert sorted(order) == list(range(len(original)))
    registers = {op:[r['reg'] for r in original if r['op']==op] for op in ('GET','SET')}
    assert all(len(v)==len(set(v)) for v in registers.values())
    assert not set(registers['GET']) & set(registers['SET'])
    values, cursor, copies = [], 0, 0
    width = 2**data['bit_width']
    for instruction in saved['output']['optimized_instructions']:
        position = len(values)
        if instruction['op'] == 'COPY':
            d = distance(instruction['source'])
            assert 1 <= d <= min(width,position)
            source = values[position-d]
            assert original[source]['op'] != 'SET'
            values.append(source)
            copies += 1
            continue
        index = order[cursor]
        cursor += 1
        node = original[index]
        assert instruction['op'] == node['op']
        assert instruction.get('reg') == node.get('reg')
        expected = [index-distance(t) for t in node.get('inputs',[])]
        actual = []
        for token in instruction.get('inputs',[]):
            d = distance(token)
            assert 1 <= d <= min(width,position)
            actual.append(values[position-d])
        assert actual == expected
        values.append(index)
    assert cursor == len(original)
    record = records[key]
    assert record['status'] == 'verified' and record['inserted_copies'] == copies
    checks.append(dict(input_sha256=key[0],original_nodes=len(original),copies=copies,window=width))
assert len(checks) == 12 and sum(r['copies'] for r in checks) == 2876
result = dict(reviewed_unix=time.time(),passed=True,verified=12,checks=checks,
              method='Root independently parses raw t# distances and replays exact original identities through every physical output slot. Checks a permutation of all original nodes, exact ordered original operands/registers, pure disjoint memory names, output window and COPY identity. Imports neither project parser, cache, scheduler nor verifier.',
              guarantee='For these pure blocks, exact original identity/ordered operands and unique disjoint GET/SET preserve values for all initial registers under the same deterministic primitive semantics. This does not certify arbitrary hazard-bearing programs or optimal COPY counts.',
              limitation='Only12 supported successful original dot cases; four restricted-matcher failures remain in the full16-input source report. New shape/order/argument holdouts and full336 portfolio validation still pending. Timing was a functional batch, not an isolated causal speed measurement.',
              evidence={name:sha(DIR/name) for name in ('report.json','inputs.jsonl','optimized_outputs.jsonl','original_orders.jsonl')})
destination = ROOT/'outputs/stage2-root-age-replay-r105.json'
destination.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(json.dumps(dict(passed=True,verified=12,copies=2876,large_case=[r for r in checks if r['original_nodes']==4095])))
