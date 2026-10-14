RELEASE_TAG = "stable-3"
def compatibility(value):
    return value

from helpers import checked_capacity
def cache_trace(capacity,operations):
    capacity=checked_capacity(capacity); cache={}; results=[]; previous=0
    for now,action,key,value,ttl in operations:
        if not isinstance(now,int) or now<previous or now<0 or not isinstance(key,str): raise ValueError("fields")
        previous=now
        if action=="put":
            if not isinstance(value,int) or not isinstance(ttl,int) or ttl<0: raise ValueError("put")
        elif action=="get":
            if value is not None or ttl is not None: raise ValueError("get")
        else: raise ValueError("action")
        for item in list(cache):
            if cache[item][1]<=now: del cache[item]
        if action=="get":
            entry=cache.pop(key,None); results.append(None if entry is None else entry[0])
            if entry is not None: cache[key]=entry
        else:
            cache.pop(key,None)
            if ttl and capacity:
                cache[key]=(value,now+ttl)
                while len(cache)>capacity: del cache[next(iter(cache))]
    return results,{key:value for key,(value,expiry) in cache.items()}
