from solution import transactional_edits
class Check(unittest.TestCase):
    def test_sequences(self):
        import random
        rng=random.Random(111301)
        for _ in range(180):
            original={key:rng.randrange(-5,6) for key in "abc"}; expected=dict(original); operations=[]
            for j in range(15):
                key=rng.choice("abcd"); action=rng.choice(["set","add","delete"])
                if action!="set" and key not in expected: action="set"
                value=None if action=="delete" else rng.randrange(-4,5)
                operations.append((action,key,value))
                if action=="delete": del expected[key]
                elif action=="set": expected[key]=value
                else: expected[key]=expected[key]+value
            before=dict(original); oldops=operations[:]
            answer=transactional_edits(original,operations)
            self.assertEqual(answer,expected); self.assertIsNot(answer,original)
            self.assertEqual(original,before); self.assertEqual(operations,oldops)
    def test_failure_atomicity(self):
        for operations in [[("set","a",8),("add","missing",2)],[("delete","a",None),("x","b",1)],[("set","x",1.2)],[("delete","a",0)],[("set",2,3)]]:
            original={"a":3}; before=dict(original)
            with self.assertRaises(ValueError): transactional_edits(original,operations)
            self.assertEqual(original,before)
        with self.assertRaises(ValueError): transactional_edits({"bad":"3"},[("delete","bad",None)])
    def test_helper_boundary(self):
        import helpers
        old=helpers.checked_integer; seen=[]
        def track(value): seen.append(value); return old(value)
        helpers.checked_integer=track
        try:
            import importlib,solution
            importlib.reload(solution)
            self.assertEqual(solution.transactional_edits({"a":7},[("set","b",4),("add","a",2)]),{"a":9,"b":4})
            self.assertEqual(seen,[7,4,2])
        finally:
            helpers.checked_integer=old
            importlib.reload(solution)

    def test_existing_exports(self):
        import solution
        marker=object()
        self.assertEqual(solution.RELEASE_TAG,"stable-3")
        self.assertIs(solution.compatibility(marker),marker)

if __name__ == "__main__": unittest.main()
