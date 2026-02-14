import re

def clean_number(text: str) -> float:
    if not text:
        return 0
    text = text.replace(",", "").strip()
    match = re.search(r"[-+]?\d*\.?\d+", text)
    return float(match.group()) if match else 0
