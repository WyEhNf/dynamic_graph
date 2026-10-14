"""Controls for truncated neighborhoods; independent original/physical checks."""
import json
from pathlib import Path
import unittest

from isa_scheduler.balanced_mobile_refine import refine_balanced_mobile, select_balanced_regions
from isa_scheduler.mobile_backbone_anytime import iter_mobile_frontier, prepare_mobile
from isa_scheduler.mobile_backbone_refine import select_mobile_regions
from scripts.general_region_raw_checks import replay
from scripts.mobile_backbone_incremental_replay import MobilePhysicalReplay
from scripts.mobile_backbone_semantics import check_semantics
from scripts.research_mobile_backbone_full336 import fingerprint, lines
from scripts.research_mobile_backbone_small import fanout_fixture, hazard_fixture

ROOT=Path(__file__).resolve().parents[1]


class BalancedMobileTests(unittest.TestCase):
    def check_result(self, data, initial, result, candidates):
        for candidate in candidates+[result['best']]:
            self.assertEqual(replay(data,candidate['output'],candidate['original_order'])['copies'],candidate['copies'])
            check_semantics(data,candidate)
        self.assertLessEqual(result['best']['copies'],initial['copies'])
        for diagnostic in result['diagnostics']:
            checker=MobilePhysicalReplay(data,initial,diagnostic.region)
            for view in iter_mobile_frontier(diagnostic):checker.accept(view)

    def test_large_closure_retains_small_valid_search(self):
        old=json.loads((ROOT/'experiments/r196-mobile-backbone-full336/report.json').read_text())
        record=next(row for row in old['records'] if row['family']=='balanced_tree' and row['node_count']==64 and row['after_copies']==10)
        data=next(case['input'] for case in lines(ROOT/'experiments/r195-mobile-backbone-full336-prepared/inputs.jsonl.gz') if fingerprint(case['input'])==record['sha256'])
        initial=next(lines(record['best_absolute_path']))
        graph=prepare_mobile(data,initial,lambda:None)
        original,rejected,_=select_mobile_regions(graph,initial,lambda:None)
        self.assertFalse(original)
        self.assertTrue(any(row['reason']=='closure_exceeds_32' for row in rejected))
        regions,_=select_balanced_regions(graph,initial,lambda:None)
        self.assertTrue(regions)
        self.assertTrue(all(1<=len(row['region']['mobile'])<=12 for row in regions))
        candidates=[]
        result=refine_balanced_mobile(data,initial,on_completed=lambda _,c:candidates.append(c),time_budget_ms=1000)
        self.assertTrue(candidates)
        self.assertLess(result['best']['copies'],initial['copies'])
        self.check_result(data,initial,result,candidates)

    def test_shared_get_with_external_users_and_hazards(self):
        for data,initial in (fanout_fixture(),hazard_fixture()):
            candidates=[]
            result=refine_balanced_mobile(data,initial,on_completed=lambda _,c:candidates.append(c))
            self.check_result(data,initial,result,candidates)
        data,initial=fanout_fixture()
        graph=prepare_mobile(data,initial,lambda:None)
        regions,_=select_balanced_regions(graph,initial,lambda:None)
        self.assertTrue(any(0 in row['region']['mobile'] and not graph['users'][0]<=set(row['region']['mobile']) for row in regions))

    def test_budget_stops_keep_valid_incumbent(self):
        fixture=json.loads((ROOT/'research/level-stage/mobile-backbone-hand45.json').read_text())
        for options in ({'time_budget_ms':1e-9},{'max_transitions':1},{'max_states':1}):
            result=refine_balanced_mobile(fixture['input'],fixture['baseline'],**options)
            self.assertLessEqual(result['stats']['attempted_transitions'],options.get('max_transitions',20000))
            self.assertLessEqual(result['stats']['processed_states'],options.get('max_states',20000))
            self.check_result(fixture['input'],fixture['baseline'],result,[])


if __name__=='__main__':unittest.main()
