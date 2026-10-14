"""Independently verify and retain the best actual plan across complete runs.

This is cumulative development evidence. It is explicitly not a single-budget
benchmark: every supplied method/run's work and failed search cost is counted.
"""
import argparse
from collections import Counter
import json
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from scripts.research_mobile_backbone_full336 import lines,fingerprint,sha,four_check


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--reports',nargs='+',type=Path,required=True)
    parser.add_argument('--out',type=Path,required=True);args=parser.parse_args()
    loaded=[];work=Counter();frontier=Counter()
    for path in args.reports:
        report=json.loads(path.read_text());assert report['completed'] and len(report['records'])==336
        for record in report['records']:
            for name,method in record['methods'].items():
                work['method_runs']+=1
                for k in ('complete_proposals','search_wall_seconds','verification_seconds','export_replay_seconds'):
                    work[k]+=method[k]
                work['attempted_transitions']+=method['stats']['attempted_transitions']
                work['processed_states']+=method['stats']['processed_states']
                frontier.update(method['frontier_counts'])
        loaded.append((path,report,{r['sha256']:r for r in report['records']}))
    args.out.mkdir(parents=True,exist_ok=False)
    records=[];counts=Counter();total_before=total_after=0;mean_before=mean_after=0
    for case in lines(ROOT/'experiments/r195-mobile-backbone-full336-prepared/inputs.jsonl.gz'):
        data=case['input'];key=fingerprint(data);baseline=loaded[0][2][key]
        row={k:baseline[k] for k in ('sha256','family','node_count','bit_width','source_status','before_copies')}
        counts[baseline['source_status']]+=1
        if baseline['before_copies'] is None:
            row.update(after_copies=None,path=None,status='original_no_incumbent_preserved')
            records.append(row);continue
        initial=Path(baseline['initial_path']);assert sha(initial)==baseline['initial_sha256']
        alternatives=[(baseline['before_copies'],str(initial),'accepted_before_this_session')]
        for path,report,mapping in loaded:
            item=mapping[key]
            assert item['before_copies']==baseline['before_copies']
            for name,method in item['methods'].items():
                bestpath=path.parent/f'{key[:16]}-{name}-best.json.gz'
                assert sha(bestpath)==report['evidence_sha256'][bestpath.name]
                alternatives.append((method['after_copies'],str(bestpath),f'{path.parent.name}/{name}'))
        cost,target,origin=min(alternatives,key=lambda a:(a[0],a[2]))
        candidate=next(lines(target));assert candidate['copies']==cost
        checks=four_check(data,candidate)
        row.update(after_copies=cost,path=target,origin=origin,sha256_compressed=sha(Path(target)),
                   status='verified',checks=checks,alternatives=len(alternatives))
        total_before+=baseline['before_copies'];total_after+=cost
        mean_before+=baseline['before_copies']/(row['node_count']+baseline['before_copies'])
        mean_after+=cost/(row['node_count']+cost)
        records.append(row)
    assert len(records)==336 and counts['verified']==272
    summary={'cases':336,'legal_count':272,'no_incumbent_count':64,'statuses':dict(counts),
        'before_copies':total_before,'after_copies':total_after,'copy_reduction':total_before-total_after,
        'improved_graphs':sum(r['after_copies']<r['before_copies'] for r in records if r['after_copies'] is not None),
        'before_legal_copy_output_mean':mean_before/272,'after_legal_copy_output_mean':mean_after/272,
        'all336_quality_mean':None,'cumulative_work_including_nonwinners':dict(work),
        'independently_replayed_physical_frontiers':dict(frontier)}
    result={'completed':True,'summary':summary,'records':records,
        'source_report_sha256':{str(p):sha(p) for p,_,_ in loaded},'acceptor_sha256':sha(Path(__file__)),
        'scope':'Cumulative best actual verified plans; all supplied run costs included; not a single 500ms result; no official Level claim.'}
    (args.out/'index.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
    print(json.dumps(summary))


if __name__=='__main__':main()
