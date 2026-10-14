from solution import merge_config
class Check(unittest.TestCase):
    def test_recursive(self):
        import copy,random
        rng=random.Random(111302)
        def tree(depth):
            out={}
            for key in "abcd":
                if rng.random()<.6: out[key]=tree(depth-1) if depth and rng.random()<.45 else rng.choice([None,-2,4,"x"])
            return out
        def expected(left,right):
            result=copy.deepcopy(left)
            for k,v in right.items():
                if v is None: result.pop(k,None)
                elif isinstance(v,dict) and isinstance(left.get(k),dict): result[k]=expected(left[k],v)
                else: result[k]=copy.deepcopy(v)
            return result
        for _ in range(160):
            base=tree(3); override=tree(3); oldb=copy.deepcopy(base); oldo=copy.deepcopy(override)
            self.assertEqual(merge_config(base,override),expected(base,override))
            self.assertEqual(base,oldb); self.assertEqual(override,oldo)
    def test_no_nested_alias(self):
        base={"stay":{"x":1},"merge":{"a":2},"none":None}; override={"new":{"y":3},"merge":{"b":4}}
        out=merge_config(base,override); out["stay"]["x"]=8; out["new"]["y"]=9; out["merge"]["a"]=0
        self.assertEqual(base,{"stay":{"x":1},"merge":{"a":2},"none":None})
        self.assertEqual(override,{"new":{"y":3},"merge":{"b":4}})
        self.assertEqual(merge_config({"a":None},{"z":None}),{"a":None})
    def test_full_validation(self):
        for base,override in [({"x":{"bad":[]}}, {"x":None}),({"x":1},{"x":2.4}),({1:3},{1:None}),({"x":1},{"x":{2:3}}),([],{}),({},None)]:
            with self.assertRaises(ValueError): merge_config(base,override)

    def test_existing_exports(self):
        import solution
        marker=object()
        self.assertEqual(solution.RELEASE_TAG,"stable-3")
        self.assertIs(solution.compatibility(marker),marker)

if __name__ == "__main__": unittest.main()
