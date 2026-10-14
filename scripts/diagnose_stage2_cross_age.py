"""Read physical COPY identity traces for the original large cross-group gap."""
import json
from collections import Counter
from pathlib import Path
from review_stage2_age_portfolio_r109 import fingerprint, distance, sha

ROOT = Path(__file__).resolve().parents[1]
STAGE = ROOT/'projects/18-isa-scheduler/experiments/r107-age-portfolio-336'


def main():
    rows = [json.loads(line) for line in (STAGE/'inputs.jsonl').read_text(encoding='utf-8').splitlines()]
    chosen = next(row for row in rows if row['family']=='cross_group_shared' and
                  len(row['input']['instructions'])==1024 and row['input']['bit_width']==3)
    original = chosen['input']['instructions']
    key = fingerprint(chosen['input'])
    saved = next(json.loads(line) for line in (STAGE/'optimized_outputs.jsonl').read_text(encoding='utf-8').splitlines()
                 if json.loads(line)['input_sha256']==key and json.loads(line)['variant']=='age_portfolio')
    order = next(json.loads(line)['original_order'] for line in (STAGE/'original_orders.jsonl').read_text(encoding='utf-8').splitlines()
                 if json.loads(line)['input_sha256']==key and json.loads(line)['variant']=='age_portfolio')
    counts, consumer_counts, origins, slots = Counter(),Counter(),{},[]
    for index,node in enumerate(original):
        consumer_counts.update(set(index-distance(token) for token in node.get('inputs',[])))
    cursor = 0
    for node in saved['output']['optimized_instructions']:
        if node['op']=='COPY':
            identity=slots[len(slots)-distance(node['source'])]
            counts[identity]+=1
        else:
            identity=order[cursor];cursor+=1;origins[identity]=len(slots)
        slots.append(identity)
    assert cursor==len(original) and sum(counts.values())==1573
    result=dict(input_sha256=key, original_nodes=1024, window=8, actual_copies=1573,
                copies_by_op=dict(Counter({op:sum(count for identity,count in counts.items() if original[identity]['op']==op)
                                          for op in ('GET','ADD','MULW')})),
                copies_by_identity=[dict(original_index=identity,op=original[identity]['op'],reg=original[identity].get('reg'),
                                         copies=count,direct_users=consumer_counts[identity],birth_output_slot=origins[identity])
                                    for identity,count in counts.most_common()],
                evidence={name:sha(STAGE/name) for name in ('inputs.jsonl','optimized_outputs.jsonl','original_orders.jsonl')},
                scope='Static attribution through actual physical output slots and original identity order. No new solver output, lowerbound, optimum, or official Level claim.')
    (ROOT/'outputs/stage2-root-cross-age-gap.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({k:v for k,v in result.items() if k not in ('evidence','copies_by_identity')}))
    print(json.dumps(result['copies_by_identity'][:12]))


if __name__=='__main__':main()
