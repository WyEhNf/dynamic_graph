from solution import priced_total
class Check(unittest.TestCase):
    def test_prices(self):
        import random
        rng=random.Random(110611)
        for _ in range(80):
            rows=[(rng.randrange(9),rng.randrange(19)) for _ in range(rng.randrange(12))]; before=rows[:]
            expected=sum(q*p for q,p in rows)
            self.assertEqual(priced_total(rows),expected-7 if expected>=100 else expected)
            self.assertEqual(rows,before)
    def test_invalid(self):
        for rows in [[(-1,2)],[(3,-2)]]:
            with self.assertRaises(ValueError): priced_total(rows)
    def test_helper_dispatch(self):
        import helpers,solution,importlib
        old=helpers.checked_cost
        try:
            helpers.checked_cost=lambda q,p: 17
            importlib.reload(solution)
            self.assertEqual(solution.priced_total([(2,5),(3,4)]),34)
        finally:
            helpers.checked_cost=old; importlib.reload(solution)

    def test_existing_exports(self):
        import solution
        marker=object()
        self.assertEqual(solution.RELEASE_TAG,"stable-3")
        self.assertIs(solution.compatibility(marker),marker)

if __name__ == "__main__": unittest.main()
