"""Root all complete outputs and streamed physical-state path audit for R172."""
import hashlib
import json
import time
from collections import Counter
from review_stage2_tree_pair_serial_controls import ROOT,P,replay,fingerprint,distance,sha
from review_stage2_tree_anytime_diagnostics import physical_prefix

def read(p):return json.loads(p.read_text(encoding='utf-8'))

def main():
    d=P/'experiments/r172-tree-pair-anytime-84';source=read(d/'source-provenance.json')
    for name,digest in source['source_sha256'].items():assert sha(d/'src'/name)==digest
    for name,digest in source['saved_baseline_dp_evidence_sha256'].items():assert sha(P/name)==digest
    for name,digest in read(d/'evidence-provenance.json')['evidence_sha256'].items():assert sha(P/name)==digest
    old=P/'experiments/r164-tree-pair-warmstart-84'
    assert sha(d/'inputs.jsonl')==sha(old/'inputs.jsonl')==source['frozen_inputs_sha256']
    cases={fingerprint(c['input']):c for c in map(json.loads,(d/'inputs.jsonl').read_text().splitlines())}
    report=read(d/'report.json');assert len(cases)==len(report['records'])==84
    proof=read(d/'unchanged-selector-proof.json');before=(old/'src/isa_scheduler/tree_pair_refine.py').read_text();after=(d/'src/isa_scheduler/tree_pair_anytime_refine.py').read_text()
    start='        block=parse_block';end='        for parent,child_copies'
    fragment=before[before.index(start):before.index(end)];assert fragment==after[after.index(start):after.index(end)]
    assert hashlib.sha256(fragment.encode()).hexdigest()==proof['selector_fragment_exact_equal_sha256']
    assert sha(d/'src/isa_scheduler/tree_pair_anytime.py')=='dac3b71701e4085f7fb7e1ca2f829937cbb028cc8b68a773c1021ff16c1477c7'
    full=outlets=labels_total=open_total=unfinished_total=states=reopens=stale=paircount=0
    costs=[[],[],[]];improved_initial=[];improved_dp=[];regressions=[];outcomes=Counter()
    def check(data,candidate):
        nonlocal full
        cost=replay(data,dict(candidate,input_sha256=fingerprint(data)));full+=1
        if 'copies' in candidate:assert cost==candidate['copies']
        return cost
    for row in report['records']:
        key=row['sha256'];case=cases[key];data=case['input'];outcomes[row['attempt']['outcome']]+=1
        if row['before_copies'] is None:
            assert row['before_status']==row['after_status']=='proven_infeasible_under_model' and row['after_copies'] is None
            assert not list(d.glob(key[:16]+'-best-output.json'));continue
        baseline=read(d/(key[:16]+'-baseline-output.json'));best=read(d/(key[:16]+'-best-output.json'));dp=read(d/(key[:16]+'-dp-actual-output.json'))
        B,A,O=[check(data,c) for c in (baseline,best,dp)]
        assert (B,A,O)==(row['before_copies'],row['after_copies'],row['dp_actual_copies']) and A<=B
        candidates=sorted(d.glob(key[:16]+'-parent*-candidate*-output.json'));candidatecosts=[]
        for path in candidates:candidatecosts.append(check(data,read(path)))
        assert A==min([B]+candidatecosts) and len(candidates)==row['attempt']['completed_output_files'];outlets+=len(candidates)
        for bank,value in zip(costs,(B,O,A)):bank.append((len(data['instructions']),value))
        if A<B:improved_initial.append(key)
        if A<O:improved_dp.append(key)
        if A>O:regressions.append(dict(input_sha256=key,initial=B,dp=O,anytime=A))
        wrapper=row['attempt'].get('stats')
        if wrapper is None:continue
        assert wrapper['processed_states']<=20000 and wrapper['complete_outputs']==len(candidates)
        assert sum(a.get('processed_states',0) for a in wrapper['attempts'])==wrapper['processed_states']
        for attempt in wrapper['attempts']:
            if 'diagnostic_export' not in attempt:continue
            stats=attempt['stats'];paircount+=1;states+=stats['states'];reopens+=stats['reopens'];stale+=stats['stale_entries']
            assert stats['baseline_copies']==B and stats['parameters']['max_outcomes']==16
            assert stats['processed_states']==sum(stats['expanded_by_progress'].values())
            exported=attempt['diagnostic_export'];item=dict(input=data,baseline=baseline,stats=stats)
            args=[[i-distance(t) for t in r.get('inputs',[])] for i,r in enumerate(data['instructions'])]
            users=[set() for r in args]
            for v,operands in enumerate(args):
                for p in operands:users[p].add(v)
            start=stats['rank_interval'][0];sides=stats['sides'];D=set(baseline['original_order'][:start]);window=1<<data['bit_width']
            labels={};physical={};counts=Counter();cache={}
            with (P/exported['path']).open(encoding='utf-8') as stream:
                for line in stream:
                    rec=json.loads(line);counts[rec['kind']]+=1
                    if rec['kind']=='frontier_header':assert rec['actual_open_count']==stats['actual_open_count'];continue
                    if rec['kind']=='immutable_path_label':
                        version=rec['label_version'];predecessor=rec['predecessor_label'];action=rec['action']
                        if action is None:
                            offsets,g,roles,ages=physical_prefix(item,[]);last={v:g-age for v,age in zip(roles,ages)}
                        else:
                            if predecessor is None:
                                offsets,g,roles,ages=physical_prefix(item,[]);last={v:g-age for v,age in zip(roles,ages)}
                            else:
                                assert predecessor<version;prior=labels[predecessor];offsets=list(prior['prefixes']);g,last=physical[predecessor];last=dict(last)
                            side,offset=action;assert offset==offsets[side];v=sides[side][offset];offsets[side]+=1
                            operands=set(args[v]);assert operands<=set(last)
                            rotates=0
                            while last:
                                p=min(last,key=last.get);age=g-last[p]
                                if age<window or p in operands:break
                                assert age==window and rotates<window;last[p]=g;g+=1;rotates+=1
                            assert all(1<=g-last[p]<=window for p in operands)
                            g+=1;pair=tuple(offsets)
                            if pair not in cache:cache[pair]=D|set(sides[0][:offsets[0]])|set(sides[1][:offsets[1]])
                            completed=cache[pair]
                            for p in operands:
                                if not users[p]-completed:del last[p]
                            if users[v]-completed:last[v]=g-1
                        roles=stats['external_roles']+sorted(set(last)-set(stats['external_roles']));ages=[g-last[v] for v in roles]
                        assert offsets==rec['prefixes'] and g==rec['g'] and ages==rec['ages'],(key,version,offsets,rec['prefixes'],g,rec['g'],roles,ages,rec['ages'])
                        assert rec['h']==len(data['instructions'])-start-sum(offsets)
                        labels[version]=rec;physical[version]=(g,last)
                    else:
                        assert rec['kind'] in ('open','unfinished_expansion');label=labels[rec['label_version']];g,last=physical[rec['label_version']]
                        assert [rec['i'],rec['j']]==label['prefixes'] and rec['g']==g and rec['h']==label['h']
                        roles=stats['external_roles']+sorted(set(last)-set(stats['external_roles']))
                        assert rec['roles']==roles and rec['ages']==[g-last[v] for v in roles]
            assert dict(counts)==exported['record_counts'] and counts['open']==stats['actual_open_count']
            assert bool(counts['unfinished_expansion'])==(stats['unfinished_expansion'] is not None)
            labels_total+=counts['immutable_path_label'];open_total+=counts['open'];unfinished_total+=counts['unfinished_expansion']
        print(json.dumps(dict(input=key[:16],full_replays=full,labels_replayed=labels_total)),flush=True)
    assert full==675 and outlets==480 and (sum(v for _,v in costs[0]),sum(v for _,v in costs[1]),sum(v for _,v in costs[2]))==(11491,11487,11456)
    assert (len(improved_initial),len(improved_dp),len(regressions))==(32,30,1)
    assert (paircount,states,reopens,stale)==(64,509447,48760,908)
    assert dict(outcomes)==report['attempt_outcomes']
    means={name:dict(copy_output=sum(v/(n+v) for n,v in bank)/len(bank),copy_original=sum(v/n for n,v in bank)/len(bank)) for name,bank in zip(('initial','dp','anytime'),costs)}
    result=dict(passed=True,reviewed_unix=time.time(),report_sha256=sha(d/'report.json'),source_provenance_sha256=sha(d/'source-provenance.json'),
        original_inputs=84,legal_incumbents=65,model_certificates_retained=19,actual_full_output_replays=675,complete_proposals=480,
        before_copies=11491,dp_copies=11487,after_copies=11456,improved_vs_initial=32,improved_vs_dp=30,regressions_vs_dp=regressions,
        actual_pairs=paircount,processed_states=states,real_graph_reopens=reopens,real_graph_stale=stale,
        immutable_labels_replayed=labels_total,actual_open_prefixes=open_total,actual_unfinished_prefixes=unfinished_total,outcomes=dict(outcomes),success_only_means=means,
        scope='All original84 retained, all480 complete proposals and65initial/best/DP outputs independently physically replayed. All saved immutable labels/OPEN/unfinished independently advanced from original operands and physical incoming prefix. Same frozen selector and initial baseline perpair, cumulative20k/500ms and16outlets eachpair. 30betterDP/one2COPY worse retained; not universal optimum/default/full336 or official Level. Diagnostic export/IO and validation outside budget; timings shared-functional only.')
    (ROOT/'outputs/stage2-root-tree-pair-anytime-84.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result))

if __name__=='__main__':main()
