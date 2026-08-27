from __future__ import annotations

"""RocketDict Stage 8 / DOE H+I structural mechanism probes.

These probes use exact public-domain Opticks passages matching the two F96
failure classes that ordinary n-best did not solve:

H: document figure reference `[in _Fig._ 2.]`.
I: a coupled measurement/extreme-scientific clause containing
   `76, 152, 228 Miles` and
   `1000000, 1000000000000, or 1000000000000000000`.

The mechanisms parse structure *before* MT, translate surrounding prose with the
same real OPUS model, and render the parsed structure from source-derived fields
with explicit provenance. They never append a missing literal after inspecting
an MT failure.

This file is a mechanism probe, not a substitute for the full Stage 8 gate. Full
promotion still requires integration into the exact F96 pipeline and the
identical ~5k challenge under rocketdict-numeric-integrity/3.2.
"""

from collections import Counter
from dataclasses import asdict, dataclass
import json
from pathlib import Path
import re
import sys
import time

sys.path.insert(0, str(Path(__file__).resolve().parent))
from stage8_g_nbest_probe import prepare_model  # noqa: E402

OUT = Path("work-stage8-hi/evidence")

H_SOURCE = (
    "The Sun's Light let into a dark Chamber through the round hole F, "
    "[in _Fig._ 2.] half an Inch wide, passed first through the Prism ABC placed "
    "at the hole, and then through a Lens PT something more than four Inches broad, "
    "and about eight Feet distant from the Prism, and thence converged to O the Focus "
    "of the Lens distant from it about three Feet, and there fell upon a white Paper DE."
)

I_SOURCE = (
    "For since the Air is compress'd by the Weight of the incumbent Atmosphere, and the "
    "Density of Air is proportional to the Force compressing it, it follows by Computation, "
    "that at the height of about seven and a half English Miles from the Earth, the Air is "
    "four times rarer than at the Surface of the Earth; and at the height of 15 Miles it is "
    "sixteen times rarer than that at the Surface of the Earth; and at the height of 22-1/2, "
    "30, or 38 Miles, it is respectively 64, 256, or 1024 times rarer, or thereabouts; and at "
    "the height of 76, 152, 228 Miles, it is about 1000000, 1000000000000, or "
    "1000000000000000000 times rarer; and so on."
)

FIG_RE = re.compile(r"\[in\s+_Fig\._\s+(?P<number>\d+)\.\]", flags=re.IGNORECASE)

# I-v2 deliberately parses the whole coupled high-risk clause. I-v1 isolated
# only the three huge values; real evidence showed that the new split then
# duplicated neighbouring 76/228 values. Quality-first means widening the AST
# boundary rather than accepting a locally-green extreme-literal check.
EXTREME_CLAUSE_RE = re.compile(
    r"at\s+the\s+height\s+of\s+"
    r"(?P<h1>\d+)\s*,\s*(?P<h2>\d+)\s*,\s*(?P<h3>\d+)\s+Miles\s*,\s*"
    r"it\s+is\s+about\s+"
    r"(?P<x>\d{7,})\s*,\s*(?P<y>\d{7,})\s*,\s*or\s+(?P<z>\d{7,})\s+"
    r"times\s+rarer",
    flags=re.IGNORECASE,
)

# Local fail-closed numeric guard used only by this mechanism probe. It is not
# named numeric-integrity/3.2 and cannot promote a Stage 8 branch. It exists to
# catch the exact regression seen in I-v1: preserving the protected values while
# duplicating/dropping neighbouring explicit values.
NUMERIC_TOKEN_RE = re.compile(
    r"(?<!\w)(?:\d+-\d+/\d+|\d+/\d+|\d{1,3}(?:[\s\u00a0\u202f]\d{3})+|\d+)(?!\w)",
    flags=re.UNICODE,
)
SPELLED_INTEGER_LICENSES = {
    "zero": "0",
    "one": "1",
    "two": "2",
    "three": "3",
    "four": "4",
    "five": "5",
    "six": "6",
    "seven": "7",
    "eight": "8",
    "nine": "9",
    "ten": "10",
    "eleven": "11",
    "twelve": "12",
    "thirteen": "13",
    "fourteen": "14",
    "fifteen": "15",
    "sixteen": "16",
}


@dataclass(frozen=True)
class Provenance:
    kind: str
    source_start: int
    source_end: int
    source_text: str
    target_start: int
    target_end: int
    target_text: str
    fields: dict


def _normalize_numeric_token(token: str) -> str:
    return re.sub(r"[\s\u00a0\u202f]", "", token)


def _numeric_counter(text: str) -> Counter[str]:
    return Counter(_normalize_numeric_token(m.group(0)) for m in NUMERIC_TOKEN_RE.finditer(text))


def _licensed_source_numeric_counter(source: str) -> Counter[str]:
    low = source.casefold()
    out: Counter[str] = Counter()
    for word, value in SPELLED_INTEGER_LICENSES.items():
        out[value] += len(re.findall(rf"(?<!\w){re.escape(word)}(?!\w)", low))
    return out


def local_numeric_guard(source: str, target: str) -> dict:
    required = _numeric_counter(source)
    target_values = _numeric_counter(target)
    licensed = _licensed_source_numeric_counter(source)
    allowed = required + licensed

    missing = {
        value: count - target_values[value]
        for value, count in required.items()
        if target_values[value] < count
    }
    unlicensed_or_duplicate = {
        value: count - allowed[value]
        for value, count in target_values.items()
        if count > allowed[value]
    }
    return {
        "contract": "stage8-hi-local-explicit-numeric-guard/2",
        "required_explicit": dict(required),
        "licensed_from_spelled_source": dict(licensed),
        "target": dict(target_values),
        "missing_required": missing,
        "unlicensed_or_duplicate": unlicensed_or_duplicate,
        "passed": not missing and not unlicensed_or_duplicate,
        "note": "probe guard only; full promotion still requires rocketdict-numeric-integrity/3.2",
    }


def translate_top1(translator, source_tok, target_tok, text: str) -> str:
    if not text.strip():
        return ""
    tokens = source_tok.encode(text, out_type=str)
    result = translator.translate_batch([tokens], beam_size=4, max_batch_size=1)[0]
    return target_tok.decode(result.hypotheses[0]).strip()


def join_parts(left: str, structure: str, right: str) -> tuple[str, int, int]:
    chunks = []
    if left.strip():
        chunks.append(left.strip())
    chunks.append(structure)
    if right.strip():
        chunks.append(right.strip())
    text = " ".join(chunks)
    start = text.index(structure)
    return text, start, start + len(structure)


def probe_h(translator, source_tok, target_tok) -> dict:
    match = FIG_RE.search(H_SOURCE)
    if not match:
        raise RuntimeError("H source figure reference was not parsed")
    number = match.group("number")
    left_source = H_SOURCE[: match.start()]
    right_source = H_SOURCE[match.end() :]

    baseline_started = time.time()
    baseline = translate_top1(translator, source_tok, target_tok, H_SOURCE)
    baseline_seconds = time.time() - baseline_started

    started = time.time()
    left_target = translate_top1(translator, source_tok, target_tok, left_source)
    right_target = translate_top1(translator, source_tok, target_tok, right_source)
    rendered = f"[на рис. {number}]"
    structured, target_start, target_end = join_parts(left_target, rendered, right_target)
    structured_seconds = time.time() - started

    provenance = Provenance(
        kind="figure-reference",
        source_start=match.start(),
        source_end=match.end(),
        source_text=match.group(0),
        target_start=target_start,
        target_end=target_end,
        target_text=rendered,
        fields={"figure_number": number, "renderer": "ru-figure-reference-v1"},
    )
    exact_reference_preserved = structured[target_start:target_end] == rendered and number in rendered
    numeric_guard = local_numeric_guard(H_SOURCE, structured)

    return {
        "case_id": "f96-occurrence-15697-figure-reference",
        "classification": "structural figure reference",
        "source": H_SOURCE,
        "parsed_reference": {"kind": "figure", "number": number},
        "baseline_target": baseline,
        "baseline_seconds": baseline_seconds,
        "baseline_numeric_guard": local_numeric_guard(H_SOURCE, baseline),
        "structured_target": structured,
        "structured_seconds": structured_seconds,
        "structured_numeric_guard": numeric_guard,
        "provenance": asdict(provenance),
        "reference_integrity_passed": exact_reference_preserved,
        "probe_passed": bool(exact_reference_preserved and numeric_guard["passed"]),
        "mechanism": "pre-MT structural parse -> translate surrounding prose -> deterministic target-language figure-reference render",
        "post_hoc_literal_append": False,
    }


def probe_i(translator, source_tok, target_tok) -> dict:
    match = EXTREME_CLAUSE_RE.search(I_SOURCE)
    if not match:
        raise RuntimeError("I source coupled extreme clause was not parsed")

    height_values = [match.group("h1"), match.group("h2"), match.group("h3")]
    rarity_values = [match.group("x"), match.group("y"), match.group("z")]
    values = [*height_values, *rarity_values]
    if len(set(rarity_values)) != 3:
        raise RuntimeError("unexpected duplicate extreme rarity literals")

    left_source = I_SOURCE[: match.start()]
    right_source = I_SOURCE[match.end() :]

    baseline_started = time.time()
    baseline = translate_top1(translator, source_tok, target_tok, I_SOURCE)
    baseline_seconds = time.time() - baseline_started
    baseline_guard = local_numeric_guard(I_SOURCE, baseline)

    started = time.time()
    left_target = translate_top1(translator, source_tok, target_tok, left_source)
    right_target = translate_top1(translator, source_tok, target_tok, right_source)
    rendered = (
        f"на высоте {height_values[0]}, {height_values[1]}, {height_values[2]} миль "
        f"он примерно в {rarity_values[0]}, {rarity_values[1]} или {rarity_values[2]} раз разреженнее"
    )
    structured, clause_start, clause_end = join_parts(left_target, rendered, right_target)
    structured_seconds = time.time() - started

    literal_provenance = []
    source_search_from = match.start()
    target_search_from = clause_start
    for value in values:
        source_pos = I_SOURCE.index(value, source_search_from, match.end())
        target_pos = structured.index(value, target_search_from, clause_end)
        literal_provenance.append(
            asdict(
                Provenance(
                    kind="structured-measurement-literal",
                    source_start=source_pos,
                    source_end=source_pos + len(value),
                    source_text=value,
                    target_start=target_pos,
                    target_end=target_pos + len(value),
                    target_text=value,
                    fields={"literal": value, "renderer": "ru-height-rarity-clause-v2"},
                )
            )
        )
        source_search_from = source_pos + len(value)
        target_search_from = target_pos + len(value)

    extracted_target = [structured[p["target_start"]:p["target_end"]] for p in literal_provenance]
    exact_structured_values_preserved = extracted_target == values
    numeric_guard = local_numeric_guard(I_SOURCE, structured)

    return {
        "case_id": "f96-occurrence-17795-extreme-sequence",
        "classification": "extreme literal/scientific-sequence fidelity",
        "strategy_revision": "I-v2 widened structural boundary after I-v1 created neighbouring 76/228 duplicates",
        "source": I_SOURCE,
        "parsed_clause": {
            "kind": "height-rarity-series",
            "height_values": height_values,
            "unit": "Miles",
            "rarity_values": rarity_values,
            "qualifier": "about",
            "comparative": "times rarer",
            "source_start": match.start(),
            "source_end": match.end(),
            "source_text": match.group(0),
        },
        "baseline_target": baseline,
        "baseline_seconds": baseline_seconds,
        "baseline_numeric_guard": baseline_guard,
        "structured_target": structured,
        "structured_seconds": structured_seconds,
        "structured_numeric_guard": numeric_guard,
        "literal_provenance": literal_provenance,
        "structured_values_integrity_passed": exact_structured_values_preserved,
        "probe_passed": bool(exact_structured_values_preserved and numeric_guard["passed"]),
        "mechanism": "pre-MT coupled measurement/enumeration AST -> translate surrounding prose -> deterministic target-language structural render",
        "post_hoc_literal_append": False,
    }


def main() -> None:
    translator, source_tok, target_tok, model_identity = prepare_model()
    h = probe_h(translator, source_tok, target_tok)
    i = probe_i(translator, source_tok, target_tok)

    payload = {
        "schema": "rocketdict-stage8-hi-structural-probe/2",
        "stage8_parent": "F96",
        "scope": "mechanism probes for the exact documented H/I failure classes; not the full 5k promotion gate",
        "model_identity": model_identity,
        "source_provenance": {
            "corpus": "Isaac Newton, Opticks, Project Gutenberg #33504",
            "canonical_url": "https://www.gutenberg.org/cache/epub/33504/pg33504.txt",
            "handoff_context": "rocketdict/RESEARCH_STATUS.md",
        },
        "H": h,
        "I": i,
        "probe_passed": bool(h["probe_passed"] and i["probe_passed"]),
        "promotion_allowed": False,
        "promotion_blocker": "integrate H/I into RocketDict source snapshot and rerun the identical F96 ~5k challenge under numeric-integrity/3.2",
    }

    OUT.mkdir(parents=True, exist_ok=True)
    path = OUT / "stage8-hi-structural-probe.json"
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(payload, ensure_ascii=False, indent=2), flush=True)

    if not payload["probe_passed"]:
        raise SystemExit("Stage 8 H/I structural mechanism probe failed")


if __name__ == "__main__":
    main()
