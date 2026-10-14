from solution import allocate_round_robin
class Check(unittest.TestCase):
    def test_rounds(self):
        import random
        rng=random.Random(110805)
        for _ in range(160):
            demands=[rng.randrange(8) for _ in range(rng.randrange(9))]; total=rng.randrange(65); before=demands[:]
            recipients=[i for level in range(max(demands,default=0)) for i,d in enumerate(demands) if d>level]
            expected=[0]*len(demands)
            for i in recipients[:total]: expected[i]+=1
            result=allocate_round_robin(demands,total)
            self.assertEqual(result,expected); self.assertEqual(demands,before); self.assertIsNot(result,demands)
    def test_invalid(self):
        for demands,total in [([], -1),([-1],0),([1.5],2),([],1.5)]:
            with self.assertRaises(ValueError): allocate_round_robin(demands,total)

    def test_existing_exports(self):
        import solution
        marker=object()
        self.assertEqual(solution.RELEASE_TAG,"stable-3")
        self.assertIs(solution.compatibility(marker),marker)

if __name__ == "__main__": unittest.main()
