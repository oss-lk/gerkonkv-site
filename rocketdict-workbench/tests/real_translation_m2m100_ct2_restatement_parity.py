from __future__ import annotations

"""Read-only CT2 parity/acceptance check for the proven M2M100 arithmetic case.

The historical PyTorch DOE is immutable reference evidence, not an authorized
target patch.  This script reuses the exact source text from that evidence and
asks the newly provisioned pinned CTranslate2 M2M100 runtime for one raw rank0
candidate.  It records exact target parity separately from independent Product
mechanical, emphasis, volume and arithmetic-restatement checks.
"""

import hashlib
import json
import os
from pathlib import Path
import re
from typing import Any

from rocketdict.emphasis_markup import compare_emphasis_markup_preservation
from rocketdict.m2m100_runtime import (
    M2M100_MODEL_SHA256,
    M2M100_REPOSITORY,
    M2M100_REVISION,
    M2M100_SOURCE_LANGUAGE,
    M2M100_TARGET_LANGUAGE,
    M2M100Translator,
    m2m100_status,
)
from rocketdict.translation_rescue import evaluate_rescue_pair

SCHEMA = "rocketdict-m2m100-ct2-arithmetic-restatement-parity/1"
HISTORICAL_SCHEMA = "rocketdict-full-opticks-run20-m2m100-product-restatement-doe/1"
HISTORICAL_EVIDENCE_SHA256 = "e3b508d5bf466d9ca8695fc8f9a4002e51cd4dfd2501f93d46190707db5bf7e7"
EXPECTED_SOURCE_START = 483234
BEAM_SIZE = 6
NUM_HYPOTHESES = 1
MAX_DECODING_LENGTH = 384
MIN_SOURCE_ALPHA_RATIO = 0.60
MAX_SOURCE_ALPHA_RATIO = 1.50
_RESTATEMENT_RE = re.compile(
    r"\b(?P<a>\d[\d,]*)\s*[x×]\s*(?P<b>\d[\d,]*)\s*"
    r"\(\s*that\s+is\s*,\s*above\s+(?P<c>\d[\d,]*)\s*\)",
    re.IGNORECASE,
)


def _canonical_sha(value: Any) -> str:
    raw = json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def _alpha(text: str) -> int:
    return sum(character.isalpha() for character in text)


def _integer(raw: str) -> int:
    return int(raw.replace(",", ""))


def _source_restatement(source: str) -> dict[str, Any] | None:
    matches = list(_RESTATEMENT_RE.finditer(source))
    if len(matches) != 1:
        return None
    match = matches[0]
    a, b, c = (_integer(match.group(name)) for name in ("a", "b", "c"))
    return {
        "a": a,
        "b": b,
        "c": c,
        "product": a * b,
        "arithmetic_verified": a * b == c,
        "source_text": match.group(0),
    }


def _load_historical(path: Path) -> tuple[dict[str, Any], dict[str, Any]]:
    evidence = json.loads(path.read_text(encoding="utf-8"))
    if evidence.get("schema") != HISTORICAL_SCHEMA:
        raise RuntimeError("historical M2M100 restatement schema drift")
    copied = dict(evidence)
    recorded = str(copied.pop("evidence_sha256"))
    actual = _canonical_sha(copied)
    if recorded != HISTORICAL_EVIDENCE_SHA256 or actual != recorded:
        raise RuntimeError("historical M2M100 restatement evidence SHA drift")
    if evidence.get("model_revision") != M2M100_REVISION:
        raise RuntimeError("historical M2M100 revision drift")
    if evidence.get("model_weight_sha256") != M2M100_MODEL_SHA256:
        raise RuntimeError("historical M2M100 weight identity drift")
    matches = [
        dict(record)
        for record in evidence.get("records") or []
        if int(record.get("source_start", -1)) == EXPECTED_SOURCE_START
    ]
    if len(matches) != 1:
        raise RuntimeError(f"historical arithmetic-record cardinality drift: {len(matches)}")
    record = matches[0]
    if record.get("mechanically_admissible") is not True:
        raise RuntimeError("historical arithmetic candidate was not mechanically admissible")
    return evidence, record


def main() -> int:
    root = Path(
        os.environ.get(
            "ROCKETDICT_M2M100_CT2_PARITY_ROOT",
            "work/m2m100-ct2-arithmetic-restatement-parity",
        )
    ).resolve()
    root.mkdir(parents=True, exist_ok=True)
    historical_path = Path(os.environ["ROCKETDICT_M2M100_HISTORICAL_EVIDENCE"]).resolve()
    if not historical_path.is_file():
        raise RuntimeError(f"historical M2M100 evidence is missing: {historical_path}")
    _historical, record = _load_historical(historical_path)

    source = str(record.get("source_text") or "")
    historical_target = str(record.get("candidate_target_text") or "")
    restatement = _source_restatement(source)
    if restatement is None or restatement["arithmetic_verified"] is not True:
        raise RuntimeError("exact historical source no longer has a verified arithmetic restatement")

    status = m2m100_status()
    if status.get("available") is not True:
        raise RuntimeError(f"pinned M2M100 CT2 runtime unavailable: {status}")
    if status.get("repository") != M2M100_REPOSITORY:
        raise RuntimeError("M2M100 runtime repository drift")
    if status.get("revision") != M2M100_REVISION:
        raise RuntimeError("M2M100 runtime revision drift")
    if status.get("model_sha256") != M2M100_MODEL_SHA256:
        raise RuntimeError("M2M100 runtime weights drift")
    if status.get("source_language") != M2M100_SOURCE_LANGUAGE:
        raise RuntimeError("M2M100 runtime source-language drift")
    if status.get("target_language") != M2M100_TARGET_LANGUAGE:
        raise RuntimeError("M2M100 runtime target-language drift")
    if status.get("torch_required_for_inference") is not False:
        raise RuntimeError("M2M100 inference unexpectedly requires torch")

    translator = M2M100Translator(device="cpu", compute_type="float32")
    generated = translator.translate(
        [source],
        beam_size=BEAM_SIZE,
        num_hypotheses=NUM_HYPOTHESES,
        max_decoding_length=MAX_DECODING_LENGTH,
    )
    if len(generated) != 1 or len(generated[0]) != 1:
        raise RuntimeError("M2M100 CT2 rank0 cardinality drift")
    hypothesis = dict(generated[0][0])
    if int(hypothesis.get("rank", -1)) != 0:
        raise RuntimeError("M2M100 CT2 result is not raw rank0")
    target = str(hypothesis.get("text") or "")
    if not target.strip():
        raise RuntimeError("M2M100 CT2 rank0 target is empty")

    verdict = evaluate_rescue_pair(source, target)
    emphasis = compare_emphasis_markup_preservation(source, target)
    source_alpha = _alpha(source)
    ratio = _alpha(target) / source_alpha if source_alpha else 1.0
    ratio_passed = MIN_SOURCE_ALPHA_RATIO <= ratio <= MAX_SOURCE_ALPHA_RATIO
    required_literals = [
        str(restatement["a"]), str(restatement["b"]), str(restatement["c"])
    ]
    numeric = dict((verdict.get("numeric_symbol") or {}).get("numeric") or {})
    observed = dict(numeric.get("observed") or {})
    arithmetic_literals_preserved = bool(
        observed.get(str(restatement["a"]), 0) >= 2
        and observed.get(str(restatement["c"]), 0) >= 1
    )
    accepted = bool(
        verdict.get("strictly_eligible") is True
        and emphasis.get("passed") is True
        and ratio_passed
        and arithmetic_literals_preserved
    )

    evidence: dict[str, Any] = {
        "schema": SCHEMA,
        "purpose": "torch-free CTranslate2 parity and independent acceptance check for pinned M2M100 arithmetic-restatement rank0",
        "promotion_allowed": False,
        "automatic_product_default_allowed": False,
        "semantic_review_required": True,
        "historical_evidence_sha256": HISTORICAL_EVIDENCE_SHA256,
        "source_start": EXPECTED_SOURCE_START,
        "source_text": source,
        "source_restatement": restatement,
        "model": {
            "repository": M2M100_REPOSITORY,
            "revision": M2M100_REVISION,
            "weight_sha256": M2M100_MODEL_SHA256,
            "source_language": M2M100_SOURCE_LANGUAGE,
            "target_language": M2M100_TARGET_LANGUAGE,
            "compute_type": "float32",
            "device": "cpu",
            "asset_manifest_sha256": status.get("asset_manifest_sha256"),
            "asset_payload_tree_sha256": status.get("asset_payload_tree_sha256"),
            "torch_required_for_inference": status.get("torch_required_for_inference"),
        },
        "generation": {
            "beam_size": BEAM_SIZE,
            "num_hypotheses": NUM_HYPOTHESES,
            "max_decoding_length": MAX_DECODING_LENGTH,
            "selected_rank": 0,
        },
        "historical_pytorch_rank0_target": historical_target,
        "ct2_rank0_target": target,
        "exact_target_parity": target == historical_target,
        "ct2_rank0_score": hypothesis.get("score"),
        "mechanical_verdict": verdict,
        "emphasis_markup": emphasis,
        "source_alpha_ratio": ratio,
        "source_alpha_ratio_range": [MIN_SOURCE_ALPHA_RATIO, MAX_SOURCE_ALPHA_RATIO],
        "source_alpha_ratio_passed": ratio_passed,
        "required_arithmetic_literals": required_literals,
        "arithmetic_literals_preserved": arithmetic_literals_preserved,
        "ct2_candidate_accepted": accepted,
        "source_bytes_rewritten": False,
        "model_input_source_rewritten": False,
        "target_rewriting": False,
        "placeholders": False,
        "post_translation_literal_injection": False,
        "corpus_specific_target_patches": False,
        "evaluator_weakened": False,
        "n_best_cherry_picking": False,
        "automatic_n_best_cherry_picking": False,
    }
    evidence["evidence_sha256"] = _canonical_sha(evidence)
    evidence_path = root / "m2m100-ct2-arithmetic-restatement-parity.json"
    evidence_path.write_text(
        json.dumps(evidence, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    summary = {
        "source_start": EXPECTED_SOURCE_START,
        "exact_target_parity": evidence["exact_target_parity"],
        "ct2_candidate_accepted": accepted,
        "arithmetic_literals_preserved": arithmetic_literals_preserved,
        "evidence_sha256": evidence["evidence_sha256"],
    }
    (root / "summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(summary, ensure_ascii=False, sort_keys=True))
    if not accepted:
        raise RuntimeError("M2M100 CT2 arithmetic-restatement rank0 did not satisfy acceptance diagnostics")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
