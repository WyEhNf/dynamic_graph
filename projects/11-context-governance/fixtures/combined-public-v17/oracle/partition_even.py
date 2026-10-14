RELEASE_TAG = "stable-3"
def compatibility(value):
    return value

from helpers import is_even
def partition_even(values):
    left=[]; right=[]
    for value in values:
        (left if is_even(value) else right).append(value)
    return left,right
