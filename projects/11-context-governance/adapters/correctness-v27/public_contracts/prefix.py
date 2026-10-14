import copy
import unittest
from solution import common_prefix

class PublicContract(unittest.TestCase):

    def test_unicode_case_empty_and_no_mutation(self):
        for values, expected in [([], ''), (['flower', 'flow', 'flight'], 'fl'), (['中文甲', '中文乙'], '中文'), (['A', 'a'], ''), (['abc', ''], ''), (['alone'], 'alone')]:
            frozen = copy.deepcopy(values)
            self.assertEqual(common_prefix(values), expected)
            self.assertEqual(values, frozen)
