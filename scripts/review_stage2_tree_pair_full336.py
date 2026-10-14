"""Root all original336 outcomes, full proposals and real age labels R178."""
from collections import Counter
import json
import time
from review_stage2_tree_pair_cap_ca93 import ROOT,P,replay,fingerprint,sha,read,audit_frontier

def lines(path):
    with path.open(encoding='utf-8') as stream:
        for line in stream: yield json.loads(line)

def main():
    d=P/'experiments/r178-anytime-full336'; prepared=P/'experiments/r177-anytime-full336-prepared'
    report=read(d/'report.json'); assert sha(d/'report.json')=='9f70d8709d90be3f5b7a02b0fa022a60f03781ccba19d2528bcf3d73bb98b201'
    prov=read(prepared/'source-provenance.json')
    for name,digest in prov['source_sha256'].items(): assert sha(prepared/'src'/name)==digest
    for name,digest in read(d/'evidence-provenance.json')['evidence_sha256'].items(): assert sha(P/name)==digest
    inputs=list(lines(prepared/'inputs.jsonl')); old=read(prepared/'report.json')
    records={r['sha256']:r for r in old['records'] if r['variant']=='age_portfolio'}
    baselines={r['input_sha256']:r['output'] for r in lines(prepared/'optimized_outputs.jsonl') if r['variant']=='age_portfolio'}
    orders={r['input_sha256']:r['original_order'] for r in lines(prepared/'original_orders.jsonl') if r['variant']=='age_portfolio'}
    best={r['input_sha256']:r for r in lines(d/'best_outputs.jsonl')}
    prechecks=read(d/'baseline-prechecks.json'); assert prechecks['count']==len(prechecks['records'])==272
    assert {r['sha256'] for r in prechecks['records']}==baselines.keys()==orders.keys()==best.keys()
    assert len(inputs)==len(report['records'])==336 and len(report['families'])==21 and report['resource_halt'] is None
    full=proposals=pairs=states=reopens=stale=0; before=after=improved=0; counts=Counter(); statuses=Counter(); costs=[]
    for case,row in zip(inputs,report['records']):
        data=case['input']; key=fingerprint(data); historical=records[key]
        assert key==row['sha256'] and case['family']==row['family']
        assert row['before_status']==row['after_status']==historical['status']; statuses[row['after_status']]+=1
        assert row['before_copies']==historical.get('inserted_copies')
        if key not in baselines:
            assert row['after_copies'] is None and row['actual_complete_proposals']==0 and row['stats'] is None; continue
        baseline=dict(output=baselines[key],original_order=orders[key],input_sha256=key)
        B=replay(data,baseline); A=replay(data,best[key]); full+=2
        assert (B,A)==(row['before_copies'],row['after_copies']) and A<=B
        before+=B; after+=A; improved+=A<B; costs.append((len(data['instructions']),B,A))
        files=sorted(d.glob(key[:16]+'-parent*-candidate*-output.json')); candidate_cost=[]
        for path in files:
            candidate=read(path); cost=replay(data,candidate); full+=1
            assert cost==candidate['copies']; candidate_cost.append(cost)
        assert len(files)==row['actual_complete_proposals'] and A==min([B]+candidate_cost); proposals+=len(files)
        wrapper=row['stats']
        if wrapper is not None:
            assert wrapper['processed_states']<=20000 and wrapper['complete_outputs']==len(files)
            assert wrapper['processed_states']==sum(a.get('processed_states',0) for a in wrapper['attempts'])
            for attempt in wrapper['attempts']:
                if 'diagnostic_export' not in attempt: continue
                child=attempt['stats']; exported=attempt['diagnostic_export']; pairs+=1
                states+=child['processed_states']; reopens+=child['reopens']; stale+=child['stale_entries']
                assert child['baseline_copies']==B and child['parameters']['max_outcomes']==16
                actual=audit_frontier(data,baseline,child,P/exported['path'])
                assert dict(actual)==exported['record_counts'] and sha(P/exported['path'])==exported['sha256']; counts.update(actual)
        print(json.dumps(dict(input=key[:16],full_replays=full,labels=counts['immutable_path_label'])),flush=True)
    assert statuses=={'verified':272,'proven_infeasible_under_model':47,'budget_exhausted':9,'scheduling_failure':8}
    assert (full,proposals,pairs,states,reopens,stale)==(1381,837,86,368149,32768,352)
    assert (before,after,improved)==(192929,192902,18)
    assert (counts['immutable_path_label'],counts['open'],counts['unfinished_expansion'])==(386672,18088,65)
    mean=sum(A/(n+A) for n,B,A in costs)/len(costs)
    assert mean==report['after_success_copy_output_mean'] and report['full_input_quality_mean'] is None
    result=dict(passed=True,reviewed_unix=time.time(),report_sha256=sha(d/'report.json'),original_inputs=336,
        retained_statuses=dict(statuses),before_copies=before,after_copies=after,improved_inputs=18,
        complete_proposals=837,actual_full_output_replays=1381,actual_pairs=86,processed_states=368149,
        immutable_labels_replayed=386672,actual_open_prefixes=18088,actual_unfinished_prefixes=65,
        graph_reopens=32768,graph_stale=352,after_success_copy_output_mean=mean,whole336_quality_mean=None,
        candidate_outcomes=report['candidate_outcomes'],scope='All original336 status/21family coverage retained, all272 baselines/finals+837proposals independently physically replayed; every386672savedlabel/18088OPEN/65unfinished advanced from original operands/physicalprefix. Sameinitial/core/selector/500ms20k16/96.18gains27COPY,272success-only mean13.7147%,64missing outputs leavewhole quality undefined.25searches partial, notLevel/default/universaloptimum or timing improvement.')
    (ROOT/'outputs/stage2-root-tree-pair-full336.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8'); print(json.dumps(result))

if __name__=='__main__': main()
