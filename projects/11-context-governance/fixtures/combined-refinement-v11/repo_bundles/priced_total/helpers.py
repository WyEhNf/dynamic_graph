def checked_cost(quantity,price):
    if quantity<0 or price<0:
        raise ValueError("negative")
    return quantity*price
