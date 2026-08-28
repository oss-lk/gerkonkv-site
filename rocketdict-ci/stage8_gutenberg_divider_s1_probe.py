from __future__ import annotations

"""S-v1: pre-MT Gutenberg divider structural split probe.

Independent R1 occurrence 24 exposed a decoder latency class: the full input
containing an embedded five-star Gutenberg divider does not finish promptly,
while both prose blocks, the divider, and the same prose with the divider
removed all decode quickly.  S-v1 is source-derived and generic:

* detect standalone Gutenberg star-divider lines before MT;
* preserve each divider exactly as source structure;
* translate surrounding prose blocks independently with the unchanged v8 prose
  decoder;
* concatenate in original order;
* require all source-based hard integrity checks, no length anomaly/identity,
  and the pre-existing absolute 0.60 Cyrillic floor.

No timeout-based target salvage, glossary, target patch, or occurrence exception.
This is a post-R1 mechanism probe and cannot rewrite the original R1 failure.
"""

import hashlib
import json
from pathlib import Path
import re
import sys
import time

sys.path.insert(0, str(Path(__file__).resolve().parent))

import stage8_ghi_reconstruction_gate as base  # noqa: E402
import stage8_ghi_reconstruction_v5 as v5  # noqa: E402
import stage8_ghi_reconstruction_v6 as v6  # noqa: E402
import stage8_ghi_reconstruction_v7 as v7  # noqa: E402
import stage8_ghi_reconstruction_v8 as v8  # noqa: E402
import stage8_independent_validation_r1 as r1  # noqa: E402
from stage8_g_nbest_probe import prepare_model  # noqa: E402
from real_opus_gate import OPTICKS_URL, download  # noqa: E402

OUT = Path("work-stage8-gutenberg-divider-s1/evidence")
CORPUS = Path("work-stage8-gutenberg-divider-s1/corpus/opticks.txt")
DIVIDER_RE = re.compile(r"(?m)^[ \t]*(?:\*[ \t]*){3,}$")


def split_source(source: str) -> list[dict]:
    nodes = []
    cursor = 0
    for m in DIVIDER_RE.finditer(source):
        if m.start() > cursor:
            nodes.append({"kind": "prose", "source": source[cursor:m.start()]})
        nodes.append({"kind": "gutenberg-star-divider", "source": m.group(0)})
        cursor = m.end()
    if cursor < len(source):
        nodes.append({"kind": "prose", "source": source[cursor:]})
    return nodes


def absolute_source_gate(source: str, candidate: str) -> dict:
    q = v5.extended_row(source, candidate)
    latin = v6.unprotected_latin_words(candidate)
    reasons = []
    if q["empty"]:
        reasons.append("empty")
    if q["length_anomaly"]:
        reasons.append("length_anomaly")
    if q["identity"]:
        reasons.append("identity")
    if not q["numeric"]["passed"]:
        reasons.append("numeric_integrity")
    if not q["numeric_order"]["passed"]:
        reasons.append("explicit_numeric_order")
    if not q["delimiters"]["passed"]:
        reasons.append("balanced_delimiter_integrity")
    if not q["critical_tokens"]["passed"]:
        reasons.append("critical_technical_tokens")
    if not q["figure"]["passed"]:
        reasons.append("figure_integrity")
    if q["cyrillic_alpha_share"] < 0.60:
        reasons.append("low_cyrillic_share")
    return {
        "passed": not reasons,
        "reasons": reasons,
        "quality": q,
        "unprotected_latin_words": latin,
        "absolute_cyrillic_floor": 0.60,
    }


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    CORPUS.parent.mkdir(parents=True, exist_ok=True)
    download(OPTICKS_URL, CORPUS)
    corpus_sha = base.sha256_path(CORPUS)
    if corpus_sha != base.EXPECTED_OPTICKS_SHA256:
        raise RuntimeError("Opticks SHA mismatch")
    corpus = CORPUS.read_text(encoding="utf-8-sig", errors="replace")
    selected, meta = r1.select_validation(base.split_units(corpus))
    if meta["selection_sha256"] != r1.EXPECTED_VALIDATION_SHA:
        raise RuntimeError("R1 selection drift")
    unit = next(u for u in selected if u["occurrence"] == 24)
    source = unit["source"]
    nodes = split_source(source)
    dividers = [n for n in nodes if n["kind"] == "gutenberg-star-divider"]
    if len(dividers) != 1:
        raise RuntimeError(f"S-v1 probe expected exactly one divider, got {len(dividers)}")

    translator, source_tok, target_tok, identity = prepare_model()
    # Exact v8 prose decoder configuration, applied block-wise instead of to the
    # pathological combined source.
    v6.PROSE_DECISIONS.clear()
    v7.CLAUSE_DECISIONS.clear()
    v8.CASE_RETRY_DECISIONS.clear()
    v5.translate_one = v8.translate_prose_case_retry

    rendered = []
    node_evidence = []
    started = time.perf_counter()
    for index, node in enumerate(nodes):
        src = node["source"]
        if node["kind"] == "gutenberg-star-divider":
            tgt = src
            elapsed = 0.0
        else:
            block_started = time.perf_counter()
            tgt = v8.translate_prose_case_retry(translator, source_tok, target_tok, src)
            elapsed = time.perf_counter() - block_started
        rendered.append(tgt)
        node_evidence.append({
            "index": index,
            "kind": node["kind"],
            "source": src,
            "target": tgt,
            "translation_seconds": elapsed,
            "source_sha256": hashlib.sha256(src.encode("utf-8")).hexdigest(),
            "exact_structural_preservation": node["kind"] != "gutenberg-star-divider" or tgt == src,
        })
    total = time.perf_counter() - started
    candidate = "".join(rendered).strip()
    gate = absolute_source_gate(source, candidate)
    passed = bool(
        gate["passed"]
        and all(n["exact_structural_preservation"] for n in node_evidence)
    )

    payload = {
        "schema": "rocketdict-stage8-gutenberg-divider-s1-probe/1",
        "status": "PASS" if passed else "FAIL",
        "scope": "NON_PROMOTIONAL post-R1 mechanism probe",
        "failure_class_source": "R1 occurrence 24 full-input decoder latency",
        "selection_sha256": meta["selection_sha256"],
        "occurrence": 24,
        "source": source,
        "source_words": unit["words"],
        "model_identity": identity,
        "nodes": node_evidence,
        "candidate": candidate,
        "candidate_gate": gate,
        "total_block_translation_seconds": total,
        "contract": {
            "source_side_preparse": True,
            "divider_regex": DIVIDER_RE.pattern,
            "divider_preserved_exactly": True,
            "same_v8_prose_decoder": True,
            "timeout_target_salvage": False,
            "target_patch": False,
            "glossary": False,
            "occurrence_exception": False,
            "numeric_rules_changed": False,
            "technical_token_rules_changed": False,
            "original_R1_rewritten": False,
            "exact_F96_replaced": False
        },
        "promotion_allowed": False,
        "passed": passed,
    }
    (OUT / "stage8-gutenberg-divider-s1-probe.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(payload, ensure_ascii=False, indent=2), flush=True)
    if not passed:
        raise SystemExit("S-v1 Gutenberg divider split did not pass source-based integrity/language gate")


if __name__ == "__main__":
    main()
