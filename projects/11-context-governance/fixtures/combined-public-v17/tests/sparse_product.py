from solution import sparse_product
class Check(unittest.TestCase):
    def test_dense_oracle(self):
        import random
        rng=random.Random(110804)
        for _ in range(100):
            rows,inner,cols=[rng.randrange(5) for _ in range(3)]
            left={(i,k):rng.randrange(-3,4) for i in range(rows) for k in range(inner) if rng.random()<.5}
            right={(k,j):rng.randrange(-3,4) for k in range(inner) for j in range(cols) if rng.random()<.5}
            oldl=left.copy(); oldr=right.copy(); expected={}
            for i in range(rows):
                for j in range(cols):
                    value=sum(left.get((i,k),0)*right.get((k,j),0) for k in range(inner))
                    if value: expected[i,j]=value
            self.assertEqual(sparse_product(left,right,rows,inner,cols),expected)
            self.assertEqual(left,oldl); self.assertEqual(right,oldr)
    def test_zero_entry_validation(self):
        for left,right,shape in [({(0,2):0},{},(1,2,1)),({},{(-1,0):0},(1,2,1)),({},{},(-1,0,0)),({},{},(65,0,0))]:
            with self.assertRaises(ValueError): sparse_product(left,right,*shape)

    def test_existing_exports(self):
        import solution
        marker=object()
        self.assertEqual(solution.RELEASE_TAG,"stable-3")
        self.assertIs(solution.compatibility(marker),marker)

if __name__ == "__main__": unittest.main()
