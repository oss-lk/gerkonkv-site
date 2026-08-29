from __future__ import annotations

import csv
import hashlib
import json
from pathlib import Path
import sys

SOURCE_URL = "https://raw.githubusercontent.com/openlanguageprofiles/olp-en-cefrj/master/cefrj-vocabulary-profile-1.5.csv"
EXPECTED_SHA256 = "b0dd3c635f1c9a4fdf1490c7e5b7c48e8bbe55b652ad0c9860a95f98e10ae498"
EXPECTED_HEADER = ["headword", "pos", "CEFR", "CoreInventory 1", "CoreInventory 2", "Threshold"]
KNOWN = {
    ("abandon", "verb"): "B1",
    ("ability", "noun"): "A2",
    ("able", "adjective"): "B1",
}


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def main() -> None:
    path = Path(sys.argv[1]).resolve()
    actual = sha256(path)
    if actual != EXPECTED_SHA256:
        raise RuntimeError(f"CEFR-J SHA mismatch: {actual} != {EXPECTED_SHA256}")
    rows = []
    with path.open("r", encoding="utf-8-sig", newline="") as fh:
        reader = csv.DictReader(fh)
        if reader.fieldnames != EXPECTED_HEADER:
            raise RuntimeError(f"Unexpected CEFR-J header: {reader.fieldnames!r}")
        for row in reader:
            rows.append(row)
    if len(rows) < 1000:
        raise RuntimeError(f"CEFR-J asset is unexpectedly small: {len(rows)} rows")
    index = {(r["headword"].casefold(), r["pos"].casefold()): r["CEFR"] for r in rows}
    for key, expected in KNOWN.items():
        if index.get(key) != expected:
            raise RuntimeError(f"CEFR-J known-row mismatch for {key}: {index.get(key)!r} != {expected!r}")
    manifest = {
        "schema": "rocketdict-workbench-cefrj-asset/1",
        "dataset": "CEFR-J Vocabulary Profile 1.5",
        "source_url": SOURCE_URL,
        "bytes": path.stat().st_size,
        "sha256": actual,
        "row_count": len(rows),
        "header": EXPECTED_HEADER,
        "terms": "Research and commercial use permitted without charge with proper citation; copyright Tono Laboratory at TUFS. Redistribution right not assumed by Workbench.",
        "redistributed_by_workbench": False,
        "runtime_processing_network_required": False,
    }
    out = Path("rocketdict-workbench-cefrj-verification")
    out.mkdir(exist_ok=True)
    (out / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(manifest, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
