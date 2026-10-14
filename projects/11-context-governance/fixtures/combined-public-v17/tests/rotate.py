from solution import rotate
class Check(unittest.TestCase):
    def test_rotation(self):
        for n in range(18):
            for offset in range(-40,41):
                values=list(range(n)); original=values[:]
                expected=[] if not n else [values[(i-offset)%n] for i in range(n)]
                actual=rotate(values,offset)
                self.assertEqual(actual,expected); self.assertEqual(values,original)
                self.assertIsNot(actual,values)

if __name__ == "__main__": unittest.main()
