from rocketdict_workbench.aligned_lexical import candidate_is_product_eligible


def test_content_and_dictionary_mwe_policy() -> None:
    assert candidate_is_product_eligible({"type":"single_word","tokens":[{"text":"glass","pos":"NOUN"}]})[0]
    assert not candidate_is_product_eligible({"type":"single_word","tokens":[{"text":"the","pos":"DET"}]})[0]
    assert not candidate_is_product_eligible({"type":"designation","tokens":[{"text":"5/62","pos":"NUM"}]})[0]
    assert candidate_is_product_eligible({"type":"prepositional_verb","tokens":[{"text":"look","pos":"VERB"},{"text":"at","pos":"ADP"}]})[0]
    assert not candidate_is_product_eligible({"type":"named_entity","tokens":[{"text":"The","pos":"DET"},{"text":"Prism","pos":"NOUN"}]})[0]
