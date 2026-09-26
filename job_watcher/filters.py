"""Title, location and experience filters driven by config/profile.yaml."""
import re

YEARS = re.compile(
    r"(?<![\d.])(\d{1,2})(?:\.\d)?\s*(?:\+|(?:-|–|to)\s*\d{1,2}(?:\.\d)?)?\s*\+?\s*(?:years?|yrs?)\b", re.I
)


WORD_NUMBERS = {
    "one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6, "seven": 7,
    "eight": 8, "nine": 9, "ten": 10, "eleven": 11, "twelve": 12, "fifteen": 15,
}
WORD_YEARS = re.compile(r"\b(" + "|".join(WORD_NUMBERS) + r")\s+(?:\+\s*)?(?:years?|yrs?)\b", re.I)


def compile_any(patterns: list[str]) -> re.Pattern:
    return re.compile("|".join(f"(?:{p})" for p in patterns), re.I)


def min_years(text: str) -> int | None:
    """Minimum years of experience a posting asks for, or None if not stated.

    Prefers the first "N years" mention near the word "experience", so a later
    "1+ years with tool X" does not override "3-7 years of experience".
    """
    text = text or ""
    found = [(m.start(), m.end(), int(m.group(1))) for m in YEARS.finditer(text)]
    found += [(m.start(), m.end(), WORD_NUMBERS[m.group(1).lower()]) for m in WORD_YEARS.finditer(text)]
    found = sorted(f for f in found if 0 < f[2] <= 25)
    if not found:
        return None
    for start, end, years in found:
        if "experience" in text[max(0, start - 80): end + 80].lower():
            return years
    return found[0][2]


class Filters:
    def __init__(self, profile: dict):
        self.include = compile_any(profile["title_include"])
        self.exclude = compile_any(profile["title_exclude"])
        self.location = compile_any(profile["locations"])
        self.max_years = profile.get("max_min_years", 3)
        self.stretch_max_years = profile.get("stretch_max_years", self.max_years)

    def title_ok(self, title: str) -> bool:
        return bool(self.include.search(title)) and not self.exclude.search(title)

    def location_ok(self, location: str) -> bool:
        return bool(self.location.search(location or ""))

    def experience_ok(self, years: int | None) -> bool:
        return years is None or years <= self.max_years

    def is_stretch(self, years: int | None) -> bool:
        """Slightly above the target; kept only if the LLM rates the fit highly."""
        return years is not None and self.max_years < years <= self.stretch_max_years
