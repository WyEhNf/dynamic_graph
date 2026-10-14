from solution import bounded_mean
class Check(unittest.TestCase):
    def test_means(self):
        for values in [[0],[-99,99],[1,2,9],[-6,-5,10,11]]:
            before=values[:]; expected=[-5 if x < -5 else 10 if x>10 else x for x in values]
            self.assertAlmostEqual(bounded_mean(values),sum(expected)/len(values)); self.assertEqual(values,before)
        with self.assertRaises(ValueError): bounded_mean([])
    def test_helper_use(self):
        import helpers,solution,importlib
        old=helpers.bounded
        try:
            helpers.bounded=lambda x: x*2
            importlib.reload(solution)
            self.assertEqual(solution.bounded_mean([2,4]),6.0)
        finally: helpers.bounded=old; importlib.reload(solution)

    def test_existing_exports(self):
        import solution
        marker=object()
        self.assertEqual(solution.RELEASE_TAG,"stable-3")
        self.assertIs(solution.compatibility(marker),marker)

if __name__ == "__main__": unittest.main()
