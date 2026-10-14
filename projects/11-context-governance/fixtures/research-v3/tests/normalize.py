from solution import normalize_weights
class Check(unittest.TestCase):
    def test_values(self):
        for values in [[],[1],[2,3,5],[0,1,0],[8,0,4]]:
            original=values[:]; result=normalize_weights(values)
            self.assertEqual(len(result),len(values)); self.assertEqual(values,original)
            for x,y in zip(result,values): self.assertAlmostEqual(x,y/sum(values))
    def test_invalid(self):
        for values in [[-1],[2,-1],[0],[0,0]]:
            with self.assertRaises(ValueError): normalize_weights(values)

if __name__ == "__main__": unittest.main()
