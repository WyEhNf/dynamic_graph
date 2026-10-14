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
    def test_validation_helper_used(self):
        import helpers,solution,importlib
        original=helpers.validate_nonnegative; calls=[]
        def track(value):
            calls.append(value); return original(value)
        try:
            helpers.validate_nonnegative=track; importlib.reload(solution)
            self.assertEqual(solution.normalize_weights([2,4]),[1/3,2/3]); self.assertEqual(calls,[2,4])
        finally:
            helpers.validate_nonnegative=original; importlib.reload(solution)

if __name__ == "__main__": unittest.main()
