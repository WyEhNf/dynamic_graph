import copy
import random
import unittest
from solution import merge_intervals

class PublicContract(unittest.TestCase):

    def test_declared_examples_and_validation(self):
        self.assertEqual(merge_intervals([]), [])
        self.assertEqual(merge_intervals([(5, 7), (1, 3), (3, 5)]), [(1, 7)])
        with self.assertRaises(ValueError):
            merge_intervals([(3, 2)])

    def test_coverage_order_idempotence_and_no_mutation(self):
        rng = random.Random(260110)
        for _ in range(80):
            intervals = [tuple(sorted((rng.randrange(-8, 9), rng.randrange(-8, 9)))) for _ in range(rng.randrange(9))]
            frozen = copy.deepcopy(intervals)
            result = merge_intervals(intervals)
            self.assertEqual(intervals, frozen)
            self.assertEqual(result, sorted(result))
            self.assertTrue(all((isinstance(p, tuple) and p[0] <= p[1] for p in result)))
            self.assertTrue(all((a[1] < b[0] for a, b in zip(result, result[1:]))))
            points = range(-16, 17)
            self.assertEqual({p for p in points if any((2 * a <= p <= 2 * b for a, b in intervals))}, {p for p in points if any((2 * a <= p <= 2 * b for a, b in result))})
            self.assertEqual(merge_intervals(result), result)
