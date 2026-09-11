from __future__ import annotations

from collections import Counter
import hashlib
import json
from pathlib import Path
import re
from typing import Any, Callable

from .database import (
    begin_run,
    connect,
    fail_run,
    finish_run,
    get_document,
    get_document_segments,
    get_run,
    get_run_items,
    replace_run_items,
    transaction,
)
from .runtime import NLP_MODELS, OpusTranslator, load_nlp, load_opus_asset


class StageExecutionError(RuntimeError):
    pass


def _canonical_sha(value: Any) -> str:
    raw = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def _stage_key(number: int) -> str:
    from .api.registry import stage_key

    return stage_key(number)


def _cached_output(database: Path, run_id: int) -> dict[str, Any]:
    with connect(database, readonly=True) as connection:
        run = get_run(connection, run_id)
    output = run.get("output")
    if not isinstance(output, dict):
        raise StageExecutionError(f"Completed stage run {run_id} has no output object")
    return {**output, "cache_hit": True}


def _start(
    database: Path,
    *,
    stage_number: int,
    implementation: str,
    input_identity: dict[str, Any],
    parameters: dict[str, Any],
) -> tuple[int, dict[str, Any] | None]:
    with transaction(database) as connection:
        run_id, cache_hit = begin_run(
            connection,
            stage_number=stage_number,
            stage_key=_stage_key(stage_number),
            implementation=implementation,
            input_identity=input_identity,
            parameters=parameters,
        )
    if cache_hit:
        return run_id, _cached_output(database, run_id)
    return run_id, None


def _complete(
    database: Path,
    run_id: int,
    output: dict[str, Any],
    *,
    items: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    with transaction(database) as connection:
        if items is not None:
            replace_run_items(connection, run_id, items)
        finish_run(connection, run_id, output)
    return {**output, "cache_hit": False}


def _fail(database: Path, run_id: int, exc: BaseException) -> None:
    try:
        with transaction(database) as connection:
            fail_run(
                connection,
                run_id,
                {"type": type(exc).__name__, "message": str(exc)},
            )
    except Exception:
        # Preserve the original execution failure. A leftover running row is a
        # visible reconciliation blocker rather than a reason to mask it.
        pass


def run_stage8(
    database: Path | str,
    *,
    document_version_id: int,
    parameters: dict[str, Any] | None = None,
    implementation: str = "en-sm",
) -> dict[str, Any]:
    database = Path(database).expanduser().resolve()
    if implementation not in NLP_MODELS:
        raise StageExecutionError(f"Unsupported production NLP implementation: {implementation}")
    parameters = dict(parameters or {})
    with connect(database, readonly=True) as connection:
        document = get_document(connection, int(document_version_id))
    input_identity = {
        "document_version_id": int(document_version_id),
        "text_sha256": str(document["text_sha256"]),
        "char_count": int(document["char_count"]),
    }
    run_id, cached = _start(
        database,
        stage_number=8,
        implementation=implementation,
        input_identity=input_identity,
        parameters=parameters,
    )
    if cached is not None:
        return cached
    try:
        nlp = load_nlp(implementation)
        content = str(document["content_text"])
        if len(content) > int(getattr(nlp, "max_length", 0) or 0):
            nlp.max_length = max(len(content) + 1024, int(nlp.max_length))
        doc = nlp(content)
        if doc.text != content:
            raise StageExecutionError("spaCy document text differs from immutable interpreted source")
        sentence_index: dict[int, int] = {}
        for index, sentence in enumerate(doc.sents):
            for token in sentence:
                sentence_index[int(token.i)] = index
        items: list[dict[str, Any]] = []
        for token in doc:
            items.append(
                {
                    "sequence_number": int(token.i),
                    "kind": "nlp_token",
                    "source_start": int(token.idx),
                    "source_end": int(token.idx + len(token.text)),
                    "source_text": token.text,
                    "target_text": None,
                    "payload": {
                        "token_index": int(token.i),
                        "lemma": str(token.lemma_),
                        "lower": str(token.lower_),
                        "pos": str(token.pos_),
                        "tag": str(token.tag_),
                        "dependency": str(token.dep_),
                        "head_token_index": int(token.head.i),
                        "sentence_index": int(sentence_index.get(int(token.i), 0)),
                        "entity_type": str(token.ent_type_) or None,
                        "entity_iob": str(token.ent_iob_) or None,
                        "morph": token.morph.to_dict(),
                        "flags": {
                            "is_alpha": bool(token.is_alpha),
                            "is_stop": bool(token.is_stop),
                            "is_oov": bool(token.is_oov),
                            "is_space": bool(token.is_space),
                            "is_punct": bool(token.is_punct),
                        },
                        "source": f"spacy:{NLP_MODELS[implementation]}",
                    },
                }
            )
        sentence_count = len(list(doc.sents))
        output = {
            "schema": "rocketdict-product-stage8/1",
            "nlp_run_id": run_id,
            "document_version_id": int(document_version_id),
            "model": NLP_MODELS[implementation],
            "implementation": implementation,
            "token_count": len(items),
            "sentence_count": sentence_count,
            "source_char_count": len(content),
            "source_text_sha256": str(document["text_sha256"]),
            "coverage_complete": True,
        }
        return _complete(database, run_id, output, items=items)
    except Exception as exc:
        _fail(database, run_id, exc)
        raise


def run_stage10(
    database: Path | str,
    *,
    nlp_run_id: int,
    parameters: dict[str, Any] | None = None,
    implementation: str = "structural-entity-term-discourse-pronoun-v1",
) -> dict[str, Any]:
    from .context_sentence_boundaries import (
        STAGE10_BOUNDARY_POLICY,
        STAGE10_CONTEXT_IMPLEMENTATION_V1,
        STAGE10_CONTEXT_IMPLEMENTATION_V2,
        coalesce_spacy_sentence_groups,
        parser_sentence_groups,
    )

    database = Path(database).expanduser().resolve()
    if implementation not in {
        STAGE10_CONTEXT_IMPLEMENTATION_V1,
        STAGE10_CONTEXT_IMPLEMENTATION_V2,
    }:
        raise StageExecutionError(
            f"Unsupported Stage10 context implementation: {implementation}"
        )
    parameters = dict(parameters or {})
    with connect(database, readonly=True) as connection:
        nlp_run = get_run(connection, int(nlp_run_id))
        if int(nlp_run["stage_number"]) != 8 or nlp_run["status"] != "completed":
            raise StageExecutionError("Stage10 requires a completed Stage8 NLP run")
        tokens = get_run_items(connection, int(nlp_run_id), kind="nlp_token")
        nlp_output = dict(nlp_run.get("output") or {})
        document = get_document(connection, int(nlp_output["document_version_id"]))
    input_identity = {
        "nlp_run_id": int(nlp_run_id),
        "nlp_output_sha256": str(nlp_run.get("output_sha256") or ""),
    }
    run_id, cached = _start(
        database,
        stage_number=10,
        implementation=implementation,
        input_identity=input_identity,
        parameters=parameters,
    )
    if cached is not None:
        return cached
    try:
        grouped: dict[int, list[dict[str, Any]]] = {}
        for token in tokens:
            sentence = int((token.get("payload") or {}).get("sentence_index") or 0)
            grouped.setdefault(sentence, []).append(token)
        content = str(document["content_text"])
        if implementation == STAGE10_CONTEXT_IMPLEMENTATION_V1:
            context_groups = parser_sentence_groups(grouped)
        else:
            context_groups = coalesce_spacy_sentence_groups(grouped, content)

        items: list[dict[str, Any]] = []
        entity_mentions = 0
        pronouns = 0
        covered_tokens = 0
        coalesced_boundary_count = sum(
            len(group["coalesced_boundaries"]) for group in context_groups
        )
        coalesced_context_count = sum(
            bool(group["coalesced_boundaries"]) for group in context_groups
        )
        for sequence, group in enumerate(context_groups):
            sentence_tokens = list(group["tokens"])
            sentence_indices = list(group["sentence_indices"])
            if not sentence_tokens or not sentence_indices:
                continue
            sentence_number = int(sentence_indices[0])
            start = min(int(row["source_start"]) for row in sentence_tokens)
            # Include trailing whitespace up to the next context start so the
            # ordered spans remain auditable against immutable source bytes.
            if sequence + 1 < len(context_groups):
                next_tokens = list(context_groups[sequence + 1]["tokens"])
                end = min(int(next_tokens[0]["source_start"]), len(content))
            else:
                end = len(content)
            if end <= start or content[start:end] == "":
                raise StageExecutionError(
                    f"Stage10 produced invalid source geometry at context {sequence}"
                )
            entities = []
            sentence_pronouns = []
            for row in sentence_tokens:
                payload = row.get("payload") or {}
                if payload.get("entity_type"):
                    entity_mentions += 1
                    entities.append(
                        {
                            "token_index": payload.get("token_index"),
                            "text": row.get("source_text"),
                            "entity_type": payload.get("entity_type"),
                        }
                    )
                if str(payload.get("pos") or "") == "PRON":
                    pronouns += 1
                    sentence_pronouns.append(
                        {
                            "token_index": payload.get("token_index"),
                            "text": row.get("source_text"),
                            "lemma": payload.get("lemma"),
                        }
                    )
            covered_tokens += len(sentence_tokens)
            payload = {
                "sentence_index": sentence_number,
                "token_count": len(sentence_tokens),
                "first_token_index": (sentence_tokens[0].get("payload") or {}).get("token_index"),
                "last_token_index": (sentence_tokens[-1].get("payload") or {}).get("token_index"),
                "entities": entities,
                "pronouns": sentence_pronouns,
            }
            if implementation == STAGE10_CONTEXT_IMPLEMENTATION_V2:
                payload.update(
                    {
                        "spacy_sentence_indices": sentence_indices,
                        "spacy_sentence_count": len(sentence_indices),
                        "coalesced_boundary_count": len(group["coalesced_boundaries"]),
                        "coalesced_boundaries": list(group["coalesced_boundaries"]),
                        "boundary_policy": STAGE10_BOUNDARY_POLICY,
                    }
                )
            items.append(
                {
                    "sequence_number": sequence,
                    "kind": "context_sentence",
                    "source_start": start,
                    "source_end": end,
                    "source_text": content[start:end],
                    "target_text": None,
                    "payload": payload,
                }
            )
        if covered_tokens != len(tokens):
            raise StageExecutionError(
                f"Stage10 token coverage mismatch: {covered_tokens} != {len(tokens)}"
            )
        if implementation == STAGE10_CONTEXT_IMPLEMENTATION_V1:
            output = {
                "schema": "rocketdict-product-stage10/1",
                "context_run_id": run_id,
                "nlp_run_id": int(nlp_run_id),
                "document_version_id": int(nlp_output["document_version_id"]),
                "sentence_count": len(items),
                "token_count": len(tokens),
                "entity_mention_count": entity_mentions,
                "pronoun_token_count": pronouns,
                "coverage_complete": covered_tokens == len(tokens),
            }
        else:
            output = {
                "schema": "rocketdict-product-stage10/2",
                "context_run_id": run_id,
                "nlp_run_id": int(nlp_run_id),
                "document_version_id": int(nlp_output["document_version_id"]),
                "implementation": implementation,
                "boundary_policy": STAGE10_BOUNDARY_POLICY,
                "spacy_sentence_count": len(grouped),
                "sentence_count": len(items),
                "coalesced_boundary_count": coalesced_boundary_count,
                "coalesced_context_count": coalesced_context_count,
                "token_count": len(tokens),
                "entity_mention_count": entity_mentions,
                "pronoun_token_count": pronouns,
                "coverage_complete": covered_tokens == len(tokens),
            }
        return _complete(database, run_id, output, items=items)
    except Exception as exc:
        _fail(database, run_id, exc)
        raise

def _segment_units(
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
        tokens = [
            token
            for token in nlp_tokens
            if int(token["source_start"]) >= start and int(token["source_end"]) <= end
            and not bool((token.get("payload") or {}).get("flags", {}).get("is_space"))
        ]
        if len(tokens) <= preferred_tokens:
            result.append(row)
            continue
        cursor = start
        for offset in range(0, len(tokens), preferred_tokens):
            batch = tokens[offset : offset + preferred_tokens]
            if offset + preferred_tokens < len(tokens):
                next_token = tokens[offset + preferred_tokens]
                cut = int(next_token["source_start"])
            else:
                cut = end
            if cut <= cursor:
                raise StageExecutionError("Stage12 planner produced a non-positive source chunk")
            result.append(
                {
                    "start": cursor,
                    "end": cut,
                    "text": content[cursor:cut],
                    "metadata": {
                        **row["metadata"],
                        "split": True,
                        "token_count": len(batch),
                    },
                }
            )
            cursor = cut
        if cursor != end:
            raise StageExecutionError("Stage12 planner failed to cover the complete source unit")
    if not result:
        raise StageExecutionError("Stage12 planner produced no translation units")
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
    parameters = dict(parameters or {})
    if parameters.get("allow_download") not in {None, False}:
        raise StageExecutionError("Product MT is offline; allow_download must be false")
    device = str(parameters.get("device") or "cpu")
    compute_type = str(parameters.get("compute_type") or "float32")
    preferred = int(parameters.get("plan_preferred_unit_tokens") or 64)
    beam_size = int(parameters.get("beam_size") or 6)
    num_hypotheses = int(parameters.get("num_hypotheses") or 1)
    with connect(database, readonly=True) as connection:
        context_run = get_run(connection, int(context_run_id))
        if int(context_run["stage_number"]) != 10 or context_run["status"] != "completed":
            raise StageExecutionError("Stage12 requires a completed Stage10 context run")
        context_output = dict(context_run.get("output") or {})
        nlp_run_id = int(context_output["nlp_run_id"])
        nlp_run = get_run(connection, nlp_run_id)
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
        parameters=parameters,
    )
    if cached is not None:
        return cached
    try:
        content = str(document["content_text"])
        units = _segment_units(
            content,
            document_segments,
            context_items,
            nlp_tokens,
            selected_format=str(document["selected_format"]),
            preferred_tokens=preferred,
        )
        translator = OpusTranslator(device=device, compute_type=compute_type)
        translated = translator.translate(
            [str(row["text"]) for row in units],
            beam_size=beam_size,
            num_hypotheses=num_hypotheses,
            max_decoding_length=max(128, preferred * 8),
        )
        asset = load_opus_asset()
        items: list[dict[str, Any]] = []
        for sequence, (unit, hypotheses) in enumerate(zip(units, translated, strict=True)):
            if not hypotheses:
                raise StageExecutionError(f"OPUS returned no hypothesis for translation unit {sequence}")
            target = str(hypotheses[0].get("text") or "").strip()
            if not target:
                raise StageExecutionError(f"OPUS returned empty target for translation unit {sequence}")
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
            "real_mt": True,
            "network_used": False,
        }
        return _complete(database, run_id, output, items=items)
    except Exception as exc:
        _fail(database, run_id, exc)
        raise


def run_stage14(
    database: Path | str,
    *,
    translation_run_id: int,
    parameters: dict[str, Any] | None = None,
    implementation: str = "glossary_refinement-current",
) -> dict[str, Any]:
    database = Path(database).expanduser().resolve()
    parameters = dict(parameters or {})
    with connect(database, readonly=True) as connection:
        translation_run = get_run(connection, int(translation_run_id))
        if int(translation_run["stage_number"]) != 12 or translation_run["status"] != "completed":
            raise StageExecutionError("Stage14 requires a completed real Stage12 translation run")
        translation_output = dict(translation_run.get("output") or {})
        if translation_output.get("real_mt") is not True:
            raise StageExecutionError("Stage14 refuses a Stage12 result that is not explicitly real MT")
        segments = get_run_items(connection, int(translation_run_id), kind="translation_segment")
    input_identity = {
        "translation_run_id": int(translation_run_id),
        "translation_output_sha256": str(translation_run.get("output_sha256") or ""),
    }
    run_id, cached = _start(
        database,
        stage_number=14,
        implementation=implementation,
        input_identity=input_identity,
        parameters=parameters,
    )
    if cached is not None:
        return cached
    try:
        # Conservative initial Product policy: no lexical rewrite is allowed
        # unless a future glossary rule carries explicit evidence.  This stage
        # still creates a distinct immutable assembly/revision boundary rather
        # than pretending the refinement component changed text.
        items = [
            {
                "sequence_number": int(row["sequence_number"]),
                "kind": "assembly_segment",
                "source_start": row.get("source_start"),
                "source_end": row.get("source_end"),
                "source_text": row.get("source_text"),
                "target_text": row.get("target_text"),
                "payload": {
                    "translation_segment_id": int(row["id"]),
                    "refinement": "preserve_without_unproven_glossary_rewrite",
                    "changed": False,
                },
            }
            for row in segments
        ]
        if not items:
            raise StageExecutionError("Stage14 received no Stage12 translation segments")
        output = {
            "schema": "rocketdict-product-stage14/1",
            "assembly_id": run_id,
            "translation_run_id": int(translation_run_id),
            "segment_count": len(items),
            "changed_segment_count": 0,
            "policy": "preserve-without-unproven-glossary-rewrite-v1",
            "real_mt_lineage": True,
        }
        return _complete(database, run_id, output, items=items)
    except Exception as exc:
        _fail(database, run_id, exc)
        raise


_DIGIT = re.compile(r"(?<![\w])([+-]?\d+(?:[.,'’]\d+)?(?:/\d+)?)(?![\w])")
_CRITICAL_SYMBOLS = ("%", "°", "±", "=", "<", ">")
_NUMBER_WORDS = {
    "zero": 0, "one": 1, "two": 2, "three": 3, "four": 4, "five": 5,
    "six": 6, "seven": 7, "eight": 8, "nine": 9, "ten": 10,
    "eleven": 11, "twelve": 12, "thirteen": 13, "fourteen": 14,
    "fifteen": 15, "sixteen": 16, "seventeen": 17, "eighteen": 18,
    "nineteen": 19, "twenty": 20, "thirty": 30, "forty": 40,
    "fifty": 50, "sixty": 60, "seventy": 70, "eighty": 80, "ninety": 90,
}


def _normalize_number(value: str) -> str:
    value = value.strip().replace("’", "'")
    if "/" in value:
        left, right = value.split("/", 1)
        return f"{_normalize_number(left)}/{_normalize_number(right)}"
    sign = ""
    if value[:1] in {"+", "-"}:
        sign, value = value[0], value[1:]
    # Treat apostrophe/comma as decimal-style historical separators; normalize
    # to a canonical dot. Thousands-specific refinement remains measurable and
    # can evolve under regression evidence without licensing missing literals.
    value = value.replace("'", ".").replace(",", ".")
    parts = value.split(".", 1)
    integer = parts[0].lstrip("0") or "0"
    fraction = parts[1].rstrip("0") if len(parts) == 2 else ""
    return sign + integer + ("." + fraction if fraction else "")


def _literal_numbers(text: str) -> list[str]:
    return [_normalize_number(match.group(1)) for match in _DIGIT.finditer(text)]


def _licensed_spelled_numbers(text: str) -> set[str]:
    words = re.findall(r"[A-Za-z]+", text.casefold())
    values: set[str] = set()
    for index, word in enumerate(words):
        if word not in _NUMBER_WORDS:
            continue
        total = _NUMBER_WORDS[word]
        if total >= 20 and index + 1 < len(words) and words[index + 1] in _NUMBER_WORDS and _NUMBER_WORDS[words[index + 1]] < 10:
            total += _NUMBER_WORDS[words[index + 1]]
        values.add(str(total))
    return values


def _assembly(database: Path, assembly_id: int) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    with connect(database, readonly=True) as connection:
        run = get_run(connection, int(assembly_id))
        if int(run["stage_number"]) != 14 or run["status"] != "completed":
            raise StageExecutionError("Stage15/16 require a completed Stage14 assembly")
        items = get_run_items(connection, int(assembly_id), kind="assembly_segment")
    if not items:
        raise StageExecutionError("Stage14 assembly contains no segments")
    return run, items


def _quality_run(
    database: Path,
    *,
    implementation: str,
    assembly_id: int,
    parameters: dict[str, Any],
    evaluator: Callable[[list[dict[str, Any]], dict[str, Any]], list[dict[str, Any]]],
) -> dict[str, Any]:
    assembly_run, segments = _assembly(database, assembly_id)
    input_identity = {
        "assembly_id": int(assembly_id),
        "assembly_output_sha256": str(assembly_run.get("output_sha256") or ""),
    }
    run_id, cached = _start(
        database,
        stage_number=15,
        implementation=implementation,
        input_identity=input_identity,
        parameters=parameters,
    )
    if cached is not None:
        return cached
    try:
        issues = evaluator(segments, parameters)
        items = [
            {
                "sequence_number": index,
                "kind": "quality_issue",
                "source_start": issue.get("source_start"),
                "source_end": issue.get("source_end"),
                "source_text": issue.get("source_text"),
                "target_text": issue.get("target_text"),
                "payload": issue,
            }
            for index, issue in enumerate(issues)
        ]
        output = {
            "schema": "rocketdict-product-stage15-quality/1",
            "quality_gate_run_id": run_id,
            "assembly_id": int(assembly_id),
            "implementation": implementation,
            "passed": not issues,
            "failure_count": len(issues),
            "issues_sha256": _canonical_sha(issues),
        }
        return _complete(database, run_id, output, items=items)
    except Exception as exc:
        _fail(database, run_id, exc)
        raise


def _numeric_issues(segments: list[dict[str, Any]], _parameters: dict[str, Any]) -> list[dict[str, Any]]:
    issues: list[dict[str, Any]] = []
    for row in segments:
        source = str(row.get("source_text") or "")
        target = str(row.get("target_text") or "")
        source_literals = Counter(_literal_numbers(source))
        target_literals = Counter(_literal_numbers(target))
        licensed_additions = _licensed_spelled_numbers(source)
        missing = list((source_literals - target_literals).elements())
        extra_counter = target_literals - source_literals
        unlicensed_extra = [
            value
            for value in extra_counter.elements()
            if value not in licensed_additions
        ]
        symbol_mismatch = {
            symbol: {"source": source.count(symbol), "target": target.count(symbol)}
            for symbol in _CRITICAL_SYMBOLS
            if source.count(symbol) != target.count(symbol)
        }
        if missing or unlicensed_extra or symbol_mismatch:
            issues.append(
                {
                    "type": "numeric_symbol_mismatch",
                    "segment_sequence": int(row["sequence_number"]),
                    "source_start": row.get("source_start"),
                    "source_end": row.get("source_end"),
                    "source_text": source,
                    "target_text": target,
                    "missing_source_literals": missing,
                    "unlicensed_target_literals": unlicensed_extra,
                    "symbol_mismatch": symbol_mismatch,
                }
            )
    return issues


def _punctuation_issues(segments: list[dict[str, Any]], _parameters: dict[str, Any]) -> list[dict[str, Any]]:
    issues: list[dict[str, Any]] = []
    paired = (("(", ")"), ("[", "]"), ("{", "}"))
    for row in segments:
        source = str(row.get("source_text") or "")
        target = str(row.get("target_text") or "")
        mismatch: dict[str, Any] = {}
        for left, right in paired:
            if source.count(left) != target.count(left) or source.count(right) != target.count(right):
                mismatch[left + right] = {
                    "source": [source.count(left), source.count(right)],
                    "target": [target.count(left), target.count(right)],
                }
        for terminal in ("?", "!"):
            if source.count(terminal) != target.count(terminal):
                mismatch[terminal] = {
                    "source": source.count(terminal),
                    "target": target.count(terminal),
                }
        if mismatch:
            issues.append(
                {
                    "type": "punctuation_mismatch",
                    "segment_sequence": int(row["sequence_number"]),
                    "source_start": row.get("source_start"),
                    "source_end": row.get("source_end"),
                    "source_text": source,
                    "target_text": target,
                    "mismatch": mismatch,
                }
            )
    return issues


def _length_issues(segments: list[dict[str, Any]], parameters: dict[str, Any]) -> list[dict[str, Any]]:
    minimum = float(parameters.get("min_ratio", 0.15))
    maximum = float(parameters.get("max_ratio", 6.0))
    if minimum <= 0 or maximum <= minimum:
        raise StageExecutionError("Invalid Stage15 length-ratio thresholds")
    issues: list[dict[str, Any]] = []
    for row in segments:
        source = str(row.get("source_text") or "")
        target = str(row.get("target_text") or "")
        source_alpha = sum(ch.isalpha() for ch in source)
        target_alpha = sum(ch.isalpha() for ch in target)
        ratio = (target_alpha / source_alpha) if source_alpha else (1.0 if not target_alpha else float("inf"))
        if not target.strip() or ratio < minimum or ratio > maximum:
            issues.append(
                {
                    "type": "length_ratio_failure",
                    "segment_sequence": int(row["sequence_number"]),
                    "source_start": row.get("source_start"),
                    "source_end": row.get("source_end"),
                    "source_text": source,
                    "target_text": target,
                    "source_alpha": source_alpha,
                    "target_alpha": target_alpha,
                    "ratio": ratio if ratio != float("inf") else "infinite",
                    "minimum": minimum,
                    "maximum": maximum,
                }
            )
    return issues


def run_numeric_symbol_gate(
    database: Path | str,
    *,
    assembly_id: int,
    parameters: dict[str, Any] | None = None,
    implementation: str = "rocketdict-numeric-symbol-preservation",
) -> dict[str, Any]:
    return _quality_run(
        Path(database).expanduser().resolve(),
        implementation=implementation,
        assembly_id=int(assembly_id),
        parameters=dict(parameters or {}),
        evaluator=_numeric_issues,
    )


def run_punctuation_gate(
    database: Path | str,
    *,
    assembly_id: int,
    parameters: dict[str, Any] | None = None,
    implementation: str = "rocketdict-punctuation-preservation",
) -> dict[str, Any]:
    return _quality_run(
        Path(database).expanduser().resolve(),
        implementation=implementation,
        assembly_id=int(assembly_id),
        parameters=dict(parameters or {}),
        evaluator=_punctuation_issues,
    )


def run_length_ratio_gate(
    database: Path | str,
    *,
    assembly_id: int,
    parameters: dict[str, Any] | None = None,
    implementation: str = "rocketdict-length-ratio-proxy",
) -> dict[str, Any]:
    return _quality_run(
        Path(database).expanduser().resolve(),
        implementation=implementation,
        assembly_id=int(assembly_id),
        parameters=dict(parameters or {}),
        evaluator=_length_issues,
    )


def run_stage16(
    database: Path | str,
    *,
    assembly_id: int,
    parameters: dict[str, Any] | None = None,
    implementation: str = "approve-if-clean-finalization",
) -> dict[str, Any]:
    database = Path(database).expanduser().resolve()
    parameters = dict(parameters or {})
    assembly_run, segments = _assembly(database, int(assembly_id))
    required_gates = {
        "rocketdict-numeric-symbol-preservation",
        "rocketdict-punctuation-preservation",
        "rocketdict-length-ratio-proxy",
    }
    with connect(database, readonly=True) as connection:
        rows = connection.execute(
            "SELECT * FROM stage_runs WHERE stage_number=15 AND status='completed' ORDER BY id"
        ).fetchall()
        passed: dict[str, int] = {}
        for row in rows:
            input_identity = json.loads(str(row["input_identity_json"]))
            if int(input_identity.get("assembly_id") or 0) != int(assembly_id):
                continue
            output = json.loads(str(row["output_json"] or "{}"))
            if output.get("passed") is True:
                passed[str(row["implementation"])] = int(row["id"])
    missing = sorted(required_gates - set(passed))
    if missing:
        raise StageExecutionError(
            f"Stage16 refuses finalization without all hard gate PASS rows for assembly {assembly_id}: {missing}"
        )
    input_identity = {
        "assembly_id": int(assembly_id),
        "assembly_output_sha256": str(assembly_run.get("output_sha256") or ""),
        "quality_gate_run_ids": {key: passed[key] for key in sorted(required_gates)},
    }
    run_id, cached = _start(
        database,
        stage_number=16,
        implementation=implementation,
        input_identity=input_identity,
        parameters=parameters,
    )
    if cached is not None:
        return cached
    try:
        items = [
            {
                "sequence_number": int(row["sequence_number"]),
                "kind": "approved_translation_segment",
                "source_start": row.get("source_start"),
                "source_end": row.get("source_end"),
                "source_text": row.get("source_text"),
                "target_text": row.get("target_text"),
                "payload": {
                    "assembly_segment_id": int(row["id"]),
                    "hard_gate_run_ids": input_identity["quality_gate_run_ids"],
                },
            }
            for row in segments
        ]
        output = {
            "schema": "rocketdict-product-stage16/1",
            "translation_revision_id": run_id,
            "stage_result_id": run_id,
            "assembly_id": int(assembly_id),
            "segment_count": len(items),
            "hard_quality_gate_count": len(required_gates),
            "approved": True,
        }
        return _complete(database, run_id, output, items=items)
    except Exception as exc:
        _fail(database, run_id, exc)
        raise


def run_stage17(
    database: Path | str,
    *,
    translation_revision_id: int,
    parameters: dict[str, Any] | None = None,
    implementation: str = "deterministic-structural-global",
) -> dict[str, Any]:
    database = Path(database).expanduser().resolve()
    parameters = dict(parameters or {})
    with connect(database, readonly=True) as connection:
        revision = get_run(connection, int(translation_revision_id))
        if int(revision["stage_number"]) != 16 or revision["status"] != "completed":
            raise StageExecutionError("Stage17 requires a completed Stage16 approved revision")
        revision_output = dict(revision.get("output") or {})
        if revision_output.get("approved") is not True:
            raise StageExecutionError("Stage17 refuses an unapproved translation revision")
        segments = get_run_items(
            connection, int(translation_revision_id), kind="approved_translation_segment"
        )
    input_identity = {
        "translation_revision_id": int(translation_revision_id),
        "translation_revision_output_sha256": str(revision.get("output_sha256") or ""),
    }
    run_id, cached = _start(
        database,
        stage_number=17,
        implementation=implementation,
        input_identity=input_identity,
        parameters=parameters,
    )
    if cached is not None:
        return cached
    try:
        if not segments:
            raise StageExecutionError("Stage17 received no approved translation segments")
        items = [
            {
                "sequence_number": int(row["sequence_number"]),
                "kind": "alignment_segment",
                "source_start": row.get("source_start"),
                "source_end": row.get("source_end"),
                "source_text": row.get("source_text"),
                "target_text": row.get("target_text"),
                "payload": {
                    "translation_revision_segment_id": int(row["id"]),
                    "alignment_method": "exact_structural_unit_identity",
                    "confidence": 1.0,
                },
            }
            for row in segments
        ]
        output = {
            "schema": "rocketdict-product-stage17/1",
            "alignment_run_id": run_id,
            "stage_result_id": run_id,
            "translation_revision_id": int(translation_revision_id),
            "segment_count": len(items),
            "coverage_complete": True,
            "uncovered_segment_count": 0,
        }
        return _complete(database, run_id, output, items=items)
    except Exception as exc:
        _fail(database, run_id, exc)
        raise
