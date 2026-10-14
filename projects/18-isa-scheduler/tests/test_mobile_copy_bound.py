"""Compare bounded fixed-backbone searches with the unpruned physical engine."""
import json
from pathlib import Path
import unittest

from isa_scheduler.mobile_backbone_fast import search_mobile_backbone as reference
from isa_scheduler.mobile_backbone_bound import search_mobile_backbone as bounded,iter_mobile_frontier
from scripts.general_region_raw_checks import replay
from scripts.mobile_backbone_incremental_replay import MobilePhysicalReplay
from scripts.mobile_backbone_semantics import check_semantics
from scripts.research_mobile_backbone_full336 import fingerprint
from scripts.research_mobile_backbone_small import fanout_fixture

ROOT=Path(__file__).resolve().parents[1]


class MobileCopyBoundTests(unittest.TestCase):
    def test_240_small_restricted_neighborhoods_against_unpruned_search(self):
        bank=ROOT/'experiments/r193-mobile-backbone-prepared'
        cases=[json.loads(line) for line in (bank/'cases.jsonl').read_text().splitlines()][:80]
        completed=0
        for case in cases:
            data=case['input'];key=fingerprint(data);n=len(data['instructions'])
            initial=json.loads((bank/'initials'/f'{key}.json').read_text())
            for members in ([0],[n-1],sorted({0,n-1})):
                region={'L':0,'R':n-1,'mobile':members};answers=[]
                for search in (reference,bounded):
                    complete=[]
                    result=search(data,initial,region,time_budget_ms=10000,max_states=20000,
                                  max_transitions=20000,max_outcomes=10000,on_completed=complete.append)
                    self.assertEqual(result['stats']['outcome'],'exhausted_improvement_search')
                    checker=MobilePhysicalReplay(data,initial,region)
                    for view in iter_mobile_frontier(result['diagnostics']):checker.accept(view)
                    for candidate in complete+[result['best']]:
                        self.assertEqual(replay(data,candidate['output'],candidate['original_order'])['copies'],candidate['copies'])
                        check_semantics(data,candidate)
                    answers.append(result['best']['copies'])
                self.assertEqual(answers[0],answers[1],(key,members))
                completed+=1
        self.assertEqual(completed,240)

    def test_high_fanout_fixed_consumers_have_same_best(self):
        data,initial=fanout_fixture();region={'L':0,'R':80,'mobile':[0]}
        values=[]
        for search in (reference,bounded):
            result=search(data,initial,region,time_budget_ms=10000,max_states=20000,max_transitions=20000,max_outcomes=10000)
            self.assertEqual(result['stats']['outcome'],'exhausted_improvement_search')
            values.append(result['best']['copies'])
        self.assertEqual(values[0],values[1])


if __name__=='__main__':unittest.main()
