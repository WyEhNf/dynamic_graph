from helpers import validate_nonnegative
def normalize_weights(weights):
    for weight in weights:
        validate_nonnegative(weight)
    if not weights:
        return []
    total=sum(weights)
    if total==0:
        raise ValueError("zero total")
    return [x/total for x in weights]
