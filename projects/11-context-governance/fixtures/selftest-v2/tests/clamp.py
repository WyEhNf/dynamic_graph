from solution import clamp
class Check(unittest.TestCase):
    def test_range(self):
        for low in range(-8, 8):
            for high in range(low, 9):
                for value in range(-10, 11):
                    expected = low if value < low else high if value > high else value
                    self.assertEqual(clamp(value, low, high), expected)
    def test_invalid(self):
        with self.assertRaises(ValueError): clamp(1, 3, 2)

if __name__ == "__main__": unittest.main()
