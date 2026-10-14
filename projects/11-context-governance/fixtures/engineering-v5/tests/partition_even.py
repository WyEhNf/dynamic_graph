from solution import partition_even
class Check(unittest.TestCase):
    def test_partition(self):
        for values in [[],[-2,-1,0,1,2,2],list(range(-17,18))]:
            before=values[:]; result=partition_even(values)
            self.assertIsInstance(result,tuple)
            self.assertEqual(result,([x for x in values if x%2==0],[x for x in values if x%2])); self.assertEqual(values,before)
            self.assertIsNot(result[0],values); self.assertIsNot(result[1],values)
    def test_helper_use(self):
        import helpers,solution,importlib
        old=helpers.is_even
        try:
            helpers.is_even=lambda x: x>0
            importlib.reload(solution)
            self.assertEqual(solution.partition_even([-1,0,1]),([1],[-1,0]))
        finally: helpers.is_even=old; importlib.reload(solution)

    def test_existing_exports(self):
        import solution
        marker=object()
        self.assertEqual(solution.RELEASE_TAG,"stable-3")
        self.assertIs(solution.compatibility(marker),marker)

if __name__ == "__main__": unittest.main()
