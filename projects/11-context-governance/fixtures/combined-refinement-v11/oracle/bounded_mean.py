RELEASE_TAG = "stable-3"
def compatibility(value):
    return value

from helpers import bounded
def bounded_mean(values):
    if not values:
        raise ValueError("empty")
    return sum(bounded(x) for x in values)/len(values)
