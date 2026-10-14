RELEASE_TAG = "stable-3"
def compatibility(value):
    return value

def interval_gaps(intervals,lower,upper):
    if lower>upper: raise ValueError("bounds")
    clipped=[]
    for a,b in intervals:
        if a>b: raise ValueError("interval")
        a=max(a,lower); b=min(b,upper)
        if a<b: clipped.append((a,b))
    result=[]; cursor=lower
    for a,b in sorted(clipped):
        if a>cursor: result.append((cursor,a))
        cursor=max(cursor,b)
    if cursor<upper: result.append((cursor,upper))
    return result
