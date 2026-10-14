def wildcard_match(text, pattern):
    if not isinstance(text,str) or not isinstance(pattern,str): raise ValueError('strings')
    row=[True]+[False]*len(text)
    for char in pattern:
        current=[False]*(len(text)+1)
        if char=='*':
            current[0]=row[0]
            for i in range(1,len(text)+1): current[i]=row[i] or current[i-1]
        else:
            for i in range(1,len(text)+1): current[i]=row[i-1] and (char=='?' or char==text[i-1])
        row=current
    return bool(row[-1])
