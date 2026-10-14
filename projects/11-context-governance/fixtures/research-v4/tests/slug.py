from solution import slug
class Check(unittest.TestCase):
    def test_examples(self):
        examples = {"Hello, WORLD!": "hello-world", "a___b": "a-b", "": "", "--": "", "42 B": "42-b", "中文 abc": "abc", "a  b   c": "a-b-c"}
        for x, y in examples.items(): self.assertEqual(slug(x), y)
    def test_properties(self):
        import random, string
        rng = random.Random(1104)
        for _ in range(100):
            text = ''.join(rng.choice(string.ascii_letters + string.digits + " ._!") for _ in range(40))
            words = []; current = ''
            for c in text.lower():
                if c in string.ascii_lowercase + string.digits: current += c
                elif current: words.append(current); current = ''
            if current: words.append(current)
            self.assertEqual(slug(text), '-'.join(words))

if __name__ == "__main__": unittest.main()
