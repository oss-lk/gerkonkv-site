from __future__ import annotations

"""R-v1 frozen-R0 regression.

After independent R1 exposed occurrence-25's protected-payload/Cyrillic-share
conflict, the local R-v1 probe changed only the measurement surface of the two
existing Cyrillic-share thresholds.  Before integrating that evaluator change,
this regression requires the complete v9 frozen-R0 output to remain identical.

The reference identity is derived from the immutable successful v9 artifact
9656546120 / run 33096154141, before R-v1 existed.
"""

import hashlib
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))

import stage8_ghi_reconstruction_v5 as v5  # noqa: E402
import stage8_ghi_reconstruction_v6 as v6  # noqa: E402
import stage8_protected_language_gate_r1_probe as rv1  # noqa: E402
import stage8_v9_term_rescue_gate as v9  # noqa: E402

OUT = Path("work-stage8-protected-language-r0/evidence")
REFERENCE_RUN = 33096154141
REFERENCE_ARTIFACT = 9656546120
REFERENCE_ARTIFACT_DIGEST = "sha256:c4945967e9a7ee223e39c5779950bf7bb0c6691d48d3b4f4e6c1e081d5eb0ac5"
REFERENCE_SELECTION_SHA = "ea193d5f589dd053b768536c9f8bb4bac90316eed79f5244592357607e02b3fe"
REFERENCE_UNITS_FILE_SHA = "eb948a94037aa72c01eccb6b10c0b97016acbd42d2516e8ee4fba7d2258a1663"
REFERENCE_CANONICAL_SHA = "1f8bb106749ce5785fc036f0d7e51406003c117b527a503382a32e02c15f63c5"


def canonical_bytes(rows: list[dict]) -> bytes:
    text = "".join(
        f"{r['occurrence']}\t{r['mechanism']}\t{r['source']}\t{r['candidate']}\n"
        for r in rows
    )
    return text.encode("utf-8")


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)

    # Change exactly one gate implementation. v8/v9 continue to own all decoder,
    # AST, semantic O-v2 and Q-v1 behaviour.
    v6.strong_quality_gate = rv1.protected_v6_strong_gate
    v5.strong_quality_gate = rv1.protected_v6_strong_gate

    run_error = None
    try:
        v9.main()
    except SystemExit as exc:
        run_error = str(exc)

    units_path = v9.EVIDENCE / "units-v9.jsonl"
    summary_path = v9.EVIDENCE / "stage8-v9-pinned-term-rescue.json"
    rows = []
    raw_sha = None
    canonical_sha = None
    summary = None
    if units_path.exists():
        raw = units_path.read_bytes()
        raw_sha = sha256_bytes(raw)
        rows = [json.loads(x) for x in raw.decode("utf-8").splitlines() if x.strip()]
        canonical_sha = sha256_bytes(canonical_bytes(rows))
    if summary_path.exists():
        summary = json.loads(summary_path.read_text(encoding="utf-8"))

    exact_candidate_identity = bool(
        len(rows) == 80
        and canonical_sha == REFERENCE_CANONICAL_SHA
    )
    # Raw file identity is recorded as a stronger diagnostic but canonical
    # content identity is the acceptance criterion because JSON key-ordering or
    # non-semantic evidence fields must not define translation behaviour.
    passed = bool(
        run_error is None
        and summary is not None
        and summary.get("passed") is True
        and summary.get("selection_sha256") == REFERENCE_SELECTION_SHA
        and exact_candidate_identity
    )

    payload = {
        "schema": "rocketdict-stage8-protected-language-r0-regression/1",
        "status": "PASS" if passed else "FAIL",
        "scope": "NON_PROMOTIONAL exact frozen-R0 behavioural regression",
        "changed_variable": "Cyrillic-share measurement surface only: whole target -> existing v6.strip_protected prose",
        "reference": {
            "v9_run": REFERENCE_RUN,
            "v9_artifact": REFERENCE_ARTIFACT,
            "artifact_digest": REFERENCE_ARTIFACT_DIGEST,
            "selection_sha256": REFERENCE_SELECTION_SHA,
            "units_file_sha256": REFERENCE_UNITS_FILE_SHA,
            "canonical_occurrence_mechanism_source_candidate_sha256": REFERENCE_CANONICAL_SHA,
        },
        "observed": {
            "run_error": run_error,
            "units": len(rows),
            "units_file_sha256": raw_sha,
            "canonical_occurrence_mechanism_source_candidate_sha256": canonical_sha,
            "raw_units_file_identical": raw_sha == REFERENCE_UNITS_FILE_SHA,
            "canonical_candidate_identity": exact_candidate_identity,
            "summary_passed": summary.get("passed") if summary else None,
            "selection_sha256": summary.get("selection_sha256") if summary else None,
            "initial_o2_failed_occurrences": summary.get("parent_v8", {}).get("initial_o2_failed_occurrences") if summary else None,
            "rescued_occurrences": summary.get("rescued_occurrences") if summary else None,
            "final_o2_failed_occurrences": summary.get("final_o2_failed_occurrences") if summary else None,
        },
        "contract": {
            "thresholds_changed": False,
            "decoder_changed": False,
            "AST_changed": False,
            "semantic_gate_changed": False,
            "Q_rescue_changed": False,
            "selection_changed": False,
            "glossary_used": False,
            "target_patch_used": False,
            "original_R1_result_rewritten": False,
            "exact_F96_replaced": False,
        },
        "promotion_allowed": False,
        "passed": passed,
    }
    (OUT / "stage8-protected-language-r0-regression.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(payload, ensure_ascii=False, indent=2), flush=True)
    if not passed:
        raise SystemExit("R-v1 changed frozen R0 behaviour or failed inherited v9 gate")


if __name__ == "__main__":
    main()
