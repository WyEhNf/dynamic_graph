import copy
from collections import Counter
import unittest
from unittest.mock import patch
import solution

class PublicContract(unittest.TestCase):

    def test_values_full_validation_and_helper(self):
        original = {'a': 4, 'b': 7}
        operations = [('add', 'a', 2), ('delete', 'b', None), ('set', 'c', 9)]
        frozen = copy.deepcopy((original, operations))
        with patch.object(solution, 'checked_integer', wraps=solution.checked_integer) as helper:
            self.assertEqual(solution.transactional_edits(original, operations), {'a': 6, 'c': 9})
            calls = Counter((c.args[0] for c in helper.call_args_list))
            self.assertTrue(all((calls[value] >= count for value, count in Counter([4, 7, 2, 9]).items())))
        self.assertEqual((original, operations), frozen)
        for original, operations in [({'x': 'bad'}, [('delete', 'x', None)]), ({1: 2}, []), ({'x': 1}, [('delete', 'x', 5)]), ({}, [('add', 'x', 1)]), ({}, [('set', 'x', 'bad')]), ({}, [('other', 'x', 1)]), ({}, [('set', 2, 3)])]:
            with self.assertRaises(ValueError):
                solution.transactional_edits(original, operations)

    def test_failure_atomicity_and_empty_copy(self):
        original = {'a': 4}
        operations = [('set', 'a', 8), ('delete', 'missing', None)]
        frozen = copy.deepcopy((original, operations))
        with self.assertRaises(ValueError):
            solution.transactional_edits(original, operations)
        self.assertEqual((original, operations), frozen)
        self.assertIsNot(solution.transactional_edits(original, []), original)
