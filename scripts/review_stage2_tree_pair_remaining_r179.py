"""Independent current-family COPY attribution and necessary-bound scope join."""
import json,time,statistics
from collections import Counter,defaultdict
from pathlib import Path
from review_stage2_vm_nested_runtime_plan import ROOT,sha,read

def rows(path):
    with path.open(encoding='utf-8')as f:
        for line in f:yield json.loads(line)

def main():
    p=ROOT/'projects/18-isa-scheduler'; d=p/'experiments/r179-full336-remaining-static'; r=read(d/'report.json'); manifest=read(d/'source-provenance.json')
    assert sha(d/'report.json')==manifest['report_sha256']=='67d52c60fb716096422caf5adfce274cb32cece338e648e9a4c57afc032b1f80'
    for name,digest in manifest['historical_evidence_sha256'].items():assert sha(p/name)==digest
    assert sha(p/'scripts/analyze_full336_remaining_static.py')==sha(d/'src/scripts/analyze_full336_remaining_static.py')==manifest['static_script_sha256']
    previous={x['sha256']:x for x in read(p/'experiments/r178-anytime-full336/report.json')['records']}
    bounds={x['sha256']:x for x in read(p/'experiments/r143-root-lifetime-summary/report.json')['records']}
    current={x['sha256']:x for x in r['records']};assert set(current)==set(previous)==set(bounds) and len(current)==336
    inputs={x['input']['block_id']:x['input']for x in rows(p/'experiments/r177-anytime-full336-prepared/inputs.jsonl')}
    copied_ops=defaultdict(Counter);total=0;legal=[]
    for entry in rows(p/'experiments/r178-anytime-full336/best_outputs.jsonl'):
        key=entry['input_sha256']; data=inputs[entry['output']['block_id']]; order=iter(entry['original_order']); history=[]; ops=Counter();count=0
        for ins in entry['output']['optimized_instructions']:
            if ins['op']=='COPY':
                distance=int(ins['source'][2:]);assert 1<=distance<=len(history); identity=history[-distance];assert identity is not None
                count+=1;ops[data['instructions'][identity]['op']]+=1
            else:identity=next(order);identity=None if ins['op']=='SET'else identity
            history.append(identity)
        assert next(order,None)is None
        row=current[key];old=previous[key];lower=bounds[key]['joint_lower']; assert row['actual_copies']==old['after_copies']==count and row['audited_necessary_copy_lower']==lower
        assert row['gap_upper']==count-lower>=0 and row['copy_original_opcode_counts']==dict(ops)
        assert len(data['instructions'])==row['node_count']; total+=count;legal.append(row);copied_ops[row['family']].update(ops)
    assert len(legal)==272 and total==192902
    assert Counter(x['status']for x in current.values())==r['all336_statuses']
    family_gaps={}
    for family,summary in r['families'].items():
        cases=[x for x in current.values()if x['family']==family]; valid=[x for x in cases if x['actual_copies']is not None]
        assert len(cases)==summary['count'] and Counter(x['status']for x in cases)==summary['statuses']
        assert sum(x['actual_copies']for x in valid)==summary['actual_copies']
        assert sum(x['audited_necessary_copy_lower']for x in valid)==summary['audited_necessary_copy_lower_on_legal']
        assert sum(x['gap_upper']for x in valid)==summary['potential_copy_reduction_upper_bound']
        assert dict(copied_ops[family])==summary['copy_identity_opcode_counts']
        gap=sum((x['actual_copies']/(x['node_count']+x['actual_copies'])-x['audited_necessary_copy_lower']/(x['node_count']+x['audited_necessary_copy_lower']))*100/272 for x in valid)
        assert abs(gap-summary['potential_272_mean_output_reduction_upper_bound_pp'])<1e-10;family_gaps[family]=gap
    floor=statistics.mean(x['audited_necessary_copy_lower']/(x['node_count']+x['audited_necessary_copy_lower'])*100 for x in legal)
    assert abs(floor-10.285229311249013)<1e-10 and floor>10
    ranked=sorted(family_gaps,key=lambda k:-family_gaps[k]);assert ranked==r['families_ranked_by_true_gap_upper']
    result=dict(passed=True,reviewed_unix=time.time(),report_sha256=sha(d/'report.json'),original_inputs=336,legal_subset=272,retained_statuses=r['all336_statuses'],current_COPY=total,families=21,legal_necessary_mean_output_pct=floor,top_families=[dict(family=k,reduction_upper_bound_pp=family_gaps[k],COPY=r['families'][k]['actual_copies'])for k in ranked[:6]],scope='All saved272 outputs COPY origins independently decoded, all336 status/current lower-bound joins and21family sums rechecked. Necessary lower10.285% only applies this self-generated equal-weight strict original-node/COPY-only subset; no official grade/distribution or reachable quality claim. New32window design/algorithm not accepted here.')
    (ROOT/'outputs/stage2-root-tree-pair-remaining-r179.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8');print(json.dumps(result))

if __name__=='__main__':main()
