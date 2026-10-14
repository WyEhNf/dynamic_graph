from solution import summarize_pairs
class Check(unittest.TestCase):
    def test_totals(self):
        pairs=[(" B ",2),("a",4),("b",-1),(" A",3),(" ",5)]; before=pairs[:]
        result=summarize_pairs(pairs)
        self.assertEqual(result,{"b":1,"a":7,"":5}); self.assertEqual(list(result),["b","a",""])
        self.assertEqual(pairs,before); self.assertEqual(summarize_pairs([]),{})
    def test_helper_use(self):
        import helpers,solution,importlib
        old=helpers.normalize_key
        try:
            helpers.normalize_key=lambda key: "group"
            importlib.reload(solution)
            self.assertEqual(solution.summarize_pairs([("a",3),("b",5)]),{"group":8})
        finally: helpers.normalize_key=old; importlib.reload(solution)

    def test_existing_exports(self):
        import solution
        marker=object()
        self.assertEqual(solution.RELEASE_TAG,"stable-3")
        self.assertIs(solution.compatibility(marker),marker)

if __name__ == "__main__": unittest.main()
