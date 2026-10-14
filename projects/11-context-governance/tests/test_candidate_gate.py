import json
from pathlib import Path
import tempfile
import unittest

from context_governance.candidate_gate import final_answer, search_candidates, search_public_code, verify_public_contract


class CandidateGateTests(unittest.TestCase):
    def test_real_public_failure_repair_and_unchanged_snapshot(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            snapshot = root / 'repo'
            snapshot.mkdir()
            source = 'def answer(x): return 0\n'
            (snapshot / 'target.py').write_text(source)
            test = root / 'public.py'
            test.write_text('import unittest\nfrom target import answer\nclass Checks(unittest.TestCase):\n'
                            '    def test_public(self):\n        self.assertEqual(answer(3), 6)\n'
                            '        self.assertEqual(answer(-2), -4)\n')
            seen = []
            def prompt(previous, feedback):
                seen.append((previous, feedback))
                return 'Public specification: double x.\n' + (feedback or '')
            candidates = [source, 'def answer(x): return x * 2\n']
            result = search_public_code(lambda p, i: {'final_output': candidates[i]}, prompt,
                                        snapshot, 'target.py', test)
            self.assertEqual((result.status, result.selected), ('PUBLIC_CHECKED_NOT_PROVED', 1))
            self.assertFalse(result.attempts[0]['public_check']['passed'])
            self.assertIn('AssertionError', seen[1][1])
            self.assertTrue(result.attempts[1]['public_check']['dependencies_unchanged'])
            self.assertEqual((snapshot / 'target.py').read_text(), source)

    def test_truncation_missing_output_exhaustion_and_strict_checker(self):
        result = search_candidates(lambda p, i: {'protocol_error': 'truncated'},
            lambda x: self.fail('must not execute'), lambda p, f: 'p', 2)
        self.assertIsNone(result.selected)
        self.assertEqual(len(result.attempts), 2)
        result = search_candidates(lambda p, i: {}, lambda x: self.fail('must not execute'), lambda p, f: 'p')
        self.assertIsNone(result.selected)
        with self.assertRaises(ValueError):
            search_candidates(lambda p, i: {'final_output': 'x'}, lambda x: {'passed': 'false'}, lambda p, f: 'p')

    def test_contract_hashes_match_all30_without_reference_access(self):
        project = Path(__file__).resolve().parents[1]
        contracts = project / 'adapters/correctness-v27'
        suite = project / 'fixtures/combined-public-v17'
        manifest = json.loads((contracts / 'contract-manifest.json').read_text())
        self.assertEqual(len(manifest['cases']), 30)
        for case in manifest['cases']:
            verify_public_contract(contracts, suite, case)
        with self.assertRaises(ValueError):
            verify_public_contract(contracts, suite, '../escape')

    def test_no_reasoning_draft_is_selected(self):
        for raw in ('<think>draft', '<think>a</think>b</think>c', '<think>a</think><think>b'):
            with self.assertRaises(ValueError):
                final_answer(raw)
        self.assertEqual(final_answer('<think>draft</think>final'), 'final')
