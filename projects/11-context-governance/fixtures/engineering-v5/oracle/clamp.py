def clamp(value, lower, upper):
    if lower > upper:
        raise ValueError("bounds")
    return min(upper, max(lower, value))
