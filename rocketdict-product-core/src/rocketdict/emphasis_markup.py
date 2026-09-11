from __future__ import annotations

"""Conservative Gutenberg underscore-emphasis preservation diagnostic.

Project Gutenberg plain-text sources use paired underscores as source-owned
presentation markup.  This diagnostic deliberately checks only the *shape* of
that markup: raw underscore cardinality, complete underscore-delimited span
cardinality, and balanced/unbalanced state.  It does not require the payload
inside a marked span to remain lexically identical because ordinary linguistic
content may be translated.

The contract is a research/selection diagnostic, not a Product hard gate.  Its
purpose is to veto rescue candidates that become mechanically cleaner by
silently dropping or inventing source emphasis markup.  It never rewrites
source or target bytes.
"""

import re
from typing import Any


EMPHASIS_MARKUP_CONTRACT = "rocketdict-maintained-emphasis-markup-preservation/1"
_COMPLETE_EMPHASIS_RE = re.compile(r"_([^_\n]+)_")


def _markup_shape(text: str) -> dict[str, Any]:
    spans = [
        {
            "start": match.start(),
            "end": match.end(),
            "payload": match.group(1),
        }
        for match in _COMPLETE_EMPHASIS_RE.finditer(text)
    ]
    underscore_count = text.count("_")
    complete_span_count = len(spans)
    balanced = underscore_count == complete_span_count * 2
    return {
        "underscore_count": underscore_count,
        "complete_span_count": complete_span_count,
        "balanced": balanced,
        "spans": spans,
    }


def compare_emphasis_markup_preservation(source: str, target: str) -> dict[str, Any]:
    """Compare Gutenberg underscore-emphasis structure without comparing payload text.

    A candidate passes only when it preserves the number of underscore markers,
    the number of complete marked spans, and whether the markup was balanced.
    Existing malformed/unbalanced source markup is therefore preserved as a
    shape rather than silently repaired.
    """

    source_shape = _markup_shape(source)
    target_shape = _markup_shape(target)
    failed_checks: list[str] = []
    if source_shape["underscore_count"] != target_shape["underscore_count"]:
        failed_checks.append("underscore_count")
    if source_shape["complete_span_count"] != target_shape["complete_span_count"]:
        failed_checks.append("complete_span_count")
    if source_shape["balanced"] != target_shape["balanced"]:
        failed_checks.append("balanced_state")
    return {
        "contract": EMPHASIS_MARKUP_CONTRACT,
        "source": source_shape,
        "target": target_shape,
        "failed_checks": failed_checks,
        "passed": not failed_checks,
    }
