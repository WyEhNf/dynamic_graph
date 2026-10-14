def validate_nonnegative(value):
    if value < 0:
        raise ValueError("negative")
