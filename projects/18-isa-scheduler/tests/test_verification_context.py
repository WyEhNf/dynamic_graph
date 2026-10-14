import copy
import json
from pathlib import Path
import unittest
from unittest.mock import patch
from isa_scheduler.model import InvalidBlock, VerificationFailed
from isa_scheduler.optimizer import optimize
from isa_scheduler.verify import VerificationContext, verify


ROOT = Path(__file__).resolve().parents[1]


class ContextTests(unittest.TestCase):
    def test_context_reconstructs_snapshot_and_rejects_changed_ordered_operand(self):
        original = json.loads((ROOT/'fixtures/official-known-input.json').read_text())
        snapshot = copy.deepcopy(original)
        output = optimize(original)
        context = VerificationContext(original)
        original['instructions'][0]['reg']='another-register'
        self.assertEqual(context.check(output), verify(snapshot, output))
        output['optimized_instructions'][2]['inputs']=['t#1','t#1']
        with self.assertRaises(InvalidBlock):context.check(output)

    def test_context_does_not_accept_unknown_output_or_noncontiguous_ids(self):
        data = json.loads((ROOT/'fixtures/official-known-input.json').read_text())
        context = VerificationContext(data)
        output = optimize(data)
        output['hidden-effect']=True
        with self.assertRaises(InvalidBlock):context.check(output)
        del output['hidden-effect'];output['optimized_instructions'][0]['id']=9
        with self.assertRaises(InvalidBlock):context.check(output)

    def test_invalid_improving_candidate_never_replaces_incumbent(self):
        data=json.loads((ROOT/'fixtures/official-known-input.json').read_text())
        output=optimize(data)
        output['optimized_instructions'][2]['inputs']=['t#1','t#1']
        with patch('isa_scheduler.optimizer.original_candidate',return_value=output):
            with self.assertRaises(VerificationFailed):optimize(data)


if __name__=='__main__':unittest.main()
