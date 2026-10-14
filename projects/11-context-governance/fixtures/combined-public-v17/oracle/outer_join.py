RELEASE_TAG = "stable-3"
def compatibility(value):
    return value

def outer_join(left,right):
    result=[]; left_keys={key for key,value in left}
    for key,value in left:
        matches=[other for rkey,other in right if rkey==key]
        if matches: result.extend((key,value,other) for other in matches)
        else: result.append((key,value,None))
    result.extend((key,None,value) for key,value in right if key not in left_keys)
    return result
