from __future__ import annotations

"""Research-only semantic review surface for punctuation-aware Stage12 cuts.

The numeric punctuation-shadow experiments intentionally translate only
numeric-bearing units. That is sufficient to detect numeric regressions but
not sufficient to promote a planner change: moving a boundary can change the
translation of ordinary prose that contains no digits at all.

This audit reconstructs the current planner-v8 Product plan from the latest
fail-closed full-Opticks Product artifact, applies a configurable punctuation
backtrack window, finds every source region whose partition changed, and
regenerates *all* shadow linguistic units in those regions with the same pinned
real OPUS float32 rank-0 runtime. It exports complete source, baseline Product
target and shadow target text for manual semantic inspection, together with
unchanged mechanical diagnostics.

No Product database rows are written. Source and target text are never
rewritten, placeholders and literal injection are forbidden, and a green
mechanical verdict is explicitly not a promotion decision.
"""

from difflib import SequenceMatcher
import hashlib
import json
import os
from pathlib import Path
import re
import sys
from typing import Any

from rocketdict.database import connect, get_document, get_document_segments, get_run_items
from rocketdict.runtime import OpusTranslator
import rocketdict.translation_stage as translation_stage
from rocketdict.translation_stage import PLANNER_CONTRACT

sys.path.insert(0, str(Path(__file__).resolve().parent))
from real_translation_nbest_feasibility import _verdict  # noqa: E402

SCHEMA = "rocketdict-full-opticks-punctuation-semantic-audit/1"
BASE_SCHEMA = "rocketdict-full-opticks-numeric-stress/3"
RAW_SOURCE_SHA256 = "1e25ec2c54fc6e9fa05d7f0a663e05cf2ee671231c65731f4845df2539dfb217"
EXPECTED_BASELINE_RUN_ID = "34338655735"
EXPECTED_BASELINE_ARTIFACT_ID = "10099448450"
BACKTRACK_TOKENS = 6
MAJOR = frozenset({";", ":", ".", "!", "?"})
ORDINARY_MT_SOURCES = frozenset(
    {"nlp_sentence", "nlp_sentence_fragment", "nlp_sentence_group"}
)
BATCH_SIZE = 48
_ASCII_WORD = re.compile(r"\b[A-Za-z]{3,}\b")
_CYRILLIC = re.compile(r"[А-Яа-яЁё]")
_ALPHA = re.compile(r"[A-Za-zА-Яа-яЁё]")


def _sha(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _canonical_sha(value: Any) -> str:
    raw = json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def _token_text(token: dict[str, Any]) -> str:
    value = token.get("source_text")
    return str(value if value is not None else token.get("text") or "")


def _normalized_similarity(left: str, right: str) -> float:
    return SequenceMatcher(
        a=" ".join(left.split()),
        b=" ".join(right.split()),
        autojunk=False,
    ).ratio()


def _russian_alpha_ratio(text: str) -> float:
    alpha = _ALPHA.findall(text)
    if not alpha:
        return 0.0
    return sum(1 for char in alpha if _CYRILLIC.fullmatch(char)) / len(alpha)


def _translate(
    translator: OpusTranslator,
    texts: list[str],
    *,
    max_decoding_length: int,
) -> list[list[dict[str, Any]]]:
    output: list[list[dict[str, Any]]] = []
    for start in range(0, len(texts), BATCH_SIZE):
        output.extend(
            translator.translate(
                texts[start : start + BATCH_SIZE],
                beam_size=6,
                num_hypotheses=1,
                max_decoding_length=max_decoding_length,
            )
        )
    if len(output) != len(texts):
        raise RuntimeError("punctuation semantic audit translation cardinality mismatch")
    return output


def _changed_regions(
    baseline_units: list[dict[str, Any]],
    shadow_units: list[dict[str, Any]],
    *,
    source_length: int,
) -> list[tuple[int, int]]:
    baseline_boundaries = {0, source_length, *[int(row["source_end"]) for row in baseline_units]}
    shadow_boundaries = {0, source_length, *[int(row["end"]) for row in shadow_units]}
    changed = sorted(baseline_boundaries ^ shadow_boundaries)
    common = sorted(baseline_boundaries & shadow_boundaries)
    if not changed:
        return []

    raw: list[tuple[int, int]] = []
    for boundary in changed:
        left = max(value for value in common if value < boundary)
        right = min(value for value in common if value > boundary)
        raw.append((left, right))

    merged: list[tuple[int, int]] = []
    for start, end in sorted(set(raw)):
        if merged and start <= merged[-1][1]:
            merged[-1] = (merged[-1][0], max(merged[-1][1], end))
        else:
            merged.append((start, end))
    return merged


def main() -> int:
    root = Path(
        os.environ.get(
            "ROCKETDICT_NUMERIC_STRESS_ROOT",
            "work/full-opticks-current/full-opticks-numeric-stress",
        )
    ).resolve()
    baseline_path = root / "full-opticks-numeric-stress.json"
    database = root / "project" / "data" / "rocketdict.sqlite"
    if not baseline_path.is_file() or not database.is_file():
        raise RuntimeError("current fail-closed full-Opticks Product artifact is incomplete")

    baseline = json.loads(baseline_path.read_text(encoding="utf-8"))
    if baseline.get("schema") != BASE_SCHEMA:
        raise RuntimeError("unexpected full-Opticks baseline schema")
    if baseline.get("source_sha256") != RAW_SOURCE_SHA256:
        raise RuntimeError("pinned Opticks identity drift")
    if baseline.get("stage12_planner_contract") != PLANNER_CONTRACT:
        raise RuntimeError("semantic audit baseline planner is not current")
    if os.environ.get("ROCKETDICT_BASELINE_RUN_ID") != EXPECTED_BASELINE_RUN_ID:
        raise RuntimeError("semantic audit baseline run identity drift")
    if os.environ.get("ROCKETDICT_BASELINE_ARTIFACT_ID") != EXPECTED_BASELINE_ARTIFACT_ID:
        raise RuntimeError("semantic audit baseline artifact identity drift")
    parameters = dict(baseline.get("stage12_parameters") or {})
    if parameters.get("enable_selective_resegmentation_rescue") is not False:
        raise RuntimeError("semantic audit requires the fail-closed Product Stage12 baseline")

    document_version_id = int(baseline["document_version_id"])
    nlp_run_id = int((baseline.get("stage8") or {})["nlp_run_id"])
    context_run_id = int((baseline.get("stage10") or {})["context_run_id"])
    translation_run_id = int((baseline.get("stage12") or {})["translation_run_id"])
    preferred_tokens = int(parameters.get("plan_preferred_unit_tokens") or 64)

    with connect(database, readonly=True) as connection:
        document = get_document(connection, document_version_id)
        segments = get_document_segments(connection, document_version_id)
        nlp_tokens = get_run_items(connection, nlp_run_id, kind="nlp_token")
        context_items = get_run_items(connection, context_run_id, kind="context_sentence")
        baseline_units = get_run_items(
            connection, translation_run_id, kind="translation_segment"
        )

    content = str(document["content_text"])
    if hashlib.sha256(content.encode("utf-8")).hexdigest() != str(
        baseline.get("source_text_sha256") or ""
    ):
        raise RuntimeError("normalized Opticks text identity drift")
    if "".join(str(row.get("source_text") or "") for row in baseline_units) != content:
        raise RuntimeError("baseline Product segments do not byte-exactly cover source")

    original_split = translation_stage._safe_forward_split_index
    choices: list[dict[str, Any]] = []

    def shadow_split(
        tokens: list[dict[str, Any]],
        *,
        desired_index: int,
        spans: list[tuple[int, int, str]],
    ) -> int:
        if desired_index >= len(tokens):
            return len(tokens)
        maintained = original_split(tokens, desired_index=desired_index, spans=spans)
        lower = max(0, desired_index - BACKTRACK_TOKENS)
        for punctuation_index in range(desired_index - 1, lower - 1, -1):
            if _token_text(tokens[punctuation_index]) not in MAJOR:
                continue
            split_index = punctuation_index + 1
            if split_index >= len(tokens):
                return len(tokens)
            cut = int(tokens[split_index]["source_start"])
            if translation_stage._cut_inside_span(cut, spans):
                continue
            if split_index != maintained:
                choices.append(
                    {
                        "desired_index": desired_index,
                        "maintained_split_index": maintained,
                        "shadow_split_index": split_index,
                        "backtrack_tokens": desired_index - split_index,
                        "punctuation": _token_text(tokens[punctuation_index]),
                        "cut": cut,
                    }
                )
            return split_index
        return maintained

    database_sha_before = _sha(database)
    translation_stage._safe_forward_split_index = shadow_split
    try:
        shadow_units = translation_stage.segment_translation_units(
            content,
            segments,
            context_items,
            nlp_tokens,
            selected_format="txt",
            preferred_tokens=preferred_tokens,
        )
    finally:
        translation_stage._safe_forward_split_index = original_split

    if "".join(str(unit["text"]) for unit in shadow_units) != content:
        raise RuntimeError("shadow plan does not byte-exactly cover source")

    regions = _changed_regions(
        baseline_units,
        shadow_units,
        source_length=len(content),
    )
    if not regions:
        raise RuntimeError(
            f"{BACKTRACK_TOKENS}-token punctuation shadow unexpectedly changes no boundaries"
        )

    affected_shadow: list[dict[str, Any]] = []
    affected_index: dict[tuple[int, int], int] = {}
    region_inputs: list[dict[str, Any]] = []
    observed_linguistic_sources: set[str] = set()
    for region_index, (start, end) in enumerate(regions):
        product_rows = [
            row
            for row in baseline_units
            if int(row["source_start"]) >= start and int(row["source_end"]) <= end
        ]
        shadow_rows = [
            unit
            for unit in shadow_units
            if int(unit["start"]) >= start and int(unit["end"]) <= end
        ]
        source = content[start:end]
        if "".join(str(row.get("source_text") or "") for row in product_rows) != source:
            raise RuntimeError(f"baseline region {region_index} does not cover source")
        if "".join(str(row["text"]) for row in shadow_rows) != source:
            raise RuntimeError(f"shadow region {region_index} does not cover source")
        for unit in shadow_rows:
            metadata = dict(unit.get("metadata") or {})
            source_kind = str(metadata.get("source") or "")
            if source_kind not in ORDINARY_MT_SOURCES:
                raise RuntimeError(
                    "punctuation shadow changed a source-owned or unknown Stage12 class: "
                    f"{source_kind!r} at {unit['start']}:{unit['end']}"
                )
            observed_linguistic_sources.add(source_kind)
            key = (int(unit["start"]), int(unit["end"]))
            if key not in affected_index:
                affected_index[key] = len(affected_shadow)
                affected_shadow.append(unit)
        region_inputs.append(
            {
                "region_index": region_index,
                "source_start": start,
                "source_end": end,
                "source_text": source,
                "baseline_units": product_rows,
                "shadow_units": shadow_rows,
            }
        )

    max_tokens = max(
        (
            int((unit.get("metadata") or {}).get("token_count") or 0)
            for unit in affected_shadow
        ),
        default=preferred_tokens,
    )
    max_decoding_length = max(128, max(preferred_tokens, max_tokens) * 8)
    translator = OpusTranslator(device="cpu", compute_type="float32")
    generated_rows = _translate(
        translator,
        [str(unit["text"]) for unit in affected_shadow],
        max_decoding_length=max_decoding_length,
    )
    generated: dict[tuple[int, int], dict[str, Any]] = {}
    for unit, hypotheses in zip(affected_shadow, generated_rows, strict=True):
        if not hypotheses:
            raise RuntimeError(f"OPUS returned no rank-0 hypothesis at {unit['start']}:{unit['end']}")
        target = str(hypotheses[0].get("text") or "")
        if not target.strip():
            raise RuntimeError(f"OPUS returned empty rank-0 target at {unit['start']}:{unit['end']}")
        generated[(int(unit["start"]), int(unit["end"]))] = {
            "target_text": target,
            "rank0_score": hypotheses[0].get("score"),
        }

    quality = dict(baseline.get("quality_gate_parameters") or {})
    punctuation_parameters = dict(quality.get("punctuation") or {})
    length_parameters = dict(quality.get("length_ratio") or {})
    review_regions: list[dict[str, Any]] = []
    for region in region_inputs:
        baseline_target = "".join(
            str(row.get("target_text") or "") for row in region["baseline_units"]
        )
        shadow_target_parts: list[str] = []
        shadow_records: list[dict[str, Any]] = []
        for unit in region["shadow_units"]:
            key = (int(unit["start"]), int(unit["end"]))
            result = generated[key]
            shadow_target_parts.append(str(result["target_text"]))
            shadow_records.append(
                {
                    "source_start": key[0],
                    "source_end": key[1],
                    "source_text": str(unit["text"]),
                    "target_text": str(result["target_text"]),
                    "rank0_score": result["rank0_score"],
                    "planner": dict(unit.get("metadata") or {}),
                }
            )
        shadow_target = "".join(shadow_target_parts)
        source_row = {
            "sequence_number": int(region["region_index"]),
            "source_start": int(region["source_start"]),
            "source_end": int(region["source_end"]),
            "source_text": str(region["source_text"]),
            "target_text": None,
        }
        baseline_verdict = _verdict(
            source_row,
            baseline_target,
            punctuation_parameters=punctuation_parameters,
            length_parameters=length_parameters,
        )
        shadow_verdict = _verdict(
            source_row,
            shadow_target,
            punctuation_parameters=punctuation_parameters,
            length_parameters=length_parameters,
        )
        review_regions.append(
            {
                "region_index": int(region["region_index"]),
                "source_start": int(region["source_start"]),
                "source_end": int(region["source_end"]),
                "source_text": str(region["source_text"]),
                "baseline_target_text": baseline_target,
                "shadow_target_text": shadow_target,
                "target_similarity": _normalized_similarity(baseline_target, shadow_target),
                "baseline_target_ascii_words": _ASCII_WORD.findall(baseline_target),
                "shadow_target_ascii_words": _ASCII_WORD.findall(shadow_target),
                "baseline_russian_alpha_ratio": _russian_alpha_ratio(baseline_target),
                "shadow_russian_alpha_ratio": _russian_alpha_ratio(shadow_target),
                "baseline_verdict": baseline_verdict,
                "shadow_verdict": shadow_verdict,
                "baseline_units": [
                    {
                        "source_start": int(row["source_start"]),
                        "source_end": int(row["source_end"]),
                        "source_text": str(row.get("source_text") or ""),
                        "target_text": str(row.get("target_text") or ""),
                        "planner": dict((row.get("payload") or {}).get("planner") or {}),
                    }
                    for row in region["baseline_units"]
                ],
                "shadow_units": shadow_records,
            }
        )

    database_sha_after = _sha(database)
    if database_sha_after != database_sha_before:
        raise RuntimeError("punctuation semantic audit mutated Product database")

    payload: dict[str, Any] = {
        "schema": SCHEMA,
        "purpose": (
            "complete semantic-review surface for every "
            f"{BACKTRACK_TOKENS}-token punctuation-shadow partition change"
        ),
        "promotion_allowed": False,
        "manual_semantic_review_required": True,
        "source_rewriting": False,
        "target_rewriting": False,
        "placeholders": False,
        "post_translation_literal_injection": False,
        "raw_source_sha256": RAW_SOURCE_SHA256,
        "source_text_sha256": str(baseline.get("source_text_sha256") or ""),
        "maintained_planner_contract": PLANNER_CONTRACT,
        "baseline_run_id": EXPECTED_BASELINE_RUN_ID,
        "baseline_artifact_id": EXPECTED_BASELINE_ARTIFACT_ID,
        "baseline_json_sha256": _sha(baseline_path),
        "baseline_rescue_enabled": False,
        "candidate_policy": {
            "backtrack_tokens": BACKTRACK_TOKENS,
            "major_punctuation": sorted(MAJOR),
            "fallback": "maintained_planner_v8_split_choice",
        },
        "allowed_linguistic_source_classes": sorted(ORDINARY_MT_SOURCES),
        "observed_linguistic_source_classes": sorted(observed_linguistic_sources),
        "generation": {"beam_size": 6, "num_hypotheses": 1},
        "max_decoding_length": max_decoding_length,
        "baseline_unit_count": len(baseline_units),
        "shadow_unit_count": len(shadow_units),
        "changed_split_choice_count": len(choices),
        "changed_split_choices": choices,
        "changed_region_count": len(review_regions),
        "affected_shadow_unit_count": len(affected_shadow),
        "mechanically_strict_baseline_region_count": sum(
            1 for row in review_regions if (row["baseline_verdict"] or {}).get("strictly_eligible") is True
        ),
        "mechanically_strict_shadow_region_count": sum(
            1 for row in review_regions if (row["shadow_verdict"] or {}).get("strictly_eligible") is True
        ),
        "database_sha256_before": database_sha_before,
        "database_sha256_after": database_sha_after,
        "database_mutated": False,
        "regions": review_regions,
    }
    payload["evidence_sha256"] = _canonical_sha(payload)
    output_root = Path(
        os.environ.get("ROCKETDICT_PUNCTUATION_SEMANTIC_ROOT", "work/punctuation-semantic-audit")
    ).resolve()
    output_root.mkdir(parents=True, exist_ok=True)
    output = output_root / "full-opticks-punctuation-semantic-audit.json"
    output.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(
        json.dumps(
            {
                "schema": SCHEMA,
                "changed_split_choice_count": payload["changed_split_choice_count"],
                "changed_region_count": payload["changed_region_count"],
                "affected_shadow_unit_count": payload["affected_shadow_unit_count"],
                "mechanically_strict_baseline_region_count": payload["mechanically_strict_baseline_region_count"],
                "mechanically_strict_shadow_region_count": payload["mechanically_strict_shadow_region_count"],
                "database_mutated": payload["database_mutated"],
                "evidence_sha256": payload["evidence_sha256"],
            },
            ensure_ascii=False,
            indent=2,
        ),
        flush=True,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
