from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .core import RocketDictCore

POLICY_KEY = "workbench-aligned-content-pos-v4"
CONTENT_POS = {"NOUN", "PROPN", "VERB", "ADJ", "ADV"}
FUNCTION_POS = {"DET", "AUX", "ADP", "PRON", "PART", "CCONJ", "SCONJ", "PUNCT", "SPACE", "SYM", "NUM"}
OBJECT_DEPENDENCIES = {"dobj", "obj", "pobj"}
ALLOWED_MWE_TYPES = {
    "phrasal_verb", "prepositional_verb", "idiom", "collocation",
    "compound_term", "technical_term", "grammar_expression",
    "discontinuous_expression",
}


def normalize_product_token(token: dict[str, Any]) -> tuple[dict[str, Any], list[str]]:
    """Apply narrow Product-Mode repairs while preserving the original evidence trail."""
    out = dict(token)
    out["flags"] = dict(token.get("flags") or {})
    repairs: list[str] = []
    pos = str(out.get("pos") or "X").upper()
    dep = str(out.get("dependency") or "").casefold()
    text = str(out.get("text") or "")

    # en_core_web_sm can occasionally tag a direct object as VERB in very
    # short subtitle-like sentences. Restrict the repair to object dependency
    # roles; do not globally rewrite ambiguous verbs.
    if pos == "VERB" and dep in OBJECT_DEPENDENCIES:
        out["pos"] = "NOUN"
        pos = "NOUN"
        repairs.append("verb_object_to_noun")

    # spaCy is_oov means "not in the model's finite vector vocabulary", not
    # "unknown English lexical item". Treating it as EntryType.UNKNOWN_TOKEN
    # is a category error for normal alphabetic content words.
    if pos in CONTENT_POS and text.isalpha() and bool(out["flags"].get("is_oov")):
        out["flags"]["is_oov"] = False
        repairs.append("spacy_is_oov_not_unknown_token")

    # A lower-case common noun that participates in an NER span should remain
    # a lexical noun when extracted as a single word. Proper nouns retain NER.
    if out.get("entity_type") and pos != "PROPN":
        out["flags"]["workbench_original_entity_type"] = out.get("entity_type")
        out["entity_type"] = None
        out["entity_iob"] = None
        repairs.append("non_propn_ner_not_entry_type")

    if repairs:
        base = str(out.get("source") or "saved_nlp")
        out["source"] = base + "+workbench_v4:" + ",".join(repairs)
    return out, repairs


def candidate_is_product_eligible(candidate: dict[str, Any]) -> tuple[bool, str]:
    tokens = list(candidate.get("tokens") or [])
    if not tokens:
        return False, "no_token_evidence"
    if len(tokens) == 1:
        token = tokens[0]
        pos = str(token.get("pos") or "X")
        text = str(token.get("text") or "")
        if pos in CONTENT_POS:
            return True, "content_pos"
        if candidate.get("type") == "abbreviation" and text.isalpha() and text.upper() == text and 2 <= len(text) <= 8:
            return True, "alphabetic_abbreviation"
        if pos in FUNCTION_POS:
            return False, f"non_dictionary_pos:{pos}"
        if any(ch.isdigit() for ch in text):
            return False, "numeric_or_designation"
        return False, f"unsupported_pos:{pos}"
    kind = str(candidate.get("type") or "")
    if kind not in ALLOWED_MWE_TYPES:
        return False, f"non_dictionary_mwe:{kind}"
    if any(str(token.get("pos") or "X") in CONTENT_POS for token in tokens):
        return True, "dictionary_mwe_with_content_head"
    return False, "mwe_without_content_pos"


def _helper_code() -> str:
    """Stable Stage18 runner identity material retained for Workbench evidence.

    Stage18 execution/storage now belongs to the maintained Product Core.  The
    old helper embedded the historical SQLAlchemy ORM implementation and made
    the unified Product runtime depend on a package the maintained core neither
    needs nor declares.  Keep a deterministic marker here because
    ``post_gate_pipeline`` includes it in its frozen runner identity, but never
    execute a second implementation of Stage18 from Workbench.
    """
    return "maintained-core-api:product.stage18.run/1;policy=" + POLICY_KEY


def run_product_aligned_lexical_extraction(
    core: RocketDictCore,
    database: Path | str,
    alignment_run_id: int,
    *,
    settings: dict[str, Any] | None = None,
    actor: str = "rocketdict-workbench:aligned-content-pos-v4",
) -> dict[str, Any]:
    """Execute the validated Stage18 policy through the maintained public API.

    ``actor`` remains in the compatibility signature because older Workbench
    callers supplied it.  It is deliberately not sent to Product Core: the
    maintained Stage18 operation is identified by its public operation,
    implementation key, input identity and parameter hash rather than by the
    historical ORM actor string.
    """
    del actor
    database_path = Path(database).expanduser().resolve()
    params = {
        "alignment_run_id": int(alignment_run_id),
        "parameters": dict(settings or {}),
        "implementation": POLICY_KEY,
    }
    payload = dict(
        core.api(
            database_path,
            "call",
            "product.stage18.run",
            "--params",
            json.dumps(params, ensure_ascii=False, separators=(",", ":")),
            timeout=600,
        )
    )
    if str(payload.get("policy") or "") != POLICY_KEY:
        raise RuntimeError(
            f"Product lexical extraction policy drift: {payload.get('policy')!r} != {POLICY_KEY!r}"
        )
    if int(payload.get("alignment_run_id") or 0) != int(alignment_run_id):
        raise RuntimeError("Product lexical extraction returned a different alignment_run_id")
    if not payload.get("coverage_complete") or int(payload.get("uncovered_token_count") or 0) != 0:
        raise RuntimeError(f"Product lexical coverage is incomplete: {payload}")
    if payload.get("source_mode") != "aligned":
        raise RuntimeError(f"Product lexical extraction unexpectedly lost alignment: {payload.get('source_mode')}")
    return payload
