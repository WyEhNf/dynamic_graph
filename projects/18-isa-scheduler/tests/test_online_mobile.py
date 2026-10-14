import json
from pathlib import Path
import unittest

from isa_scheduler.online_mobile_refine import refine_online_mobile
from isa_scheduler.mobile_backbone_fast import iter_mobile_frontier
from scripts.general_region_raw_checks import replay
from scripts.mobile_backbone_incremental_replay import MobilePhysicalReplay
from scripts.mobile_backbone_semantics import check_semantics

ROOT=Path(__file__).resolve().parents[1]


class OnlineMobileTests(unittest.TestCase):
    def test_reseed_frontiers_keep_their_own_incumbent(self):
        from scripts.research_mobile_backbone_full336 import lines,fingerprint
        report=json.loads((ROOT/'experiments/r196-mobile-backbone-full336/report.json').read_text())
        record=next(row for row in report['records'] if row['family']=='balanced_tree' and row['node_count']==64 and row['after_copies']==10)
        data=next(case['input'] for case in lines(ROOT/'experiments/r195-mobile-backbone-full336-prepared/inputs.jsonl.gz') if fingerprint(case['input'])==record['sha256'])
        initial=next(lines(record['best_absolute_path']));complete=[]
        result=refine_online_mobile(data,initial,time_budget_ms=1000,on_completed=lambda _,c:complete.append(c))
        self.assertTrue(complete)
        for candidate in complete+[result['best']]:
            self.assertEqual(replay(data,candidate['output'],candidate['original_order'])['copies'],candidate['copies'])
            check_semantics(data,candidate)
        for diagnostic in result['diagnostics']:
            checker=MobilePhysicalReplay(data,diagnostic.incumbent,diagnostic.region)
            for view in iter_mobile_frontier(diagnostic):checker.accept(view)
        self.assertLess(result['best']['copies'],initial['copies'])
        self.assertTrue(any(d.incumbent['copies']<initial['copies'] for d in result['diagnostics']))
        self.assertLessEqual(result['stats']['attempted_transitions'],20000)
        self.assertLessEqual(result['stats']['processed_states'],20000)

    def test_tiny_total_budget_retains_incumbent(self):
        fixture=json.loads((ROOT/'research/level-stage/mobile-backbone-hand45.json').read_text())
        result=refine_online_mobile(fixture['input'],fixture['baseline'],time_budget_ms=1e-9)
        self.assertEqual(result['best'],fixture['baseline'])
        self.assertEqual(result['stats']['complete_outputs'],0)
        self.assertEqual(result['stats']['outcome'],'partial_total_deadline')


if __name__=='__main__':unittest.main()
