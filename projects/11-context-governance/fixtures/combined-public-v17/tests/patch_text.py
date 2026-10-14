from solution import patch_text
class Check(unittest.TestCase):
    def test_original_coordinates(self):
        self.assertEqual(patch_text("abcdef",[(4,6,"Y"),(1,3,"X"),(1,1,"A"),(3,3,"B"),(1,1,"C")]),"aACXBdY")
        self.assertEqual(patch_text("",[(0,0,"a"),(0,0,"b")]),"ab")
    def test_random(self):
        import random
        rng=random.Random(111303)
        for _ in range(220):
            text="abcdefghijkl"; edits=[]; removals={}; inserts={}; p=0
            while p<len(text):
                if rng.random()<.3:
                    end=min(len(text),p+rng.randrange(1,4)); removals[p]=(end,str(p)); edits.append((p,end,str(p))); p=end
                else: p+=1
            legal=[p for p in range(len(text)+1) if not any(s<p<e for s,(e,r) in removals.items())]
            for _ in range(5):
                p=rng.choice(legal); value=rng.choice("XYZ"); edits.append((p,p,value))
            rng.shuffle(edits); old=edits[:]
            for s,e,r in edits:
                if s==e: inserts.setdefault(s,[]).append(r)
            expected=[]
            for p in range(len(text)+1):
                if any(s<p<e for s,(e,r) in removals.items()): continue
                expected.extend(inserts.get(p,[]))
                if p in removals: expected.append(removals[p][1])
                elif p<len(text) and not any(s<=p<e for s,(e,r) in removals.items()): expected.append(text[p])
            self.assertEqual(patch_text(text,edits),"".join(expected)); self.assertEqual(edits,old)
    def test_reject(self):
        for edits in [[(0,3,"a"),(2,4,"b")],[(0,3,"a"),(1,1,"b")],[(-1,0,"")],[(0,5,"")],[(0,1,2)],[(.0,1,"")]]:
            with self.assertRaises(ValueError): patch_text("abcd",edits)

    def test_existing_exports(self):
        import solution
        marker=object()
        self.assertEqual(solution.RELEASE_TAG,"stable-3")
        self.assertIs(solution.compatibility(marker),marker)

if __name__ == "__main__": unittest.main()
