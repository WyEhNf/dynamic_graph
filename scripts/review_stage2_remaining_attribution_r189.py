"""Independent attribution of accepted immutable R187 outputs; no scheduling."""
import gzip,hashlib,json
from collections import Counter,defaultdict
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];P=ROOT/'projects/18-isa-scheduler'
def read(p):return json.loads(Path(p).read_text(encoding='utf-8'))
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def rows(p):
    with gzip.open(p,'rt',encoding='utf-8') as f:
        for line in f:yield json.loads(line)
def main():
    d=P/'experiments/r189-general-region-remaining-static';report=read(d/'report.json')
    assert sha(d/'report.json')=='8c7a7700a17fd7dd1bb4909e8febce2ef4a721cebda360bda0fc99250ca4417c'
    old=read(P/'experiments/r187-general-region-full336/report.json');boundpath=P/'experiments/r143-root-lifetime-summary/report.json'
    assert report['source_report_sha256']==sha(P/'experiments/r187-general-region-full336/report.json')
    assert report['source_bound_sha256']==sha(boundpath)
    oldmap={r['sha256']:r for r in old['records']};lower={r['sha256']:r for r in read(boundpath)['records']};newmap={r['sha256']:r for r in report['records']}
    prepared=P/'experiments/r186-general-region-full336-prepared';g=Path('G:/Hackathon-stage2-artifacts/project18/r187-general-region-full336')
    fam=defaultdict(lambda:dict(count=0,statuses=Counter(),search_outcomes=Counter(),copies=0,necessary_lower=0,copy_origins=Counter(),completed_proposals=0,complete_proposal_comparison=Counter(),gap_upper_pp=0.))
    proposals=Counter();legal=0;copies=0
    for case in rows(prepared/'inputs.jsonl.gz'):
        data=case['input'];key=hashlib.sha256(json.dumps(data,sort_keys=True,separators=(',',':'),ensure_ascii=False).encode()).hexdigest();s=oldmap[key];n=newmap[key];b=lower[key];f=fam[case['family']]
        assert n['family']==case['family'] and n['N']==len(data['instructions']) and n['W']==1<<data['bit_width']
        assert n['source_status']==s['source_status'] and n['candidate_outcome']==s['candidate_outcome'] and n['copies']==s['after_copies'] and n['necessary_lower']==b['joint_lower']
        f['count']+=1;f['statuses'][s['source_status']]+=1;f['search_outcomes'][s['candidate_outcome']]+=1;f['completed_proposals']+=s['actual_complete_outputs']
        if s['after_copies'] is None:continue
        legal+=1;file=g/(key[:16]+'-best.json.gz')
        if not file.exists():file=prepared/'initials'/(key+'.json.gz')
        saved=next(rows(file));order=saved['original_order'];birth={i:rank for rank,i in enumerate(order)};history=[];cursor=0;counts=Counter()
        for emitted in saved['output']['optimized_instructions']:
            if emitted['op']=='COPY':
                identity=history[-int(emitted['source'][2:])];assert identity is not None;counts[identity]+=1
            else:identity=order[cursor] if emitted['op']!='SET' else None;cursor+=1
            history.append(identity)
        assert cursor==len(order) and sum(counts.values())==s['after_copies'];origins=Counter()
        for i,c in counts.items():origins[data['instructions'][i]['op']]+=c
        assert n['copy_origins']==dict(origins)
        users=defaultdict(set)
        for i,instruction in enumerate(data['instructions']):
            for t in instruction.get('inputs',[]):users[i-int(t[2:])].add(i)
        expected=[]
        for i,c in counts.most_common(8):
            ranks=[birth[u] for u in users[i]]
            expected.append(dict(id=i,op=data['instructions'][i]['op'],copies=c,birth_original_rank=birth[i],direct_consumer_count=len(ranks),first_consumer_rank=min(ranks) if ranks else None,last_consumer_rank=max(ranks) if ranks else None,birth_to_first_use_original_gap=min(ranks)-birth[i] if ranks else None))
        assert n['copied_identities']==expected
        count=s['after_copies'];lo=b['joint_lower'];f['copies']+=count;copies+=count;f['necessary_lower']+=lo;f['copy_origins'].update(origins);f['gap_upper_pp']+=(count/(len(order)+count)-lo/(len(order)+lo))*100/272
        if s['actual_complete_outputs']:
            seen=0
            for proposal in rows(Path(s['complete_absolute_path'])):
                value=proposal['candidate']['copies'];label='better_initial' if value<s['before_copies'] else 'same_initial' if value==s['before_copies'] else 'worse_initial'
                f['complete_proposal_comparison'][label]+=1;proposals[label]+=1;seen+=1
            assert seen==s['actual_complete_outputs']
    assert len(oldmap)==len(newmap)==336 and legal==272 and copies==192859
    for name,values in fam.items():
        saved=report['families'][name]
        for k,v in values.items():
            if isinstance(v,Counter):v=dict(v)
            if isinstance(v,float):assert abs(v-saved[k])<1e-12
            else:assert v==saved[k],(name,k)
    assert dict(proposals)==dict(better_initial=98,same_initial=2893,worse_initial=1689)
    result=dict(passed=True,scope='Read-only independent original-identity COPY attribution and direct-use rank joins; accepted whole-output semantics came from R187 root audit. No solver or oracle called.',report_sha256=sha(d/'report.json'),inputs=336,families=21,legal=272,missing_outputs=64,COPY=192859,full_proposals=4680,proposal_comparison=dict(proposals),family_summaries={k:{q:v for q,v in f.items() if q in ('copies','necessary_lower','gap_upper_pp','copy_origins')} for k,f in fam.items()},official_Level_proven=False)
    (ROOT/'outputs/stage2-root-remaining-attribution-r189.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8');print(json.dumps({k:v for k,v in result.items() if k!='family_summaries'}))
if __name__=='__main__':main()
