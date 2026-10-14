from solution import shipping_fee
class Check(unittest.TestCase):
    def test_fee(self):
        for weight in range(70):
            self.assertEqual(shipping_fee(weight), 0 if weight >= 23 else 17 + weight * 6)
    def test_invalid(self):
        with self.assertRaises(ValueError): shipping_fee(-1)
    def test_dependency_changes(self):
        import config, importlib, solution
        original = (config.BASE_FEE, config.PER_KG, config.FREE_FROM_KG)
        try:
            for base, rate, threshold in [(3, 2, 5), (9, 7, 3)]:
                config.BASE_FEE, config.PER_KG, config.FREE_FROM_KG = base, rate, threshold
                importlib.reload(solution)
                for weight in range(12):
                    self.assertEqual(solution.shipping_fee(weight), 0 if weight >= threshold else base + weight * rate)
        finally:
            config.BASE_FEE, config.PER_KG, config.FREE_FROM_KG = original
            importlib.reload(solution)

if __name__ == "__main__": unittest.main()
