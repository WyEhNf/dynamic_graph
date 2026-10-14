from solution import accepted
class Check(unittest.TestCase):
    def test_threshold(self):
        values=list(range(-10,20)); original=values[:]
        self.assertEqual(accepted(values),[x for x in values if x>=7]); self.assertEqual(values,original); self.assertEqual(accepted([]),[])
    def test_dependency(self):
        import config,solution,importlib
        original=config.LIMIT
        try:
            for threshold in [-4,3,12]:
                config.LIMIT=threshold; importlib.reload(solution)
                self.assertEqual(solution.accepted(list(range(-10,20))),[x for x in range(-10,20) if x>=threshold])
        finally:
            config.LIMIT=original; importlib.reload(solution)
    def test_helper_used(self):
        import helpers,solution,importlib
        original=helpers.inclusive
        try:
            helpers.inclusive=lambda value,threshold: value < threshold
            importlib.reload(solution)
            self.assertEqual(solution.accepted(list(range(12))),list(range(7)))
        finally:
            helpers.inclusive=original; importlib.reload(solution)

if __name__ == "__main__": unittest.main()
