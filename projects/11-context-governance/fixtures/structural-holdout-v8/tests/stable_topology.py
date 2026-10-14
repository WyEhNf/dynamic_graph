from solution import stable_topology
class Check(unittest.TestCase):
    def test_random_dags(self):
        import random
        rng=random.Random(110801)
        for n in range(9):
            for _ in range(20):
                order=list(range(n)); rng.shuffle(order)
                edges=[(order[i],order[j]) for i in range(n) for j in range(i+1,n) if rng.random()<.35]
                if edges: edges+=edges[:2]
                rng.shuffle(edges); before=edges[:]
                adj=[set() for _ in range(n)]; indeg=[0]*n
                for u,v in set(edges): adj[u].add(v); indeg[v]+=1
                expected=[]; ready=[i for i in range(n) if not indeg[i]]
                while ready:
                    ready.sort(); u=ready.pop(0); expected.append(u)
                    for v in adj[u]:
                        indeg[v]-=1
                        if not indeg[v]: ready.append(v)
                self.assertEqual(stable_topology(n,edges),expected); self.assertEqual(edges,before)
    def test_invalid(self):
        for n,edges in [(2,[(0,1),(1,0)]),(1,[(0,0)]),(2,[(0,2)]),(-1,[]),(65,[])]:
            with self.assertRaises(ValueError): stable_topology(n,edges)

    def test_existing_exports(self):
        import solution
        marker=object()
        self.assertEqual(solution.RELEASE_TAG,"stable-3")
        self.assertIs(solution.compatibility(marker),marker)

if __name__ == "__main__": unittest.main()
