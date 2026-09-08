from __future__ import annotations

"""Maintained Product Stage12 translation execution.

The planner is quality-first and source-structural.  Ordinary text keeps the
protected-span semantics proven by planner v3: a soft token budget may not cut
inside balanced ``[]``, ``()``, ``{}`` or valid Gutenberg ``_..._`` emphasis,
and malformed emphasis parity may not coalesce unrelated paragraphs.

Planner v4 additionally recognizes conservative ASCII-table blocks in TXT
sources before MT.  A table remains one contiguous Product translation segment
for hard-gate/alignment coverage, while source-only logical text groups are sent
to the real OPUS backend.  Source-owned table geometry and alpha-free
numeric/symbolic cells are never reconstructed after MT: their exact bytes and
source spans are known before the model call and are rendered unchanged.  No
special table behavior is applied to subtitle cue segments.

Planner v7 keeps evidence-backed Gutenberg block structural labels byte-exact
and coalesces split-created whitespace-only boundaries from both structural-label
and ASCII-table partitioning into adjacent ordinary prose, so every ordinary MT
request remains lexical. Structural label model input still expands only the
documented abbreviation and selects only strict raw OPUS candidates. Inline
labels stay ordinary prose; table spans remain unchanged.

Primary OPUS requests are executed in bounded, ordered batches. This is an
execution/resource contract only: it does not change planner-v7 source units,
model inputs, generation settings, raw hypotheses or output ordering.
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
from .structural_labels import (
    STRUCTURAL_LABEL_CONTRACT,
    STRUCTURAL_LABEL_GENERATION_CELLS,
    StructuralLabel,
    evaluate_structural_label_hypotheses,
    parse_structural_label_unit,
    partition_txt_base_with_block_structural_labels,
)
from .table_stage12 import (
    TABLE_STAGE12_CONTRACT,
    build_stage12_table_plan,
    partition_txt_base_with_ascii_tables,
    render_stage12_table_rank0,
    table_plan_metrics,
)

PLANNER_CONTRACT = "rocketdict-stage12-protected-split/7"
REQUEST_BATCH_CONTRACT = "rocketdict-stage12-bounded-request-batch/1"
DEFAULT_REQUEST_BATCH_SIZE = 48
MAX_REQUEST_BATCH_SIZE = 128


def _starts_blank_paragraph_break(text: str, offset: int) -> bool:
    if offset < 0 or offset >= len(text) or text[offset] != "\n":
        return False
    cursor = offset + 1
    while cursor < len(text) and text[cursor] in " \t\r":
        cursor += 1
    return cursor < len(text) and text[cursor] == "\n"


def _can_open_emphasis(text: str, offset: int) -> bool:
    next_index = offset + 1
    if next_index >= len(text):
        return False
    following = text[next_index]
    if following.isspace():
        return False
    previous = text[offset - 1] if offset else ""
    if previous and previous.isalnum():
        return following.isalnum()
    return following not in ",.;:!?)]}"


def _balanced_protected_spans(
    text: str, *, absolute_start: int
) -> list[tuple[int, int, str]]:
    """Return balanced source-owned protected spans, never fabricated closers."""
    spans: list[tuple[int, int, str]] = []
    stacks: dict[str, list[int]] = {"[": [], "(": [], "{": []}
    closing = {"]": ("[", "square"), ")": ("(", "round"), "}": ("{", "curly")}
    emphasis_start: int | None = None

    for offset, char in enumerate(text):
        if emphasis_start is not None and _starts_blank_paragraph_break(text, offset):
            emphasis_start = None

        if char in stacks:
            stacks[char].append(offset)
            continue
        if char in closing:
            opener, kind = closing[char]
            if stacks[opener]:
                opened = stacks[opener].pop()
                spans.append(
                    (absolute_start + opened, absolute_start + offset + 1, kind)
                )
            continue

        if char == "_" and not any(stacks.values()):
            previous = text[offset - 1] if offset else ""
            if emphasis_start is None:
                if _can_open_emphasis(text, offset):
                    emphasis_start = offset
                continue
            if offset > emphasis_start + 1 and previous and not previous.isspace():
                spans.append(
                    (
                        absolute_start + emphasis_start,
                        absolute_start + offset + 1,
                        "emphasis",
                    )
                )
                emphasis_start = None
                continue
            if _can_open_emphasis(text, offset):
                emphasis_start = offset

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


def _raw_base_units(
    content: str,
    document_segments: list[dict[str, Any]],
    context_items: list[dict[str, Any]],
    *,
    selected_format: str,
) -> list[dict[str, Any]]:
    base: list[dict[str, Any]] = []
    if selected_format == "txt":
        for row in context_items:
            start = int(row["source_start"])
            end = int(row["source_end"])
            sequence = int(row["sequence_number"])
            base.append(
                {
                    "start": start,
                    "end": end,
                    "text": str(row["source_text"]),
                    "metadata": {
                        "source": "nlp_sentence",
                        "context_sentence_start": sequence,
                        "context_sentence_end": sequence,
                        "context_sentence_count": 1,
                    },
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

    for row in base:
        start, end = int(row["start"]), int(row["end"])
        if start < 0 or end <= start or end > len(content):
            raise StageExecutionError("Stage12 planner received an invalid base source span")
        if content[start:end] != str(row["text"]):
            raise StageExecutionError("Stage12 planner base span differs from immutable source")
    return base


def _coalesce_txt_protected_boundaries(
    content: str,
    base: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Merge NLP sentence units only across genuinely balanced source spans."""
    if not base:
        return []
    global_spans = _balanced_protected_spans(content, absolute_start=0)
    merged: list[dict[str, Any]] = []
    current = {**base[0], "metadata": dict(base[0].get("metadata") or {})}

    for row in base[1:]:
        boundary = int(row["start"])
        current_end = int(current["end"])
        if boundary != current_end:
            raise StageExecutionError(
                "Stage12 TXT context sentences are not contiguous in immutable source"
            )
        if _cut_inside_span(boundary, global_spans):
            current["end"] = int(row["end"])
            current["text"] = content[int(current["start"]):int(current["end"])]
            metadata = dict(current.get("metadata") or {})
            row_meta = dict(row.get("metadata") or {})
            metadata["source"] = "nlp_sentence_group"
            metadata["context_sentence_end"] = int(
                row_meta.get("context_sentence_end", row_meta.get("context_sentence_start", 0))
            )
            metadata["context_sentence_count"] = int(
                metadata.get("context_sentence_count") or 1
            ) + int(row_meta.get("context_sentence_count") or 1)
            metadata["protected_sentence_boundary_coalesced"] = True
            current["metadata"] = metadata
            continue
        merged.append(current)
        current = {**row, "metadata": dict(row.get("metadata") or {})}
    merged.append(current)
    return merged


def _non_space_tokens_in_span(
    nlp_tokens: list[dict[str, Any]], start: int, end: int
) -> list[dict[str, Any]]:
    return [
        token
        for token in nlp_tokens
        if int(token["source_start"]) >= start
        and int(token["source_end"]) <= end
        and not bool((token.get("payload") or {}).get("flags", {}).get("is_space"))
    ]


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

    raw_base = _raw_base_units(
        content,
        document_segments,
        context_items,
        selected_format=selected_format,
    )
    base = (
        _coalesce_txt_protected_boundaries(content, raw_base)
        if selected_format == "txt"
        else raw_base
    )
    if selected_format == "txt":
        try:
            base = partition_txt_base_with_ascii_tables(content, base)
            base = partition_txt_base_with_block_structural_labels(content, base)
        except ValueError as exc:
            raise StageExecutionError(f"Stage12 source-structure partition failed: {exc}") from exc

    result: list[dict[str, Any]] = []
    for row in base:
        start, end = int(row["start"]), int(row["end"])
        row_text = content[start:end]
        tokens = _non_space_tokens_in_span(nlp_tokens, start, end)
        metadata = dict(row.get("metadata") or {})

        if metadata.get("source") == "structural_label":
            result.append(
                {
                    **row,
                    "metadata": {
                        **metadata,
                        "planner_contract": PLANNER_CONTRACT,
                        "split": False,
                        "token_count": len(tokens),
                        "protected_span_count": 1,
                        "structural_label_atomic": True,
                    },
                }
            )
            continue

        if metadata.get("source") == "ascii_table":
            try:
                plan = build_stage12_table_plan(row_text, absolute_start=start)
                metrics = table_plan_metrics(plan)
            except ValueError as exc:
                raise StageExecutionError(f"Stage12 ASCII-table planning failed: {exc}") from exc
            result.append(
                {
                    **row,
                    "metadata": {
                        **metadata,
                        "planner_contract": PLANNER_CONTRACT,
                        "split": False,
                        "token_count": int(metrics["max_logical_group_word_proxy"]),
                        "table_source_token_count": len(tokens),
                        **metrics,
                    },
                }
            )
            continue

        spans = _balanced_protected_spans(row_text, absolute_start=start)
        if len(tokens) <= preferred_tokens:
            result.append(
                {
                    **row,
                    "metadata": {
                        **metadata,
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
                        **metadata,
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


def _translate_primary_request_batches(
    translator: OpusTranslator,
    texts: list[str],
    *,
    batch_size: int,
    beam_size: int,
    num_hypotheses: int,
    max_decoding_length: int,
) -> list[list[dict[str, Any]]]:
    """Translate primary Stage12 requests in bounded order-preserving batches.

    Batch boundaries are not source/planner boundaries and never enter target
    assembly. A backend cardinality drift fails closed before any result can be
    persisted.
    """
    if batch_size < 1 or batch_size > MAX_REQUEST_BATCH_SIZE:
        raise StageExecutionError(
            f"Stage12 request batch size must be in 1..{MAX_REQUEST_BATCH_SIZE}"
        )
    output: list[list[dict[str, Any]]] = []
    for start in range(0, len(texts), batch_size):
        batch = texts[start : start + batch_size]
        translated = translator.translate(
            batch,
            beam_size=beam_size,
            num_hypotheses=num_hypotheses,
            max_decoding_length=max_decoding_length,
        )
        if len(translated) != len(batch):
            raise StageExecutionError(
                "OPUS returned a different Stage12 request batch cardinality"
            )
        output.extend(translated)
    if len(output) != len(texts):
        raise StageExecutionError(
            "OPUS returned a different Stage12 total request cardinality"
        )
    return output


def _translate_structural_label_units(
    translator: OpusTranslator,
    labels: dict[int, StructuralLabel],
) -> dict[str, Any]:
    """Translate only source-defined structural-label units with staged raw OPUS.

    This is deliberately not a generic n-best fallback.  Each request is a
    canonical source-side expansion of a byte-exact block label, and acceptance
    is delegated to the strict maintained structural-label selector.
    """
    selected: dict[int, dict[str, Any]] = {}
    cells: dict[int, list[dict[str, Any]]] = {index: [] for index in labels}
    unresolved = list(labels)
    request_count = 0

    for beam_size, num_hypotheses in STRUCTURAL_LABEL_GENERATION_CELLS:
        if not unresolved:
            break
        requests = [labels[index].canonical_model_input for index in unresolved]
        generated = translator.translate(
            requests,
            beam_size=beam_size,
            num_hypotheses=num_hypotheses,
            max_decoding_length=128,
        )
        request_count += len(requests)
        if len(generated) != len(unresolved):
            raise StageExecutionError(
                "OPUS returned a different structural-label request cardinality"
            )
        rescued: set[int] = set()
        for index, hypotheses in zip(unresolved, generated, strict=True):
            evaluation = evaluate_structural_label_hypotheses(labels[index], hypotheses)
            cell = {
                "generation": {
                    "beam_size": beam_size,
                    "num_hypotheses": num_hypotheses,
                },
                "evaluation": evaluation,
                "hypotheses": hypotheses,
            }
            cells[index].append(cell)
            choice = evaluation.get("selected")
            if isinstance(choice, dict):
                selected[index] = {
                    "target_text": str(choice["target_text"]),
                    "rank": int(choice["rank"]),
                    "generation": dict(cell["generation"]),
                    "hypotheses": hypotheses,
                }
                rescued.add(index)
        unresolved = [index for index in unresolved if index not in rescued]

    if unresolved:
        details = [
            f"{labels[index].kind}:{labels[index].number}" for index in unresolved
        ]
        raise StageExecutionError(
            "real OPUS produced no acceptable structural-label hypothesis: "
            + ", ".join(details)
        )
    return {
        "selected": selected,
        "cells": cells,
        "request_count": request_count,
        "escalated_count": sum(
            1
            for row in selected.values()
            if int(row["generation"]["beam_size"]) > STRUCTURAL_LABEL_GENERATION_CELLS[0][0]
        ),
    }


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
    requested_structural = str(
        effective.get("structural_label_contract") or STRUCTURAL_LABEL_CONTRACT
    )
    if requested_structural != STRUCTURAL_LABEL_CONTRACT:
        raise StageExecutionError(
            f"Unsupported Stage12 structural-label contract {requested_structural!r}; "
            f"expected {STRUCTURAL_LABEL_CONTRACT!r}"
        )
    effective["structural_label_contract"] = STRUCTURAL_LABEL_CONTRACT
    device = str(effective.get("device") or "cpu")
    compute_type = str(effective.get("compute_type") or "float32")
    preferred = int(effective.get("plan_preferred_unit_tokens") or 64)
    beam_size = int(effective.get("beam_size") or 6)
    num_hypotheses = int(effective.get("num_hypotheses") or 1)
    requested_batch_contract = str(
        effective.get("request_batch_contract") or REQUEST_BATCH_CONTRACT
    )
    if requested_batch_contract != REQUEST_BATCH_CONTRACT:
        raise StageExecutionError(
            f"Unsupported Stage12 request batch contract {requested_batch_contract!r}; "
            f"expected {REQUEST_BATCH_CONTRACT!r}"
        )
    effective["request_batch_contract"] = REQUEST_BATCH_CONTRACT
    raw_batch_size = effective.get("request_batch_size", DEFAULT_REQUEST_BATCH_SIZE)
    if isinstance(raw_batch_size, bool):
        raise StageExecutionError("Stage12 request_batch_size must be an integer")
    try:
        request_batch_size = int(raw_batch_size)
    except (TypeError, ValueError) as exc:
        raise StageExecutionError("Stage12 request_batch_size must be an integer") from exc
    if request_batch_size < 1 or request_batch_size > MAX_REQUEST_BATCH_SIZE:
        raise StageExecutionError(
            f"Stage12 request_batch_size must be in 1..{MAX_REQUEST_BATCH_SIZE}"
        )
    effective["request_batch_size"] = request_batch_size

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

        table_plans: dict[int, Any] = {}
        structural_label_plans: dict[int, StructuralLabel] = {}
        request_texts: list[str] = []
        request_refs: list[tuple[int, int | None]] = []
        request_proxy_counts: list[int] = []
        for unit_index, unit in enumerate(units):
            metadata = dict(unit.get("metadata") or {})
            if metadata.get("source") == "ascii_table":
                try:
                    plan = build_stage12_table_plan(
                        str(unit["text"]), absolute_start=int(unit["start"])
                    )
                except ValueError as exc:
                    raise StageExecutionError(
                        f"Stage12 ASCII-table execution planning failed: {exc}"
                    ) from exc
                table_plans[unit_index] = plan
                for group in plan.groups:
                    request_texts.append(group.source_text)
                    request_refs.append((unit_index, int(group.index)))
                    request_proxy_counts.append(max(1, len(group.source_text.split())))
            elif metadata.get("source") == "structural_label":
                try:
                    label = parse_structural_label_unit(str(unit["text"]))
                except ValueError as exc:
                    raise StageExecutionError(
                        f"Stage12 structural-label unit parsing failed: {exc}"
                    ) from exc
                if (
                    str(metadata.get("structural_label_contract") or "")
                    != STRUCTURAL_LABEL_CONTRACT
                    or str(metadata.get("structural_label_kind") or "") != label.kind
                    or str(metadata.get("structural_label_number") or "") != label.number
                    or str(metadata.get("canonical_model_input") or "")
                    != label.canonical_model_input
                ):
                    raise StageExecutionError(
                        "Stage12 structural-label planner/execution metadata drift"
                    )
                structural_label_plans[unit_index] = label
            else:
                request_texts.append(str(unit["text"]))
                request_refs.append((unit_index, None))
                request_proxy_counts.append(
                    max(1, int(metadata.get("token_count") or 0))
                )

        max_request_tokens = max(request_proxy_counts, default=0)
        translator = OpusTranslator(device=device, compute_type=compute_type)
        translated = _translate_primary_request_batches(
            translator,
            request_texts,
            batch_size=request_batch_size,
            beam_size=beam_size,
            num_hypotheses=num_hypotheses,
            max_decoding_length=max(128, max(preferred, max_request_tokens) * 8),
        ) if request_texts else []
        if len(translated) != len(request_refs):
            raise StageExecutionError("OPUS returned a different Stage12 request cardinality")
        generated = {
            reference: hypotheses
            for reference, hypotheses in zip(request_refs, translated, strict=True)
        }
        structural_execution = _translate_structural_label_units(
            translator, structural_label_plans
        ) if structural_label_plans else {
            "selected": {},
            "cells": {},
            "request_count": 0,
            "escalated_count": 0,
        }

        asset = load_opus_asset()
        items: list[dict[str, Any]] = []
        table_group_total = 0
        table_multi_piece_total = 0
        table_preserved_chars = 0
        for sequence, unit in enumerate(units):
            metadata = dict(unit.get("metadata") or {})
            if metadata.get("source") == "ascii_table":
                plan = table_plans[sequence]
                hypotheses_by_group = {
                    int(group.index): generated[(sequence, int(group.index))]
                    for group in plan.groups
                }
                try:
                    target, group_evidence = render_stage12_table_rank0(
                        plan, hypotheses_by_group
                    )
                except ValueError as exc:
                    raise StageExecutionError(
                        f"Stage12 ASCII-table rendering failed: {exc}"
                    ) from exc
                metrics = table_plan_metrics(plan)
                table_group_total += int(metrics["logical_group_count"])
                table_multi_piece_total += int(metrics["multi_piece_group_count"])
                table_preserved_chars += int(metrics["preserved_source_character_count"])
                payload = {
                    "planner": metadata,
                    "hypotheses": [],
                    "selected_rank": 0,
                    "composite_real_mt": True,
                    "table": {
                        "stage12_contract": TABLE_STAGE12_CONTRACT,
                        "structure_contract": metadata.get("table_structure_contract"),
                        "logical_contract": metadata.get("table_logical_contract"),
                        "metrics": metrics,
                        "logical_groups": group_evidence,
                    },
                }
            elif metadata.get("source") == "structural_label":
                selection = structural_execution["selected"].get(sequence)
                if not isinstance(selection, dict):
                    raise StageExecutionError(
                        f"Stage12 lacks selected structural-label hypothesis for unit {sequence}"
                    )
                target = str(selection["target_text"]).strip()
                if not target:
                    raise StageExecutionError(
                        f"Stage12 selected an empty structural-label target for unit {sequence}"
                    )
                payload = {
                    "planner": metadata,
                    "hypotheses": list(selection["hypotheses"]),
                    "selected_rank": int(selection["rank"]),
                    "structural_label": {
                        "contract": STRUCTURAL_LABEL_CONTRACT,
                        "canonical_model_input": structural_label_plans[sequence].canonical_model_input,
                        "generation": dict(selection["generation"]),
                        "cells": structural_execution["cells"][sequence],
                        "raw_model_selection": True,
                        "target_rewriting": False,
                        "source_bytes_rewritten": False,
                    },
                }
            else:
                hypotheses = generated[(sequence, None)]
                if not hypotheses:
                    raise StageExecutionError(
                        f"OPUS returned no hypothesis for translation unit {sequence}"
                    )
                target = str(hypotheses[0].get("text") or "").strip()
                if not target:
                    raise StageExecutionError(
                        f"OPUS returned empty target for translation unit {sequence}"
                    )
                payload = {
                    "planner": metadata,
                    "hypotheses": hypotheses,
                    "selected_rank": 0,
                }

            items.append(
                {
                    "sequence_number": sequence,
                    "kind": "translation_segment",
                    "source_start": int(unit["start"]),
                    "source_end": int(unit["end"]),
                    "source_text": str(unit["text"]),
                    "target_text": target,
                    "payload": payload,
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
            "request_batch_contract": REQUEST_BATCH_CONTRACT,
            "request_batch_size": request_batch_size,
            "primary_model_batch_count": (
                (len(request_texts) + request_batch_size - 1) // request_batch_size
                if request_texts
                else 0
            ),
            "structural_label_contract": STRUCTURAL_LABEL_CONTRACT,
            "structural_label_unit_count": len(structural_label_plans),
            "structural_label_escalated_unit_count": int(structural_execution["escalated_count"]),
            "structural_label_model_request_count": int(structural_execution["request_count"]),
            "table_stage12_contract": TABLE_STAGE12_CONTRACT,
            "table_block_count": len(table_plans),
            "table_logical_group_count": table_group_total,
            "table_multi_piece_group_count": table_multi_piece_total,
            "table_preserved_source_character_count": table_preserved_chars,
            "model_request_count": len(request_texts) + int(structural_execution["request_count"]),
            "max_translation_unit_tokens": max(
                max_request_tokens,
                2 if structural_label_plans else 0,
            ),
            "real_mt": True,
            "network_used": False,
        }
        return _complete(database, run_id, output, items=items)
    except Exception as exc:
        _fail(database, run_id, exc)
        raise
