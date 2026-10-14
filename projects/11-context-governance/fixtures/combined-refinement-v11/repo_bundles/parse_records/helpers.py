import config
def parse_record(line):
    parts=line.split(config.SEPARATOR)
    if len(parts)!=2 or not parts[0].strip():
        raise ValueError("record")
    return parts[0].strip(),int(parts[1].strip())
