from __future__ import annotations

"""Research-only maintained ASCII-table translation feasibility on full Opticks.

The probe detects every conservative ASCII-table block directly from the pinned
contiguous source.  Source-owned geometry and alpha-free numeric/symbolic cells
are never sent through MT; alpha-bearing cell fragments are translated by the
pinned real OPUS float32 model.  Selection is limited to raw beam-6 hypotheses
that pass the maintained integrity/research checks.  Nothing is inserted or
reconstructed after model generation.

This is evidence for a future Stage12 structural executor, not Product promotion.
"""

from collections import Counter
import hashlib
import json
import os
from pathlib import Path
from typing import Any

from rocketdict.numeric_integrity import (
    CONTRACT as NUMERIC_CONTRACT,
    evaluate_numeric_symbol_pair,
    extract_numeric_literals,
)
from rocketdict.research_diagnostics import (
    CRITICAL_TOKEN_CONTRACT,
    DELIMITER_CONTRACT,
    OUTPUT_ARTIFACT_CONTRACT,
    compare_critical_technical_tokens,
    compare_delimiter_preservation,
    compare_output_artifacts,
)
from rocketdict.runtime import OpusTranslator
from rocketdict.table_structure import (
    TABLE_STRUCTURE_CONTRACT,
    detect_ascii_table_blocks,
    plan_ascii_table_pieces,
    render_ascii_table,
)

SCHEMA = "rocketdict-full-opticks-table-cells-feasibility/1"
OPTICKS_SHA256 = "1e25ec2c54fc6e9fa05d7f0a663e05cf2ee671231c65731f4845df2539dfb217"
GENERATION = {"beam_size": 6, "num_hypotheses": 6}
BATCH_SIZE = 64
MIN_LENGTH_RATIO = 0.15
MAX_LENGTH_RATIO = 6.0


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


def _punctuation(source: str, target: str) -> dict[str, Any]:
    mismatch: dict[str, Any] = {}
    for left, right in (("(", ")"), ("[", "]"), ("{", "}")):
        source_counts = [source.count(left), source.count(right)]
        target_counts = [target.count(left), target.count(right)]
        if source_counts != target_counts:
            mismatch[left + right] = {"source": source_counts, "target": target_counts}
    for terminal in ("?", "!"):
        if source.count(terminal) != target.count(terminal):
            mismatch[terminal] = {
                "source": source.count(terminal),
                "target": target.count(terminal),
            }
    return {"mismatch": mismatch, "passed": not mismatch}


def _length(source: str, target: str) -> dict[str, Any]:
    source_alpha = sum(char.isalpha() for char in source)
    target_alpha = sum(char.isalpha() for char in target)
    ratio = (
        target_alpha / source_alpha
        if source_alpha
        else (1.0 if not target_alpha else float("inf"))
    )
    passed = bool(
        target.strip()
        and ratio >= MIN_LENGTH_RATIO
        and ratio <= MAX_LENGTH_RATIO
    )
    return {
        "source_alpha": source_alpha,
        "target_alpha": target_alpha,
        "ratio": ratio if ratio != float("inf") else "infinite",
        "passed": passed,
    }


def _verdict(source: str, target: str) -> dict[str, Any]:
    numeric = evaluate_numeric_symbol_pair(source, target)
    punctuation = _punctuation(source, target)
    length = _length(source, target)
    delimiters = compare_delimiter_preservation(source, target)
    critical = compare_critical_technical_tokens(source, target)
    artifacts = compare_output_artifacts(source, target)
    strict = bool(
        numeric.get("passed") is True
        and punctuation["passed"] is True
        and length["passed"] is True
        and delimiters.get("passed") is True
        and critical.get("passed") is True
        and artifacts.get("passed") is True
    )
    return {
        "numeric_symbol": numeric,
        "punctuation": punctuation,
        "length": length,
        "delimiter_preservation": delimiters,
        "critical_technical_tokens": critical,
        "output_artifacts": artifacts,
        "strictly_eligible": strict,
    }


def _translate_batches(
    translator: OpusTranslator,
    texts: list[str],
) -> list[list[dict[str, Any]]]:
    output: list[list[dict[str, Any]]] = []
    for start in range(0, len(texts), BATCH_SIZE):
        output.extend(
            translator.translate(
                texts[start : start + BATCH_SIZE],
                beam_size=GENERATION["beam_size"],
                num_hypotheses=GENERATION["num_hypotheses"],
                max_decoding_length=256,
            )
        )
    if len(output) != len(texts):
        raise RuntimeError("table-cells OPUS batch cardinality mismatch")
    return output


def main() -> int:
    root = Path(
        os.environ.get(
            "ROCKETDICT_TABLE_CELLS_ROOT",
            "work/full-opticks-table-cells",
        )
    ).resolve()
    root.mkdir(parents=True, exist_ok=True)
    source_path = Path(os.environ["ROCKETDICT_OPTICKS_SOURCE"]).resolve()
    if _sha_file(source_path) != OPTICKS_SHA256:
        raise RuntimeError("Pinned Opticks source hash drift")
    source = source_path.read_text(encoding="utf-8")

    blocks = detect_ascii_table_blocks(source)
    if not blocks:
        raise RuntimeError("No maintained ASCII-table blocks detected in full Opticks")

    piece_rows: list[dict[str, Any]] = []
    block_piece_lists: list[list[Any]] = []
    alpha_source_in_tables = 0
    alpha_source_routed_to_mt = 0
    passthrough_numeric_literals = 0
    translated_piece_numeric_literals = 0

    for block_index, block in enumerate(blocks):
        block_text = source[block.start : block.end]
        pieces = plan_ascii_table_pieces(block_text, absolute_start=block.start)
        block_piece_lists.append(pieces)
        alpha_source_in_tables += sum(char.isalpha() for char in block_text)
        for piece in pieces:
            if piece.kind == "translate":
                alpha = sum(char.isalpha() for char in piece.text)
                if alpha <= 0:
                    raise RuntimeError("translate table piece contains no alphabetic payload")
                alpha_source_routed_to_mt += alpha
                translated_piece_numeric_literals += len(extract_numeric_literals(piece.text))
                piece_rows.append(
                    {
                        "block_index": block_index,
                        "piece_index": piece.index,
                        "source_start": piece.start,
                        "source_end": piece.end,
                        "line_index": piece.line_index,
                        "cell_index": piece.cell_index,
                        "source_text": piece.text,
                    }
                )
            else:
                if any(char.isalpha() for char in piece.text):
                    raise RuntimeError(
                        "alpha-bearing table source escaped the real-MT piece plan"
                    )
                if piece.kind == "passthrough":
                    passthrough_numeric_literals += len(extract_numeric_literals(piece.text))

    if alpha_source_routed_to_mt != alpha_source_in_tables:
        raise RuntimeError(
            "table-cells plan failed complete alphabetic source routing: "
            f"{alpha_source_routed_to_mt} != {alpha_source_in_tables}"
        )

    translator = OpusTranslator(device="cpu", compute_type="float32")
    generated = _translate_batches(
        translator,
        [str(row["source_text"]) for row in piece_rows],
    )

    translation_maps: list[dict[int, str]] = [dict() for _ in blocks]
    selected_rank_distribution: Counter[int] = Counter()
    piece_failures: list[dict[str, Any]] = []
    piece_evidence: list[dict[str, Any]] = []

    for row, hypotheses in zip(piece_rows, generated, strict=True):
        if not hypotheses:
            raise RuntimeError("OPUS returned no table-cell hypothesis")
        candidates: list[dict[str, Any]] = []
        selected: dict[str, Any] | None = None
        for hypothesis in hypotheses:
            target = str(hypothesis.get("text") or "")
            verdict = _verdict(str(row["source_text"]), target)
            candidate = {
                "rank": int(hypothesis.get("rank") or 0),
                "score": hypothesis.get("score"),
                "target_text": target,
                "verdict": verdict,
            }
            candidates.append(candidate)
            if selected is None and verdict["strictly_eligible"] is True:
                selected = candidate

        if selected is None:
            selected = candidates[0]
            piece_failures.append(
                {
                    **row,
                    "reason": "no_raw_hypothesis_passed_strict_table_cell_checks",
                    "rank0_target_text": candidates[0]["target_text"],
                }
            )
        selected_rank_distribution[int(selected["rank"])] += 1
        translation_maps[int(row["block_index"])][int(row["piece_index"])] = str(
            selected["target_text"]
        )
        piece_evidence.append(
            {
                **row,
                "selected": selected,
                "candidate_count": len(candidates),
                "strict_candidate_ranks": [
                    int(candidate["rank"])
                    for candidate in candidates
                    if (candidate.get("verdict") or {}).get("strictly_eligible") is True
                ],
                "candidates": candidates,
            }
        )

    block_evidence: list[dict[str, Any]] = []
    passed_blocks = 0
    for block_index, block in enumerate(blocks):
        source_text = source[block.start : block.end]
        target_text = render_ascii_table(
            source_text,
            block_piece_lists[block_index],
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
            verdict["strictly_eligible"] is True
            and geometry["pipe_count_preserved"] is True
            and geometry["newline_count_preserved"] is True
            and geometry["left_brace_count_preserved"] is True
        )
        passed_blocks += int(passed)
        block_evidence.append(
            {
                "block_index": block_index,
                "source_start": block.start,
                "source_end": block.end,
                "first_line": block.first_line,
                "last_line": block.last_line,
                "pipe_line_count": block.pipe_line_count,
                "separator_line_count": block.separator_line_count,
                "source_text": source_text,
                "target_text": target_text,
                "source_numeric_literal_count": len(extract_numeric_literals(source_text)),
                "target_numeric_literal_count": len(extract_numeric_literals(target_text)),
                "geometry": geometry,
                "verdict": verdict,
                "passed": passed,
            }
        )

    asset = translator.asset
    payload: dict[str, Any] = {
        "schema": SCHEMA,
        "purpose": "full contiguous Opticks feasibility for maintained source-owned ASCII table cell translation",
        "promotion_allowed": False,
        "no_synthetic_target_repair": True,
        "all_alpha_payload_routed_to_real_mt": alpha_source_routed_to_mt == alpha_source_in_tables,
        "source_sha256": OPTICKS_SHA256,
        "source_char_count": len(source),
        "table_structure_contract": TABLE_STRUCTURE_CONTRACT,
        "numeric_contract": NUMERIC_CONTRACT,
        "research_contracts": {
            "delimiter": DELIMITER_CONTRACT,
            "critical_token": CRITICAL_TOKEN_CONTRACT,
            "output_artifact": OUTPUT_ARTIFACT_CONTRACT,
        },
        "generation": dict(GENERATION),
        "table_block_count": len(blocks),
        "passed_table_block_count": passed_blocks,
        "failed_table_block_count": len(blocks) - passed_blocks,
        "translation_piece_count": len(piece_rows),
        "piece_without_strict_candidate_count": len(piece_failures),
        "alpha_source_char_count_in_tables": alpha_source_in_tables,
        "alpha_source_char_count_routed_to_mt": alpha_source_routed_to_mt,
        "passthrough_numeric_literal_count": passthrough_numeric_literals,
        "translated_piece_numeric_literal_count": translated_piece_numeric_literals,
        "selected_rank_distribution": {
            str(rank): count for rank, count in sorted(selected_rank_distribution.items())
        },
        "model": {
            "revision": asset.revision,
            "source_archive_sha256": asset.source_archive_sha256,
            "manifest_sha256": asset.manifest_sha256,
            "payload_tree_sha256": asset.payload_tree_sha256,
            "compute_type": "float32",
            "device": "cpu",
        },
        "piece_failures": piece_failures,
        "pieces": piece_evidence,
        "blocks": block_evidence,
    }
    payload["evidence_sha256"] = _canonical_sha(payload)

    output = root / "full-opticks-table-cells-feasibility.json"
    output.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "schema": SCHEMA,
                "table_block_count": len(blocks),
                "passed_table_block_count": passed_blocks,
                "translation_piece_count": len(piece_rows),
                "piece_without_strict_candidate_count": len(piece_failures),
                "selected_rank_distribution": payload["selected_rank_distribution"],
                "evidence_sha256": payload["evidence_sha256"],
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
