"""Same declared-budget immediate-adoption comparison on the original full336.

Both methods start from the same R196 + seven R197 accepted incumbents. Input
statuses without a legal incumbent are retained explicitly, not scored zero.
Every complete candidate and physical frontier is preserved and checked.
"""
import argparse
from collections import Counter
import gzip
import json
from pathlib import Path
import shutil
import sys
from time import perf_counter

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from isa_scheduler.online_mobile_refine import refine_online_mobile
from isa_scheduler.balanced_mobile_fast_refine import refine_balanced_mobile_fast
from isa_scheduler.mobile_backbone_anytime import iter_mobile_frontier
from scripts.mobile_backbone_incremental_replay import MobilePhysicalReplay
from scripts.research_mobile_backbone_full336 import four_check, fingerprint, lines, sha


def write(path, value):
    path.write_text(json.dumps(value, indent=2), encoding='utf-8')


def save(path, value):
    with gzip.open(path, 'xt', encoding='utf-8', compresslevel=1) as stream:
        stream.write(json.dumps(value, separators=(',', ':'))+'\n')


def run(out, budget_ms):
    out.mkdir(parents=True, exist_ok=False)
    prior_path = ROOT/'experiments/r196-mobile-backbone-full336/report.json'
    r196 = json.loads(prior_path.read_text())
    old = {row['sha256']: row for row in r196['records']}
    r197path = Path('G:/Hackathon-stage2-artifacts/project18/r197-composed-selected7/report.json')
    r197 = json.loads(r197path.read_text())
    newer = {row['sha256']: row for row in r197['records']}
    inventory = {row['sha256']: row for row in json.loads((ROOT/'experiments/r195-mobile-backbone-full336-prepared/inventory.json').read_text())}
    sources = [Path(__file__), ROOT/'isa_scheduler/online_mobile_refine.py', ROOT/'isa_scheduler/balanced_mobile_refine.py', ROOT/'isa_scheduler/balanced_mobile_fast_refine.py', ROOT/'isa_scheduler/mobile_backbone_fast.py',
               ROOT/'isa_scheduler/mobile_backbone_refine.py', ROOT/'isa_scheduler/mobile_backbone_anytime.py',
               ROOT/'isa_scheduler/general_region_anytime.py', ROOT/'scripts/mobile_backbone_incremental_replay.py']
    declaration = {'cases': 336, 'selection': 'complete original336, unchanged input order',
        'same_initial': 'R196 best, overridden only by the seven verified R197 best outputs',
        'time_budget_ms_each': budget_ms, 'states_each': 20000, 'transitions_each': 20000,
        'comparison_order': 'static/online on even indexed input; online/static on odd',
        'outlets_per_region_both': 4,
        'online_max_rounds': 8, 'both_per_region_transitions': 'max(2000,min(10000,2*span+128)) clipped by remaining total',
        'scope': 'Same declared per-graph budget; both wall and work caps apply; CPU contention possible. Validation/export outside search budget.',
        'source_sha256': {str(p.relative_to(ROOT)): sha(p) for p in sources},
        'baseline_report_sha256': sha(prior_path), 'r197_report_sha256': sha(r197path)}
    write(out/'declaration.json', declaration)
    report = {'declaration': declaration, 'records': [], 'completed': False}
    began = perf_counter()
    resources = lambda: {'disk_free_bytes': shutil.disk_usage(out).free}
    for input_index, case in enumerate(lines(ROOT/'experiments/r195-mobile-backbone-full336-prepared/inputs.jsonl.gz')):
        data = case['input']; key = fingerprint(data); source = old[key]
        record = {name: source[name] for name in ('sha256', 'family', 'node_count', 'bit_width', 'source_status')}
        record['methods'] = {}
        if source['after_copies'] is None:
            record.update(before_copies=None, status='original_no_incumbent_retained')
            report['records'].append(record)
            continue
        if key in newer:
            initial_path = r197path.parent/f'{key[:16]}-best.json.gz'
            assert sha(initial_path) == r197['evidence_sha256'][initial_path.name]
        elif source.get('best_absolute_path'):
            initial_path = Path(source['best_absolute_path'])
            assert sha(initial_path) == source['best_compressed_SHA']
        else:
            initial_path = Path(inventory[key]['initial_absolute_path'])
            assert sha(initial_path) == inventory[key]['initial_compressed_SHA']
        initial = next(lines(initial_path))
        four_check(data, initial)
        record.update(before_copies=initial['copies'], initial_path=str(initial_path), initial_sha256=sha(initial_path),
                      status='verified_zero_copy' if initial['copies']==0 else 'searched')
        if initial['copies']:
            ordering = [('static', refine_balanced_mobile_fast), ('online', refine_online_mobile)]
            if input_index % 2:
                ordering.reverse()
            for name, method in ordering:
                prefix=f'{key[:16]}-{name}'
                count = 0
                tick = perf_counter()
                with gzip.open(out/f'{prefix}-proposals.jsonl.gz', 'xt', encoding='utf-8', compresslevel=1) as stream:
                    def sink(region, candidate):
                        nonlocal count
                        stream.write(json.dumps({'region': region, 'candidate': candidate}, separators=(',', ':'))+'\n')
                        count += 1
                    result=method(data, initial, time_budget_ms=budget_ms, max_states=20000,
                                  max_transitions=20000, on_completed=sink, resource_snapshot=resources)
                search_wall=perf_counter()-tick
                tick=perf_counter()
                for proposal in lines(out/f'{prefix}-proposals.jsonl.gz'):
                    four_check(data, proposal['candidate'])
                four_check(data, result['best'])
                verify_wall=perf_counter()-tick
                save(out/f'{prefix}-best.json.gz', result['best'])
                counts=Counter();tick=perf_counter()
                for index, diagnostic in enumerate(result['diagnostics']):
                    frontier_initial=getattr(diagnostic,'incumbent',initial)
                    save(out/f'{prefix}-region{index}-initial.json.gz',frontier_initial)
                    replay=MobilePhysicalReplay(data, frontier_initial, diagnostic.region)
                    with gzip.open(out/f'{prefix}-region{index}-frontier.jsonl.gz', 'xt', encoding='utf-8', compresslevel=1) as stream:
                        for view in iter_mobile_frontier(diagnostic):
                            replay.accept(view); counts[view['kind']]+=1
                            stream.write(json.dumps(view,separators=(',',':'))+'\n')
                record['methods'][name]={'after_copies': result['best']['copies'],
                    'complete_proposals':count, 'stats':result['stats'],
                    'frontier_counts':dict(counts), 'search_wall_seconds':search_wall,
                    'verification_seconds':verify_wall, 'export_replay_seconds':perf_counter()-tick}
                del result
            print(json.dumps({'input':input_index, 'family':record['family'], 'n':record['node_count'],
                'before':record['before_copies'], **{name:value['after_copies'] for name,value in record['methods'].items()}}), flush=True)
        report['records'].append(record)
        write(out/'partial.json', report)
    assert len(report['records'])==336
    legal=[row for row in report['records'] if row['before_copies'] is not None]
    summary={'count':336,'legal_count':len(legal),'no_incumbent_count':336-len(legal),
        'source_statuses':dict(Counter(row['source_status'] for row in report['records'])),
        'before_copies':sum(row['before_copies'] for row in legal),
        'before_legal_copy_output_mean':sum(row['before_copies']/(row['node_count']+row['before_copies']) for row in legal)/len(legal),
        'all336_quality_mean':None,'methods':{}}
    for name in ('static','online'):
        copies=lambda row: row['methods'][name]['after_copies'] if row['methods'] else row['before_copies']
        summary['methods'][name]={'after_copies':sum(copies(row) for row in legal),
            'improved_count':sum(copies(row)<row['before_copies'] for row in legal),
            'legal_copy_output_mean':sum(copies(row)/(row['node_count']+copies(row)) for row in legal)/len(legal),
            'complete_proposals':sum(row['methods'][name]['complete_proposals'] for row in legal if row['methods']),
            'search_wall_seconds':sum(row['methods'][name]['search_wall_seconds'] for row in legal if row['methods']),
            'verification_seconds':sum(row['methods'][name]['verification_seconds'] for row in legal if row['methods']),
            'export_replay_seconds':sum(row['methods'][name]['export_replay_seconds'] for row in legal if row['methods']),
            'transitions':sum(row['methods'][name]['stats']['attempted_transitions'] for row in legal if row['methods'])}
    report.update(completed=True,summary=summary,wall_seconds=perf_counter()-began,
                  evidence_sha256={p.name:sha(p) for p in out.glob('*.gz')})
    write(out/'report.json',report)
    print(json.dumps(summary),flush=True)


def audit(out):
    from scripts.general_region_raw_checks import replay
    from scripts.mobile_backbone_semantics import check_semantics
    report=json.loads((out/'report.json').read_text());assert report['completed']
    for name,expected in report['evidence_sha256'].items():assert sha(out/name)==expected,name
    records={row['sha256']:row for row in report['records']};counts=Counter();frontier=Counter()
    def verify(data,candidate):
        assert replay(data,candidate['output'],candidate['original_order'])['copies']==candidate['copies']
        check_semantics(data,candidate);counts['whole_outputs']+=1
    for case in lines(ROOT/'experiments/r195-mobile-backbone-full336-prepared/inputs.jsonl.gz'):
        data=case['input'];key=fingerprint(data);record=records[key];counts['inputs']+=1
        if record['before_copies'] is None:counts['no_incumbent_preserved']+=1;continue
        initial=next(lines(record['initial_path']));verify(data,initial)
        assert sha(Path(record['initial_path']))==record['initial_sha256']
        for name,item in record['methods'].items():
            prefix=f'{key[:16]}-{name}';proposals=0
            for p in lines(out/f'{prefix}-proposals.jsonl.gz'):verify(data,p['candidate']);proposals+=1
            assert proposals==item['complete_proposals'];counts['proposals']+=proposals
            best=next(lines(out/f'{prefix}-best.json.gz'));verify(data,best)
            assert best['copies']==item['after_copies']<=initial['copies']
            counts['method_runs']+=1;local=Counter()
            for path in sorted(out.glob(f'{prefix}-region*-frontier.jsonl.gz')):
                checker=None
                for view in lines(path):
                    if view['kind']=='header':
                        frontier_initial=next(lines(Path(str(path).replace('-frontier.jsonl.gz','-initial.json.gz'))))
                        verify(data,frontier_initial)
                        checker=MobilePhysicalReplay(data,frontier_initial,view['region'])
                    assert checker is not None;checker.accept(view);local[view['kind']]+=1
            assert dict(local)==item['frontier_counts'];frontier.update(local)
            assert item['stats']['processed_states']<=20000 and item['stats']['attempted_transitions']<=20000
    result={'passed':True,'counts':dict(counts),'frontier_counts':dict(frontier),
            'summary':report['summary'],'report_sha256':sha(out/'report.json')}
    write(out/'independent-audit.json',result);print(json.dumps(result),flush=True)


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--out',type=Path,required=True)
    parser.add_argument('--budget-ms',type=float,default=500);parser.add_argument('--audit',action='store_true')
    args=parser.parse_args()
    audit(args.out) if args.audit else run(args.out,args.budget_ms)
