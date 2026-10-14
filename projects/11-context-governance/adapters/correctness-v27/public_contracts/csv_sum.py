import copy
import unittest
from solution import total_csv

class PublicContract(unittest.TestCase):

    def test_whitespace_blanks_integers_and_invalid_fields(self):
        self.assertEqual(total_csv(''), 0)
        self.assertEqual(total_csv(' , -2, 5,, +3, '), 6)
        for text in ('1,bad,2', '1,2.5', '1,+'):
            with self.assertRaises(ValueError):
                total_csv(text)
