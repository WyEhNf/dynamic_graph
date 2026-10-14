from solution import merge_intervals
class Check(unittest.TestCase):
    def test_examples(self):
        for values,expected in [([],[]), ([(4,8),(1,4)],[(1,8)]), ([(1,1),(2,3)],[(1,1),(2,3)]), ([(1,8),(2,3),(10,12)],[(1,8),(10,12)])]:
            original=values[:]; self.assertEqual(merge_intervals(values),expected); self.assertEqual(values,original)
    def test_invalid(self):
        with self.assertRaises(ValueError): merge_intervals([(4,2)])

if __name__ == "__main__": unittest.main()
