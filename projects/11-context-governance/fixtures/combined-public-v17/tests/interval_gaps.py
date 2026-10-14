from solution import interval_gaps
class Check(unittest.TestCase):
    def test_integer_coverage(self):
        import random
        rng=random.Random(110803)
        for _ in range(160):
            lo=rng.randrange(-10,5); hi=lo+rng.randrange(16)
            intervals=[tuple(sorted((rng.randrange(-15,20),rng.randrange(-15,20)))) for _ in range(rng.randrange(12))]
            before=intervals[:]; cells=[x for x in range(lo,hi) if not any(a<=x<b for a,b in intervals)]
            expected=[]
            for x in cells:
                if expected and expected[-1][1]==x: expected[-1]=(expected[-1][0],x+1)
                else: expected.append((x,x+1))
            self.assertEqual(interval_gaps(intervals,lo,hi),expected); self.assertEqual(intervals,before)
    def test_invalid_outside(self):
        for intervals,lo,hi in [([(100,99)],0,1),([(2,1)],0,0),([],3,2)]:
            with self.assertRaises(ValueError): interval_gaps(intervals,lo,hi)

    def test_existing_exports(self):
        import solution
        marker=object()
        self.assertEqual(solution.RELEASE_TAG,"stable-3")
        self.assertIs(solution.compatibility(marker),marker)

if __name__ == "__main__": unittest.main()
