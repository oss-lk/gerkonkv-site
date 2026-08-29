from rocketdict_workbench.lexical_eligibility import candidate_is_product_eligible


def _candidate(text: str, pos: str, kind: str = "single_word"):
    return {"type": kind, "tokens": [{"text": text, "pos": pos}]}


def test_content_words_survive_and_function_words_do_not() -> None:
    assert candidate_is_product_eligible(_candidate("glass", "NOUN"))[0]
    assert candidate_is_product_eligible(_candidate("separates", "VERB"))[0]
    assert not candidate_is_product_eligible(_candidate("the", "DET"))[0]
    assert not candidate_is_product_eligible(_candidate("is", "AUX"))[0]
    assert not candidate_is_product_eligible(_candidate("5/62", "NUM", "designation"))[0]


def test_prepositional_mwe_can_survive_function_member() -> None:
    candidate = {
        "type": "prepositional_verb",
        "tokens": [
            {"text": "look", "pos": "VERB"},
            {"text": "at", "pos": "ADP"},
        ],
    }
    assert candidate_is_product_eligible(candidate) == (True, "dictionary_mwe_with_content_head")


def test_generic_noun_chunks_and_numeric_entities_are_not_dictionary_entries() -> None:
    noun_chunk = {
        "type": "noun_chunk",
        "tokens": [
            {"text": "The", "pos": "DET"},
            {"text": "glass", "pos": "NOUN"},
        ],
    }
    numeric_entity = {
        "type": "named_entity",
        "tokens": [
            {"text": "5/62", "pos": "NUM"},
            {"text": "inch", "pos": "NOUN"},
        ],
    }
    assert not candidate_is_product_eligible(noun_chunk)[0]
    assert not candidate_is_product_eligible(numeric_entity)[0]
