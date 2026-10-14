"""R197 selected DEV experiment: use a VERIFIED improvement as next incumbent.

Fixed selected set is exactly R196's seven improved graphs. Total search budget
1000ms/40000 states/40000 transitions, <=3 rounds, <=500ms/20000 per round.
Validation/export are separately timed and not part of the search allowance.
All complete proposals and physical frontiers are saved, including losers.
This larger-budget selected experiment is not a full336 or same-budget result.
"""
from collections import Counter
import gzip
import hashlib
import json
from pathlib import Path
import sys
from time import perf_counter

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from isa_scheduler.mobile_backbone_refine import refine_mobile_backbones
from isa_scheduler.mobile_backbone_anytime import iter_mobile_frontier
from scripts.mobile_backbone_incremental_replay import MobilePhysicalReplay
from scripts.research_mobile_backbone_full336 import four_check, fingerprint, lines, sha
from scripts.research_mobile_backbone_small import resources as old_resources

OUT=Path('G:/Hackathon-stage2-artifacts/project18/r197-composed-selected7')


def save(path, value):
    with gzip.open(path,'xt',encoding='utf-8',compresslevel=1) as stream:
        stream.write(json.dumps(value,separators=(',',':'))+'\n')


def main():
    import shutil
    OUT.mkdir(exist_ok=False)
    def resources():
        r=old_resources();r['disk_free_bytes']=shutil.disk_usage(OUT).free
        if r['free_RAM_bytes']<768*1024**2: raise RuntimeError('RAM reserve')
        return r
    previous=ROOT/'experiments/r196-mobile-backbone-full336/report.json'
    r196=json.loads(previous.read_text())
    selected={r['sha256']:r for r in r196['records'] if r['before_copies'] is not None and r['after_copies']<r['before_copies']}
    assert len(selected)==7
    declaration={'selection':'exact seven R196 improvements, previously evaluated DEV',
        'max_rounds':3,'total_search_ms':1000,'total_states':40000,'total_transitions':40000,
        'per_round_ms':500,'per_round_states':20000,'per_round_transitions':20000,
        'baseline_report_sha256':sha(previous),'source_sha256':sha(Path(__file__)),
        'frozen_engine_sha256':sha(ROOT/'isa_scheduler/mobile_backbone_refine.py'),
        'default_changed':False,'budget_scope':'search includes parse/selection/emission/sink; checks/export separately timed'}
    (OUT/'declaration.json').write_text(json.dumps(declaration,indent=2))
    report={'declaration':declaration,'records':[],'completed':False}
    began=perf_counter()
    for case in lines(ROOT/'experiments/r195-mobile-backbone-full336-prepared/inputs.jsonl.gz'):
        data=case['input'];key=fingerprint(data)
        if key not in selected: continue
        source=selected[key];assert sha(Path(source['best_absolute_path']))==source['best_compressed_SHA']
        best=next(lines(source['best_absolute_path']));four_check(data,best)
        record={'sha256':key,'family':source['family'],'before_copies':best['copies'],'rounds':[]}
        elapsed=states=transitions=0
        for round_no in range(3):
            if elapsed>=1000 or states>=40000 or transitions>=40000:break
            prefix=f'{key[:16]}-round{round_no}'
            save(OUT/f'{prefix}-initial.json.gz',best)
            check_start=perf_counter();count=0
            with gzip.open(OUT/f'{prefix}-proposals.jsonl.gz','xt',encoding='utf-8',compresslevel=1) as stream:
                def sink(region,candidate):
                    nonlocal count
                    stream.write(json.dumps({'region':region,'candidate':candidate},separators=(',',':'))+'\n');count+=1
                result=refine_mobile_backbones(data,best,time_budget_ms=min(500,1000-elapsed),
                    max_states=min(20000,40000-states),max_transitions=min(20000,40000-transitions),
                    on_completed=sink,resource_snapshot=resources)
            elapsed+=result['stats']['search_emit_ms'];states+=result['stats']['processed_states'];transitions+=result['stats']['attempted_transitions']
            tick=perf_counter()
            for proposal in lines(OUT/f'{prefix}-proposals.jsonl.gz'):four_check(data,proposal['candidate'])
            four_check(data,result['best'])
            verification_seconds=perf_counter()-tick
            counts=Counter();tick=perf_counter()
            for index,diagnostic in enumerate(result['diagnostics']):
                replay=MobilePhysicalReplay(data,best,diagnostic.region)
                with gzip.open(OUT/f'{prefix}-region{index}-frontier.jsonl.gz','xt',encoding='utf-8',compresslevel=1) as stream:
                    for view in iter_mobile_frontier(diagnostic):
                        replay.accept(view);counts[view['kind']]+=1
                        stream.write(json.dumps(view,separators=(',',':'))+'\n')
            export_seconds=perf_counter()-tick
            improved=result['best']['copies']<best['copies']
            record['rounds'].append({'round':round_no,'before':best['copies'],'after':result['best']['copies'],
                'all_complete_proposals':count,'stats':result['stats'],'independent_frontier_replay_counts':dict(counts),
                'verification_seconds':verification_seconds,'export_and_replay_seconds':export_seconds,
                'whole_round_seconds':perf_counter()-check_start,'adopted':improved})
            best=result['best'];del result
            if not improved:break
        save(OUT/f'{key[:16]}-best.json.gz',best)
        record.update(after_copies=best['copies'],total_search_ms=elapsed,total_states=states,total_transitions=transitions)
        report['records'].append(record)
        (OUT/'partial.json').write_text(json.dumps(report,indent=2))
        print(json.dumps({'family':record['family'],'before':record['before_copies'],'after':record['after_copies'],'rounds':len(record['rounds'])}),flush=True)
    assert len(report['records'])==7
    report.update(completed=True,wall_seconds=perf_counter()-began,
        total_before_copies=sum(r['before_copies'] for r in report['records']),
        total_after_copies=sum(r['after_copies'] for r in report['records']),
        evidence_sha256={p.name:sha(p) for p in OUT.glob('*.gz')})
    (OUT/'report.json').write_text(json.dumps(report,indent=2))
    print(json.dumps({k:report[k] for k in ['completed','total_before_copies','total_after_copies','wall_seconds']}))


if __name__=='__main__':main()
