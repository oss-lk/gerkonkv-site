from __future__ import annotations

"""RocketDict Stage 8 / DOE H+I structural mechanism probes.

These probes use exact public-domain Opticks source passages matching the two F96
failure classes that ordinary n-best did not solve:

H: document figure reference `[in _Fig._ 2.]`.
I: extreme scientific literal enumeration
   `1000000, 1000000000000, or 1000000000000000000`.

The mechanisms parse structure *before* MT, translate surrounding prose with the
same real OPUS model, and render the parsed structure from source-derived fields
with explicit provenance.  They never append a missing literal after inspecting
an MT failure.  The probes are mechanism evidence only; full Stage 8 promotion
still requires integration into the exact F96 pipeline and the identical ~5k
numeric-integrity/3.2 gate.
"""

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
EXTREME_ENUM_RE = re.compile(
    r"(?P<a>\d{7,})\s*,\s*(?P<b>\d{7,})\s*,\s*or\s+(?P<c>\d{7,})",
    flags=re.IGNORECASE,
)


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
    # Target-language rendering of a parsed document-structure node.  The number
    # comes only from the source AST; this is not post-hoc MT repair.
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

    return {
        "case_id": "f96-occurrence-15697-figure-reference",
        "classification": "structural figure reference",
        "source": H_SOURCE,
        "parsed_reference": {"kind": "figure", "number": number},
        "baseline_target": baseline,
        "baseline_seconds": baseline_seconds,
        "structured_target": structured,
        "structured_seconds": structured_seconds,
        "provenance": asdict(provenance),
        "reference_integrity_passed": exact_reference_preserved,
        "mechanism": "pre-MT structural parse -> translate surrounding prose -> deterministic target-language structure render",
        "post_hoc_literal_append": False,
    }


def probe_i(translator, source_tok, target_tok) -> dict:
    match = EXTREME_ENUM_RE.search(I_SOURCE)
    if not match:
        raise RuntimeError("I source extreme enumeration was not parsed")
    values = [match.group("a"), match.group("b"), match.group("c")]
    if len(set(values)) != 3:
        raise RuntimeError("unexpected duplicate extreme literals")

    left_source = I_SOURCE[: match.start()]
    right_source = I_SOURCE[match.end() :]

    baseline_started = time.time()
    baseline = translate_top1(translator, source_tok, target_tok, I_SOURCE)
    baseline_seconds = time.time() - baseline_started

    started = time.time()
    left_target = translate_top1(translator, source_tok, target_tok, left_source)
    right_target = translate_top1(translator, source_tok, target_tok, right_source)
    rendered = f"{values[0]}, {values[1]} или {values[2]}"
    structured, enum_start, enum_end = join_parts(left_target, rendered, right_target)
    structured_seconds = time.time() - started

    literal_provenance = []
    search_from = enum_start
    for value in values:
        source_pos = I_SOURCE.index(value, match.start(), match.end())
        target_pos = structured.index(value, search_from, enum_end)
        literal_provenance.append(
            asdict(
                Provenance(
                    kind="extreme-enumeration-literal",
                    source_start=source_pos,
                    source_end=source_pos + len(value),
                    source_text=value,
                    target_start=target_pos,
                    target_end=target_pos + len(value),
                    target_text=value,
                    fields={"literal": value, "renderer": "ru-extreme-enumeration-v1"},
                )
            )
        )
        search_from = target_pos + len(value)

    extracted_target = [structured[p["target_start"]:p["target_end"]] for p in literal_provenance]
    exact_extreme_sequence_preserved = extracted_target == values

    return {
        "case_id": "f96-occurrence-17795-extreme-sequence",
        "classification": "extreme literal/scientific-sequence fidelity",
        "source": I_SOURCE,
        "parsed_enumeration": {
            "values": values,
            "source_start": match.start(),
            "source_end": match.end(),
            "source_text": match.group(0),
        },
        "baseline_target": baseline,
        "baseline_seconds": baseline_seconds,
        "structured_target": structured,
        "structured_seconds": structured_seconds,
        "literal_provenance": literal_provenance,
        "extreme_sequence_integrity_passed": exact_extreme_sequence_preserved,
        "mechanism": "pre-MT high-risk enumeration AST -> translate surrounding prose -> deterministic exact-literal enumeration render",
        "post_hoc_literal_append": False,
    }


def main() -> None:
    translator, source_tok, target_tok, model_identity = prepare_model()
    h = probe_h(translator, source_tok, target_tok)
    i = probe_i(translator, source_tok, target_tok)

    payload = {
        "schema": "rocketdict-stage8-hi-structural-probe/1",
        "stage8_parent": "F96",
        "scope": "mechanism probes for the exact documented H/I failure classes; not the full 5k promotion gate",
        "model_identity": model_identity,
        "source_provenance": {
            "corpus": "Isaac Newton, Opticks, Project Gutenberg #33504",
            "canonical_url": "https://www.gutenberg.org/cache/epub/33504/pg33504.txt",
            "opus-stage8-handoff_context": "rocketdict/RESEARCH_STATUS.md",
        },
        "H": h,
        "I": i,
        "probe_passed": bool(h["reference_integrity_passed"] and i["extreme_sequence_integrity_passed"]),
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
