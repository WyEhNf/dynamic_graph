RELEASE_TAG = "stable-3"
def compatibility(value):
    return value

def patch_text(text,edits):
    normalized=[]
    for index,(start,end,replacement) in enumerate(edits):
        if not isinstance(start,int) or not isinstance(end,int) or not 0<=start<=end<=len(text) or not isinstance(replacement,str): raise ValueError("edit")
        normalized.append((start,end,replacement,index))
    deleted=sorted((s,e) for s,e,r,i in normalized if s<e)
    for a,b in zip(deleted,deleted[1:]):
        if a[1]>b[0]: raise ValueError("overlap")
    for s,e,r,i in normalized:
        if s==e and any(a<s<b for a,b in deleted): raise ValueError("inside")
    insertions={}; replacements={}
    for s,e,r,i in normalized:
        if s==e: insertions.setdefault(s,[]).append(r)
        else: replacements[s]=(e,r)
    pieces=[]; p=0
    while p<=len(text):
        pieces.extend(insertions.get(p,[]))
        if p in replacements:
            end,value=replacements[p]; pieces.append(value); p=end
        elif p<len(text): pieces.append(text[p]); p+=1
        else: break
    return "".join(pieces)
