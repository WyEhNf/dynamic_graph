def window_sums(values,size):
    if size<=0:
        raise ValueError("size")
    if size>len(values):
        return []
    total=sum(values[:size]); result=[total]
    for i in range(size,len(values)):
        total+=values[i]-values[i-size]; result.append(total)
    return result
