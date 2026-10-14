from solution import total_csv
class Check(unittest.TestCase):
    def test_values(self):
        for text, expected in [("", 0), (", ,", 0), ("1,2,-3", 0), (" 4 , , +7, -9 ", 2), ("8", 8)]:
            self.assertEqual(total_csv(text), expected)
    def test_invalid(self):
        for text in ["1,x", "2,1.2", "nan", "1,--3"]:
            with self.assertRaises(ValueError): total_csv(text)

if __name__ == "__main__": unittest.main()
