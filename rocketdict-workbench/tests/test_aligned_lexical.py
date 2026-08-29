from rocketdict_workbench.aligned_lexical import candidate_is_product_eligible, normalize_product_token


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
