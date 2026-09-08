from __future__ import annotations

"""One-shot fail-closed migration for ASCII-table boundary whitespace.

The first complete persisted Product Stage12 run over Opticks proved that table
partitioning can leave a split-created whitespace-only fragment outside a table.
SentencePiece normalizes such a request to zero tokens. Planner v7 keeps the
immutable table span unchanged and attaches only table-split whitespace to an
adjacent ordinary prose row before MT.

The invoking workflow commits maintained files only after focused and complete
dependency-light Product/Workbench suites pass. Remove this helper afterward.
"""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def replace_once(path: Path, old: str, new: str) -> None:
    text = path.read_text(encoding="utf-8")
    count = text.count(old)
    if count != 1:
        raise RuntimeError(f"{path}: expected one anchor, found {count}: {old!r}")
    path.write_text(text.replace(old, new), encoding="utf-8")


def main() -> int:
    table = ROOT / "rocketdict-product-core/src/rocketdict/table_stage12.py"
    translation = ROOT / "rocketdict-product-core/src/rocketdict/translation_stage.py"
    registry = ROOT / "rocketdict-product-core/src/rocketdict/api/registry.py"
    table_tests = ROOT / "rocketdict-product-core/tests/test_table_stage12.py"
    structural_tests = ROOT / "rocketdict-product-core/tests/test_translation_stage_structural_labels.py"

    helper = '''\n\ndef _coalesce_table_split_boundary_whitespace(\n    content: str, rows: Sequence[dict[str, Any]]\n) -> list[dict[str, Any]]:\n    """Attach table-split whitespace-only fragments to adjacent ordinary prose.\n\n    Only fragments explicitly created by ``ascii_table_boundary_split`` are\n    eligible. Table spans themselves are never extended or rewritten. If no\n    ordinary neighbor exists inside the non-table slice, fail closed instead of\n    inventing passthrough semantics.\n    """\n    output = [\n        {**row, "metadata": dict(row.get("metadata") or {})}\n        for row in rows\n    ]\n\n    def is_split_whitespace(row: dict[str, Any]) -> bool:\n        metadata = dict(row.get("metadata") or {})\n        return bool(metadata.get("ascii_table_boundary_split")) and not str(\n            row.get("text") or ""\n        ).strip()\n\n    def merge(\n        whitespace: dict[str, Any], neighbor: dict[str, Any], *, prepend: bool\n    ) -> dict[str, Any]:\n        metadata = dict(neighbor.get("metadata") or {})\n        if metadata.get("source") == "ascii_table":\n            raise ValueError("table boundary whitespace cannot extend an ASCII table")\n        whitespace_metadata = dict(whitespace.get("metadata") or {})\n        metadata.setdefault("source_before_table_split", metadata.get("source"))\n        metadata["source"] = "nlp_sentence_fragment"\n        metadata["ascii_table_boundary_split"] = True\n        metadata["ascii_table_boundary_whitespace_coalesced"] = True\n\n        starts = [\n            int(value)\n            for value in (\n                metadata.get("context_sentence_start"),\n                whitespace_metadata.get("context_sentence_start"),\n            )\n            if value is not None\n        ]\n        ends = [\n            int(value)\n            for value in (\n                metadata.get("context_sentence_end"),\n                whitespace_metadata.get("context_sentence_end"),\n            )\n            if value is not None\n        ]\n        if starts and ends:\n            metadata["context_sentence_start"] = min(starts)\n            metadata["context_sentence_end"] = max(ends)\n            metadata["context_sentence_count"] = (\n                int(metadata["context_sentence_end"])\n                - int(metadata["context_sentence_start"])\n                + 1\n            )\n\n        if prepend:\n            start = int(whitespace["start"])\n            end = int(neighbor["end"])\n        else:\n            start = int(neighbor["start"])\n            end = int(whitespace["end"])\n        return {\n            "start": start,\n            "end": end,\n            "text": content[start:end],\n            "metadata": metadata,\n        }\n\n    while len(output) > 1 and is_split_whitespace(output[0]):\n        whitespace = output.pop(0)\n        output[0] = merge(whitespace, output[0], prepend=True)\n\n    while len(output) > 1 and is_split_whitespace(output[-1]):\n        whitespace = output.pop()\n        output[-1] = merge(whitespace, output[-1], prepend=False)\n\n    if len(output) == 1 and is_split_whitespace(output[0]):\n        raise ValueError("table partition produced isolated whitespace-only source gap")\n    return output\n'''
    anchor = "\n\ndef _slice_base_rows(\n"
    text = table.read_text(encoding="utf-8")
    if text.count(anchor) != 1:
        raise RuntimeError("table_stage12.py insertion anchor drift")
    if "def _coalesce_table_split_boundary_whitespace(" in text:
        raise RuntimeError("table whitespace helper already exists")
    table.write_text(text.replace(anchor, helper + anchor), encoding="utf-8")

    replace_once(
        table,
        '    if output and "".join(str(row["text"]) for row in output) != content[start:end]:\n        raise ValueError("Stage12 non-table base slicing is not byte-exact")\n    return output\n',
        '    if output and "".join(str(row["text"]) for row in output) != content[start:end]:\n        raise ValueError("Stage12 non-table base slicing is not byte-exact")\n    output = _coalesce_table_split_boundary_whitespace(content, output)\n    if output and "".join(str(row["text"]) for row in output) != content[start:end]:\n        raise ValueError("Stage12 table-boundary whitespace coalescing is not byte-exact")\n    return output\n',
    )

    replace_once(
        translation,
        'Planner v6 isolates evidence-backed Gutenberg block structural labels before\nMT and coalesces split-created whitespace-only boundary fragments into adjacent\nordinary prose so every model request remains lexical. Label spans themselves\nstay byte-exact; only their separate model input expands the documented\nabbreviation, and only strict raw OPUS candidates may be selected. Inline\nlabels stay ordinary prose.\n',
        'Planner v7 keeps evidence-backed Gutenberg block structural labels byte-exact\nand coalesces split-created whitespace-only boundaries from both structural-label\nand ASCII-table partitioning into adjacent ordinary prose, so every ordinary MT\nrequest remains lexical. Structural label model input still expands only the\ndocumented abbreviation and selects only strict raw OPUS candidates. Inline\nlabels stay ordinary prose; table spans remain unchanged.\n',
    )
    replace_once(
        translation,
        'PLANNER_CONTRACT = "rocketdict-stage12-protected-split/6"',
        'PLANNER_CONTRACT = "rocketdict-stage12-protected-split/7"',
    )
    replace_once(
        registry,
        'STAGE12_PLANNER_CONTRACT = "rocketdict-stage12-protected-split/6"',
        'STAGE12_PLANNER_CONTRACT = "rocketdict-stage12-protected-split/7"',
    )
    replace_once(
        structural_tests,
        'assert PLANNER_CONTRACT == "rocketdict-stage12-protected-split/6"',
        'assert PLANNER_CONTRACT == "rocketdict-stage12-protected-split/7"',
    )

    regression = '''\n\ndef test_partition_coalesces_split_newline_after_table_into_following_prose() -> None:\n    table = (\n        "------+------\\n"\n        "Head  | Other\\n"\n        "More  | Text \\n"\n        "Tail  | Text \\n"\n        "------+------\\n"\n    )\n    content = table + "\\nFollowing prose."\n    table_end = len(table)\n    # Match the full-Opticks shape: one Stage10 sentence ends one byte after\n    # the detected table, leaving a split-created newline outside the table.\n    base = [\n        _base(0, table_end + 1, content, sequence=0),\n        _base(table_end + 1, len(content), content, sequence=1),\n    ]\n    rows = partition_txt_base_with_ascii_tables(content, base)\n\n    assert rows[0]["metadata"]["source"] == "ascii_table"\n    assert rows[0]["text"] == table\n    assert not [row for row in rows if not str(row["text"]).strip()]\n    assert rows[1]["start"] == table_end\n    assert rows[1]["text"] == "\\nFollowing prose."\n    assert rows[1]["metadata"]["ascii_table_boundary_whitespace_coalesced"] is True\n    assert "".join(str(row["text"]) for row in rows) == content\n'''
    marker = "\n\ndef test_single_pipe_prose_is_not_promoted_to_table() -> None:\n"
    text = table_tests.read_text(encoding="utf-8")
    if text.count(marker) != 1:
        raise RuntimeError("test_table_stage12.py insertion anchor drift")
    table_tests.write_text(text.replace(marker, regression + marker), encoding="utf-8")

    print("Stage12 ASCII-table boundary planner v7 migration applied")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
