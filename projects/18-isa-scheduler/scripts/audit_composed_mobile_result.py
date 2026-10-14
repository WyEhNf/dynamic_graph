"""Second read-only audit of each round against ITS saved incumbent, no search."""
from collections import Counter
import json
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from scripts.research_mobile_backbone_full336 import lines, fingerprint, sha
from scripts.general_region_raw_checks import replay
from scripts.mobile_backbone_semantics import check_semantics
from scripts.mobile_backbone_incremental_replay import MobilePhysicalReplay

OUT=Path('G:/Hackathon-stage2-artifacts/project18/r197-composed-selected7')


def main():
    report=json.loads((OUT/'report.json').read_text());assert report['completed']
    for name,expected in report['evidence_sha256'].items():assert sha(OUT/name)==expected,name
    records={r['sha256']:r for r in report['records']};assert len(records)==7
    totals=Counter();frontier=Counter()
    def verify(data,candidate):
        assert replay(data,candidate['output'],candidate['original_order'])['copies']==candidate['copies']
        check_semantics(data,candidate);totals['whole_outputs']+=1
    for case in lines(ROOT/'experiments/r195-mobile-backbone-full336-prepared/inputs.jsonl.gz'):
        data=case['input'];key=fingerprint(data)
        if key not in records:continue
        r=records[key];initial_copies=r['before_copies']
        for round_no,round_record in enumerate(r['rounds']):
            prefix=f'{key[:16]}-round{round_no}'
            initial=next(lines(OUT/f'{prefix}-initial.json.gz'));verify(data,initial)
            assert initial['copies']==initial_copies==round_record['before']
            count=0
            for proposal in lines(OUT/f'{prefix}-proposals.jsonl.gz'):
                verify(data,proposal['candidate']);count+=1
            assert count==round_record['all_complete_proposals'];totals['proposals']+=count
            counts=Counter()
            for p in sorted(OUT.glob(f'{prefix}-region*-frontier.jsonl.gz')):
                checker=None
                for view in lines(p):
                    if view['kind']=='header':checker=MobilePhysicalReplay(data,initial,view['region'])
                    assert checker is not None;checker.accept(view);counts[view['kind']]+=1
            assert dict(counts)==round_record['independent_frontier_replay_counts']
            frontier.update(counts);totals['rounds']+=1
            assert round_record['after']<=round_record['before'];initial_copies=round_record['after']
        best=next(lines(OUT/f'{key[:16]}-best.json.gz'));verify(data,best)
        assert best['copies']==initial_copies==r['after_copies']
        assert r['total_states']<=40000 and r['total_transitions']<=40000
        totals['improved_graphs']+=r['after_copies']<r['before_copies']
    result={'passed':True,'records':7,'before_copies':report['total_before_copies'],'after_copies':report['total_after_copies'],
        'totals':dict(totals),'frontier':dict(frontier),'default_changed':False,
        'scope':'selected previously used DEV, larger search budget, no full336 replacement or official Level claim',
        'report_sha256':sha(OUT/'report.json'),'audit_sha256':sha(Path(__file__))}
    with (ROOT.parents[1]/'outputs/composed-mobile-selected7-audit-2026-10-12.json').open('x') as stream:json.dump(result,stream,indent=2)
    print(json.dumps(result))


if __name__=='__main__':main()
