def total_csv(text):
    return sum(int(part.strip()) for part in text.split(",") if part.strip())
