from __future__ import annotations

"""Diagnostic segmentation latency probe for independent R1 occurrence 24."""

import json
import os
from pathlib import Path
import re
import sys
import time

sys.path.insert(0, str(Path(__file__).resolve().parent))

from stage8_g_nbest_probe import prepare_model  # noqa: E402
import stage8_ghi_reconstruction_v5 as v5  # noqa: E402

SOURCE = """Since Sir_ Isaac's
Lectiones Opticae, _which he publickly read in the University of_
Cambridge _in the Years 1669, 1670, and 1671, are lately printed, it has
been thought proper to make at the bottom of the Pages several Citations
from thence, where may be found the Demonstrations, which the Author
omitted in these_ Opticks.

       *       *       *       *       *

Transcriber's Note: There are several greek letters used in the
descriptions of the illustrations."""

MODE = os.environ.get("OCC24_SEGMENT_MODE", "full")
OUT = Path("work-stage8-r1-occ24-segment") / MODE
DIVIDER_RE = re.compile(r"(?m)^\s*(?:\*\s*){5}$")
M = DIVIDER_RE.search(SOURCE)
if M is None:
    raise RuntimeError("expected Gutenberg divider not found")

VARIANTS = {
    "before": SOURCE[:M.start()].strip(),
    "divider": SOURCE[M.start():M.end()].strip(),
    "after": SOURCE[M.end():].strip(),
    "without-divider": (SOURCE[:M.start()] + "\n\n" + SOURCE[M.end():]).strip(),
    "full": SOURCE,
}


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    text = VARIANTS[MODE]
    started = time.perf_counter()
    (OUT / "before.json").write_text(json.dumps({
        "mode": MODE,
        "source": text,
        "chars": len(text),
        "words": v5.word_count(text),
    }, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    translator, source_tok, target_tok, identity = prepare_model()
    prepared = time.perf_counter()
    target = v5.translate_batch(translator, source_tok, target_tok, [text])[0]
    ended = time.perf_counter()
    payload = {
        "schema": "rocketdict-stage8-r1-occ24-segment-latency/1",
        "diagnostic_only": True,
        "mode": MODE,
        "source": text,
        "target": target,
        "model_identity": identity,
        "timing_seconds": {
            "prepare_model": prepared - started,
            "translate_beam4": ended - prepared,
            "total": ended - started,
        },
    }
    (OUT / "result.json").write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(payload, ensure_ascii=False, indent=2), flush=True)


if __name__ == "__main__":
    main()
