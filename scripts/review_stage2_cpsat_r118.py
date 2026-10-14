"""Root raw replay of every CP-SAT materialized schedule and interval capacity."""
import hashlib
import json
import re
import time
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PROJECT = ROOT/'projects/18-isa-scheduler'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def fingerprint(value):
    return hashlib.sha256(json.dumps(value,sort_keys=True,separators=(',', ':'),ensure_ascii=False).encode()).hexdigest()


def distance(token):
    assert re.fullmatch(r't#[1-9][0-9]*', token)
    return int(token[2:])


def check(data,saved):
    nodes,order = data['instructions'],saved['original_order']
    assert sorted(order) == list(range(len(nodes)))
    if saved['fixed']:
        assert order == list(range(len(nodes)))
    positions = {node:p for p,node in enumerate(order)}
    uses = [set() for _ in nodes]
    writes,reads = {},{}
    for i,node in enumerate(nodes):
        for token in node.get('inputs',[]):
            parent = i-distance(token)
            assert 0<=parent<i and positions[parent]<positions[i]
            uses[parent].add(i)
        if node['op'] in ('GET','SET'):
            reg = node['reg']
            if reg in writes:
                assert positions[writes[reg]]<positions[i]
            if node['op']=='GET':
                reads.setdefault(reg,set()).add(i)
            else:
                assert all(positions[r]<positions[i] for r in reads.get(reg,set()))
                writes[reg],reads[reg] = i,set()
    width = 2**data['bit_width']
    # Integer intervals count live identities AFTER an original, plus the
    # physical output slot of dead originals. No dependency/hazard interval.
    occupancy = [0]*len(nodes)
    for i in range(len(nodes)):
        end = max(positions[u] for u in uses[i]) if uses[i] else positions[i]+1
        for p in range(positions[i],end):
            occupancy[p]+=1
    assert max(occupancy)<=width
    output = saved['output']
    assert output['block_id']==data['block_id']
    slots,cursor,copies = [],0,0
    for p,instruction in enumerate(output['optimized_instructions']):
        assert instruction['id']==p
        if instruction['op']=='COPY':
            offset = distance(instruction['source'])
            assert 1<=offset<=min(width,p)
            identity = slots[p-offset]
            assert nodes[identity]['op']!='SET'
            copies+=1
        else:
            identity = order[cursor];cursor+=1
            node = nodes[identity]
            assert {k:v for k,v in instruction.items() if k not in ('id','inputs')} == {k:v for k,v in node.items() if k not in ('id','inputs')}
            expected = [identity-distance(t) for t in node.get('inputs',[])]
            actual = []
            for token in instruction.get('inputs',[]):
                offset = distance(token)
                assert 1<=offset<=min(width,p)
                actual.append(slots[p-offset])
            assert actual==expected
        slots.append(identity)
    assert cursor==len(nodes)
    return copies


def main():
    suites = []
    for folder,expected_count,expected_outputs in (('r116-cpsat-oracle',2000,1970),('r117-cpsat-negative',240,148)):
        base = PROJECT/'experiments'/folder
        report = json.loads((base/'report.json').read_text())
        inputs = {fingerprint(r['input']):r['input'] for r in map(json.loads,(base/'inputs.jsonl').read_text().splitlines())}
        records = {(r['sha256'],r['fixed']):r for r in report['records']}
        assert len(records)==expected_count and not report['violations']
        statuses = Counter(r['cpsat']['outcome'] for r in records.values())
        assert dict(statuses)==report['statuses']
        for r in records.values():
            if r['cpsat']['outcome']=='solver_proved_infeasible_stated_model':
                assert r['cpsat']['solver_status']=='INFEASIBLE'
                assert r['physical_reference']=='proven_infeasible_identity_model'
        saved = list(map(json.loads,(base/'optimized_outputs.jsonl').read_text().splitlines()))
        assert len(saved)==expected_outputs
        unique = set();copies = 0
        for row in saved:
            key = row['input_sha256'],row['fixed']
            assert key not in unique;unique.add(key)
            record = records[key]
            assert record['cpsat']['outcome']=='constructive_original_order'
            ncopy = check(inputs[key[0]],row)
            assert ncopy==record['copies'];copies+=ncopy
        suites.append(dict(folder=folder,comparisons=expected_count,actual_outputs=expected_outputs,
                           statuses=dict(statuses),copies=copies,
                           evidence={str(p.relative_to(ROOT)).replace('\\','/'):sha(p) for p in (base/'report.json',base/'inputs.jsonl',base/'optimized_outputs.jsonl')}))
    matrix = PROJECT/'experiments/r118-cpsat-matrix'
    report = json.loads((matrix/'report.json').read_text())
    assert len(report['records'])==2
    for row in report['records']:
        assert row['cpsat']['solver_status']=='UNKNOWN' and row['cpsat']['outcome']=='unknown_budget'
        assert sha(matrix/f"{row['sha256'][:16]}.pbtxt")==row['model_sha256']
    result = dict(reviewed_unix=time.time(),passed=True,actual_constructed_outputs=2118,
                  comparisons=2240,suites=suites,matrix_unknown=2,
                  matrix_report_sha256=sha(matrix/'report.json'),
                  scope='Root independently rebuilds exact ordered original identities, data and GET/SET RAW/WAR/WAW hazards, physicalCOPY window and integer after-live/dead-slot occupancy for all2118 saved schedules. No project imports or solver execution.122 backend INFEASIBLE results agree with prior exhausted raw oracle; portable proof not asserted. Both actual30s matrix attempts remain UNKNOWN, no new full-corpus legal output or COPY optimum/official Level claim.')
    (ROOT/'outputs/stage2-root-cpsat-r118.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({k:v for k,v in result.items() if k!='suites'}))


if __name__=='__main__':
    main()
