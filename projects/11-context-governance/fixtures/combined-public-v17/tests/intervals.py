from solution import merge_intervals
class Check(unittest.TestCase):
    def test_examples(self):
        for values,expected in [([],[]), ([(4,8),(1,4)],[(1,8)]), ([(1,1),(2,3)],[(1,1),(2,3)]), ([(1,8),(2,3),(10,12)],[(1,8),(10,12)])]:
            original=values[:]; self.assertEqual(merge_intervals(values),expected); self.assertEqual(values,original)
    def test_invalid(self):
        with self.assertRaises(ValueError): merge_intervals([(4,2)])
    def test_half_integer_coverage(self):
        import random
        rng=random.Random(1183)
        for _ in range(150):
            pairs=[tuple(sorted((rng.randrange(-8,9),rng.randrange(-8,9)))) for _ in range(rng.randrange(15))]
            original=pairs[:]; merged=merge_intervals(pairs)
            coverage=lambda intervals: {p for a,b in intervals for p in range(2*a,2*b+1)}
            self.assertEqual(coverage(merged),coverage(original)); self.assertEqual(pairs,original)
            self.assertTrue(all(isinstance(x,tuple) and len(x)==2 and x[0]<=x[1] for x in merged))
            self.assertTrue(all(merged[i][1]<merged[i+1][0] for i in range(len(merged)-1)))

if __name__ == "__main__": unittest.main()
