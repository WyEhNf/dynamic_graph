import sqlite3
import tempfile
import unittest
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from context_governance.session_metrics import SessionMetrics


class TestSessionMetrics(unittest.TestCase):
    def test_parallel_records_weighted_totals_and_quality_regression(self):
        with tempfile.TemporaryDirectory() as folder:
            ledger=SessionMetrics(Path(folder)/'metrics.sqlite3')
            def write(index):
                ledger.record_pair('session',str(index),baseline_tokens=100 if index==0 else 1000,
                    compressed_tokens=90 if index==0 else 100,baseline_ttft_ms=100,
                    compressed_ttft_ms=40,baseline_correct=True,compressed_correct=index!=3,
                    importance_ms=10,governance_ms=2)
            with ThreadPoolExecutor(max_workers=4) as executor:
                list(executor.map(write,range(4)))
            summary=ledger.summary('session')
            self.assertEqual(summary['requests'],4)
            self.assertAlmostEqual(summary['aggregate_compression_ratio'],1-390/3100)
            self.assertEqual(summary['paired_regressions'],['3'])
            self.assertFalse(summary['quality_gate_passed'])
            with self.assertRaises(sqlite3.IntegrityError): write(0)
            self.assertEqual(ledger.summary('session')['requests'],4)

    def test_unknown_and_invalid_metrics_do_not_become_success(self):
        with tempfile.TemporaryDirectory() as folder:
            ledger=SessionMetrics(Path(folder)/'metrics.sqlite3')
            self.assertIsNone(ledger.summary('empty')['quality_gate_passed'])
            arguments=dict(baseline_tokens=100,compressed_tokens=10,baseline_ttft_ms=100,
                compressed_ttft_ms=20,baseline_correct=True,compressed_correct=True,importance_ms=1,governance_ms=2)
            for field,value in [('baseline_tokens',0),('compressed_tokens',True),('compressed_ttft_ms',float('nan')),
                                ('importance_ms',-1),('compressed_correct','not evaluated')]:
                with self.assertRaises(ValueError): ledger.record_pair('s',field,**{**arguments,field:value})
            self.assertEqual(ledger.summary('s')['requests'],0)
