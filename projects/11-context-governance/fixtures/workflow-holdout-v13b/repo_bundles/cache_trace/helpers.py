from config import LIMIT
def checked_capacity(value):
    if not isinstance(value,int) or not 0<=value<=LIMIT: raise ValueError("capacity")
    return value
