import re
from typing import Optional

PROVINCE_CODES = {
    "AB",
    "BC",
    "MB",
    "NB",
    "NL",
    "NS",
    "NT",
    "NU",
    "ON",
    "PE",
    "QC",
    "SK",
    "YT",
}

PROVINCE_NAMES = {
    "ALBERTA",
    "BRITISH COLUMBIA",
    "MANITOBA",
    "NEW BRUNSWICK",
    "NEWFOUNDLAND",
    "NOVA SCOTIA",
    "NUNAVUT",
    "ONTARIO",
    "PRINCE EDWARD ISLAND",
    "QUEBEC",
    "SASKATCHEWAN",
    "YUKON",
    "NORTHWEST TERRITORIES",
}

PROVINCE_PATTERN = "|".join(sorted(PROVINCE_CODES | PROVINCE_NAMES))


def _is_province_segment(segment: str) -> bool:
    if not segment:
        return False
    seg = segment.strip().upper()
    if not seg:
        return False
    if seg in PROVINCE_CODES or seg in PROVINCE_NAMES:
        return True
    for code in PROVINCE_CODES:
        if seg.startswith(f"{code} "):
            return True
    for name in PROVINCE_NAMES:
        if seg.startswith(f"{name} "):
            return True
    return False


def extract_city(text: Optional[str]) -> Optional[str]:
    """Best-effort extraction of city/area name from a free-form address or title."""
    if not isinstance(text, str):
        return None

    value = text.strip()
    if not value:
        return None

    province_regex = rf"(?:{PROVINCE_PATTERN})"

    # Pattern: "... , City , ON ..."
    match = re.search(rf",\s*([A-Za-z][A-Za-z\s'.-]+?),\s*{province_regex}\b", value, flags=re.I)
    if match:
        return match.group(1).strip().title()

    # Pattern: "City, ON ..."
    match = re.match(rf"\s*([A-Za-z][A-Za-z\s'.-]+?),\s*{province_regex}\b", value, flags=re.I)
    if match:
        return match.group(1).strip().title()

    # Pattern: "City ON" (no comma)
    match = re.search(rf"([A-Za-z][A-Za-z\s'.-]+)\s+{province_regex}\b", value, flags=re.I)
    if match:
        candidate = match.group(1).strip()
        if candidate:
            return candidate.title()

    # Fallback: choose first comma-separated segment that resembles a city
    parts = [part.strip() for part in re.split(r",|\n", value) if part.strip()]
    for part in reversed(parts):
        if _is_province_segment(part):
            continue
        if any(char.isdigit() for char in part):
            continue
        if len(part) <= 1:
            continue
        if part.upper() == part:
            continue
        return part.title()

    # Fallback: use alphabetic words if no commas present
    words = re.findall(r"[A-Za-z][A-Za-z'.-]+(?:\s+[A-Za-z][A-Za-z'.-]+)*", value)
    for word in words:
        if _is_province_segment(word):
            continue
        return word.title()

    return None


def normalize_area_name(value: Optional[str]) -> Optional[str]:
    """Normalize user-provided area or city text into a canonical form."""
    if not value:
        return None

    if not isinstance(value, str):
        return None

    city = extract_city(value)
    if city:
        return city

    cleaned = re.sub(r"[^A-Za-z\s'.-]", " ", value).strip()
    cleaned = re.sub(r"\s{2,}", " ", cleaned)
    if not cleaned:
        return None

    return cleaned.title()
