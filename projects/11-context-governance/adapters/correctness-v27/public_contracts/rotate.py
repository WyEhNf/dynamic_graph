import copy
import unittest
from solution import rotate

class PublicContract(unittest.TestCase):

    def test_modular_right_rotation_fresh_and_input(self):
        values = [1, 2, 3, 4]
        frozen = values[:]
        for offset in range(-10, 11):
            actual = rotate(values, offset)
            self.assertIsNot(actual, values)
            self.assertEqual(actual, [values[(i - offset) % len(values)] for i in range(len(values))])
            self.assertEqual(rotate(actual, -offset), values)
            self.assertEqual(values, frozen)
        self.assertEqual(rotate([], 100), [])
