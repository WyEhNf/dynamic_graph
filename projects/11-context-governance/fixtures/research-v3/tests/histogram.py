from solution import histogram
class Check(unittest.TestCase):
    def test_counts(self):
        import random
        rng=random.Random(1185)
        for _ in range(120):
            values=[rng.choice([1,2,"x","y"]) for _ in range(rng.randrange(35))]; original=values[:]
            result=histogram(values)
            self.assertEqual(list(result),list(dict.fromkeys(values)))
            self.assertEqual(result,{x:values.count(x) for x in values}); self.assertEqual(values,original)

if __name__ == "__main__": unittest.main()
