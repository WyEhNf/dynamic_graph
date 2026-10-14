from solution import chunks
class Check(unittest.TestCase):
    def test_chunks(self):
        for n in range(35):
            for size in range(1, 12):
                data = list(range(n)); original = data[:]
                result = chunks(data, size)
                self.assertEqual([x for group in result for x in group], original)
                self.assertTrue(all(len(g) == size for g in result[:-1]))
                self.assertTrue(not result or 0 < len(result[-1]) <= size)
                self.assertEqual(data, original)
    def test_invalid(self):
        for size in [0, -1]:
            with self.assertRaises(ValueError): chunks([1], size)

if __name__ == "__main__": unittest.main()
