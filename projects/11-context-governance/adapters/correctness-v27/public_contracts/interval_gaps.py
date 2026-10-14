import copy
import random
import unittest
import solution

class PublicContract(unittest.TestCase):

    def test_validation_even_outside_and_equal_bounds(self):
        for intervals, lower, upper in [([(20, 19)], 0, 3), ([(2, 1)], 0, 0), ([], 3, 2)]:
            with self.assertRaises(ValueError):
                solution.interval_gaps(intervals, lower, upper)
        self.assertEqual(solution.interval_gaps([], 0, 4), [(0, 4)])
        self.assertEqual(solution.interval_gaps([(0, 2), (2, 4)], 0, 4), [])
        self.assertEqual(solution.interval_gaps([(2, 2)], 0, 4), [(0, 4)])

    def test_public_coverage_property_and_no_mutation(self):
        rng = random.Random(260110)
        for _ in range(80):
            lower, upper = sorted((rng.randrange(-5, 6), rng.randrange(-5, 6)))
            intervals = [tuple(sorted((rng.randrange(-8, 9), rng.randrange(-8, 9)))) for _ in range(rng.randrange(7))]
            frozen = copy.deepcopy(intervals)
            result = solution.interval_gaps(intervals, lower, upper)
            expected_points = {x for x in range(lower, upper) if not any((a <= x < b for a, b in intervals))}
            self.assertEqual({x for a, b in result for x in range(a, b)}, expected_points)
            self.assertEqual(result, sorted(result))
            self.assertTrue(all((lower <= a < b <= upper for a, b in result)))
            self.assertTrue(all((a[1] < b[0] for a, b in zip(result, result[1:]))))
            self.assertEqual(intervals, frozen)
