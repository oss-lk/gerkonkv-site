from rocketdict_workbench.lexical_opus import admissible_ru_candidate, normalize_lexical_text, probe_forms, provider_confidence


def test_probe_order_prefers_dictionary_shape_signal() -> None:
    probes = probe_forms("prism")
    assert probes[0]["kind"] == "titlecase"
    assert probes[0]["text"] == "Prism"
    assert probes[1]["text"] == "prism"


def test_ru_candidate_sanity() -> None:
    assert admissible_ru_candidate("inch", "Дюйм") == (True, None)
    assert admissible_ru_candidate("prism", "prism")[0] is False
    assert admissible_ru_candidate("inch", "62")[0] is False
    assert normalize_lexical_text("  Призма. ") == "призма"
    assert provider_confidence(0, "titlecase") > provider_confidence(0, "lemma")
