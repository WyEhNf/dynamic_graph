"""Derive paired quality, per-family and latency statistics without dropping failures."""
import argparse
import collections
import json
from pathlib import Path
import statistics
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from isa_scheduler.evaluation import percentile


def analyze(report, before, after):
    by_input = {}
    for record in report['records']:
        by_input.setdefault(record['sha256'], {})[record['variant']] = record
    pairs = [(group[before], group[after]) for group in by_input.values() if before in group and after in group]
    if not pairs:raise ValueError(f"No paired records for variants {before!r} and {after!r}; inspect paired_variants in report.json")
    both = [(a,b) for a,b in pairs if a['status']==b['status']=='verified']
    rows = {}
    for family in sorted({a['family'] for a,b in pairs}):
        group = [(a,b) for a,b in pairs if a['family']==family]
        shared = [(a,b) for a,b in group if a['status']==b['status']=='verified']
        rows[family] = {'status_pairs':dict(collections.Counter(f"{a['status']}->{b['status']}" for a,b in group)),
                        'joint_successes':len(shared),
                        'before_copies':sum(a['inserted_copies'] for a,b in shared),
                        'after_copies':sum(b['inserted_copies'] for a,b in shared),
                        'median_speedup_joint':statistics.median(a['optimizer_ms']/b['optimizer_ms'] for a,b in shared) if shared else None}
    result={'before':before,'after':after,'corpus_sha256':report['corpus_sha256'],'case_count':len(pairs),
            'joint_successes':len(both),'status_pairs':dict(collections.Counter(f"{a['status']}->{b['status']}" for a,b in pairs)),
            'quality_pairs':dict(collections.Counter('better' if b['inserted_copies']<a['inserted_copies'] else 'worse' if b['inserted_copies']>a['inserted_copies'] else 'same' for a,b in both)),
            'before_copies_joint':sum(a['inserted_copies'] for a,b in both),
            'after_copies_joint':sum(b['inserted_copies'] for a,b in both),
            'median_speedup_joint':statistics.median(a['optimizer_ms']/b['optimizer_ms'] for a,b in both) if both else None,
            'families':rows}
    for label,index in (('before',0),('after',1)):
        data=[p[index] for p in pairs]
        success=[x for x in data if x['status']=='verified']
        result[label+'_metrics']={'latency_all_ms':{f'p{int(q*100)}':percentile([x['optimizer_ms'] for x in data],q)for q in (.5,.95,.99)},
                                  'equal_weight_copy_output_success':statistics.mean(x['inserted_copies']/x['output_count']for x in success)if success else None,
                                  'equal_weight_copy_original_success':statistics.mean(x['inserted_copies']/x['node_count']for x in success)if success else None,
                                  'failure_rate':1-len(success)/len(data)}
    return result


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('report');parser.add_argument('--before',default='v02_auto');parser.add_argument('--after',default='current_auto')
    args=parser.parse_args();path=Path(args.report)
    result=analyze(json.loads(path.read_text(encoding='utf-8')),args.before,args.after)
    destination=path.with_name(f'analysis-{args.before}-{args.after}.json')
    destination.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(result,ensure_ascii=False,indent=2))
