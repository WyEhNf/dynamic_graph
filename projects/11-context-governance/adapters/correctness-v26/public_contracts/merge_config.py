import copy
import unittest
import solution

class PublicContract(unittest.TestCase):
    def test_nested_replacement_deletion_and_exports(self):
        base = {'a':{'keep':1,'gone':2}, 'ordinary':None, 'replaced':{'old':3}}
        override = {'a':{'gone':None,'new':4}, 'replaced':'text', 'missing':None, 'insert':{'n':5}}
        frozen = copy.deepcopy((base,override))
        actual = solution.merge_config(base,override)
        self.assertEqual(actual, {'a':{'keep':1,'new':4},'ordinary':None,'replaced':'text','insert':{'n':5}})
        self.assertEqual((base,override), frozen)
        self.assertEqual(solution.RELEASE_TAG, 'stable-3')
        marker = object()
        self.assertIs(solution.compatibility(marker), marker)

    def test_validate_all_branches_and_recursive_independence(self):
        for base,override in [({'a':{'bad':[]}}, {'a':None}), ({'a':{2:3}}, {'a':1}), ({}, {'a':{'bad':object()}})]:
            with self.assertRaises(ValueError): solution.merge_config(base,override)
        base = {'unchanged':{'deep':{'v':1}}}
        override = {'inserted':{'deep':{'v':2}}}
        frozen = copy.deepcopy((base,override))
        actual = solution.merge_config(base,override)
        actual['unchanged']['deep']['v'] = 8
        actual['inserted']['deep']['v'] = 9
        self.assertEqual((base,override), frozen)
        self.assertIsNot(solution.merge_config(base,{}), base)
