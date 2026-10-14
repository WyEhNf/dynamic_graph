"""Independent full-original deadline emitter and both-concat R161 audit."""
import json
import time
from review_stage2_spine_extensions import ROOT, replay, fingerprint, read_lines, sha, distance

P = ROOT/'projects/18-isa-scheduler'
D = P/'experiments/r161-tree-pair-serial-controls'
B = P/'experiments/r158-tree-fixed-pair-diagnostic'


def emit(data, order):
    original = data['instructions']
    operands = [[i-distance(t) for t in r.get('inputs', [])] for i, r in enumerate(original)]
    future = [set() for _ in original]
    for consumer, args in enumerate(operands):
        for producer in args:
            future[producer].add(consumer)
    window = 1 << data['bit_width']
    emitted, last, done = [], {}, set()
    for index in order:
        assert set(operands[index]) <= done
        relays = 0
        while last:
            producer = min(last, key=last.get)
            offset = len(emitted)-last[producer]
            if offset < window or producer in operands[index]:
                break
            if offset > window or relays >= window:
                return None
            emitted.append(dict(id=len(emitted), op='COPY', source=f't#{offset}'))
            last[producer] = len(emitted)-1
            relays += 1
        row = {k:v for k,v in original[index].items() if k not in ('id', 'inputs')}
        row['id'] = len(emitted)
        if operands[index]:
            offsets = [len(emitted)-last[p] for p in operands[index]]
            assert all(1 <= x <= window for x in offsets)
            row['inputs'] = [f't#{x}' for x in offsets]
        emitted.append(row)
        done.add(index)
        for producer in set(operands[index]):
            if not (future[producer]-done):
                del last[producer]
        if future[index]-done:
            last[index] = len(emitted)-1
    return dict(block_id=data['block_id'], optimized_instructions=emitted)


def main():
    evidence = {}
    def read(path):
        evidence[path.relative_to(ROOT).as_posix()] = sha(path)
        return json.loads(path.read_text(encoding='utf-8'))
    for manifest_name in ('source-provenance.json', 'evidence-provenance.json'):
        manifest = read(D/manifest_name)
        for name, digest in manifest.get('evidence_sha256', {}).items():
            assert sha(P/name) == digest
        for name, digest in manifest.get('source_sha256', {}).items():
            assert sha(D/'src'/name) == digest
    inputs = {fingerprint(r['input']):r['input'] for r in read_lines(B/'inputs.jsonl')}
    evidence[(B/'inputs.jsonl').relative_to(ROOT).as_posix()] = sha(B/'inputs.jsonl')
    diagnostic = {(r['input_sha256'],r['parent']):r for r in read(B/'report.json')['records']}
    report = read(D/'report.json')
    assert report['count'] == len(report['records']) == 20
    baselines = {}
    for key, data in inputs.items():
        baseline = read(B/(key[:16]+'-baseline-output.json'))
        rebuilt = emit(data, baseline['original_order'])
        assert rebuilt['block_id'] == baseline['output']['block_id']
        assert rebuilt['optimized_instructions'] == baseline['output']['optimized_instructions']
        replay(data, baseline)
        baselines[key] = baseline
    legal, failed, strict = 0, 0, []
    for row in report['records']:
        key, parent = row['input_sha256'], row['parent']
        data, baseline = inputs[key], baselines[key]
        source = diagnostic[key,parent]
        start, stop = source['stats']['rank_interval']
        a,b = source['stats']['sides']
        costs = []
        for side, pair in enumerate(((a,b),(b,a))):
            order = baseline['original_order'][:start] + pair[0] + pair[1] + [parent] + baseline['original_order'][stop+1:]
            result = emit(data, order)
            stem = key[:16]+f'-parent{parent}-serial{side}'
            if result is None:
                record = read(D/(stem+'-failure.json'))
                assert record['original_order'] == order
                assert record['outcome'] == 'restricted_fixed_order_failure'
                failed += 1; costs.append(None)
            else:
                record = read(D/(stem+'-output.json'))
                assert record['original_order'] == order and record['output'] == result
                record['input_sha256'] = key
                cost = replay(data, record)
                assert cost == record['copies']
                legal += 1; costs.append(cost)
        assert costs == [row['serialAB_copies'],row['serialBA_copies']]
        valid = [c for c in costs if c is not None]
        assert row['both_serial_completed'] == (len(valid)==2)
        assert row['fixed_pair_copies'] == source['after_copies']
        assert row['gain_beyond_best_serial'] == min(valid)-source['after_copies']
        if len(valid)==2 and min(valid)>source['after_copies']:
            strict.append(dict(input_sha256=key,parent=parent,serial_copies=costs,interleaved_copies=source['after_copies']))
    assert (legal,failed,len(strict)) == (33,7,4)
    assert report['positive_beyond_both_serial'] == 4 and report['restricted_fixed_order_failures'] == 7
    result = dict(passed=True, reviewed_unix=time.time(), controls=40,
        independently_reconstructed_baselines=2, independently_replayed_full_outputs=legal,
        independently_reproduced_restricted_failures=failed, strictly_better_than_both_serial=strict,
        evidence=evidence, scope='Both concatenations on unchanged full64-node originals and same prefix/suffix. Independent set-based emitter reconstructed exact physical rows and seven restricted deadline failures; these failures do not prove graph infeasibility. Four interleaved proposals strictly beat both completed serial controls, including parent59 28/23 versus21. Proposals are separate, not additive; no global optimality/officialLevel claim.')
    (ROOT/'outputs/stage2-root-tree-pair-serial-controls.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({k:v for k,v in result.items() if k!='evidence'}))


if __name__=='__main__':
    main()
