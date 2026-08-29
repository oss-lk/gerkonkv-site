from __future__ import annotations

"""NON-PROMOTIONAL behavioral/interface reconstruction for lost numeric-integrity/3.2.

This is NOT the recovered RocketDict 0.30.40 `translation/integrity.py` source.
It exists only to make the documented Stage 8 numeric contract executable for
recovery experiments while exact source remains unavailable.
"""

from collections import Counter
from dataclasses import dataclass
import re

RECONSTRUCTION_CONTRACT = "rocketdict-numeric-integrity/3.2-interface-reconstruction/1"
EXACT_CONTRACT_CLAIMED = False

# Basic explicit English number-word licences already evidenced by Stage 8
# records. Deliberately do not infer arbitrary prose numerals here.
NUMBER_WORDS = {
    "zero": "0", "one": "1", "two": "2", "three": "3", "four": "4",
    "five": "5", "six": "6", "seven": "7", "eight": "8", "nine": "9",
    "ten": "10", "eleven": "11", "twelve": "12", "thirteen": "13",
    "fourteen": "14", "fifteen": "15", "sixteen": "16", "seventeen": "17",
    "eighteen": "18", "nineteen": "19", "twenty": "20", "thirty": "30",
    "forty": "40", "fifty": "50", "sixty": "60", "seventy": "70",
    "eighty": "80", "ninety": "90",
}

# Ordered alternatives matter. More structured literals are consumed before
# simpler decimal/integer forms.
_NUMERIC_RE = re.compile(
    r"(?<![\w])(?P<token>[+\-−]?\d+(?:\s*[-–]\s*|\s+)\d+\s*/\s*\d+(?:st|nd|rd|th|d|[-‑–]?(?:й|я|е|го|му|ым|ом|ой|ую|ых))?"
    r"|[+\-−]?\d+\s*/\s*\d+(?:st|nd|rd|th|d|[-‑–]?(?:й|я|е|го|му|ым|ом|ой|ую|ых))?"
    r"|[+\-−]?\d+['’]\d+"
    r"|[+\-−]?\d{1,3}(?:(?:[\s\u00a0\u202f]\d{3}){1,}|(?:,\d{3}){1,})"
    r"|[+\-−]?\d+[.,]\d+"
    r"|[+\-−]?\d+(?:st|nd|rd|th|d|[-‑–]?(?:й|я|е|го|му|ым|ом|ой|ую|ых))?)(?![\w])",
    re.IGNORECASE | re.UNICODE,
)
_ORDINAL_SUFFIX_RE = re.compile(
    r"(?:st|nd|rd|th|d|[-‑–]?(?:й|я|е|го|му|ым|ом|ой|ую|ых))$",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class NumericLiteral:
    raw: str
    canonical: str
    start: int
    end: int


def _strip_ordinal_suffix(token: str) -> str:
    return _ORDINAL_SUFFIX_RE.sub("", token)


def normalize_numeric_literal(raw: str) -> str:
    token = raw.casefold().replace("−", "-").replace("‑", "-").replace("–", "-")
    token = re.sub(r"[\u00a0\u202f]", " ", token)
    token = _strip_ordinal_suffix(token)
    token = re.sub(r"\s*/\s*", "/", token)
    token = re.sub(r"\s*-\s*", "-", token)

    if re.fullmatch(r"[+-]?\d+['’]\d+", token):
        return token.replace("’", "'").replace("'", ".")
    if re.fullmatch(r"[+-]?\d+(?:-| )\d+/\d+", token):
        return re.sub(r" ", "-", token)
    if re.fullmatch(r"[+-]?\d+/\d+", token):
        return token

    compact = token.replace(" ", "")
    if re.fullmatch(r"[+-]?\d{1,3}(?:,\d{3})+", compact):
        compact = compact.replace(",", "")
    elif "," in compact:
        compact = compact.replace(",", ".")

    if re.fullmatch(r"[+-]?\d+", compact):
        sign = ""
        digits = compact
        if digits[:1] in "+-":
            sign, digits = digits[0], digits[1:]
        digits = digits.lstrip("0") or "0"
        return ("-" if sign == "-" else "") + digits
    return compact


def normalize_numeric_options(raw: str) -> tuple[str, ...]:
    """Return conservative alternatives for a single comma/three-digit tail."""
    primary = normalize_numeric_literal(raw)
    compact = raw.casefold().replace("−", "-").replace(" ", "").replace("\u00a0", "").replace("\u202f", "")
    compact = _strip_ordinal_suffix(compact)
    match = re.fullmatch(r"([+-]?\d{1,3}),(\d{3})", compact)
    if not match:
        return (primary,)
    grouped = normalize_numeric_literal(match.group(1) + match.group(2))
    decimal = match.group(1) + "." + match.group(2)
    return tuple(dict.fromkeys((grouped, decimal)))


def extract_numeric_literals(text: str) -> list[NumericLiteral]:
    return [
        NumericLiteral(
            match.group("token"),
            normalize_numeric_literal(match.group("token")),
            match.start("token"),
            match.end("token"),
        )
        for match in _NUMERIC_RE.finditer(text)
    ]


def contains_numeric_literal(text: str) -> bool:
    return _NUMERIC_RE.search(text) is not None


def numeric_counter(text: str) -> Counter[str]:
    return Counter(item.canonical for item in extract_numeric_literals(text))


def spelled_numeric_licenses(source: str) -> Counter[str]:
    low = source.casefold()
    out: Counter[str] = Counter()
    for word, value in NUMBER_WORDS.items():
        count = len(re.findall(rf"(?<!\w){re.escape(word)}(?!\w)", low))
        if count:
            out[value] += count
    return out


def _positive_delta(left: Counter[str], right: Counter[str]) -> dict[str, int]:
    return {key: left[key] - right[key] for key in left if left[key] > right[key]}


def compare_numeric_integrity(source: str, target: str) -> dict:
    required = numeric_counter(source)
    licensed = spelled_numeric_licenses(source)
    allowed = required + licensed
    observed: Counter[str] = Counter()
    for item in extract_numeric_literals(target):
        options = normalize_numeric_options(item.raw)
        chosen = next((value for value in options if observed[value] < allowed[value]), options[0])
        observed[chosen] += 1

    missing = _positive_delta(required, observed)
    excess = _positive_delta(observed, allowed)
    duplicate_required = {key: value for key, value in excess.items() if key in required}
    unlicensed_additions = {key: value for key, value in excess.items() if key not in required}

    return {
        "contract": RECONSTRUCTION_CONTRACT,
        "exact_contract_claimed": False,
        "required": dict(required),
        "observed": dict(observed),
        "licensed_spelled": dict(licensed),
        "missing": missing,
        "duplicate_required": duplicate_required,
        "unlicensed_additions_observed": unlicensed_additions,
        "passed": not missing and not duplicate_required and not unlicensed_additions,
    }


def self_check() -> dict:
    cases = []

    def check(name: str, source: str, target: str, expected_pass: bool, *, missing=None, additions=None) -> None:
        result = compare_numeric_integrity(source, target)
        assert result["passed"] is expected_pass, (name, result)
        if missing is not None:
            assert result["missing"] == missing, (name, result)
        if additions is not None:
            assert result["unlicensed_additions_observed"] == additions, (name, result)
        cases.append({"name": name, "result": result})

    for literal in ["22-1/2", "24th", "1/89000th", "42d", "1 000 000", "1,000,000", "1,5", "1'699", "0'000625", "4'27"]:
        assert contains_numeric_literal(literal), literal

    check("mixed_fraction_identity", "22-1/2 Inches", "22 1/2 дюйма", True)
    check("ordinal_suffix_en_to_ru", "24th order", "24-й порядок", True)
    check("fraction_ordinal_suffix", "1/89000th part", "1/89000-я часть", True)
    check("old_ordinal_d", "42d observation", "42-я запись", True)
    check("grouped_space_comma", "1,000,000 times", "1 000 000 раз", True)
    check("single_grouped_thousand", "1,000 times", "1 000 раз", True)
    check("decimal_comma", "1,5 Inches", "1,5 дюйма", True)
    check("newton_apostrophe_decimal", "1'699 and 0'000625", "1,699 и 0,000625", True)
    check("f96_15697_structural_reference_loss", "[in _Fig._ 2.] four Inches eight Feet three Feet", "[на рис.] 4 дюйма 8 футов 3 фута", False, missing={"2": 1}, additions={})
    check("f96_16200_missing_three", "15 Min. that of the exterior 3 Degr.", "15 Мин. внешней части.", False, missing={"3": 1}, additions={})
    check("f96_16200_nbest_preserves", "15 Min. that of the exterior 3 Degr.", "15 Мин. внешней части 3 дегр.", True)
    check("f96_17795_extreme_sequence", "1000000, 1000000000000, or 1000000000000000000 times rarer", "1 000 000 000 и 1 000 000 000 000 раз реже", False, missing={"1000000": 1, "1000000000000000000": 1}, additions={"1000000000": 1})
    check("duplicate_required_literal", "15 Min.", "15 мин. 15", False)
    check("unlicensed_addition", "15 Min.", "15 мин. 99", False, additions={"99": 1})

    return {
        "schema": "rocketdict-stage8-integrity32-interface-reconstruction-selfcheck/1",
        "promotion_allowed": False,
        "exact_contract_claimed": False,
        "case_count": len(cases),
        "cases": cases,
    }


if __name__ == "__main__":
    import json
    print(json.dumps(self_check(), ensure_ascii=False, indent=2))
