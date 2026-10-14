from config import INTEGER_KIND
def checked_integer(value):
    if not isinstance(value,INTEGER_KIND): raise ValueError("integer")
    return value
