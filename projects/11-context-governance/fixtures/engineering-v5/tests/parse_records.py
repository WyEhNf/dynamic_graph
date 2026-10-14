from solution import parse_records
class Check(unittest.TestCase):
    def test_records(self):
        self.assertEqual(parse_records(" a : +3\n\nb:-2\na:4 "),[("a",3),("b",-2),("a",4)])
        self.assertEqual(parse_records(" \n\t"),[])
    def test_invalid(self):
        for text in ["x",":3","x:nan","x:1:2"]:
            with self.assertRaises(ValueError): parse_records(text)
    def test_config_chain(self):
        import config
        old=config.SEPARATOR
        try:
            config.SEPARATOR="|"
            self.assertEqual(parse_records("a|3\nb|-4"),[("a",3),("b",-4)])
        finally: config.SEPARATOR=old

    def test_existing_exports(self):
        import solution
        marker=object()
        self.assertEqual(solution.RELEASE_TAG,"stable-3")
        self.assertIs(solution.compatibility(marker),marker)

if __name__ == "__main__": unittest.main()
