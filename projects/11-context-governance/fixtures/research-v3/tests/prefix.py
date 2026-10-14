from solution import common_prefix
class Check(unittest.TestCase):
    def test_prefix(self):
        for words,expected in [([],""),(["flower","flow","flight"],"fl"),(["ab","AB"],""),(["中文甲","中文乙"],"中文"),(["a",""],""),(["same"],"same")]:
            original=words[:]; self.assertEqual(common_prefix(words),expected); self.assertEqual(words,original)

if __name__ == "__main__": unittest.main()
