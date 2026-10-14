from solution import cache_trace
class Check(unittest.TestCase):
    def test_random_trace(self):
        import random
        rng=random.Random(111304)
        for capacity in range(5):
            for _ in range(45):
                entries={}; rank=[]; answer=[]; operations=[]; now=0
                for j in range(35):
                    now+=rng.randrange(3); key=rng.choice("abcd"); action=rng.choice(["put","get"])
                    value=rng.randrange(-5,6) if action=="put" else None; ttl=rng.randrange(7) if action=="put" else None
                    operations.append((now,action,key,value,ttl))
                    expired=[k for k in rank if entries[k][1]<=now]
                    for k in expired: rank.remove(k); del entries[k]
                    if action=="get":
                        answer.append(entries[key][0] if key in entries else None)
                        if key in entries: rank.remove(key); rank.append(key)
                    else:
                        if key in entries: rank.remove(key); del entries[key]
                        if ttl and capacity:
                            entries[key]=(value,now+ttl); rank.append(key)
                            if len(rank)>capacity: victim=rank.pop(0); del entries[victim]
                before=operations[:]
                self.assertEqual(cache_trace(capacity,operations),(answer,{k:v[0] for k,v in entries.items()}))
                self.assertEqual(operations,before)
    def test_validation(self):
        cases=[[(1,"put","a",1,1),(0,"get","a",None,None)],[(0,"x","a",None,None)],[(0,"get","a",1,None)],[(0,"put","a",1,-1)],[(0,"put",4,1,1)],[(0,"put","a",1.5,1)]]
        for operations in cases:
            with self.assertRaises(ValueError): cache_trace(0,operations)
        with self.assertRaises(ValueError): cache_trace(-1,[])
    def test_capacity_helper_result(self):
        import helpers,importlib,solution
        old=helpers.checked_capacity; seen=[]
        def capped(value): seen.append(value); old(value); return 1
        helpers.checked_capacity=capped
        try:
            importlib.reload(solution)
            answer=solution.cache_trace(3,[(0,"put","a",1,10),(0,"put","b",2,10),(1,"get","a",None,None)])
            self.assertEqual(answer,([None],{"b":2})); self.assertEqual(seen,[3])
        finally:
            helpers.checked_capacity=old
            importlib.reload(solution)

    def test_existing_exports(self):
        import solution
        marker=object()
        self.assertEqual(solution.RELEASE_TAG,"stable-3")
        self.assertIs(solution.compatibility(marker),marker)

if __name__ == "__main__": unittest.main()
