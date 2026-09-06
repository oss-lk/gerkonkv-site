from __future__ import annotations

"""Maintained Product Stage12 translation execution.

The historical quality evidence showed that a hard token-count cut can bisect
source-owned Gutenberg/technical structures such as ``[Greek: ...]`` and
``_..._``.  This module keeps the preferred token count as a soft budget: when
a desired cut falls inside a *balanced source span*, the cut is deferred until
a later token boundary outside that span.  It never fabricates closing syntax
for malformed/unbalanced input.
"""

from pathlib import Path
from typing import Any

from .database import (
    connect,
    get_document,
    get_document_segments,
    get_run,
    get_run_items,
)
from .runtime import OpusTranslator, load_opus_asset
from .stages import StageExecutionError, _complete, _fail, _start

PLANNER_CONTRACT = "rocketdict-stage12-protected-split/1"


def _balanced_protected_spans(text: str, *, absolute_start: int) -> list[tuple[int, int, str]]:
    """Return only source spans whose delimiters are actually balanced.

    ``end`` is exclusive.  Unmatched source delimiters are intentionally absent
    from the result: planner policy must not invent structure that the immutable
    source does not contain.
    """
    spans: list[tuple[int, int, str]] = []
    square_stack: list[int] = []
    emphasis_start: int | None = None
    for offset, char in enumerate(text):
        if char == "[":
            square_stack.append(offset)
            continue
        if char == "]" and square_stack:
            opened = square_stack.pop()
            spans.append((absolute_start + opened, absolute_start + offset + 1, "square"))
            continue
        # Gutenberg emphasis is source structure only outside square-bracket
        # payloads.  Nested underscores are not invented; unmatched markers are
        # simply left unprotected and remain visible to downstream gates.
        if char == "_" and not square_stack:
            if emphasis_start is None:
                emphasis_start = offset
            else:
                spans.append(
                    (
                        absolute_start + emphasis_start,
                        absolute_start + offset + 1,
                        "emphasis",
                    )
                )
                emphasis_start = None
    return sorted(spans)


def _cut_inside_span(cut: int, spans: list[tuple[int, int, str]]) -> bool:
    return any(start < cut < end for start, end, _kind in spans)


def _safe_forward_split_index(
    tokens: list[dict[str, Any]],
    *,
    desired_index: int,
    spans: list[tuple[int, int, str]],
) -> int:
    if desired_index >= len(tokens):
        return len(tokens)
    for index in range(desired_index, len(tokens)):
        cut = int(tokens[index]["source_start"])
        if not _cut_inside_span(cut, spans):
            return index
    return len(tokens)


def segment_translation_units(
    content: str,
    document_segments: list[dict[str, Any]],
    context_items: list[dict[str, Any]],
    nlp_tokens: list[dict[str, Any]],
    *,
    selected_format: str,
    preferred_tokens: int,
) -> list[dict[str, Any]]:
    if preferred_tokens < 1:
        raise StageExecutionError("plan_preferred_unit_tokens must be positive")
    base: list[dict[str, Any]] = []
    if selected_format == "txt":
        for row in context_items:
            base.append(
                {
                    "start": int(row["source_start"]),
                    "end": int(row["source_end"]),
                    "text": str(row["source_text"]),
                    "metadata": {"source": "nlp_sentence"},
                }
            )
    else:
        for row in document_segments:
            base.append(
                {
                    "start": int(row["start_char"]),
                    "end": int(row["end_char"]),
                    "text": str(row["text"]),
                    "metadata": {
                        "source": "subtitle_segment",
                        "segment_sequence": int(row["sequence_number"]),
                        "start_ms": row.get("start_ms"),
                        "end_ms": row.get("end_ms"),
                    },
                }
            )

    result: list[dict[str, Any]] = []
    for row in base:
        start, end = int(row["start"]), int(row["end"])
        row_text = content[start:end]
        if row_text != str(row["text"]):
            raise StageExecutionError("Stage12 planner base span differs from immutable source")
        tokens = [
            token
            for token in nlp_tokens
            if int(token["source_start"]) >= start
            and int(token["source_end"]) <= end
            and not bool((token.get("payload") or {}).get("flags", {}).get("is_space"))
        ]
        spans = _balanced_protected_spans(row_text, absolute_start=start)
        if len(tokens) <= preferred_tokens:
            result.append(
                {
                    **row,
                    "metadata": {
                        **row["metadata"],
                        "planner_contract": PLANNER_CONTRACT,
                        "split": False,
                        "token_count": len(tokens),
                        "protected_span_count": len(spans),
                    },
                }
            )
            continue

        cursor = start
        token_index = 0
        while token_index < len(tokens):
            desired_index = min(token_index + preferred_tokens, len(tokens))
            split_index = _safe_forward_split_index(
                tokens,
                desired_index=desired_index,
                spans=spans,
            )
            if split_index <= token_index:
                raise StageExecutionError("Stage12 planner failed to advance token coverage")
            if split_index >= len(tokens):
                cut = end
                split_index = len(tokens)
            else:
                cut = int(tokens[split_index]["source_start"])
            if cut <= cursor:
                raise StageExecutionError("Stage12 planner produced a non-positive source chunk")
            batch = tokens[token_index:split_index]
            result.append(
                {
                    "start": cursor,
                    "end": cut,
                    "text": content[cursor:cut],
                    "metadata": {
                        **row["metadata"],
                        "planner_contract": PLANNER_CONTRACT,
                        "split": True,
                        "token_count": len(batch),
                        "preferred_token_budget": preferred_tokens,
                        "protected_span_count": len(spans),
                        "protected_split_deferred": split_index > desired_index,
                    },
                }
            )
            cursor = cut
            token_index = split_index
        if cursor != end:
            raise StageExecutionError("Stage12 planner failed to cover the complete source unit")

    if not result:
        raise StageExecutionError("Stage12 planner produced no translation units")
    # Ordered output must remain a lossless projection of each base source span.
    for row in base:
        pieces = [
            item["text"]
            for item in result
            if int(item["start"]) >= int(row["start"])
            and int(item["end"]) <= int(row["end"])
        ]
        if "".join(pieces) != content[int(row["start"]):int(row["end"])]:
            raise StageExecutionError("Stage12 planner source coverage is not byte-exact")
    return result


def run_stage12(
    database: Path | str,
    *,
    context_run_id: int,
    parameters: dict[str, Any] | None = None,
    implementation: str = "opus-en-ru-ct2",
) -> dict[str, Any]:
    database = Path(database).expanduser().resolve()
    if implementation != "opus-en-ru-ct2":
        raise StageExecutionError(f"Unsupported real MT implementation: {implementation}")
    effective = dict(parameters or {})
    if effective.get("allow_download") not in {None, False}:
        raise StageExecutionError("Product MT is offline; allow_download must be false")
    requested_planner = str(effective.get("planner_contract") or PLANNER_CONTRACT)
    if requested_planner != PLANNER_CONTRACT:
        raise StageExecutionError(
            f"Unsupported Stage12 planner contract {requested_planner!r}; expected {PLANNER_CONTRACT!r}"
        )
    effective["planner_contract"] = PLANNER_CONTRACT
    device = str(effective.get("device") or "cpu")
    compute_type = str(effective.get("compute_type") or "float32")
    preferred = int(effective.get("plan_preferred_unit_tokens") or 64)
    beam_size = int(effective.get("beam_size") or 6)
    num_hypotheses = int(effective.get("num_hypotheses") or 1)

    with connect(database, readonly=True) as connection:
        context_run = get_run(connection, int(context_run_id))
        if int(context_run["stage_number"]) != 10 or context_run["status"] != "completed":
            raise StageExecutionError("Stage12 requires a completed Stage10 context run")
        context_output = dict(context_run.get("output") or {})
        nlp_run_id = int(context_output["nlp_run_id"])
        nlp_tokens = get_run_items(connection, nlp_run_id, kind="nlp_token")
        context_items = get_run_items(connection, int(context_run_id), kind="context_sentence")
        document_version_id = int(context_output["document_version_id"])
        document = get_document(connection, document_version_id)
        document_segments = get_document_segments(connection, document_version_id)

    input_identity = {
        "context_run_id": int(context_run_id),
        "context_output_sha256": str(context_run.get("output_sha256") or ""),
        "document_version_id": document_version_id,
        "source_text_sha256": str(document["text_sha256"]),
    }
    run_id, cached = _start(
        database,
        stage_number=12,
        implementation=implementation,
        input_identity=input_identity,
        parameters=effective,
    )
    if cached is not None:
        return cached

    try:
        content = str(document["content_text"])
        units = segment_translation_units(
            content,
            document_segments,
            context_items,
            nlp_tokens,
            selected_format=str(document["selected_format"]),
            preferred_tokens=preferred,
        )
        max_unit_tokens = max(
            int((row.get("metadata") or {}).get("token_count") or 0) for row in units
        )
        translator = OpusTranslator(device=device, compute_type=compute_type)
        translated = translator.translate(
            [str(row["text"]) for row in units],
            beam_size=beam_size,
            num_hypotheses=num_hypotheses,
            max_decoding_length=max(128, max(preferred, max_unit_tokens) * 8),
        )
        asset = load_opus_asset()
        items: list[dict[str, Any]] = []
        for sequence, (unit, hypotheses) in enumerate(zip(units, translated, strict=True)):
            if not hypotheses:
                raise StageExecutionError(
                    f"OPUS returned no hypothesis for translation unit {sequence}"
                )
            target = str(hypotheses[0].get("text") or "").strip()
            if not target:
                raise StageExecutionError(
                    f"OPUS returned empty target for translation unit {sequence}"
                )
            items.append(
                {
                    "sequence_number": sequence,
                    "kind": "translation_segment",
                    "source_start": int(unit["start"]),
                    "source_end": int(unit["end"]),
                    "source_text": str(unit["text"]),
                    "target_text": target,
                    "payload": {
                        "planner": dict(unit.get("metadata") or {}),
                        "hypotheses": hypotheses,
                        "selected_rank": 0,
                    },
                }
            )
        source_chars = sum(len(str(row["source_text"] or "")) for row in items)
        if source_chars <= 0:
            raise StageExecutionError("Stage12 translated zero source characters")
        output = {
            "schema": "rocketdict-product-stage12/1",
            "translation_run_id": run_id,
            "context_run_id": int(context_run_id),
            "document_version_id": document_version_id,
            "segment_count": len(items),
            "source_character_sum": source_chars,
            "empty_output_count": 0,
            "backend_error_count": 0,
            "backend": "CTranslate2Marian",
            "model_revision": asset.revision,
            "model_archive_sha256": asset.source_archive_sha256,
            "model_manifest_sha256": asset.manifest_sha256,
            "compute_type": compute_type,
            "planner_contract": PLANNER_CONTRACT,
            "max_translation_unit_tokens": max_unit_tokens,
            "real_mt": True,
            "network_used": False,
        }
        return _complete(database, run_id, output, items=items)
    except Exception as exc:
        _fail(database, run_id, exc)
        raise
