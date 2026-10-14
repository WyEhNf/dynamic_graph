"""Read-only R187 attribution. No scheduler, verifier or oracle imports."""
from collections import Counter,defaultdict
from datetime import datetime,timezone
import gzip
import hashlib
import json
from pathlib import Path
from time import perf_counter

ROOT=Path(__file__).resolve().parents[1]
SOURCE=ROOT/'experiments/r187-general-region-full336'
PREPARED=ROOT/'experiments/r186-general-region-full336-prepared'
ARTIFACTS=Path(r'G:\Hackathon-stage2-artifacts\project18\r187-general-region-full336')
DEST=ROOT/'experiments/r189-general-region-remaining-static'


def read(path): return json.loads(path.read_text(encoding='utf-8'))
def sha(path): return hashlib.sha256(path.read_bytes()).hexdigest()
def fingerprint(data): return hashlib.sha256(json.dumps(data,sort_keys=True,separators=(',',':'),ensure_ascii=False).encode()).hexdigest()
def compressed(path):
    with gzip.open(path,'rt',encoding='utf-8') as stream:
        for line in stream: yield json.loads(line)


def main():
    DEST.mkdir(exist_ok=False); started=perf_counter(); report=read(SOURCE/'report.json')
    records={row['sha256']:row for row in report['records']}
    lower={row['sha256']:row for row in read(ROOT/'experiments/r143-root-lifetime-summary/report.json')['records']}
    families=defaultdict(lambda:{'count':0,'statuses':Counter(),'search_outcomes':Counter(),'copies':0,'necessary_lower':0,
        'copy_origins':Counter(),'completed_proposals':0,'complete_proposal_comparison':Counter(),'gap_upper_pp':0.0})
    outputs=[]; cases=[]
    for case in compressed(PREPARED/'inputs.jsonl.gz'):
        data=case['input']; key=fingerprint(data); saved=records[key]; bounds=lower[key]; family=families[case['family']]
        family['count']+=1; family['statuses'][saved['source_status']]+=1; family['search_outcomes'][saved['candidate_outcome']]+=1
        family['completed_proposals']+=saved['actual_complete_outputs']
        item={'sha256':key,'family':case['family'],'N':len(data['instructions']),'W':2**data['bit_width'],
              'source_status':saved['source_status'],'candidate_outcome':saved['candidate_outcome'],'copies':saved['after_copies'],
              'necessary_lower':bounds['joint_lower'],'attempts':[]}
        if saved['after_copies'] is not None:
            path=ARTIFACTS/f'{key[:16]}-best.json.gz'
            if not path.exists(): path=PREPARED/'initials'/f'{key}.json.gz'
            emitted=next(compressed(path)); order=emitted['original_order']; rows=emitted['output']['optimized_instructions']
            history=[]; cursor=0; origins=Counter(); identity_copies=Counter(); births={}
            for row in rows:
                if row['op']=='COPY':
                    identity=history[-int(row['source'][2:])]; identity_copies[identity]+=1; origins[data['instructions'][identity]['op']]+=1
                else:
                    identity=order[cursor]; births[identity]=cursor; cursor+=1
                    if row['op']=='SET': identity=None
                history.append(identity)
            assert sum(origins.values())==saved['after_copies']
            family['copy_origins'].update(origins); family['copies']+=saved['after_copies']; family['necessary_lower']+=bounds['joint_lower']
            c=saved['after_copies']; l=bounds['joint_lower']; n=len(order)
            family['gap_upper_pp']+=(c/(n+c)-l/(n+l))*100/272
            args=[tuple(i-int(t[2:]) for t in row.get('inputs',[])) for i,row in enumerate(data['instructions'])]
            consumers=defaultdict(list)
            for index,sources in enumerate(args):
                for source in set(sources): consumers[source].append(index)
            item['copy_origins']=dict(origins); item['copied_identities']=[]
            for identity,count in identity_copies.most_common(8):
                uses=consumers[identity]; ranks=[births[user] for user in uses]
                item['copied_identities'].append({'id':identity,'op':data['instructions'][identity]['op'],'copies':count,
                    'birth_original_rank':births[identity],'direct_consumer_count':len(uses),
                    'first_consumer_rank':min(ranks) if ranks else None,'last_consumer_rank':max(ranks) if ranks else None,
                    'birth_to_first_use_original_gap':min(ranks)-births[identity] if ranks else None})
            if saved['actual_complete_outputs']:
                for proposal in compressed(Path(saved['complete_absolute_path'])):
                    value=proposal['candidate']['copies']
                    label='better_initial' if value<saved['before_copies'] else 'same_initial' if value==saved['before_copies'] else 'worse_initial'
                    family['complete_proposal_comparison'][label]+=1
            if saved.get('stats'):
                for attempt in saved['stats']['attempts']:
                    stats=attempt['stats']; item['attempts'].append({'start':attempt['start'],'outcome':stats['outcome'],
                        'expansions':stats['processed_states'],'transitions':stats['attempted_transitions'],'complete':stats['complete_outputs']})
        cases.append(item)
    result={'count':len(cases),'families':dict(families),'records':cases,
        'necessary_scope':'R143 fixed original336 strict-identity necessary bound, equal output denominator; 272 legal subset lower10.285229311249013%, not official or achieved.',
        'gap_scope':'COPY-minus-bound and pp are possible improvement UPPER bounds, not attainability.',
        'elapsed_static_read_seconds':perf_counter()-started,'source_report_sha256':sha(SOURCE/'report.json'),
        'source_bound_sha256':sha(ROOT/'experiments/r143-root-lifetime-summary/report.json')}
    (DEST/'report.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
    provenance={'frozen_at_utc':datetime.now(timezone.utc).isoformat(),'script_sha256':sha(Path(__file__)),
        'report_sha256':sha(DEST/'report.json'),'phase':'Read-only static attribution; no solver/oracle/verification.'}
    (DEST/'source-provenance.json').write_text(json.dumps(provenance,indent=2),encoding='utf-8')
    print(json.dumps({'report':str(DEST/'report.json'),'sha256':provenance['report_sha256'],'families':dict(families)},ensure_ascii=False))


if __name__=='__main__': main()
