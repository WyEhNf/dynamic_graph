def rotate(values, offset):
    if not values:
        return []
    k=offset % len(values)
    return values[-k:] + values[:-k] if k else values[:]
