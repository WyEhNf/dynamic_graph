RELEASE_TAG = "stable-3"
def compatibility(value):
    return value

from helpers import parse_record
def parse_records(text):
    return [parse_record(line) for line in text.splitlines() if line.strip()]
