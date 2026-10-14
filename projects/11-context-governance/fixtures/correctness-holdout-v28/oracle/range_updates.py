def range_updates(values, operations):
    if any(not isinstance(value,int) for value in values): raise ValueError('values')
    for start,end,delta in operations:
        if not all(isinstance(x,int) for x in (start,end,delta)) or not 0<=start<=end<=len(values): raise ValueError('operation')
    diff=[0]*(len(values)+1)
    for start,end,delta in operations:
        diff[start]+=delta
        diff[end]-=delta
    running=0
    result=[]
    for i,value in enumerate(values):
        running+=diff[i]
        result.append(value+running)
    return result
