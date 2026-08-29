from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterable


class ProductPolicyError(RuntimeError):
    pass


# Curated from the RocketDict lab registry contracts. These are the English
# profiles that provide genuine linguistic analysis rather than tokenization-
# only/code-only fallback behavior. Availability is still checked at runtime.
FULL_EN_NLP_PRIORITY = (
    "stanza-full-en",
    "trankit-full-en",
    "en-trf",
    "en-lg",
    "en-md",
    "en-sm",
)

TRANSLATION_PRIORITY = (
    "opus-en-ru-ct2",
    "nllb-1.3b-en-ru-ct2",
    "nllb-600m-en-ru-ct2",
    "m2m100-1.2b-en-ru-ct2",
    "m2m100-418m-en-ru-ct2",
)

REFERENCE_FREE_QUALITY_PRIORITY = (
    "numeric-symbol-integrity-v1",
    "source-target-structural-quality",
    "source-target-integrity",
)

SENSE_TRANSLATION_PRIORITY = (
    "aligned-local-consensus",
    "project-evidence-consensus",
    "local-snapshots-only",
    "sense_translation-current",
)


@dataclass(frozen=True)
class ProductSelection:
    stage_number: int
    stage_key: str
    implementation_key: str
    reason: str


def _available(implementation: dict[str, Any]) -> bool:
    return bool((implementation.get("availability") or {}).get("available"))


def _eligible(implementation: dict[str, Any]) -> bool:
    return bool(implementation.get("production_eligible")) and not bool(implementation.get("testing_only"))


def _by_key(implementations: Iterable[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    return {str(item.get("implementation_key")): item for item in implementations if item.get("implementation_key")}


def is_code_only_nlp(implementation: dict[str, Any]) -> bool:
    tags = {str(x).casefold() for x in implementation.get("tags") or []}
    label = str(implementation.get("label") or "").casefold()
    return "code-only" in tags or "code-only" in label or "tokenizer" in label and "full" not in label


def select_full_nlp(stage: dict[str, Any], *, require_available: bool) -> ProductSelection:
    implementations = list(stage.get("implementations") or [])
    index = _by_key(implementations)
    for key in FULL_EN_NLP_PRIORITY:
        item = index.get(key)
        if item is None or not _eligible(item):
            continue
        if require_available and not _available(item):
            continue
        if is_code_only_nlp(item):
            continue
        return ProductSelection(int(stage["number"]), str(stage["key"]), key, "full_lemma_pos_nlp")
    available_code_only = [
        str(x.get("implementation_key")) for x in implementations
        if _eligible(x) and _available(x) and is_code_only_nlp(x)
    ]
    suffix = f" Available code-only fallbacks: {available_code_only}." if available_code_only else ""
    raise ProductPolicyError(
        "Product Mode requires an English NLP implementation with real lemma and POS capabilities; "
        "tokenizer-only/code-only NLP is allowed only in Research Mode." + suffix
    )


def _select_priority(
    stage: dict[str, Any],
    priority: tuple[str, ...],
    *,
    require_available: bool,
    reason: str,
) -> ProductSelection | None:
    index = _by_key(stage.get("implementations") or [])
    for key in priority:
        item = index.get(key)
        if item is None or not _eligible(item):
            continue
        if require_available and not _available(item):
            continue
        return ProductSelection(int(stage["number"]), str(stage["key"]), key, reason)
    return None


def select_product_implementation(stage: dict[str, Any], *, require_available: bool = False) -> ProductSelection:
    number = int(stage.get("number") or 0)
    if number == 8:
        return select_full_nlp(stage, require_available=require_available)
    if number == 12:
        selected = _select_priority(stage, TRANSLATION_PRIORITY, require_available=require_available, reason="quality_proven_real_mt_priority")
        if selected:
            return selected
    if number == 20:
        selected = _select_priority(stage, SENSE_TRANSLATION_PRIORITY, require_available=require_available, reason="lexical_evidence_consensus_priority")
        if selected:
            return selected

    implementations = list(stage.get("implementations") or [])
    candidates = [x for x in implementations if _eligible(x) and (not require_available or _available(x))]
    if not candidates:
        raise ProductPolicyError(f"No production implementation is {'available for' if require_available else 'registered for'} stage {number} {stage.get('key')}")
    selected = candidates[0]
    return ProductSelection(number, str(stage.get("key") or ""), str(selected["implementation_key"]), "first_eligible_after_product_rules")


def validate_product_configuration(config: dict[str, Any], lab_manifest: dict[str, Any]) -> list[str]:
    """Fail closed on configurations that can produce technically valid but poor dictionaries."""
    warnings: list[str] = []
    stage_catalog = {int(s.get("number") or 0): s for s in lab_manifest.get("stages") or []}
    configured = {int(s.get("stage_number") or 0): s for s in config.get("stages") or [] if s.get("enabled", True)}

    nlp = configured.get(8)
    if nlp is None:
        raise ProductPolicyError("Product Mode configuration has no enabled Stage 8 NLP analysis")
    nlp_key = str(nlp.get("implementation") or "")
    stage8 = stage_catalog.get(8)
    if stage8 is None:
        raise ProductPolicyError("Lab manifest has no Stage 8 NLP registry")
    index8 = _by_key(stage8.get("implementations") or [])
    item8 = index8.get(nlp_key)
    if item8 is None:
        raise ProductPolicyError(f"Configured NLP implementation is absent from registry: {nlp_key}")
    if nlp_key not in FULL_EN_NLP_PRIORITY or is_code_only_nlp(item8):
        raise ProductPolicyError(
            f"NLP implementation {nlp_key!r} is not accepted for final Product Mode dictionaries; "
            "use Stanza/Trankit/full spaCy or run it only as a Research Mode variant"
        )

    mt = configured.get(12)
    if mt is None:
        raise ProductPolicyError("Product Mode configuration has no enabled Stage 12 real translation")
    mt_key = str(mt.get("implementation") or "")
    if "identity" in mt_key.casefold() or "fake" in mt_key.casefold() or "mock" in mt_key.casefold():
        raise ProductPolicyError(f"Fake/identity MT is forbidden in Product Mode: {mt_key}")
    if mt_key not in TRANSLATION_PRIORITY:
        warnings.append(f"Stage12 uses {mt_key}; this is not in the currently proven Product Mode MT preference list")

    return warnings
