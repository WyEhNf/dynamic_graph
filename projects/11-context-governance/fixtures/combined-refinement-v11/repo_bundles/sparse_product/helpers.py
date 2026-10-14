from config import MAX_SIZE
def checked_size(n):
    if not isinstance(n,int) or n<0 or n>MAX_SIZE:
        raise ValueError("size")
    return n
def checked_vertex(v,n):
    if not isinstance(v,int) or not 0<=v<n:
        raise ValueError("vertex")
    return v
