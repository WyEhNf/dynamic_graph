from solution import choose_records
class Check(unittest.TestCase):
    def test_selection(self):
        data=[("a",3),("b",4),("c",7),("b",4)]; before=data[:]
        self.assertEqual(choose_records(data),data[1:]); self.assertEqual(data,before)
        self.assertEqual(choose_records([]),[])
    def test_dependency_use(self):
        import helpers,solution,importlib
        old=helpers.qualifies
        try:
            helpers.qualifies=lambda x: x<4
            importlib.reload(solution)
            self.assertEqual(solution.choose_records([("a",3),("b",4)]),[("a",3)])
        finally: helpers.qualifies=old; importlib.reload(solution)

    def test_existing_exports(self):
        import solution
        marker=object()
        self.assertEqual(solution.RELEASE_TAG,"stable-3")
        self.assertIs(solution.compatibility(marker),marker)

if __name__ == "__main__": unittest.main()
