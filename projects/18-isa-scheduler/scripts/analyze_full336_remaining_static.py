"""Raw saved-output attribution and audited bound join, no solver imports."""
from collections import Counter, defaultdict
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import shutil

ROOT=Path(__file__).resolve().parents[1]
def read(path): return json.loads(path.read_text(encoding='utf-8'))
def sha(path): return hashlib.sha256(path.read_bytes()).hexdigest()
def rows(path):
    with path.open(encoding='utf-8') as stream:
        for line in stream: yield json.loads(line)
def write(path,data): path.write_text(json.dumps(data,indent=2)+'\n',encoding='utf-8')


def main():
    source=ROOT/'experiments/r178-anytime-full336'; bound=ROOT/'experiments/r143-root-lifetime-summary/report.json'
    folder=ROOT/'experiments/r179-full336-remaining-static'; folder.mkdir(exist_ok=False)
    report=read(source/'report.json'); bank={r['sha256']:r for r in report['records']}
    lowers={r['sha256']:r for r in read(bound)['records']}
    inputs={row['input']['block_id']:row['input'] for row in rows(ROOT/'experiments/r177-anytime-full336-prepared/inputs.jsonl')}
    records={}
    for key,old in bank.items():
        lower=lowers[key]; assert old['family']==lower['family'] and old['node_count']==lower['node_count']
        counts=Counter(); statuses=Counter(); partials=Counter(); labels=Counter()
        for attempt in (old['stats'] or {}).get('attempts',[]):
            counts['pairs']+=attempt.get('parent') is not None
            counts['expansions']+=attempt.get('processed_states',0)
            statuses[attempt['outcome']]+=1
            reason=attempt.get('stats',{}).get('message') or attempt.get('message')
            if reason: partials[reason]+=1
            labels.update(attempt.get('diagnostic_export',{}).get('record_counts',{}))
        records[key]={'sha256':key,'family':old['family'],'node_count':old['node_count'],'bit_width':old['bit_width'],
              'status':old['after_status'],'candidate_outcome':old['candidate_outcome'],'planned_route':old['planned_route'],
              'before_copies':old['before_copies'],'actual_copies':old['after_copies'],'audited_necessary_copy_lower':lower['joint_lower'],
              'gap_upper':None if old['after_copies'] is None else old['after_copies']-lower['joint_lower'],
              'attempt_counts':dict(counts),'pair_outcomes':dict(statuses),'partial_reasons':dict(partials),'raw_diagnostic_counts':dict(labels)}
        if records[key]['gap_upper'] is not None: assert records[key]['gap_upper']>=0
    for entry in rows(source/'best_outputs.jsonl'):
        key=entry['input_sha256']; data=inputs[entry['output']['block_id']]; order=entry['original_order']
        history=[]; cursor=0; opcounts=Counter(); identities=Counter(); by_cursor=Counter()
        for row in entry['output']['optimized_instructions']:
            if row['op']=='COPY':
                identity=history[len(history)-int(row['source'][2:])]; assert identity is not None
                identities[identity]+=1; opcounts[data['instructions'][identity]['op']]+=1; by_cursor[cursor]+=1
            else:
                identity=order[cursor]; cursor+=1
                if row['op']=='SET': identity=None
            history.append(identity)
        assert sum(identities.values())==records[key]['actual_copies'] and cursor==len(order)
        records[key]['copy_original_opcode_counts']=dict(opcounts)
        records[key]['top_copied_original_identities']=[{'original_index':identity,'op':data['instructions'][identity]['op'],'copies':count} for identity,count in identities.most_common(8)]
        windows={}
        n=len(order)
        for copy_cursor in by_cursor:
            for start in (max(0,min(n-32,(copy_cursor//16)*16)),max(0,min(n-32,(copy_cursor//16)*16-16))):
                start=max(0,start); end=min(n,start+32)
                windows[start]=sum(count for rank,count in by_cursor.items() if start<=rank<end)
        records[key]['proposed_top32_windows']=[{'start':start,'end':min(n,start+32),'saved_local_copy_count':count} for start,count in sorted(windows.items(),key=lambda item:(-item[1],item[0]))[:8]]
    families={}
    for family in sorted({r['family'] for r in records.values()}):
        cases=[r for r in records.values() if r['family']==family]; legal=[r for r in cases if r['actual_copies'] is not None]
        opcounts=Counter(); routes=Counter(); reasons=Counter(); outcome=Counter()
        for r in cases:
            opcounts.update(r.get('copy_original_opcode_counts',{})); routes[r['planned_route']]+=1
            reasons.update(r['partial_reasons']); outcome[r['candidate_outcome']]+=1
        families[family]={'count':len(cases),'statuses':dict(Counter(r['status'] for r in cases)),
           'search_coverage':dict(routes),'candidate_outcomes':dict(outcome),'actual_partial_reasons':dict(reasons),
           'actual_copies':sum(r['actual_copies'] for r in legal),
           'audited_necessary_copy_lower_on_legal':sum(r['audited_necessary_copy_lower'] for r in legal),
           'potential_copy_reduction_upper_bound':sum(r['gap_upper'] for r in legal),
           'copy_identity_opcode_counts':dict(opcounts),
           'potential_272_mean_output_reduction_upper_bound_pp':sum((r['actual_copies']/(r['node_count']+r['actual_copies'])-r['audited_necessary_copy_lower']/(r['node_count']+r['audited_necessary_copy_lower']))*100/272 for r in legal)}
    result={'created_utc':datetime.now(timezone.utc).isoformat(),'all336_statuses':report['after_statuses'],
        'all336_count':336,'legal_count':272,'actual_total_copy':192902,'families':families,
        'families_ranked_by_true_gap_upper':[family for family in sorted(families,key=lambda family:-families[family]['potential_272_mean_output_reduction_upper_bound_pp'])],
        'top_legal_case_gap_upper':sorted([r for r in records.values() if r['gap_upper'] is not None],key=lambda r:-r['gap_upper'])[:25],
        'records':list(records.values()),'r143_necessary_scope':read(bound)['measured272_necessary_only'],
        'scope':'No new bound proof/schedule/oracle/verification. Read-only join to previously auditedR143 strict originalidentity/COPY-only bounds. C-L is upper bound on possible reduction, not reachable target; all336 including64 no-output statuses retained. R143 all336 necessary average is not official valid-block quality; 272 bound10.285229311% exceeds10 only forthisselfgenerated strict-modelsubset with equalweight/outputdenominator. No alias/reGET/recompute/spill authorization.'}
    write(folder/'report.json',result)
    evidence=[source/'report.json',source/'best_outputs.jsonl',source/'evidence-provenance.json',bound,ROOT/'experiments/r177-anytime-full336-prepared/inputs.jsonl']
    target=folder/'src/scripts'/Path(__file__).name; target.parent.mkdir(parents=True,exist_ok=True); shutil.copy2(Path(__file__),target)
    write(folder/'source-provenance.json',{'frozen_utc':datetime.now(timezone.utc).isoformat(),'static_script_sha256':sha(Path(__file__)),
        'historical_evidence_sha256':{str(p.relative_to(ROOT)):sha(p) for p in evidence},'report_sha256':sha(folder/'report.json'),
        'scope':'Static only, no scheduler/parser/verifier/oracle imports; no solver batch/default.'})
    print(json.dumps({'families':[{'family':family,**{k:v for k,v in families[family].items() if k not in ('search_coverage','candidate_outcomes','actual_partial_reasons','statuses')}} for family in result['families_ranked_by_true_gap_upper']], 'whole336_states':result['all336_statuses']}))


if __name__=='__main__': main()
