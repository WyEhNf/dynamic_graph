import sys
from pathlib import Path
import unittest
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
from profile_vm_dispatch import load_pairs, trace


class DispatchProfileTests(unittest.TestCase):
    def test_disjoint_triple_and_side_entry(self):
        self.assertEqual(load_pairs([('LOAD', 0.), ('LOAD', 0.), ('LOAD', 0.)]), ({0}, True))
        self.assertEqual(load_pairs([('LOAD', 0.), ('LOAD', 0.), ('JUMP', 1.)]), (set(), True))
        self.assertEqual(load_pairs([('LOAD', 0.), ('LOAD', 0.), ('JUMP', float('nan'))]), (set(), False))

    def test_executed_counts_and_exact_budget_boundary(self):
        fields = {'slots': '1', 'shape_slot': '0'}
        rows = [('LOAD', 0.), ('LOAD', 0.), ('ADD', 0.), ('POP', 0.), ('CONST', 0.), ('RETURN', 0.)]
        output, record = trace(fields, rows, 3, [0.] * 9, limit=6)
        self.assertEqual(record['steps'], 6)
        self.assertEqual(record['executed_load_pairs'], 1)
        self.assertEqual(record['opcode_counts']['LOAD'], 2)
        with self.assertRaisesRegex(ValueError, 'budget'):
            trace(fields, rows, 3, [0.] * 9, limit=5)

    def test_dynamic_loop_frequencies(self):
        fields = {'slots': '2', 'shape_slot': '0'}
        rows = [('CONST', 2.), ('STORE', 1.), ('LOAD', 1.), ('CONST', 1.), ('SUB', 0.),
                ('DUP', 0.), ('STORE', 1.), ('JNZ', 2.), ('CONST', 0.), ('RETURN', 0.)]
        _, record = trace(fields, rows, 3, [0.] * 9)
        self.assertEqual(record['steps'], 16)
        self.assertEqual(record['pc_counts'][2], 2)
        self.assertEqual(record['dynamic_bigram_counts']['JNZ LOAD'], 1)
