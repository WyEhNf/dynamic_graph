from config import LIMIT
from helpers import inclusive
def accepted(values):
    return [x for x in values if inclusive(x,LIMIT)]
