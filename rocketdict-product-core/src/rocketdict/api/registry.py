from __future__ import annotations

import hashlib
import json
from typing import Any

from rocketdict.evidence import cefrj_status, cmudict_status
from rocketdict.runtime import NLP_MODELS, nlp_status, opus_status

REGISTRY_SCHEMA = "rocketdict-product-core-lab-registry/2"
STAGE12_PLANNER_CONTRACT = "rocketdict-stage12-protected-split/6"
STAGE12_STRUCTURAL_LABEL_CONTRACT = "rocketdict-stage12-block-structural-label-opus/1"
NUMERIC_INTEGRITY_CONTRACT = "rocketdict-maintained-numeric-integrity/5"


def _canon(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False)


def _sha(value: Any) -> str:
    return hashlib.sha256(_canon(value).encode("utf-8")).hexdigest()


def _control(key: str, default: Any, *, kind: str = "value") -> dict[str, Any]:
    return {"key": key, "default": default, "kind": kind}


# Static descriptor material. Runtime availability is deliberately excluded from
# descriptor hashes so installing a model/evidence asset does not change operation identity.
_STAGE_DESCRIPTORS: list[dict[str, Any]] = [
    {
        "number": 8,
        "key": "nlp_analysis",
        "label": "Production English NLP",
        "implementations": [
            {
                "implementation_key": key,
                "label": f"spaCy full English NLP ({model})",
                "production_eligible": True,
                "testing_only": False,
                "tags": ["full-nlp", "lemma", "pos", "dependency", "offline"],
                "required_inputs": ["document_version_id"],
                "controls": [],
            }
            for key, model in NLP_MODELS.items()
        ],
    },
    {
        "number": 10,
        "key": "context_enrichment",
        "label": "Context graph enrichment",
        "implementations": [
            {
                "implementation_key": "structural-entity-term-discourse-pronoun-v1",
                "label": "Deterministic structural/entity/context graph v1",
                "production_eligible": True,
                "testing_only": False,
                "tags": ["deterministic", "context", "offline"],
                "required_inputs": ["nlp_run_id"],
                "controls": [],
            }
        ],
    },
    {
        "number": 12,
        "key": "translation_baseline",
        "label": "Real EN-RU machine translation",
        "implementations": [
            {
                "implementation_key": "opus-en-ru-ct2",
                "label": "OPUS EN-RU CTranslate2 Marian",
                "production_eligible": True,
                "testing_only": False,
                "tags": ["real-mt", "offline", "opus", "ctranslate2", "structure-aware-planner", "structural-label-aware"],
                "required_inputs": ["context_run_id"],
                "controls": [
                    _control("allow_download", False),
                    _control("device", "cpu"),
                    _control("compute_type", "float32"),
                    _control("run_assemble", True),
                    _control("planner_contract", STAGE12_PLANNER_CONTRACT),
                    _control("structural_label_contract", STAGE12_STRUCTURAL_LABEL_CONTRACT),
                    _control("plan_preferred_unit_tokens", 64),
                    _control("beam_size", 6),
                    _control("num_hypotheses", 1),
                ],
            }
        ],
    },
    {
        "number": 14,
        "key": "refinement",
        "label": "Glossary/context refinement",
        "implementations": [
            {
                "implementation_key": "glossary_refinement-current",
                "label": "Conservative glossary/context refinement",
                "production_eligible": True,
                "testing_only": False,
                "tags": ["deterministic", "quality-first", "offline"],
                "required_inputs": ["translation_run_id"],
                "controls": [],
            }
        ],
    },
    {
        "number": 15,
        "key": "quality",
        "label": "Hard translation quality gates",
        "implementations": [
            {
                "implementation_key": "rocketdict-numeric-symbol-preservation",
                "label": "Numeric and critical-symbol preservation",
                "production_eligible": True,
                "testing_only": False,
                "tags": ["hard-gate", "reference-free", "versioned-evaluator"],
                "required_inputs": ["assembly_id"],
                "controls": [
                    _control("evaluator_contract", NUMERIC_INTEGRITY_CONTRACT),
                ],
            },
            {
                "implementation_key": "rocketdict-punctuation-preservation",
                "label": "Punctuation preservation",
                "production_eligible": True,
                "testing_only": False,
                "tags": ["hard-gate", "reference-free"],
                "required_inputs": ["assembly_id"],
                "controls": [],
            },
            {
                "implementation_key": "rocketdict-length-ratio-proxy",
                "label": "Source/target length-ratio proxy",
                "production_eligible": True,
                "testing_only": False,
                "tags": ["hard-gate", "reference-free"],
                "required_inputs": ["assembly_id"],
                "controls": [
                    _control("min_ratio", 0.15),
                    _control("max_ratio", 6.0),
                ],
            },
        ],
    },
    {
        "number": 16,
        "key": "finalization",
        "label": "Approved translation finalization",
        "implementations": [
            {
                "implementation_key": "approve-if-clean-finalization",
                "label": "Finalize only after all Stage15 hard gates pass",
                "production_eligible": True,
                "testing_only": False,
                "tags": ["approval", "fail-closed"],
                "required_inputs": ["assembly_id"],
                "controls": [],
            }
        ],
    },
    {
        "number": 17,
        "key": "alignment",
        "label": "Bilingual alignment",
        "implementations": [
            {
                "implementation_key": "deterministic-structural-global",
                "label": "Deterministic structural global alignment",
                "production_eligible": True,
                "testing_only": False,
                "tags": ["alignment", "deterministic"],
                "required_inputs": ["translation_revision_id"],
                "controls": [],
            }
        ],
    },
    {
        "number": 19,
        "key": "sense_induction",
        "label": "Contextual sense induction",
        "implementations": [
            {
                "implementation_key": "deterministic-context-target-graph",
                "label": "Deterministic context/target graph senses",
                "production_eligible": True,
                "testing_only": False,
                "tags": ["sense", "deterministic"],
                "required_inputs": ["extraction_run_id"],
                "controls": [],
            }
        ],
    },
    {
        "number": 20,
        "key": "sense_translation",
        "label": "Contextual lexical sense translation",
        "implementations": [
            {
                "implementation_key": "contextual-lexical-opus-v3",
                "label": "Real OPUS n-best lexical sense translation",
                "production_eligible": True,
                "testing_only": False,
                "tags": ["real-mt", "sense-scoped", "n-best", "offline"],
                "required_inputs": ["sense_induction_run_id"],
                "controls": [
                    _control("beam_size", 12),
                    _control("num_hypotheses", 12),
                    _control("maximum_candidates_per_lemma", 8),
                    _control("probe_batch_size", 64),
                ],
            }
        ],
    },
    {
        "number": 21,
        "key": "cefr",
        "label": "CEFR-J assessment",
        "implementations": [
            {
                "implementation_key": "cefrj-vocabulary-1.5",
                "label": "CEFR-J Vocabulary Profile 1.5",
                "production_eligible": True,
                "testing_only": False,
                "tags": ["external-evidence", "offline", "pinned"],
                "required_inputs": ["lexical_entry_id"],
                "controls": [_control("use_builtin_smoke_sources", False)],
            }
        ],
    },
    {
        "number": 22,
        "key": "pronunciation",
        "label": "Pronunciation evidence",
        "implementations": [
            {
                "implementation_key": "cmudict-production",
                "label": "Exact CMUdict pronunciation",
                "production_eligible": True,
                "testing_only": False,
                "tags": ["cmudict", "exact", "offline", "no-generated-fallback"],
                "required_inputs": ["lexical_entry_id"],
                "controls": [_control("enable_generated_fallback", False)],
            }
        ],
    },
    {
        "number": 23,
        "key": "examples",
        "label": "Sense-scoped examples",
        "implementations": [
            {
                "implementation_key": "examples-current",
                "label": "Document-aligned sense examples",
                "production_eligible": True,
                "testing_only": False,
                "tags": ["sense-scoped", "document-evidence", "offline"],
                "required_inputs": ["lexical_sense_id"],
                "controls": [_control("corpus_snapshots", [])],
            }
        ],
    },
    {
        "number": 24,
        "key": "cards",
        "label": "Immutable dictionary card assembly",
        "implementations": [
            {
                "implementation_key": "cards-current",
                "label": "Product dictionary cards",
                "production_eligible": True,
                "testing_only": False,
                "tags": ["cards", "immutable"],
                "required_inputs": ["lexical_sense_id"],
                "controls": [],
            }
        ],
    },
    {
        "number": 25,
        "key": "export",
        "label": "Product export",
        "implementations": [
            {
                "implementation_key": "export-json",
                "label": "Structured JSON export",
                "production_eligible": True,
                "testing_only": False,
                "tags": ["export", "immutable-set"],
                "required_inputs": ["set_revision_id"],
                "controls": [_control("output_path", "")],
            }
        ],
    },
]


def _descriptor_payload(stage: dict[str, Any], implementation: dict[str, Any]) -> dict[str, Any]:
    return {
        "stage_number": int(stage["number"]),
        "stage_key": str(stage["key"]),
        "implementation_key": str(implementation["implementation_key"]),
        "production_eligible": bool(implementation["production_eligible"]),
        "testing_only": bool(implementation["testing_only"]),
        "tags": list(implementation.get("tags") or []),
        "required_inputs": list(implementation.get("required_inputs") or []),
        "controls": list(implementation.get("controls") or []),
    }


def descriptor_hash(stage_number: int, implementation_key: str) -> str:
    for stage in _STAGE_DESCRIPTORS:
        if int(stage["number"]) != int(stage_number):
            continue
        for implementation in stage["implementations"]:
            if implementation["implementation_key"] == implementation_key:
                return _sha(_descriptor_payload(stage, implementation))
    raise KeyError((stage_number, implementation_key))


def stage_key(stage_number: int) -> str:
    for stage in _STAGE_DESCRIPTORS:
        if int(stage["number"]) == int(stage_number):
            return str(stage["key"])
    raise KeyError(stage_number)


def required_inputs(stage_number: int, implementation_key: str) -> list[str]:
    for stage in _STAGE_DESCRIPTORS:
        if int(stage["number"]) != int(stage_number):
            continue
        for implementation in stage["implementations"]:
            if implementation["implementation_key"] == implementation_key:
                return list(implementation.get("required_inputs") or [])
    raise KeyError((stage_number, implementation_key))


def _availability(stage_number: int, implementation_key: str) -> dict[str, Any]:
    if stage_number == 8:
        return nlp_status(implementation_key)
    if stage_number in {12, 20}:
        return opus_status()
    if stage_number == 21:
        return cefrj_status()
    if stage_number == 22:
        return cmudict_status()
    if stage_number in {10, 14, 15, 16, 17, 19, 23, 24, 25}:
        return {"available": True, "reason": "maintained_product_core", "offline": True}
    return {
        "available": False,
        "reason": "maintained_product_core_operation_not_implemented",
        "offline": True,
    }


def _static_registry_identity() -> dict[str, Any]:
    stages = []
    for stage in _STAGE_DESCRIPTORS:
        implementations = []
        for implementation in stage["implementations"]:
            row = dict(implementation)
            row["descriptor_hash"] = _sha(_descriptor_payload(stage, implementation))
            implementations.append(row)
        stages.append(
            {
                "number": int(stage["number"]),
                "key": str(stage["key"]),
                "label": str(stage["label"]),
                "implementations": implementations,
            }
        )
    return {
        "schema": REGISTRY_SCHEMA,
        "source_language": "en",
        "target_language": "ru",
        "stages": stages,
    }


_STATIC = _static_registry_identity()
REGISTRY_HASH = _sha(_STATIC)


def lab_manifest(*, probe_runtime: bool = False) -> dict[str, Any]:
    stages: list[dict[str, Any]] = []
    for stage in _STATIC["stages"]:
        implementations = []
        for implementation in stage["implementations"]:
            row = dict(implementation)
            row["availability"] = _availability(
                int(stage["number"]), str(implementation["implementation_key"])
            )
            implementations.append(row)
        stages.append({**stage, "implementations": implementations})
    available = sum(
        1
        for stage in stages
        for implementation in stage["implementations"]
        if (implementation.get("availability") or {}).get("available") is True
    )
    total = sum(len(stage["implementations"]) for stage in stages)
    return {
        "schema": REGISTRY_SCHEMA,
        "registry_hash": REGISTRY_HASH,
        "source_language": "en",
        "target_language": "ru",
        "probe_runtime": bool(probe_runtime),
        "summary": {
            "stage_count": len(stages),
            "implementation_count": total,
            "available_implementation_count": available,
        },
        "stages": stages,
    }
