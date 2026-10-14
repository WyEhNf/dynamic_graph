RELEASE_TAG = "stable-3"
def compatibility(value):
    return value

from helpers import checked_size,checked_vertex
def stable_topology(n,edges):
    checked_size(n)
    links=set()
    for u,v in edges:
        checked_vertex(u,n); checked_vertex(v,n); links.add((u,v))
    remaining=set(range(n)); result=[]
    while remaining:
        ready=[v for v in remaining if not any(b==v and a in remaining for a,b in links)]
        if not ready: raise ValueError("cycle")
        v=min(ready); remaining.remove(v); result.append(v)
    return result
