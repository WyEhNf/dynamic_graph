from solution import shipping_fee
from config import BASE_FEE, PER_KG, FREE_FROM_KG
class Check(unittest.TestCase):
    def test_fee(self):
        for weight in range(70):
            self.assertEqual(shipping_fee(weight), 0 if weight >= FREE_FROM_KG else BASE_FEE + weight * PER_KG)
    def test_invalid(self):
        with self.assertRaises(ValueError): shipping_fee(-1)

if __name__ == "__main__": unittest.main()
