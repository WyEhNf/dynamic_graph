import itertools
import unittest
from solution import wildcard_match
def words(alphabet,maximum):
    return [''.join(chars) for n in range(maximum+1) for chars in itertools.product(alphabet,repeat=n)]
def enumerative_match(text,pattern):
    # Independent exhaustive split choices, not the reference's DP algorithm.
    if not pattern: return not text
    head=pattern[0]
    if head=='*': return any(enumerative_match(text[k:],pattern[1:]) for k in range(len(text)+1))
    return bool(text) and (head=='?' or head==text[0]) and enumerative_match(text[1:],pattern[1:])
class Evaluation(unittest.TestCase):
    def test_exhaustive_small_strings_patterns(self):
        for text in words('ab',4):
            for pattern in words('ab?*',4):
                self.assertIs(wildcard_match(text,pattern),bool(enumerative_match(text,pattern)))
    def test_unicode_literals_anchors_types_and_empty(self):
        for text,pattern in [('中🙂a','?*a'),('a[b].c','a[b].c'),('abc','*b*'),('','?'),('a',''),('abc','**a**c**'),('中中','中?')]:
            self.assertIs(wildcard_match(text,pattern),bool(enumerative_match(text,pattern)))
        for text,pattern in [(1,'*'),('a',None),([],''),('',{})]:
            with self.assertRaises(ValueError): wildcard_match(text,pattern)
