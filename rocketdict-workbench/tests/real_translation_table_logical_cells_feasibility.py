from __future__ import annotations

"""Research-only logical-cell translation over every maintained Opticks table.

This is the semantic follow-up to physical table-cells/1.  The source-only
logical grouping combines wrapped headers/descriptions before real OPUS MT while
leaving source-owned geometry and alpha-free numeric cells outside the model.
The rendered complete table must still pass the maintained full-table strict
checks.  No source literal is injected after MT and no Product default changes.
"""

from collections import Counter
import hashlib
import json
import os
from pathlib import Path
import re
from typing import Any

from rocketdict.numeric_integrity import CONTRACT as NUMERIC_CONTRACT
from rocketdict.runtime import OpusTranslator
from rocketdict.table_logical_structure import (
    LOGICAL_TABLE_CONTRACT,
    plan_logical_table_text_groups,
    render_logical_ascii_table,
)
from rocketdict.table_structure import (
    TABLE_STRUCTURE_CONTRACT,
    detect_ascii_table_blocks,
    plan_ascii_table_pieces,
)

from real_translation_table_cells_feasibility import _verdict

SCHEMA = "rocketdict-full-opticks-table-logical-cells-feasibility/1"
OPTICKS_SHA256 = "1e25ec2c54fc6e9fa05d7f0a663e05cf2ee671231c65731f4845df2539dfb217"
GENERATION = {"beam_size": 6, "num_hypotheses": 6}
BATCH_SIZE = 64
_NUMERIC_RELATION_RE = re.compile(
    r"^\s*[+\-−]?\d[\d\s.,'’/\-−–+]*\s+(?:to)\s+[+\-−]?\d[\d\s.,'’/\-−–+]*\s*$",
    re.IGNORECASE,
)


def _sha_file(path: Path) -> str:
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


def _is_numeric_relation(source: str) -> bool:
    return _NUMERIC_RELATION_RE.fullmatch(source) is not None


def _candidate_eligible(source: str, verdict: dict[str, Any]) -> tuple[bool, str]:
    required = bool(
        (verdict.get("numeric_symbol") or {}).get("passed") is True
        and (verdict.get("punctuation") or {}).get("passed") is True
        and (verdict.get("delimiter_preservation") or {}).get("passed") is True
        and (verdict.get("critical_technical_tokens") or {}).get("passed") is True
        and (verdict.get("output_artifacts") or {}).get("passed") is True
    )
    if not required:
        return False, "integrity_or_structure_failure"
    if (verdict.get("length") or {}).get("passed") is True:
        return True, "full_local_strict"
    if _is_numeric_relation(source):
        # Micro relation cells can legitimately lexicalize "to" as a dash.  The
        # assembled table remains subject to the ordinary Product length gate.
        return True, "numeric_relation_full_table_length"
    return False, "local_length_failure"


def _translate_batches(translator: OpusTranslator, texts: list[str]) -> list[list[dict[str, Any]]]:
    output: list[list[dict[str, Any]]] = []
    for start in range(0, len(texts), BATCH_SIZE):
        output.extend(
            translator.translate(
                texts[start : start + BATCH_SIZE],
                beam_size=GENERATION["beam_size"],
                num_hypotheses=GENERATION["num_hypotheses"],
                max_decoding_length=384,
            )
        )
    if len(output) != len(texts):
        raise RuntimeError("logical table OPUS batch cardinality mismatch")
    return output


def main() -> int:
    root = Path(
        os.environ.get(
            "ROCKETDICT_TABLE_LOGICAL_ROOT",
            "work/full-opticks-table-logical-cells",
        )
    ).resolve()
    root.mkdir(parents=True, exist_ok=True)
    source_path = Path(os.environ["ROCKETDICT_OPTICKS_SOURCE"]).resolve()
    if _sha_file(source_path) != OPTICKS_SHA256:
        raise RuntimeError("Pinned Opticks source hash drift")
    source = source_path.read_text(encoding="utf-8")

    blocks = detect_ascii_table_blocks(source)
    if not blocks:
        raise RuntimeError("No maintained ASCII-table blocks detected")

    block_plans: list[dict[str, Any]] = []
    group_rows: list[dict[str, Any]] = []
    alpha_total = 0
    alpha_grouped = 0
    physical_translate_count = 0

    for block_index, block in enumerate(blocks):
        block_text = source[block.start : block.end]
        pieces = plan_ascii_table_pieces(block_text, absolute_start=block.start)
        groups = plan_logical_table_text_groups(
            block_text,
            pieces,
            absolute_start=block.start,
        )
        physical_translate = [piece for piece in pieces if piece.kind == "translate"]
        physical_translate_count += len(physical_translate)
        alpha_total += sum(
            sum(char.isalpha() for char in piece.text)
            for piece in physical_translate
        )
        alpha_grouped += sum(
            sum(char.isalpha() for char in group.source_text)
            for group in groups
        )
        block_plans.append(
            {
                "block": block,
                "source_text": block_text,
                "pieces": pieces,
                "groups": groups,
            }
        )
        for group in groups:
            group_rows.append(
                {
                    "block_index": block_index,
                    "group_index": group.index,
                    "piece_indices": list(group.piece_indices),
                    "source_text": group.source_text,
                    "first_line": group.first_line,
                    "last_line": group.last_line,
                    "lane": group.lane,
                    "section": group.section,
                    "numeric_bearing": group.numeric_bearing,
                    "numeric_relation": _is_numeric_relation(group.source_text),
                    "grouping_reason": group.grouping_reason,
                }
            )

    if alpha_grouped != alpha_total:
        raise RuntimeError(
            f"logical grouping alpha coverage mismatch: {alpha_grouped} != {alpha_total}"
        )

    translator = OpusTranslator(device="cpu", compute_type="float32")
    generated = _translate_batches(
        translator,
        [str(row["source_text"]) for row in group_rows],
    )

    translation_maps: list[dict[int, str]] = [dict() for _ in blocks]
    group_failures: list[dict[str, Any]] = []
    group_evidence: list[dict[str, Any]] = []
    rank_distribution: Counter[int] = Counter()
    selection_reason_counts: Counter[str] = Counter()

    for row, hypotheses in zip(group_rows, generated, strict=True):
        if not hypotheses:
            raise RuntimeError("OPUS returned no logical table hypothesis")
        candidates: list[dict[str, Any]] = []
        selected: dict[str, Any] | None = None
        selected_reason: str | None = None
        for hypothesis in hypotheses:
            target = str(hypothesis.get("text") or "")
            verdict = _verdict(str(row["source_text"]), target)
            eligible, reason = _candidate_eligible(str(row["source_text"]), verdict)
            candidate = {
                "rank": int(hypothesis.get("rank") or 0),
                "score": hypothesis.get("score"),
                "target_text": target,
                "eligible": eligible,
                "eligibility_reason": reason,
                "verdict": verdict,
            }
            candidates.append(candidate)
            if selected is None and eligible:
                selected = candidate
                selected_reason = reason

        if selected is None:
            selected = candidates[0]
            selected_reason = "fallback_rank0_no_eligible_raw_candidate"
            group_failures.append(
                {
                    **row,
                    "rank0_target_text": candidates[0]["target_text"],
                    "candidate_failure_reasons": [
                        candidate["eligibility_reason"] for candidate in candidates
                    ],
                }
            )
        rank_distribution[int(selected["rank"])] += 1
        selection_reason_counts[str(selected_reason)] += 1
        translation_maps[int(row["block_index"])][int(row["group_index"])] = str(
            selected["target_text"]
        )
        group_evidence.append(
            {
                **row,
                "selected": selected,
                "selected_reason": selected_reason,
                "eligible_candidate_ranks": [
                    int(candidate["rank"])
                    for candidate in candidates
                    if candidate["eligible"] is True
                ],
                "candidates": candidates,
            }
        )

    block_evidence: list[dict[str, Any]] = []
    passed_blocks = 0
    for block_index, plan in enumerate(block_plans):
        block = plan["block"]
        source_text = str(plan["source_text"])
        target_text = render_logical_ascii_table(
            source_text,
            plan["pieces"],
            plan["groups"],
            translation_maps[block_index],
        )
        verdict = _verdict(source_text, target_text)
        geometry = {
            "source_pipe_count": source_text.count("|"),
            "target_pipe_count": target_text.count("|"),
            "source_newline_count": source_text.count("\n"),
            "target_newline_count": target_text.count("\n"),
            "source_left_brace_count": source_text.count("{"),
            "target_left_brace_count": target_text.count("{"),
            "pipe_count_preserved": source_text.count("|") == target_text.count("|"),
            "newline_count_preserved": source_text.count("\n") == target_text.count("\n"),
            "left_brace_count_preserved": source_text.count("{") == target_text.count("{"),
        }
        passed = bool(
            verdict.get("strictly_eligible") is True
            and all(
                geometry[key] is True
                for key in (
                    "pipe_count_preserved",
                    "newline_count_preserved",
                    "left_brace_count_preserved",
                )
            )
        )
        passed_blocks += int(passed)
        block_evidence.append(
            {
                "block_index": block_index,
                "source_start": block.start,
                "source_end": block.end,
                "source_text": source_text,
                "target_text": target_text,
                "logical_group_count": len(plan["groups"]),
                "multi_piece_group_count": sum(
                    1 for group in plan["groups"] if len(group.piece_indices) > 1
                ),
                "geometry": geometry,
                "verdict": verdict,
                "passed": passed,
            }
        )

    asset = translator.asset
    payload: dict[str, Any] = {
        "schema": SCHEMA,
        "purpose": "full contiguous Opticks semantic feasibility for source-only logical ASCII table text grouping",
        "promotion_allowed": False,
        "no_synthetic_target_repair": True,
        "source_sha256": OPTICKS_SHA256,
        "source_char_count": len(source),
        "physical_table_contract": TABLE_STRUCTURE_CONTRACT,
        "logical_table_contract": LOGICAL_TABLE_CONTRACT,
        "numeric_contract": NUMERIC_CONTRACT,
        "generation": dict(GENERATION),
        "table_block_count": len(blocks),
        "passed_table_block_count": passed_blocks,
        "failed_table_block_count": len(blocks) - passed_blocks,
        "physical_translate_piece_count": physical_translate_count,
        "logical_group_count": len(group_rows),
        "multi_piece_group_count": sum(
            1 for row in group_rows if len(row["piece_indices"]) > 1
        ),
        "numeric_relation_group_count": sum(
            1 for row in group_rows if row["numeric_relation"] is True
        ),
        "group_without_eligible_candidate_count": len(group_failures),
        "alpha_source_char_count": alpha_total,
        "alpha_source_char_count_in_logical_groups": alpha_grouped,
        "selected_rank_distribution": {
            str(rank): count for rank, count in sorted(rank_distribution.items())
        },
        "selection_reason_counts": dict(sorted(selection_reason_counts.items())),
        "model": {
            "revision": asset.revision,
            "source_archive_sha256": asset.source_archive_sha256,
            "manifest_sha256": asset.manifest_sha256,
            "payload_tree_sha256": asset.payload_tree_sha256,
            "compute_type": "float32",
            "device": "cpu",
        },
        "group_failures": group_failures,
        "groups": group_evidence,
        "blocks": block_evidence,
    }
    payload["evidence_sha256"] = _canonical_sha(payload)
    output = root / "full-opticks-table-logical-cells-feasibility.json"
    output.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "schema": SCHEMA,
                "table_block_count": len(blocks),
                "passed_table_block_count": passed_blocks,
                "physical_translate_piece_count": physical_translate_count,
                "logical_group_count": len(group_rows),
                "multi_piece_group_count": payload["multi_piece_group_count"],
                "numeric_relation_group_count": payload["numeric_relation_group_count"],
                "group_without_eligible_candidate_count": len(group_failures),
                "selected_rank_distribution": payload["selected_rank_distribution"],
                "selection_reason_counts": payload["selection_reason_counts"],
                "evidence_sha256": payload["evidence_sha256"],
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
