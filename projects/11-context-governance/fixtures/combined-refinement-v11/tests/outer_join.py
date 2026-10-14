from solution import outer_join
class Check(unittest.TestCase):
    def test_duplicate_order(self):
        self.assertEqual(outer_join([("b",1),("a",2),("b",3)],[("b",4),("c",5),("b",6)]),[("b",1,4),("b",1,6),("a",2,None),("b",3,4),("b",3,6),("c",None,5)])
    def test_random(self):
        import random
        rng=random.Random(110806)
        for _ in range(160):
            left=[(rng.choice("abc"),rng.randrange(7)) for _ in range(rng.randrange(8))]
            right=[(rng.choice("abcd"),rng.randrange(7)) for _ in range(rng.randrange(8))]
            oldl=left[:]; oldr=right[:]; bykey={}
            for key,value in right: bykey.setdefault(key,[]).append(value)
            expected=[]
            for key,value in left:
                for other in bykey.get(key,[None]): expected.append((key,value,other))
            for key,value in right:
                if all(key!=k for k,v in left): expected.append((key,None,value))
            result=outer_join(left,right)
            self.assertEqual(result,expected); self.assertEqual(left,oldl); self.assertEqual(right,oldr)

    def test_existing_exports(self):
        import solution
        marker=object()
        self.assertEqual(solution.RELEASE_TAG,"stable-3")
        self.assertIs(solution.compatibility(marker),marker)

if __name__ == "__main__": unittest.main()
