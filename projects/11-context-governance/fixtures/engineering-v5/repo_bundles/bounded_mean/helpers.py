from config import LOWER,UPPER
def bounded(value):
    return min(UPPER,max(LOWER,value))
