from __future__ import annotations

"""One-shot, assertion-heavy repository migration for numeric prime hard-gate v5.

This file is intentionally temporary.  The accompanying workflow runs it once,
executes focused regressions, and commits only if those regressions pass.
"""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def replace_once(path: str, old: str, new: str) -> None:
    file_path = ROOT / path
    text = file_path.read_text(encoding="utf-8")
    count = text.count(old)
    if count != 1:
        raise RuntimeError(f"{path}: expected one migration anchor, found {count}: {old!r}")
    file_path.write_text(text.replace(old, new, 1), encoding="utf-8")


def append_once(path: str, marker: str, addition: str) -> None:
    file_path = ROOT / path
    text = file_path.read_text(encoding="utf-8")
    if marker in text:
        raise RuntimeError(f"{path}: migration marker already present: {marker!r}")
    if not text.endswith("\n"):
        text += "\n"
    file_path.write_text(text + addition, encoding="utf-8")


def main() -> int:
    numeric = "rocketdict-product-core/src/rocketdict/numeric_integrity.py"
    replace_once(
        numeric,
        "from .numeric_words import extract_russian_ordinals\nfrom .stages import StageExecutionError, _quality_run\n",
        "from .numeric_words import extract_russian_ordinals\n"
        "from .prime_notation import compare_numeric_prime_notation\n"
        "from .stages import StageExecutionError, _quality_run\n",
    )
    replace_once(
        numeric,
        'CONTRACT = "rocketdict-maintained-numeric-integrity/4"',
        'CONTRACT = "rocketdict-maintained-numeric-integrity/5"',
    )
    replace_once(
        numeric,
        "    unlicensed_additions = {key: value for key, value in excess.items() if key not in required}\n"
        "    return {\n",
        "    unlicensed_additions = {key: value for key, value in excess.items() if key not in required}\n"
        "    prime_notation = compare_numeric_prime_notation(source, target)\n"
        "    return {\n",
    )
    replace_once(
        numeric,
        '        "unlicensed_additions": unlicensed_additions,\n'
        '        "passed": not missing and not duplicate_required and not unlicensed_additions,\n',
        '        "unlicensed_additions": unlicensed_additions,\n'
        '        "prime_notation": prime_notation,\n'
        '        "passed": (\n'
        '            not missing\n'
        '            and not duplicate_required\n'
        '            and not unlicensed_additions\n'
        '            and prime_notation["passed"] is True\n'
        '        ),\n',
    )
    replace_once(
        numeric,
        '                "symbol_mismatch": dict(result["symbol_mismatch"]),\n'
        '                "numeric_detail": numeric,\n',
        '                "symbol_mismatch": dict(result["symbol_mismatch"]),\n'
        '                "prime_notation_mismatch": (\n'
        '                    None\n'
        '                    if numeric["prime_notation"]["passed"] is True\n'
        '                    else dict(numeric["prime_notation"])\n'
        '                ),\n'
        '                "numeric_detail": numeric,\n',
    )

    replace_once(
        "rocketdict-product-core/src/rocketdict/api/registry.py",
        'NUMERIC_INTEGRITY_CONTRACT = "rocketdict-maintained-numeric-integrity/4"',
        'NUMERIC_INTEGRITY_CONTRACT = "rocketdict-maintained-numeric-integrity/5"',
    )

    diagnostics = "rocketdict-product-core/src/rocketdict/research_diagnostics.py"
    replace_once(
        diagnostics,
        "mirroring Product numeric-v4 semantics without licensing cardinal/technical\n",
        "mirroring Product numeric literal-equivalence semantics without licensing cardinal/technical\n",
    )
    replace_once(
        diagnostics,
        "    ``1.F.4.``, and conservative numeric prime-mark notation. Prime notation is\n"
        "    research-only and deliberately does not change the Product numeric hard gate.\n",
        "    ``1.F.4.``, and conservative numeric prime-mark notation. The prime subcheck\n"
        "    mirrors promoted Product numeric-v5 prime semantics so research selection cannot\n"
        "    silently admit a candidate that the Product hard gate rejects.\n",
    )

    append_once(
        "rocketdict-product-core/tests/test_numeric_integrity.py",
        "test_prime_semantics_are_part_of_numeric_hard_gate",
        '''\n\ndef test_prime_semantics_are_part_of_numeric_hard_gate() -> None:\n    source = "it exceeds not 2'' 45''' or 3''."\n    target = "она не превышает 2 футов 45' или 3''."\n    result = compare_numeric_integrity(source, target)\n\n    # Legacy numeric-v4 preserved all three digit values here and therefore\n    # passed.  V5 must additionally preserve the ordered prime-unit signature.\n    assert result["missing"] == {}\n    assert result["duplicate_required"] == {}\n    assert result["unlicensed_additions"] == {}\n    assert result["prime_notation"]["passed"] is False\n    assert result["prime_notation"]["source_signature"] == [\n        {"value": "2", "prime_count": 2},\n        {"value": "45", "prime_count": 3},\n        {"value": "3", "prime_count": 2},\n    ]\n    assert result["passed"] is False\n    assert evaluate_numeric_symbol_pair(source, target)["passed"] is False\n\n\ndef test_stage15_gate_blocks_prime_semantic_corruption(tmp_path: Path) -> None:\n    db = tmp_path / "prime-hard-gate.sqlite"\n    bootstrap_database(db)\n    source = "it exceeds not 2'' 45''' or 3''."\n    target = "она не превышает 2 футов 45' или 3''."\n    with transaction(db) as connection:\n        assembly_id, cache_hit = begin_run(\n            connection,\n            stage_number=14,\n            stage_key="refinement",\n            implementation="glossary_refinement-current",\n            input_identity={"seed": "prime-v5-hard-gate"},\n            parameters={},\n        )\n        assert cache_hit is False\n        replace_run_items(\n            connection,\n            assembly_id,\n            [\n                {\n                    "sequence_number": 0,\n                    "kind": "assembly_segment",\n                    "source_start": 0,\n                    "source_end": len(source),\n                    "source_text": source,\n                    "target_text": target,\n                    "payload": {},\n                }\n            ],\n        )\n        finish_run(\n            connection,\n            assembly_id,\n            {\n                "schema": "rocketdict-product-stage14/1",\n                "assembly_id": assembly_id,\n                "segment_count": 1,\n                "real_mt_lineage": True,\n            },\n        )\n\n    result = run_numeric_symbol_gate(db, assembly_id=assembly_id)\n    assert result["passed"] is False\n    assert result["failure_count"] == 1\n''',
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
