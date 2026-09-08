from __future__ import annotations

"""One-shot, assertion-heavy Stage12 structural-label planner/execution migration.

The workflow that invokes this file commits only after focused regressions and
the complete dependency-light Product Core suite pass. Remove this file and its
workflow after successful promotion.
"""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def write(path: str, value: str) -> None:
    (ROOT / path).write_text(value, encoding="utf-8")


def replace_once(path: str, old: str, new: str) -> None:
    text = read(path)
    count = text.count(old)
    if count != 1:
        raise RuntimeError(f"{path}: expected one anchor, found {count}: {old[:120]!r}")
    write(path, text.replace(old, new, 1))


TRANSLATION = "rocketdict-product-core/src/rocketdict/translation_stage.py"
STRUCTURAL = "rocketdict-product-core/src/rocketdict/structural_labels.py"
REGISTRY = "rocketdict-product-core/src/rocketdict/api/registry.py"
TEST = "rocketdict-product-core/tests/test_translation_stage_structural_labels.py"

# Fail if migration was already applied or the starting contracts drifted.
if "rocketdict-stage12-protected-split/5" in read(TRANSLATION):
    raise RuntimeError("Stage12 planner /5 is already present")
if 'PLANNER_CONTRACT = "rocketdict-stage12-protected-split/4"' not in read(TRANSLATION):
    raise RuntimeError("unexpected Stage12 planner starting contract")
if "partition_txt_base_with_block_structural_labels" in read(STRUCTURAL):
    raise RuntimeError("structural-label partition helper already exists")
if (ROOT / TEST).exists():
    raise RuntimeError(f"refusing to overwrite existing {TEST}")

# 1) Add source-only block-label partitioning beside the maintained label contract.
structural = read(STRUCTURAL)
structural += r'''


def _slice_base_rows(
    content: str,
    base: Sequence[dict[str, Any]],
    *,
    start: int,
    end: int,
) -> list[dict[str, Any]]:
    """Slice existing Stage12 TXT base rows without inventing source bytes."""
    if end <= start:
        return []
    output: list[dict[str, Any]] = []
    for row in base:
        row_start = int(row["start"])
        row_end = int(row["end"])
        left = max(start, row_start)
        right = min(end, row_end)
        if right <= left:
            continue
        metadata = dict(row.get("metadata") or {})
        if left != row_start or right != row_end:
            if metadata.get("source") == "ascii_table":
                raise ValueError("supported structural label overlaps an ASCII-table unit")
            metadata["source_before_structural_label_split"] = metadata.get("source")
            metadata["source"] = "nlp_sentence_fragment"
            metadata["structural_label_boundary_split"] = True
        output.append(
            {
                "start": left,
                "end": right,
                "text": content[left:right],
                "metadata": metadata,
            }
        )
    if output and "".join(str(row["text"]) for row in output) != content[start:end]:
        raise ValueError("structural-label non-label slicing is not byte-exact")
    return output


def partition_txt_base_with_block_structural_labels(
    content: str,
    base: Sequence[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Make supported block labels standalone byte-exact Stage12 base units.

    Detection runs on the complete immutable TXT source, not on already split
    context fragments. This is required because full-Opticks evidence proved
    that planner /4 cut 48/109 supported labels across Stage12 boundaries.
    Inline labels remain ordinary prose.
    """
    if not base:
        return []
    scope_start = int(base[0]["start"])
    scope_end = int(base[-1]["end"])
    if scope_end <= scope_start:
        raise ValueError("Stage12 structural-label base scope is empty")
    if "".join(str(row["text"]) for row in base) != content[scope_start:scope_end]:
        raise ValueError("Stage12 structural-label input base is not contiguous")

    labels = [
        label
        for label in detect_structural_labels(content, block_only=True)
        if label.source_end > scope_start and label.source_start < scope_end
    ]
    for label in labels:
        if label.source_start < scope_start or label.source_end > scope_end:
            raise ValueError("block structural label crosses Stage12 TXT scope")
        for row in base:
            if (row.get("metadata") or {}).get("source") != "ascii_table":
                continue
            if label.source_start < int(row["end"]) and label.source_end > int(row["start"]):
                raise ValueError("supported structural label overlaps an ASCII table")

    output: list[dict[str, Any]] = []
    cursor = scope_start
    for label_index, label in enumerate(labels):
        if label.source_start < cursor:
            raise ValueError("supported structural labels overlap")
        output.extend(_slice_base_rows(content, base, start=cursor, end=label.source_start))
        output.append(
            {
                "start": int(label.source_start),
                "end": int(label.source_end),
                "text": content[label.source_start:label.source_end],
                "metadata": {
                    "source": "structural_label",
                    "structural_label_index": label_index,
                    "structural_label_contract": STRUCTURAL_LABEL_CONTRACT,
                    "structural_label_kind": label.kind,
                    "structural_label_number": label.number,
                    "canonical_model_input": label.canonical_model_input,
                },
            }
        )
        cursor = int(label.source_end)
    output.extend(_slice_base_rows(content, base, start=cursor, end=scope_end))

    if not output:
        raise ValueError("Stage12 structural-label partition produced no source units")
    if "".join(str(row["text"]) for row in output) != content[scope_start:scope_end]:
        raise ValueError("Stage12 structural-label partition is not byte-exact")
    for left, right in zip(output, output[1:]):
        if int(left["end"]) != int(right["start"]):
            raise ValueError("Stage12 structural-label partition produced a source gap")
    return output
'''
write(STRUCTURAL, structural)

# 2) Wire partitioning and staged real-OPUS selection into maintained Stage12.
replace_once(
    TRANSLATION,
    "from .runtime import OpusTranslator, load_opus_asset\nfrom .stages import StageExecutionError, _complete, _fail, _start\n",
    "from .runtime import OpusTranslator, load_opus_asset\n"
    "from .stages import StageExecutionError, _complete, _fail, _start\n"
    "from .structural_labels import (\n"
    "    STRUCTURAL_LABEL_CONTRACT,\n"
    "    STRUCTURAL_LABEL_GENERATION_CELLS,\n"
    "    StructuralLabel,\n"
    "    evaluate_structural_label_hypotheses,\n"
    "    parse_structural_label_unit,\n"
    "    partition_txt_base_with_block_structural_labels,\n"
    ")\n",
)
replace_once(
    TRANSLATION,
    'PLANNER_CONTRACT = "rocketdict-stage12-protected-split/4"',
    'PLANNER_CONTRACT = "rocketdict-stage12-protected-split/5"',
)
replace_once(
    TRANSLATION,
    '''    if selected_format == "txt":
        try:
            base = partition_txt_base_with_ascii_tables(content, base)
        except ValueError as exc:
            raise StageExecutionError(f"Stage12 ASCII-table partition failed: {exc}") from exc

    result: list[dict[str, Any]] = []
''',
    '''    if selected_format == "txt":
        try:
            base = partition_txt_base_with_ascii_tables(content, base)
            base = partition_txt_base_with_block_structural_labels(content, base)
        except ValueError as exc:
            raise StageExecutionError(f"Stage12 source-structure partition failed: {exc}") from exc

    result: list[dict[str, Any]] = []
''',
)
replace_once(
    TRANSLATION,
    '''        metadata = dict(row.get("metadata") or {})

        if metadata.get("source") == "ascii_table":
''',
    '''        metadata = dict(row.get("metadata") or {})

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
''',
)

helper = r'''

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
'''
replace_once(
    TRANSLATION,
    "    return result\n\n\ndef run_stage12(\n",
    "    return result\n" + helper + "\n\ndef run_stage12(\n",
)
replace_once(
    TRANSLATION,
    '''    effective["planner_contract"] = PLANNER_CONTRACT
    device = str(effective.get("device") or "cpu")
''',
    '''    effective["planner_contract"] = PLANNER_CONTRACT
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
''',
)
replace_once(
    TRANSLATION,
    '''        table_plans: dict[int, Any] = {}
        request_texts: list[str] = []
''',
    '''        table_plans: dict[int, Any] = {}
        structural_label_plans: dict[int, StructuralLabel] = {}
        request_texts: list[str] = []
''',
)
replace_once(
    TRANSLATION,
    '''            else:
                request_texts.append(str(unit["text"]))
                request_refs.append((unit_index, None))
''',
    '''            elif metadata.get("source") == "structural_label":
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
''',
)
replace_once(
    TRANSLATION,
    '''        generated = {
            reference: hypotheses
            for reference, hypotheses in zip(request_refs, translated, strict=True)
        }

        asset = load_opus_asset()
''',
    '''        generated = {
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
''',
)
replace_once(
    TRANSLATION,
    '''            else:
                hypotheses = generated[(sequence, None)]
                if not hypotheses:
''',
    '''            elif metadata.get("source") == "structural_label":
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
''',
)
replace_once(
    TRANSLATION,
    '''            "planner_contract": PLANNER_CONTRACT,
            "table_stage12_contract": TABLE_STAGE12_CONTRACT,
            "table_block_count": len(table_plans),
''',
    '''            "planner_contract": PLANNER_CONTRACT,
            "structural_label_contract": STRUCTURAL_LABEL_CONTRACT,
            "structural_label_unit_count": len(structural_label_plans),
            "structural_label_escalated_unit_count": int(structural_execution["escalated_count"]),
            "structural_label_model_request_count": int(structural_execution["request_count"]),
            "table_stage12_contract": TABLE_STAGE12_CONTRACT,
            "table_block_count": len(table_plans),
''',
)
replace_once(
    TRANSLATION,
    '''            "model_request_count": len(request_texts),
            "max_translation_unit_tokens": max_request_tokens,
''',
    '''            "model_request_count": len(request_texts) + int(structural_execution["request_count"]),
            "max_translation_unit_tokens": max(
                max_request_tokens,
                2 if structural_label_plans else 0,
            ),
''',
)

# Update the explanatory module contract text without changing ordinary/table semantics.
replace_once(
    TRANSLATION,
    "Planner v4 additionally recognizes conservative ASCII-table blocks in TXT\n",
    "Planner v4 additionally recognizes conservative ASCII-table blocks in TXT\n",
)
# The no-op assertion above intentionally proves the documented v4 table text still exists.
translation = read(TRANSLATION)
needle = "special table behavior is applied to subtitle cue segments.\n"
if translation.count(needle) != 1:
    raise RuntimeError("translation-stage docstring anchor drift")
translation = translation.replace(
    needle,
    "special table behavior is applied to subtitle cue segments.\n\n"
    "Planner v5 additionally isolates evidence-backed Gutenberg block structural\n"
    "labels before MT. Their immutable source spans stay byte-exact; only the\n"
    "separate model input expands the documented abbreviation, and only strict\n"
    "raw OPUS candidates may be selected. Inline labels stay ordinary prose.\n",
    1,
)
write(TRANSLATION, translation)

# 3) Publish both planner and structural execution identities in the registry.
replace_once(
    REGISTRY,
    'STAGE12_PLANNER_CONTRACT = "rocketdict-stage12-protected-split/4"',
    'STAGE12_PLANNER_CONTRACT = "rocketdict-stage12-protected-split/5"\n'
    'STAGE12_STRUCTURAL_LABEL_CONTRACT = "rocketdict-stage12-block-structural-label-opus/1"',
)
replace_once(
    REGISTRY,
    '''                    _control("planner_contract", STAGE12_PLANNER_CONTRACT),
                    _control("plan_preferred_unit_tokens", 64),
''',
    '''                    _control("planner_contract", STAGE12_PLANNER_CONTRACT),
                    _control("structural_label_contract", STAGE12_STRUCTURAL_LABEL_CONTRACT),
                    _control("plan_preferred_unit_tokens", 64),
''',
)
replace_once(
    REGISTRY,
    '"tags": ["real-mt", "offline", "opus", "ctranslate2", "structure-aware-planner"],',
    '"tags": ["real-mt", "offline", "opus", "ctranslate2", "structure-aware-planner", "structural-label-aware"],',
)

# 4) Add focused planner/execution/registry regressions.
test_content = r'''from __future__ import annotations

import re

import pytest

from rocketdict.api.registry import (
    STAGE12_PLANNER_CONTRACT,
    STAGE12_STRUCTURAL_LABEL_CONTRACT,
    lab_manifest,
)
from rocketdict.stages import StageExecutionError
from rocketdict.structural_labels import (
    STRUCTURAL_LABEL_CONTRACT,
    parse_structural_label_unit,
)
from rocketdict.translation_stage import (
    PLANNER_CONTRACT,
    _translate_structural_label_units,
    segment_translation_units,
)


def _context(sequence: int, start: int, end: int, content: str) -> dict:
    return {
        "sequence_number": sequence,
        "source_start": start,
        "source_end": end,
        "source_text": content[start:end],
        "payload": {"sentence_index": sequence},
    }


def _tokens(content: str) -> list[dict]:
    return [
        {
            "sequence_number": index,
            "source_start": match.start(),
            "source_end": match.end(),
            "source_text": match.group(0),
            "payload": {"flags": {"is_space": False}},
        }
        for index, match in enumerate(re.finditer(r"\S+", content))
    ]


def test_planner_v5_isolates_block_label_even_when_old_context_splits_it_three_ways() -> None:
    content = "Lead paragraph.\n\n_Exper._ 11. Following prose."
    label_start = content.index("_Exper._")
    boundary1 = label_start + 4
    boundary2 = content.index(" 11.") + 1
    context = [
        _context(0, 0, boundary1, content),
        _context(1, boundary1, boundary2, content),
        _context(2, boundary2, len(content), content),
    ]

    units = segment_translation_units(
        content,
        [],
        context,
        _tokens(content),
        selected_format="txt",
        preferred_tokens=64,
    )

    labels = [row for row in units if row["metadata"].get("source") == "structural_label"]
    assert len(labels) == 1
    label = labels[0]
    assert label["text"] == "_Exper._ 11."
    assert label["start"] == label_start
    assert label["end"] == label_start + len("_Exper._ 11.")
    assert label["metadata"]["planner_contract"] == PLANNER_CONTRACT
    assert label["metadata"]["structural_label_contract"] == STRUCTURAL_LABEL_CONTRACT
    assert label["metadata"]["canonical_model_input"] == "Experiment 11."
    assert label["metadata"]["structural_label_atomic"] is True
    assert "".join(str(row["text"]) for row in units) == content


def test_planner_v5_leaves_inline_supported_label_on_ordinary_text_path() -> None:
    content = "Inline (_Exper._ 10. _Part_ 2.) remains ordinary prose."
    context = [_context(0, 0, len(content), content)]
    units = segment_translation_units(
        content,
        [],
        context,
        _tokens(content),
        selected_format="txt",
        preferred_tokens=64,
    )
    assert not [row for row in units if row["metadata"].get("source") == "structural_label"]
    assert "".join(str(row["text"]) for row in units) == content


class _FakeTranslator:
    def __init__(self, *, never_accept: bool = False) -> None:
        self.calls: list[tuple[tuple[str, ...], int, int]] = []
        self.never_accept = never_accept

    def translate(
        self,
        texts: list[str],
        *,
        beam_size: int,
        num_hypotheses: int,
        max_decoding_length: int,
    ) -> list[list[dict]]:
        assert max_decoding_length == 128
        self.calls.append((tuple(texts), beam_size, num_hypotheses))
        rows: list[list[dict]] = []
        for text in texts:
            if self.never_accept:
                rows.append([{"rank": 0, "text": "Неверная метка 999."}])
            elif text == "Experiment 11.":
                rows.append([{"rank": 0, "text": "Эксперимент 11."}])
            elif text == "Observation 1." and beam_size == 6:
                rows.append([{"rank": 0, "text": "Замечание 1."}])
            elif text == "Observation 1." and beam_size == 12:
                rows.append([
                    {"rank": 0, "text": "Примечание 1."},
                    {"rank": 5, "text": "Наблюдение 1."},
                ])
            else:
                raise AssertionError((text, beam_size, num_hypotheses))
        return rows


def test_structural_label_execution_escalates_only_unresolved_label() -> None:
    translator = _FakeTranslator()
    labels = {
        7: parse_structural_label_unit("_Exper._ 11."),
        9: parse_structural_label_unit("_Obs._ 1."),
    }
    result = _translate_structural_label_units(translator, labels)

    assert translator.calls == [
        (("Experiment 11.", "Observation 1."), 6, 6),
        (("Observation 1.",), 12, 12),
    ]
    assert result["request_count"] == 3
    assert result["escalated_count"] == 1
    assert result["selected"][7]["target_text"] == "Эксперимент 11."
    assert result["selected"][7]["generation"]["beam_size"] == 6
    assert result["selected"][9]["target_text"] == "Наблюдение 1."
    assert result["selected"][9]["rank"] == 5
    assert result["selected"][9]["generation"]["beam_size"] == 12


def test_structural_label_execution_fails_closed_without_raw_acceptable_candidate() -> None:
    with pytest.raises(StageExecutionError, match="no acceptable structural-label"):
        _translate_structural_label_units(
            _FakeTranslator(never_accept=True),
            {3: parse_structural_label_unit("_Exper._ 11.")},
        )


def test_registry_publishes_planner_v5_and_structural_label_contract() -> None:
    assert PLANNER_CONTRACT == "rocketdict-stage12-protected-split/5"
    assert STAGE12_PLANNER_CONTRACT == PLANNER_CONTRACT
    assert STAGE12_STRUCTURAL_LABEL_CONTRACT == STRUCTURAL_LABEL_CONTRACT
    manifest = lab_manifest(probe_runtime=False)
    stage12 = next(row for row in manifest["stages"] if int(row["number"]) == 12)
    implementation = next(
        row
        for row in stage12["implementations"]
        if row["implementation_key"] == "opus-en-ru-ct2"
    )
    controls = {row["key"]: row.get("default") for row in implementation["controls"]}
    assert controls["planner_contract"] == PLANNER_CONTRACT
    assert controls["structural_label_contract"] == STRUCTURAL_LABEL_CONTRACT
    assert "structural-label-aware" in implementation["tags"]
'''
write(TEST, test_content)

# Final static assertions before handing the tree to pytest.
assert 'PLANNER_CONTRACT = "rocketdict-stage12-protected-split/5"' in read(TRANSLATION)
assert "partition_txt_base_with_block_structural_labels" in read(TRANSLATION)
assert "_translate_structural_label_units" in read(TRANSLATION)
assert "STAGE12_STRUCTURAL_LABEL_CONTRACT" in read(REGISTRY)
assert "structural_label_contract" in read(REGISTRY)
print("Stage12 structural-label planner/execution v5 migration applied", flush=True)
