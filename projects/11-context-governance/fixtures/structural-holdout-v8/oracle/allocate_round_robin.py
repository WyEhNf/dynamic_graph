RELEASE_TAG = "stable-3"
def compatibility(value):
    return value

def allocate_round_robin(demands,total):
    if not isinstance(total,int) or total<0: raise ValueError("total")
    if any(not isinstance(d,int) or d<0 for d in demands): raise ValueError("demand")
    result=[0]*len(demands)
    while total:
        changed=False
        for i,d in enumerate(demands):
            if result[i]<d and total:
                result[i]+=1; total-=1; changed=True
        if not changed: break
    return result
