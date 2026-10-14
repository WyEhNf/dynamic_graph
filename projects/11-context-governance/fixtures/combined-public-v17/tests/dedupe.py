from solution import stable_unique
class Check(unittest.TestCase):
    def test_unique(self):
        import random
        rng = random.Random(1103)
        for _ in range(120):
            data = [rng.choice([0, 1, 2, "a", "b", ""]) for _ in range(rng.randrange(30))]
            expected = []
            for x in data:
                if x not in expected: expected.append(x)
            original = data[:]
            self.assertEqual(stable_unique(data), expected)
            self.assertEqual(data, original)

if __name__ == "__main__": unittest.main()
