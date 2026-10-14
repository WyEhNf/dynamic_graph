from solution import runs
class Check(unittest.TestCase):
    def test_runs(self):
        import random
        rng=random.Random(1181)
        for _ in range(150):
            values=[rng.choice([0,1,"a","b"]) for _ in range(rng.randrange(50))]; original=values[:]
            groups=runs(values)
            self.assertEqual([v for v,n in groups for _ in range(n)], original)
            self.assertTrue(all(n>0 for _,n in groups))
            self.assertTrue(all(groups[i][0]!=groups[i+1][0] for i in range(len(groups)-1)))
            self.assertEqual(values, original)

if __name__ == "__main__": unittest.main()
