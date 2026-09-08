from __future__ import annotations

"""One-shot assertion-heavy migration for Stage12 structural-boundary whitespace.

Full Opticks Product Stage12 first exposed that planner v5 can create standalone
whitespace-only units immediately after an isolated Gutenberg structural label.
SentencePiece normalizes those requests to an empty token sequence.  Planner v6
keeps the label byte-exact and coalesces only split-created boundary whitespace
into adjacent ordinary prose before MT.

The invoking workflow commits maintained files only after dependency-light
Product Core and Workbench regressions pass. Remove this helper after promotion.
"""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def replace_once(path: Path, old: str, new: str) -> None:
    text = path.read_text(encoding="utf-8")
    count = text.count(old)
    if count != 1:
        raise RuntimeError(f"{path}: expected one migration anchor, found {count}: {old!r}")
    path.write_text(text.replace(old, new), encoding="utf-8")


def main() -> int:
    structural = ROOT / "rocketdict-product-core/src/rocketdict/structural_labels.py"
    translation = ROOT / "rocketdict-product-core/src/rocketdict/translation_stage.py"
    registry = ROOT / "rocketdict-product-core/src/rocketdict/api/registry.py"
    tests = ROOT / "rocketdict-product-core/tests/test_translation_stage_structural_labels.py"

    helper = '''\n\ndef _coalesce_split_boundary_whitespace(\n    content: str, rows: Sequence[dict[str, Any]]\n) -> list[dict[str, Any]]:\n    """Attach split-created whitespace-only fragments to ordinary prose.\n\n    Structural labels remain exact standalone source spans.  The only fragments\n    eligible here are whitespace-only rows that were *created by structural-label\n    slicing*. Existing semantic rows are never silently rewritten.  ASCII tables\n    are not extended because their source geometry is a separate maintained\n    contract; an otherwise unrepresentable whitespace-only gap fails closed.\n    """\n    output = [\n        {**row, "metadata": dict(row.get("metadata") or {})}\n        for row in rows\n    ]\n\n    def is_split_whitespace(row: dict[str, Any]) -> bool:\n        metadata = dict(row.get("metadata") or {})\n        return bool(metadata.get("structural_label_boundary_split")) and not str(\n            row.get("text") or ""\n        ).strip()\n\n    def merge(\n        whitespace: dict[str, Any], neighbor: dict[str, Any], *, prepend: bool\n    ) -> dict[str, Any]:\n        metadata = dict(neighbor.get("metadata") or {})\n        if metadata.get("source") == "ascii_table":\n            raise ValueError(\n                "structural-label boundary whitespace cannot be merged into an ASCII table"\n            )\n        whitespace_metadata = dict(whitespace.get("metadata") or {})\n        metadata.setdefault(\n            "source_before_structural_label_split", metadata.get("source")\n        )\n        metadata["source"] = "nlp_sentence_fragment"\n        metadata["structural_label_boundary_split"] = True\n        metadata["structural_label_boundary_whitespace_coalesced"] = True\n\n        starts = [\n            int(value)\n            for value in (\n                metadata.get("context_sentence_start"),\n                whitespace_metadata.get("context_sentence_start"),\n            )\n            if value is not None\n        ]\n        ends = [\n            int(value)\n            for value in (\n                metadata.get("context_sentence_end"),\n                whitespace_metadata.get("context_sentence_end"),\n            )\n            if value is not None\n        ]\n        if starts and ends:\n            metadata["context_sentence_start"] = min(starts)\n            metadata["context_sentence_end"] = max(ends)\n            metadata["context_sentence_count"] = (\n                int(metadata["context_sentence_end"])\n                - int(metadata["context_sentence_start"])\n                + 1\n            )\n\n        if prepend:\n            start = int(whitespace["start"])\n            end = int(neighbor["end"])\n        else:\n            start = int(neighbor["start"])\n            end = int(whitespace["end"])\n        return {\n            "start": start,\n            "end": end,\n            "text": content[start:end],\n            "metadata": metadata,\n        }\n\n    while len(output) > 1 and is_split_whitespace(output[0]):\n        whitespace = output.pop(0)\n        output[0] = merge(whitespace, output[0], prepend=True)\n\n    while len(output) > 1 and is_split_whitespace(output[-1]):\n        whitespace = output.pop()\n        output[-1] = merge(whitespace, output[-1], prepend=False)\n\n    if len(output) == 1 and is_split_whitespace(output[0]):\n        raise ValueError(\n            "structural-label partition produced an isolated whitespace-only source gap"\n        )\n    return output\n'''

    anchor = "\n\ndef _slice_base_rows(\n"
    text = structural.read_text(encoding="utf-8")
    if text.count(anchor) != 1:
        raise RuntimeError("structural_labels.py: _slice_base_rows insertion anchor drift")
    if "def _coalesce_split_boundary_whitespace(" in text:
        raise RuntimeError("structural boundary whitespace helper already exists")
    structural.write_text(text.replace(anchor, helper + anchor), encoding="utf-8")

    replace_once(
        structural,
        '    if output and "".join(str(row["text"]) for row in output) != content[start:end]:\n        raise ValueError("structural-label non-label slicing is not byte-exact")\n    return output\n',
        '    if output and "".join(str(row["text"]) for row in output) != content[start:end]:\n        raise ValueError("structural-label non-label slicing is not byte-exact")\n    output = _coalesce_split_boundary_whitespace(content, output)\n    if output and "".join(str(row["text"]) for row in output) != content[start:end]:\n        raise ValueError("structural-label whitespace coalescing is not byte-exact")\n    return output\n',
    )

    replace_once(
        translation,
        'Planner v5 additionally isolates evidence-backed Gutenberg block structural\nlabels before MT. Their immutable source spans stay byte-exact; only the\nseparate model input expands the documented abbreviation, and only strict\nraw OPUS candidates may be selected. Inline labels stay ordinary prose.\n',
        'Planner v6 isolates evidence-backed Gutenberg block structural labels before\nMT and coalesces split-created whitespace-only boundary fragments into adjacent\nordinary prose so every model request remains lexical. Label spans themselves\nstay byte-exact; only their separate model input expands the documented\nabbreviation, and only strict raw OPUS candidates may be selected. Inline\nlabels stay ordinary prose.\n',
    )
    replace_once(
        translation,
        'PLANNER_CONTRACT = "rocketdict-stage12-protected-split/5"',
        'PLANNER_CONTRACT = "rocketdict-stage12-protected-split/6"',
    )
    replace_once(
        registry,
        'STAGE12_PLANNER_CONTRACT = "rocketdict-stage12-protected-split/5"',
        'STAGE12_PLANNER_CONTRACT = "rocketdict-stage12-protected-split/6"',
    )

    replace_once(
        tests,
        "def test_planner_v5_isolates_block_label_even_when_old_context_splits_it_three_ways() -> None:",
        "def test_planner_v6_isolates_block_label_even_when_old_context_splits_it_three_ways() -> None:",
    )
    replace_once(
        tests,
        "def test_planner_v5_leaves_inline_supported_label_on_ordinary_text_path() -> None:",
        "def test_planner_v6_leaves_inline_supported_label_on_ordinary_text_path() -> None:",
    )
    replace_once(
        tests,
        "def test_registry_publishes_planner_v5_and_structural_label_contract() -> None:\n    assert PLANNER_CONTRACT == \"rocketdict-stage12-protected-split/5\"",
        "def test_registry_publishes_planner_v6_and_structural_label_contract() -> None:\n    assert PLANNER_CONTRACT == \"rocketdict-stage12-protected-split/6\"",
    )

    regression = '''\n\ndef test_planner_v6_coalesces_label_boundary_whitespace_into_following_prose() -> None:\n    content = "Lead paragraph.\\n\\n_Exper._ 11.\\n\\nFollowing prose."\n    label_start = content.index("_Exper._")\n    label_end = label_start + len("_Exper._ 11.")\n    # Reproduce the full-Opticks failure shape: Stage10 ends one sentence after\n    # the label's source-owned blank separator, so isolating the exact label\n    # would otherwise leave a standalone "\\n\\n" unit.\n    context = [\n        _context(0, 0, label_end + 2, content),\n        _context(1, label_end + 2, len(content), content),\n    ]\n\n    units = segment_translation_units(\n        content,\n        [],\n        context,\n        _tokens(content),\n        selected_format="txt",\n        preferred_tokens=64,\n    )\n\n    labels = [row for row in units if row["metadata"].get("source") == "structural_label"]\n    assert len(labels) == 1\n    assert labels[0]["text"] == "_Exper._ 11."\n    assert labels[0]["start"] == label_start\n    assert labels[0]["end"] == label_end\n    assert not [row for row in units if not str(row["text"]).strip()]\n    following = next(row for row in units if int(row["start"]) == label_end)\n    assert following["text"].startswith("\\n\\nFollowing prose.")\n    assert following["metadata"]["structural_label_boundary_whitespace_coalesced"] is True\n    assert following["metadata"]["planner_contract"] == PLANNER_CONTRACT\n    assert "".join(str(row["text"]) for row in units) == content\n'''
    marker = "\n\ndef test_planner_v6_leaves_inline_supported_label_on_ordinary_text_path() -> None:\n"
    text = tests.read_text(encoding="utf-8")
    if text.count(marker) != 1:
        raise RuntimeError("structural-label test insertion marker drift")
    tests.write_text(text.replace(marker, regression + marker), encoding="utf-8")

    print("Stage12 structural-boundary planner v6 migration applied")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
