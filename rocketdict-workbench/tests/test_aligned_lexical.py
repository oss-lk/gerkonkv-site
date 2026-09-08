from __future__ import annotations

import json

from rocketdict.lexical import POLICY_KEY as CORE_STAGE18_POLICY_KEY
from rocketdict_workbench.aligned_lexical import (
    POLICY_KEY,
    candidate_is_product_eligible,
    normalize_product_token,
    run_product_aligned_lexical_extraction,
)


def test_stage18_bridge_policy_matches_maintained_core() -> None:
    assert POLICY_KEY == "workbench-aligned-content-pos-v5"
    assert POLICY_KEY == CORE_STAGE18_POLICY_KEY


def test_content_and_dictionary_mwe_policy() -> None:
    assert candidate_is_product_eligible({"type":"single_word","tokens":[{"text":"glass","pos":"NOUN"}]})[0]
    assert not candidate_is_product_eligible({"type":"single_word","tokens":[{"text":"the","pos":"DET"}]})[0]
    assert not candidate_is_product_eligible({"type":"designation","tokens":[{"text":"5/62","pos":"NUM"}]})[0]
    assert candidate_is_product_eligible({"type":"prepositional_verb","tokens":[{"text":"look","pos":"VERB"},{"text":"at","pos":"ADP"}]})[0]
    assert not candidate_is_product_eligible({"type":"named_entity","tokens":[{"text":"The","pos":"DET"},{"text":"Prism","pos":"NOUN"}]})[0]


def test_short_context_object_pos_repair_is_narrow_and_auditable() -> None:
    token, repairs = normalize_product_token({
        "text": "colours", "pos": "VERB", "dependency": "dobj",
        "entity_type": None, "entity_iob": None, "flags": {"is_oov": True}, "source": "saved_nlp",
    })
    assert token["pos"] == "NOUN"
    assert token["flags"]["is_oov"] is False
    assert "verb_object_to_noun" in repairs
    assert "spacy_is_oov_not_unknown_token" in repairs
    assert "workbench_v4" in token["source"]


def test_proper_noun_ner_is_preserved_but_common_word_ner_is_not_entry_type() -> None:
    common, common_repairs = normalize_product_token({
        "text":"inch", "pos":"NOUN", "dependency":"attr", "entity_type":"QUANTITY", "entity_iob":"I", "flags":{}, "source":"saved_nlp",
    })
    assert common["entity_type"] is None
    assert "non_propn_ner_not_entry_type" in common_repairs
    proper, proper_repairs = normalize_product_token({
        "text":"Newton", "pos":"PROPN", "dependency":"nsubj", "entity_type":"PERSON", "entity_iob":"B", "flags":{}, "source":"saved_nlp",
    })
    assert proper["entity_type"] == "PERSON"
    assert "non_propn_ner_not_entry_type" not in proper_repairs


def test_stage18_bridge_uses_maintained_public_api_without_legacy_orm(tmp_path) -> None:
    class Core:
        def __init__(self) -> None:
            self.calls = []

        def _run(self, *args, **kwargs):  # type: ignore[no-untyped-def]
            raise AssertionError("legacy Stage18 subprocess must not execute")

        def api(self, database, *args, timeout=300.0):  # type: ignore[no-untyped-def]
            self.calls.append((database, args, timeout))
            assert args[:3] == ("call", "product.stage18.run", "--params")
            params = json.loads(args[3])
            assert params == {
                "alignment_run_id": 17,
                "parameters": {"probe": "strict"},
                "implementation": POLICY_KEY,
            }
            return {
                "schema": "rocketdict-product-stage18/1",
                "policy": POLICY_KEY,
                "extraction_run_id": 18,
                "stage_result_id": 18,
                "alignment_run_id": 17,
                "nlp_run_id": 8,
                "source_mode": "aligned",
                "eligible_token_count": 3,
                "occurrence_count": 3,
                "lexical_entry_count": 3,
                "coverage_complete": True,
                "uncovered_token_count": 0,
                "cache_hit": False,
            }

    database = tmp_path / "db.sqlite"
    database.touch()
    core = Core()
    payload = run_product_aligned_lexical_extraction(
        core, database, 17, settings={"probe": "strict"}
    )

    assert payload["extraction_run_id"] == 18
    assert len(core.calls) == 1
    assert core.calls[0][0] == database.resolve()
    assert core.calls[0][2] == 600
