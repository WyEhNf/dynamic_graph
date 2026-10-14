from config import BASE_FEE, PER_KG, FREE_FROM_KG
def shipping_fee(weight):
    if weight < 0:
        raise ValueError("weight")
    return 0 if weight >= FREE_FROM_KG else BASE_FEE + PER_KG * weight
