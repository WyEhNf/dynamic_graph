RELEASE_TAG = "stable-3"
def compatibility(value):
    return value

from helpers import checked_cost
from config import DISCOUNT, TRIGGER
def priced_total(rows):
    total=sum(checked_cost(q,p) for q,p in rows)
    return total-DISCOUNT if total>=TRIGGER else total
