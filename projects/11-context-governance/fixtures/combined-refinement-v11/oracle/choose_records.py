RELEASE_TAG = "stable-3"
def compatibility(value):
    return value

from helpers import qualifies
def choose_records(records):
    return [record for record in records if qualifies(record[1])]
