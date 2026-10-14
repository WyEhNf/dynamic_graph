RELEASE_TAG = "stable-3"
def compatibility(value):
    return value

from helpers import checked_size,checked_vertex
def shortest_layers(n,edges,start):
    checked_size(n); checked_vertex(start,n)
    adj=[set() for _ in range(n)]
    for u,v in edges:
        checked_vertex(u,n); checked_vertex(v,n); adj[u].add(v)
    seen={start}; frontier=[start]; result=[]
    while frontier:
        result.append(sorted(frontier))
        following=set()
        for u in frontier: following.update(adj[u])
        following-=seen; seen.update(following); frontier=list(following)
    return result
