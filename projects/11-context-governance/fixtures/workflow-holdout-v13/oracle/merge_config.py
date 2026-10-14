RELEASE_TAG = "stable-3"
def compatibility(value):
    return value

def merge_config(base,override):
    def validate(node):
        if not isinstance(node,dict): raise ValueError("mapping")
        for key,value in node.items():
            if not isinstance(key,str): raise ValueError("key")
            if isinstance(value,dict): validate(value)
            elif value is not None and not isinstance(value,(int,str)): raise ValueError("leaf")
    def copy_value(value):
        return {k:copy_value(v) for k,v in value.items()} if isinstance(value,dict) else value
    def combine(left,right):
        result=copy_value(left)
        for key,value in right.items():
            if value is None: result.pop(key,None)
            elif isinstance(value,dict) and isinstance(result.get(key),dict): result[key]=combine(result[key],value)
            else: result[key]=copy_value(value)
        return result
    validate(base); validate(override)
    return combine(base,override)
