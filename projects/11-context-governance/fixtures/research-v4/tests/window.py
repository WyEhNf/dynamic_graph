from solution import window_sums
class Check(unittest.TestCase):
    def test_windows(self):
        for n in range(20):
            values=[i%5-2 for i in range(n)]; original=values[:]
            for size in range(1,23): self.assertEqual(window_sums(values,size),[sum(values[i:i+size]) for i in range(n-size+1)])
            self.assertEqual(values,original)
    def test_invalid(self):
        for size in [0,-2]:
            with self.assertRaises(ValueError): window_sums([1,2],size)

if __name__ == "__main__": unittest.main()
