import unittest
from solution import wildcard_match
class PublicContract(unittest.TestCase):
    def test_declared_pattern_semantics(self):
        for text,pattern,expected in [('ab','a?',True),('abc','a*c',True),('abc','a',False),('','**',True),('中a','?a',True),('a.b','a.b',True)]:
            self.assertIs(wildcard_match(text,pattern),expected)
        with self.assertRaises(ValueError): wildcard_match(None,'*')
