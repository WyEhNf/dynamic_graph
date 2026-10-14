import copy
import json
from pathlib import Path
import unittest

from isa_scheduler.refine import refine,normalize_incumbent
from isa_scheduler.model import InvalidBlock
from scripts.general_region_raw_checks import replay
from scripts.mobile_backbone_semantics import check_semantics

ROOT=Path(__file__).resolve().parents[1]


class RefineEntryTests(unittest.TestCase):
    def test_public_entry_returns_reusable_verified_witness(self):
        fixture=json.loads((ROOT/'research/level-stage/mobile-backbone-hand45.json').read_text())
        output=refine(fixture['input'],fixture['baseline'],time_budget_ms=500)
        self.assertLess(output['stats']['inserted_copy_count'],13)
        package=normalize_incumbent(output)
        self.assertEqual(replay(fixture['input'],package['output'],package['original_order'])['copies'],package['copies'])
        check_semantics(fixture['input'],package)
        second=refine(fixture['input'],output,time_budget_ms=50)
        self.assertLessEqual(second['stats']['inserted_copy_count'],package['copies'])

    def test_missing_or_corrupt_identity_witness_is_rejected(self):
        fixture=json.loads((ROOT/'research/level-stage/mobile-backbone-hand45.json').read_text())
        with self.assertRaises(InvalidBlock):refine(fixture['input'],fixture['baseline']['output'])
        bad=copy.deepcopy(fixture['baseline']);bad['original_order'][1]=0
        with self.assertRaises(InvalidBlock):refine(fixture['input'],bad)


if __name__=='__main__':unittest.main()
