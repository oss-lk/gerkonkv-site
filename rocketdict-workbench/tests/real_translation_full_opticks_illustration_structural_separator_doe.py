from __future__ import annotations

"""Read-only DOE for source-planned illustration separator preservation.

The experiment starts from exact rank0-clean run41.  It recognizes the complete
source shape before any MT call, partitions it into translate/preserve/translate
pieces, and carries only the immutable source-owned blank-line piece verbatim.
This mirrors the maintained ASCII-table render contract: preserved bytes are
part of a pre-MT source plan, never a target-side repair.  Both translated
pieces remain unmodified raw rank0 outputs.
"""

import hashlib
import json
import os
from pathlib import Path
import re
from typing import Any

from rocketdict.alternative_mt_runtime import TcBigTranslator
from rocketdict.database import connect, get_document, get_run, get_run_items
from rocketdict.emphasis_markup import compare_emphasis_markup_preservation
from rocketdict.runtime import OpusTranslator
from rocketdict.translation_rescue import evaluate_rescue_pair

SCHEMA = "rocketdict-full-opticks-illustration-structural-separator-doe/1"
SOURCE_PLAN_CONTRACT = "rocketdict-illustration-source-planned-structural-pieces/1"
BASE_DATABASE_SHA256 = "e48df8a90a3aa5e07bbc7e86c150d7b65ce450e7b6a0ec0d2e34a0caf9846e2e"
BASE_RUN_ID = 41
BASE_OUTPUT_SHA256 = "d8948e43158a126703a90e6ce1cd25725da8774e1db64410ca67e3ec7bb1a10f"
SOURCE_TEXT_SHA256 = "436bfa539f5e8c84c5c3af71eff49a89858d3b2c4ad45ddd55144b6f4066c87a"
EXPECTED_STARTS = [72401, 90105]

_PATTERN = re.compile(
    r"\A(?P<label>\[Illustration:\s*FIG\.\s*\d+\.\])"
    r"(?P<separator>\r?\n[ \t]*\r?\n)"
    r"(?P<suffix>_Illustration\._)"
    r"(?P<trailing>[ \t]*)\Z",
    re.IGNORECASE,
)


def _sha_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def _canonical_sha(value: Any) -> str:
    return hashlib.sha256(
        json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()
    ).hexdigest()


def _rank0(translator: Any, texts: list[str]) -> dict[str, dict[str, Any]]:
    generated = translator.translate(texts, beam_size=6, num_hypotheses=1, max_decoding_length=128)
    if len(generated) != len(texts):
        raise RuntimeError("rank0 batch cardinality drift")
    out: dict[str, dict[str, Any]] = {}
    for source, hypotheses in zip(texts, generated, strict=True):
        if len(hypotheses) != 1 or int(hypotheses[0].get("rank", -1)) != 0:
            raise RuntimeError(f"rank0 hypothesis drift for {source!r}")
        target = str(hypotheses[0].get("text") or "")
        if not target.strip():
            raise RuntimeError(f"empty rank0 hypothesis for {source!r}")
        out[source] = {"rank": 0, "text": target, "score": hypotheses[0].get("score")}
    return out


def _hard_failure(source: str, target: str, family: str) -> bool:
    verdict = evaluate_rescue_pair(source, target)
    if family == "punctuation":
        return verdict.get("punctuation_passed") is not True
    raise ValueError(family)


def _piece(source: str, raw: dict[str, Any], model: str, start: int) -> dict[str, Any]:
    target = str(raw["text"])
    verdict = evaluate_rescue_pair(source, target)
    emphasis = compare_emphasis_markup_preservation(source, target)
    return {
        "kind": "translate",
        "model": model,
        "source_start": start,
        "source_end": start + len(source),
        "source_text": source,
        "raw_rank": 0,
        "raw_score": raw.get("score"),
        "raw_target": target,
        "mechanical_verdict": verdict,
        "emphasis_markup": emphasis,
        "strictly_eligible": verdict.get("strictly_eligible") is True,
    }


def main() -> int:
    root = Path(os.environ.get("ROCKETDICT_ILLUSTRATION_SEPARATOR_DOE_ROOT", "work/illustration-structural-separator-doe")).resolve()
    root.mkdir(parents=True, exist_ok=True)
    db = root / "rocketdict.sqlite"
    before = _sha_file(db)
    if before != BASE_DATABASE_SHA256:
        raise RuntimeError(f"DOE requires exact run41 DB: {before}")

    with connect(db, readonly=True) as connection:
        run = get_run(connection, BASE_RUN_ID)
        rows = sorted(get_run_items(connection, BASE_RUN_ID, kind="translation_segment"), key=lambda r: int(r["sequence_number"]))
        output = dict(run.get("output") or {})
        document = get_document(connection, int(output["document_version_id"]))
    if str(run.get("output_sha256") or "") != BASE_OUTPUT_SHA256:
        raise RuntimeError("run41 output identity drift")
    if str(document.get("text_sha256") or "") != SOURCE_TEXT_SHA256:
        raise RuntimeError("source identity drift")
    content = str(document["content_text"])
    if "".join(str(r.get("source_text") or "") for r in rows) != content:
        raise RuntimeError("run41 source coverage drift")

    cohort: list[dict[str, Any]] = []
    for row in rows:
        source = str(row.get("source_text") or "")
        target = str(row.get("target_text") or "")
        if _PATTERN.fullmatch(source) and _hard_failure(source, target, "punctuation"):
            cohort.append(row)
    starts = [int(r["source_start"]) for r in cohort]
    if starts != EXPECTED_STARTS:
        raise RuntimeError(f"illustration cohort drift: {starts!r}")

    parsed: list[dict[str, Any]] = []
    requests = {"opus": [], "tc_big": []}
    for row in cohort:
        source = str(row["source_text"])
        match = _PATTERN.fullmatch(source)
        assert match is not None
        label = match.group("label")
        separator = match.group("separator")
        suffix = match.group("suffix")
        trailing = match.group("trailing")
        if label + separator + suffix + trailing != source:
            raise RuntimeError("source plan coverage drift")
        if not separator or separator.strip() or separator.count("\n") < 2:
            raise RuntimeError("source separator is not a blank-line structural piece")
        parsed.append({"row": row, "label": label, "separator": separator, "suffix": suffix, "trailing": trailing})
        for model in requests:
            for text in (label, suffix):
                if text not in requests[model]:
                    requests[model].append(text)

    opus = _rank0(OpusTranslator(device="cpu", compute_type="float32"), requests["opus"])
    tc_big = _rank0(TcBigTranslator(device="cpu", compute_type="float32"), requests["tc_big"])
    by_model = {"opus": opus, "tc_big": tc_big}

    candidates: list[dict[str, Any]] = []
    for item in parsed:
        row = item["row"]
        source = str(row["source_text"])
        start = int(row["source_start"])
        label = str(item["label"])
        separator = str(item["separator"])
        suffix = str(item["suffix"])
        trailing = str(item["trailing"])
        for label_model in ("opus", "tc_big"):
            for suffix_model in ("opus", "tc_big"):
                label_raw = by_model[label_model][label]
                suffix_raw = by_model[suffix_model][suffix]
                label_piece = _piece(label, label_raw, label_model, start)
                sep_start = start + len(label)
                suffix_start = sep_start + len(separator)
                suffix_piece = _piece(suffix, suffix_raw, suffix_model, suffix_start)
                target = str(label_raw["text"]) + separator + str(suffix_raw["text"]) + trailing
                verdict = evaluate_rescue_pair(source, target)
                emphasis = compare_emphasis_markup_preservation(source, target)
                exact_separator_preserved = target[len(str(label_raw["text"])):len(str(label_raw["text"])) + len(separator)] == separator
                passed = bool(
                    label_piece["strictly_eligible"]
                    and suffix_piece["strictly_eligible"]
                    and verdict.get("strictly_eligible") is True
                    and emphasis.get("passed") is True
                    and exact_separator_preserved
                )
                candidates.append(
                    {
                        "candidate_id": f"illustration:{start}:planned-separator:{label_model}+{suffix_model}",
                        "source_start": start,
                        "source_end": int(row["source_end"]),
                        "source_text": source,
                        "base_target": str(row.get("target_text") or ""),
                        "source_plan_contract": SOURCE_PLAN_CONTRACT,
                        "source_plan_created_before_mt": True,
                        "pieces": [
                            label_piece,
                            {
                                "kind": "preserve_source_structure",
                                "source_start": sep_start,
                                "source_end": suffix_start,
                                "source_text": separator,
                                "rendered_text": separator,
                                "source_owned": True,
                            },
                            suffix_piece,
                            {
                                "kind": "preserve_source_structure",
                                "source_start": suffix_start + len(suffix),
                                "source_end": int(row["source_end"]),
                                "source_text": trailing,
                                "rendered_text": trailing,
                                "source_owned": True,
                            },
                        ],
                        "joined_target": target,
                        "aggregate_mechanical_verdict": verdict,
                        "aggregate_emphasis_markup": emphasis,
                        "exact_source_separator_preserved": exact_separator_preserved,
                        "mechanical_passed": passed,
                        "raw_rank0_only": True,
                        "source_bytes_rewritten": False,
                        "target_rewriting": False,
                        "placeholders": False,
                        "post_translation_literal_injection": False,
                        "source_owned_structural_passthrough": True,
                        "automatic_n_best_cherry_picking": False,
                    }
                )

    after = _sha_file(db)
    if after != before:
        raise RuntimeError("read-only DOE mutated database")
    passed_ids = [c["candidate_id"] for c in candidates if c["mechanical_passed"]]
    evidence: dict[str, Any] = {
        "schema": SCHEMA,
        "source_plan_contract": SOURCE_PLAN_CONTRACT,
        "precedent_contract": "rocketdict-stage12-ascii-table-logical-rank0/1",
        "base_translation_run_id": BASE_RUN_ID,
        "base_translation_output_sha256": BASE_OUTPUT_SHA256,
        "base_database_sha256": before,
        "source_text_sha256": SOURCE_TEXT_SHA256,
        "illustration_source_starts": starts,
        "candidate_count": len(candidates),
        "mechanically_passed_candidate_ids": passed_ids,
        "candidates": candidates,
        "database_unchanged": after == before,
        "source_coverage_byte_exact": True,
        "source_plan_created_before_mt": True,
        "raw_rank0_only": True,
        "source_bytes_rewritten": False,
        "target_rewriting": False,
        "placeholders": False,
        "post_translation_literal_injection": False,
        "source_owned_structural_passthrough": True,
        "corpus_specific_target_patches": False,
        "evaluator_weakened": False,
        "n_best_cherry_picking": False,
        "automatic_n_best_cherry_picking": False,
        "promotion_allowed": False,
        "semantic_boundary_review_required": True,
    }
    evidence["evidence_sha256"] = _canonical_sha(evidence)
    path = root / "full-opticks-illustration-structural-separator-doe.json"
    path.write_text(json.dumps(evidence, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")
    (root / "summary.json").write_text(
        json.dumps({"candidate_count": len(candidates), "mechanically_passed_candidate_ids": passed_ids, "evidence_sha256": evidence["evidence_sha256"]}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(json.dumps({"candidate_count": len(candidates), "mechanically_passed_candidate_ids": passed_ids, "evidence_sha256": evidence["evidence_sha256"]}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
