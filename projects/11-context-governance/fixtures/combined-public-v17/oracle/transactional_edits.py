RELEASE_TAG = "stable-3"
def compatibility(value):
    return value

from helpers import checked_integer
def transactional_edits(original,operations):
    result={}
    for key,value in original.items():
        if not isinstance(key,str): raise ValueError("key")
        checked_integer(value); result[key]=value
    for action,key,value in operations:
        if not isinstance(key,str): raise ValueError("key")
        if action in ("set","add"):
            checked_integer(value)
            if action=="set": result[key]=value
            elif key in result: result[key]+=value
            else: raise ValueError("missing")
        elif action=="delete" and value is None and key in result:
            del result[key]
        else: raise ValueError("operation")
    return result
