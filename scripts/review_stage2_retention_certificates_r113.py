"""Root raw-JSON closure proof checker, independent of project code."""
import hashlib
import json
import re
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DIR = ROOT/'projects/18-isa-scheduler/experiments/r110-retention-failures'


def fingerprint(value):
    return hashlib.sha256(json.dumps(value,sort_keys=True,separators=(',', ':'),ensure_ascii=False).encode()).hexdigest()


def check(data, certificate):
    nodes, width = data['instructions'], 2**data['bit_width']
    n = len(nodes)
    assert certificate['node_count']==n and certificate['window']==width
    assert certificate['kind']=='retention_order_dominance_closed_masks' and certificate['memory_order']=='hazard'
    arguments, dependencies, consumers, hazard_rows = [], [], [0]*n, []
    writes, reads = {}, {}
    for index, node in enumerate(nodes):
        assert node['op'] in ('GET','SET','ADD','MULW')
        args = set()
        for token in node.get('inputs',[]):
            assert re.fullmatch(r't#[1-9][0-9]*',token)
            parent = index-int(token[2:])
            assert 0<=parent<index and nodes[parent]['op']!='SET'
            args.add(parent);consumers[parent] |= 1<<index
        hazards = set()
        if node['op'] in ('GET','SET'):
            register = node['reg']
            if register in writes:hazards.add(writes[register])
            if node['op']=='GET':reads.setdefault(register,set()).add(index)
            else:
                hazards.update(reads.get(register,set()));reads[register]=set();writes[register]=index
        arguments.append(args);hazard_rows.append(sorted(hazards))
        dependencies.append(sum(1<<parent for parent in args|hazards))
    assert hazard_rows==certificate['original_order_dependencies']
    masks = {int(token,16) for token in certificate['completed_masks_hex']}
    assert len(masks)==len(certificate['completed_masks_hex']) and 0 in masks and (1<<n)-1 not in masks
    safe_edges = 0
    for done in masks:
        assert 0<=done<(1<<n)
        future = ((1<<n)-1)^done
        live = {index for index in range(n) if done>>index&1 and consumers[index]&future}
        assert len(live)<=width
        candidates, dead_candidates = [], []
        for index in range(n):
            if done>>index&1:
                assert dependencies[index]&done==dependencies[index]
                continue
            if dependencies[index]&done!=dependencies[index]:continue
            remaining = future^(1<<index)
            killed = {parent for parent in arguments[index] if not consumers[parent]&remaining}
            if len(live)==width and not killed:continue
            produced = bool(consumers[index]&remaining)
            if len(live-killed)+produced>width:continue
            following = done|(1<<index)
            candidates.append(following)
            if not produced:dead_candidates.append(following)
        safe_edges += len(candidates)
        # Ready dead-output steps dominate for existence only: moving such a
        # step earlier adds no live output and can only remove future uses.
        if dead_candidates:
            assert any(following in masks for following in dead_candidates)
        else:
            assert all(following in masks for following in candidates)
    return dict(nodes=n,window=width,masks=len(masks),safe_edges=safe_edges)


def main():
    inputs = {fingerprint(row['input']):row['input'] for row in map(json.loads,(DIR/'inputs.jsonl').read_text().splitlines())}
    rows = list(map(json.loads,(DIR/'retention-proofs.jsonl').read_text().splitlines()))
    assert len(rows)==9
    results = [dict(input_sha256=row['input_sha256'],**check(inputs[row['input_sha256']],row['certificate'])) for row in rows]
    rejected = 0
    for row in rows:
        altered = dict(row['certificate'],completed_masks_hex=['0x0'])
        try:check(inputs[row['input_sha256']],altered)
        except AssertionError:rejected+=1
    assert rejected==9
    result = dict(reviewed_unix=time.time(),passed=True,certificates=9,results=results,tampered_closures_rejected=9,
                  evidence={name:hashlib.sha256((DIR/name).read_bytes()).hexdigest() for name in ('inputs.jsonl','retention-proofs.jsonl','report.json')},
                  theorem='Strict original identity/COPY-only feasibility: completed mask determines future-needed data identities. Every original step must leave at mostW live identities and when alreadyW must last-consume one. Oldest-live COPY rotations construct the next legal step in at mostW-1 relays. Memory hazards constrain readiness, not temp lifetimes. Dead-output ready dominance preserves existence, not minimal COPY.',
                  scope='Root rebuilds data and GET/SET RAW/WAR/WAW from original raw JSON, checks every safe transition in all certificate masks under the independently reviewed rotation/dominance premises, initial mask included and final excluded. Imports no parser, scheduler, live set, certificate verifier or original candidate state. Removes every closure to verify rejection.',
                  limitation='Nine prior unknown synthetic inputs certified infeasible only within the strict identity model; eight matrix budget failures remain unknown. This produces no new legal output, optimality result or official Level claim.')
    (ROOT/'outputs/stage2-root-retention-closure-r113.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(dict(passed=True,certificates=9,mask_counts=[r['masks'] for r in results],tamper_rejections=9)))


if __name__=='__main__':main()
