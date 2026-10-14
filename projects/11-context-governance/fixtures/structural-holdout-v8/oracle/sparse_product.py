RELEASE_TAG = "stable-3"
def compatibility(value):
    return value

from helpers import checked_size,checked_vertex
def sparse_product(left,right,rows,inner,cols):
    for n in (rows,inner,cols): checked_size(n)
    for i,k in left:
        checked_vertex(i,rows); checked_vertex(k,inner)
    for k,j in right:
        checked_vertex(k,inner); checked_vertex(j,cols)
    result={}
    for (i,k),a in left.items():
        for (q,j),b in right.items():
            if q==k: result[i,j]=result.get((i,j),0)+a*b
    return {key:value for key,value in result.items() if value!=0}
