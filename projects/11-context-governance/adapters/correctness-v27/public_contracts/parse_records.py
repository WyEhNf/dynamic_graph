from collections import Counter
import copy
import unittest
import solution
from unittest.mock import patch

class PublicContract(unittest.TestCase):

    def test_helper_every_nonblank_line_order_and_errors(self):
        text = 'first\n  \nsecond\nfirst'

        def parse(line):
            return (line.strip(), len(line.strip()))
        with patch.object(solution, 'parse_record', side_effect=parse) as helper:
            self.assertEqual(solution.parse_records(text), [('first', 5), ('second', 6), ('first', 5)])
            self.assertFalse(Counter(['first', 'second', 'first']) - Counter([c.args[0].strip() for c in helper.call_args_list]))
        with patch.object(solution, 'parse_record', side_effect=ValueError('public malformed')):
            with self.assertRaises(ValueError):
                solution.parse_records('malformed')
        self.assertEqual(solution.parse_records('  \n'), [])
