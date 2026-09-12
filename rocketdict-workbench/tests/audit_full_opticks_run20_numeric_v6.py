from __future__ import annotations

"""Read-only replay of numeric-integrity/6 against the exact persisted run20 DB."""

from collections import Counter
import hashlib
import json
import os
from pathlib import Path
import re
import sqlite3

from rocketdict.numeric_integrity import (
    CONTRACT,
    _NUMBER_WORDS,
    _ORDINAL_WORDS,
    compare_numeric_integrity,
    evaluate_numeric_symbol_pair,
    spelled_numeric_licenses,
)

EXPECTED_DB_SHA256 = "879ea83d0f6803e2fdce609e4ef0dc57017626e4fd0e007d3440b12c7f6f4f2d"
EXPECTED_FAILURE_SEQUENCES = [
    325,
    641,
    642,
    644,
    646,
    750,
    751,
    752,
    1570,
    1580,
    1762,
    1791,
    2293,
    2349,
    2360,
    2378,
    2743,
    2745,
    2893,
    3001,
]
EXPECTED_LICENSE_CHANGE_SEQUENCES = [1791, 2758, 2932, 3106]


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _legacy_v5_licenses(source: str) -> Counter[str]:
    """Exact source-word licence semantics from numeric-integrity/5."""
    words = re.findall(r"(?<![A-Za-z])([A-Za-z]+)(?![A-Za-z])", source.casefold())
    out: Counter[str] = Counter()
    index = 0
    while index < len(words):
        word = words[index]
        ordinal = _ORDINAL_WORDS.get(word)
        if ordinal is not None:
            out[str(ordinal)] += 1
            index += 1
            continue
        value = _NUMBER_WORDS.get(word)
        if value is None:
            index += 1
            continue
        if (
            value >= 20
            and value < 100
            and value % 10 == 0
            and index + 1 < len(words)
            and 0 < (_NUMBER_WORDS.get(words[index + 1]) or 0) < 10
        ):
            out[str(value + _NUMBER_WORDS[words[index + 1]])] += 1
            index += 2
            continue
        out[str(value)] += 1
        index += 1
    return out


def main() -> None:
    database = Path(os.environ["ROCKETDICT_RUN20_NUMERIC_V6_DB"]).resolve()
    if _sha256(database) != EXPECTED_DB_SHA256:
        raise AssertionError("run20 database identity mismatch")
    if CONTRACT != "rocketdict-maintained-numeric-integrity/6":
        raise AssertionError(f"unexpected numeric contract: {CONTRACT}")

    uri = f"file:{database.as_posix()}?mode=ro"
    with sqlite3.connect(uri, uri=True) as connection:
        connection.row_factory = sqlite3.Row
        integrity = str(connection.execute("PRAGMA integrity_check").fetchone()[0])
        foreign_keys = list(connection.execute("PRAGMA foreign_key_check"))
        rows = list(
            connection.execute(
                "SELECT sequence_number, source_start, source_end, source_text, target_text "
                "FROM run_items WHERE run_id=20 ORDER BY sequence_number"
            )
        )

    if integrity != "ok" or foreign_keys:
        raise AssertionError(f"run20 sqlite integrity failure: {integrity=}, fk={len(foreign_keys)}")
    if len(rows) != 3341:
        raise AssertionError(f"unexpected run20 row count: {len(rows)}")

    failures: list[dict[str, object]] = []
    licence_changes: list[dict[str, object]] = []
    row_by_sequence = {int(row["sequence_number"]): row for row in rows}
    for row in rows:
        source = str(row["source_text"] or "")
        target = str(row["target_text"] or "")
        verdict = evaluate_numeric_symbol_pair(source, target)
        if verdict["passed"] is not True:
            failures.append(
                {
                    "sequence_number": int(row["sequence_number"]),
                    "source_start": row["source_start"],
                    "source_end": row["source_end"],
                    "numeric": verdict["numeric"],
                    "symbol_mismatch": verdict["symbol_mismatch"],
                }
            )
        old = _legacy_v5_licenses(source)
        new = spelled_numeric_licenses(source)
        if old != new:
            licence_changes.append(
                {
                    "sequence_number": int(row["sequence_number"]),
                    "source_start": row["source_start"],
                    "source_end": row["source_end"],
                    "v5": dict(old),
                    "v6": dict(new),
                }
            )

    failure_sequences = [int(item["sequence_number"]) for item in failures]
    if failure_sequences != EXPECTED_FAILURE_SEQUENCES:
        raise AssertionError(
            f"numeric /6 changed run20 failure cohort: {failure_sequences}"
        )
    changed_sequences = [int(item["sequence_number"]) for item in licence_changes]
    if changed_sequences != EXPECTED_LICENSE_CHANGE_SEQUENCES:
        raise AssertionError(
            f"unexpected source-word licence blast radius: {changed_sequences}"
        )

    row_1791 = row_by_sequence[1791]
    source_1791 = str(row_1791["source_text"])
    current_1791 = compare_numeric_integrity(source_1791, str(row_1791["target_text"]))
    if current_1791["passed"] is not False:
        raise AssertionError("run20 seq1791 wrong 100,000 unexpectedly passed")
    if current_1791["unlicensed_additions"] != {"100000": 1}:
        raise AssertionError(f"unexpected seq1791 debt: {current_1791['unlicensed_additions']}")
    if spelled_numeric_licenses(source_1791) != Counter({"1000000": 1}):
        raise AssertionError("seq1791 source scale was not composed to 1,000,000")
    if compare_numeric_integrity(source_1791, "1,000,000")["passed"] is not True:
        raise AssertionError("correct 1,000,000 counterfactual is not licensed")
    if compare_numeric_integrity(source_1791, "100,000")["passed"] is not False:
        raise AssertionError("truncated 100,000 counterfactual was incorrectly licensed")

    output = {
        "schema": "rocketdict-full-opticks-run20-numeric-v6-audit/1",
        "database_sha256": EXPECTED_DB_SHA256,
        "translation_run_id": 20,
        "translation_row_count": len(rows),
        "numeric_contract": CONTRACT,
        "failure_count": len(failures),
        "failure_sequences": failure_sequences,
        "legacy_v5_failure_count": 20,
        "pass_fail_drift_from_v5": 0,
        "source_word_licence_change_count": len(licence_changes),
        "source_word_licence_changes": licence_changes,
        "seq1791_current_target_remains_failed": True,
        "seq1791_correct_million_counterfactual_passes": True,
        "sqlite_integrity": integrity,
        "foreign_key_violations": len(foreign_keys),
    }
    output_path = Path(os.environ.get("ROCKETDICT_RUN20_NUMERIC_V6_EVIDENCE", "run20-numeric-v6-audit.json"))
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(output, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(output, ensure_ascii=False, sort_keys=True))


if __name__ == "__main__":
    main()
