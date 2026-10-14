from solution import shortest_layers
class Check(unittest.TestCase):
    def test_distances(self):
        import random
        rng=random.Random(110802)
        for n in range(1,10):
            for _ in range(15):
                edges=[(u,v) for u in range(n) for v in range(n) if rng.random()<.2]; start=rng.randrange(n); before=edges[:]
                distance=[n+1]*n; distance[start]=0
                for _ in range(n):
                    for u,v in edges: distance[v]=min(distance[v],distance[u]+1)
                expected=[[v for v in range(n) if distance[v]==d] for d in range(n)]
                expected=[layer for layer in expected if layer]
                self.assertEqual(shortest_layers(n,edges,start),expected); self.assertEqual(edges,before)
    def test_validate_unreachable(self):
        for n,edges,start in [(3,[(2,3)],0),(0,[],0),(3,[],-1),(65,[],0)]:
            with self.assertRaises(ValueError): shortest_layers(n,edges,start)

    def test_existing_exports(self):
        import solution
        marker=object()
        self.assertEqual(solution.RELEASE_TAG,"stable-3")
        self.assertIs(solution.compatibility(marker),marker)

if __name__ == "__main__": unittest.main()
