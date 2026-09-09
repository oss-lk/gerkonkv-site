from __future__ import annotations

"""Run the complete punctuation semantic audit for the seven-token variant.

The underlying audit intentionally remains a reusable research surface.  This
wrapper changes only the boundary search window, then rewrites the descriptive
artifact fields so the retained evidence is self-describing and re-hashes the
canonical payload.  Product code and the baseline Product database are never
modified.
"""

import json
import os
from pathlib import Path

import real_translation_full_opticks_punctuation_semantic_audit as audit


if __name__ == "__main__":
    audit.BACKTRACK_TOKENS = 7
    code = audit.main()
    output_root = Path(
        os.environ.get(
            "ROCKETDICT_PUNCTUATION_SEMANTIC_ROOT",
            "work/punctuation-semantic-audit",
        )
    ).resolve()
    output = output_root / "full-opticks-punctuation-semantic-audit.json"
    payload = json.loads(output.read_text(encoding="utf-8"))
    payload["purpose"] = (
        "complete semantic-review surface for every seven-token "
        "punctuation-shadow partition change"
    )
    payload["variant_contract"] = "rocketdict-punctuation-shadow-seven-token-research/1"
    payload.pop("evidence_sha256", None)
    payload["evidence_sha256"] = audit._canonical_sha(payload)
    output.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    raise SystemExit(code)
