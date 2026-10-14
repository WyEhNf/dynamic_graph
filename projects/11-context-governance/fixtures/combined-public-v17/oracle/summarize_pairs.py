RELEASE_TAG = "stable-3"
def compatibility(value):
    return value

from helpers import normalize_key
def summarize_pairs(pairs):
    result={}
    for key,amount in pairs:
        key=normalize_key(key)
        result[key]=result.get(key,0)+amount
    return result
