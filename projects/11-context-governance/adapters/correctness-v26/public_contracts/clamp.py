import copy
import unittest
from solution import clamp
class PublicContract(unittest.TestCase):
    def test_values_and_reversed_bounds(self):
        for low in range(-3,4):
            for high in range(low,4):
                for value in range(-5,6):
                    actual=clamp(value,low,high)
                    self.assertTrue(low<=actual<=high)
                    self.assertEqual(actual,value if low<=value<=high else low if value<low else high)
        with self.assertRaises(ValueError): clamp(0,2,1)
