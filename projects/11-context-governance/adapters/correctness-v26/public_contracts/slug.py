import copy
import unittest
from solution import slug
class PublicContract(unittest.TestCase):
    def test_ascii_runs_lowercase_and_edges(self):
        for text,expected in [('', ''),('!?!',''),('  HELLO...World 99 ','hello-world-99'),('a中文b','a-b'),('A__--B','a-b'),('123','123')]:
            self.assertEqual(slug(text),expected)
            self.assertEqual(slug(slug(text)),expected)
