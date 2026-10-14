"""Every emitted physical transition agrees with the frozen set engine."""
import json
from pathlib import Path
import unittest

from isa_scheduler.mobile_backbone_anytime import search_mobile_backbone as old_search
from isa_scheduler.mobile_backbone_fast import search_mobile_backbone as fast_search, iter_mobile_frontier
from scripts.general_region_raw_checks import replay
from scripts.mobile_backbone_incremental_replay import MobilePhysicalReplay
from scripts.mobile_backbone_semantics import check_semantics
from scripts.research_mobile_backbone_full336 import fingerprint

ROOT=Path(__file__).resolve().parents[1]


class BitsetMobileTests(unittest.TestCase):
    def test_80_real_physical_frontiers_and_all_complete_outputs(self):
        bank=ROOT/'experiments/r193-mobile-backbone-prepared'
        cases=[json.loads(line) for line in (bank/'cases.jsonl').read_text().splitlines()][:80]
        self.assertEqual(len(cases),80)
        for case in cases:
            data=case['input'];key=fingerprint(data)
            initial=json.loads((bank/'initials'/f'{key}.json').read_text())
            observed=[]
            for search in (old_search,fast_search):
                complete=[]
                result=search(data,initial,case['region'],time_budget_ms=10000,
                    max_states=500,max_transitions=500,max_outcomes=16,on_completed=complete.append)
                self.assertNotIn('deadline',result['stats']['outcome'])
                frontier=list(iter_mobile_frontier(result['diagnostics']))
                checker=MobilePhysicalReplay(data,initial,case['region'])
                for view in frontier:checker.accept(view)
                for candidate in complete+[result['best']]:
                    self.assertEqual(replay(data,candidate['output'],candidate['original_order'])['copies'],candidate['copies'])
                    check_semantics(data,candidate)
                observed.append((result['best'],complete,frontier,{name:result['stats'][name] for name in
                    ('outcome','processed_states','attempted_transitions','accepted_labels','complete_outputs','reopens','stale','max_open')}))
            self.assertEqual(observed[0],observed[1],key)


if __name__=='__main__':unittest.main()
