from __future__ import annotations

"""Resolve the narrowest real-MT target evidence for a lexical source token.

Ordinary translation segments expose one target for their whole aligned source
unit.  Stage12 table-aware segments additionally carry exact source spans and
raw OPUS targets for source-only logical table text groups.  Lexical extraction
must use that narrower group target instead of assigning the whole rendered
table to every word, otherwise unrelated table cells collapse into the same
sense evidence.
"""

from dataclasses import dataclass
from typing import Any


TABLE_LEXICAL_EVIDENCE_CONTRACT = "rocketdict-table-lexical-target-evidence/1"


class TargetEvidenceError(RuntimeError):
    pass


@dataclass(frozen=True)
class TargetEvidence:
    text: str
    scope: str
    metadata: dict[str, Any]


def _contains(span: dict[str, Any], start: int, end: int) -> bool:
    return int(span.get("start") or -1) <= start and int(span.get("end") or -1) >= end


def resolve_target_evidence(
    *,
    token_start: int,
    token_end: int,
    alignment: dict[str, Any],
    translation_segment: dict[str, Any],
) -> TargetEvidence:
    if token_start < 0 or token_end <= token_start:
        raise TargetEvidenceError("invalid lexical token source span")
    for row, label in ((alignment, "alignment"), (translation_segment, "translation")):
        if int(row.get("source_start") or -1) > token_start or int(row.get("source_end") or -1) < token_end:
            raise TargetEvidenceError(f"{label} segment does not contain lexical token")

    payload = dict(translation_segment.get("payload") or {})
    table = payload.get("table")
    if not isinstance(table, dict):
        text = str(alignment.get("target_text") or "").strip()
        if not text:
            raise TargetEvidenceError("ordinary alignment has empty target evidence")
        return TargetEvidence(
            text=text,
            scope="alignment_segment",
            metadata={"contract": TABLE_LEXICAL_EVIDENCE_CONTRACT},
        )

    groups = table.get("logical_groups")
    if not isinstance(groups, list) or not groups:
        raise TargetEvidenceError("table translation segment lacks logical group evidence")
    matches: list[dict[str, Any]] = []
    for group in groups:
        if not isinstance(group, dict):
            raise TargetEvidenceError("malformed table logical group evidence")
        spans = group.get("source_spans")
        if not isinstance(spans, list) or not spans:
            raise TargetEvidenceError("table logical group lacks source spans")
        if any(isinstance(span, dict) and _contains(span, token_start, token_end) for span in spans):
            matches.append(group)

    if len(matches) != 1:
        raise TargetEvidenceError(
            "lexical token must map to exactly one table logical target group: "
            f"matches={len(matches)}, token=[{token_start},{token_end})"
        )
    group = matches[0]
    target = str(group.get("target_text") or "").strip()
    if not target:
        raise TargetEvidenceError("table logical group has empty target text")
    return TargetEvidence(
        text=target,
        scope="table_logical_group",
        metadata={
            "contract": TABLE_LEXICAL_EVIDENCE_CONTRACT,
            "table_stage12_contract": table.get("stage12_contract"),
            "table_structure_contract": table.get("structure_contract"),
            "table_logical_contract": table.get("logical_contract"),
            "group_index": int(group.get("group_index") or 0),
            "grouping_reason": group.get("grouping_reason"),
            "source_spans": list(group.get("source_spans") or []),
        },
    )
