from rocketdict_workbench.lexical_opus import (
    admissible_ru_candidate,
    clean_probe_target,
    effective_probe_pos,
    normalize_lexical_text,
    probe_forms,
    provider_confidence,
)


def test_noun_probe_prefers_dictionary_shape_signal() -> None:
    probes = probe_forms("prism", "NOUN", "single_word", None)
    assert probes[0]["kind"] == "titlecase"
    assert probes[0]["text"] == "Prism"
    assert probes[1]["text"] == "prism"


def test_verb_and_adjective_probes_are_pos_aware() -> None:
    verb = probe_forms("separate", "VERB", "single_word", "ROOT")
    assert verb[0]["kind"] == "verb_argument"
    assert verb[0]["text"] == "to separate something"
    adjective = probe_forms("thick", "ADJ", "single_word", "acomp")
    assert adjective[0]["kind"] == "adjective_copula"
    assert adjective[0]["text"] == "is thick"


def test_dependency_can_add_auditable_pos_repair() -> None:
    assert effective_probe_pos("VERB", "dobj") == ("NOUN", "dependency_pos_repair")
    probes = probe_forms("colour", "VERB", "single_word", "dobj")
    assert probes[0]["kind"] == "titlecase"
    assert probes[0]["effective_pos"] == "NOUN"


def test_generic_argument_probe_is_reduced_to_lexical_translation() -> None:
    assert clean_probe_target("Разделить что-то", "verb_argument") == ("Разделить", "strip_generic_argument")
    assert clean_probe_target("Взглянуть на что-нибудь.", "verb_argument") == ("Взглянуть на", "strip_generic_argument")


def test_ru_candidate_sanity_and_infinitive_bonus() -> None:
    assert admissible_ru_candidate("inch", "Дюйм") == (True, None)
    assert admissible_ru_candidate("prism", "prism")[0] is False
    assert admissible_ru_candidate("inch", "62")[0] is False
    assert normalize_lexical_text("  Призма. ") == "призма"
    assert provider_confidence(2, "verb_argument", base_confidence=0.98, effective_pos="VERB", target="Разделить") > provider_confidence(0, "verb_argument", base_confidence=0.98, effective_pos="VERB", target="Раздели")
