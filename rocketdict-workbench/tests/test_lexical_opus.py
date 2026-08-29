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


def test_verb_and_adjective_probes_are_pos_aware() -> None:
    verb = probe_forms("separate", "VERB", "single_word", "ROOT")
    assert verb[0]["kind"] == "verb_argument"
    assert verb[0]["text"] == "to separate something"
    assert probe_forms("thick", "ADJ", "single_word", "acomp")[0]["text"] == "is thick"


def test_verb_mwe_gets_verb_shape_even_when_entry_pos_is_mwe() -> None:
    probes = probe_forms("look at", "MWE", "prepositional_verb", None)
    assert probes[0]["effective_pos"] == "VERB"
    assert probes[0]["pos_reason"] == "verb_mwe_entry_type"


def test_dependency_can_add_auditable_pos_repair() -> None:
    assert effective_probe_pos("VERB", "dobj") == ("NOUN", "dependency_pos_repair")
    probes = probe_forms("colour", "VERB", "single_word", "dobj")
    assert probes[0]["effective_pos"] == "NOUN"


def test_generic_argument_probe_is_reduced_to_lexical_translation() -> None:
    assert clean_probe_target("Разделить что-то", "verb_argument") == ("Разделить", "strip_generic_argument")
    assert clean_probe_target("Взглянуть на что-нибудь.", "verb_argument") == ("Взглянуть на", "strip_generic_argument")


def test_ru_candidate_sanity_is_fail_closed() -> None:
    assert admissible_ru_candidate("inch", "Дюйм") == (True, None)
    assert admissible_ru_candidate("prism", "prism")[0] is False
    assert admissible_ru_candidate("fig", "Рисунок 1")[0] is False
    assert admissible_ru_candidate("colour", "Цвет@ info")[0] is False
    assert admissible_ru_candidate("look at", "Взглянуть", entry_type="prepositional_verb") == (False, "incomplete_multiword_translation")
    assert admissible_ru_candidate("look at", "посмотреть на", entry_type="prepositional_verb") == (True, None)
    assert normalize_lexical_text("  Призма. ") == "призма"


def test_infinitive_dictionary_shape_beats_personal_verb_form() -> None:
    infinitive = provider_confidence(
        9,
        "verb_infinitive",
        base_confidence=0.84,
        effective_pos="VERB",
        target="Посмотреть",
        entry_type="single_word",
    )
    personal = provider_confidence(
        0,
        "verb_argument",
        base_confidence=0.98,
        effective_pos="VERB",
        target="Посмотрим",
        entry_type="single_word",
    )
    assert infinitive > personal


def test_transitive_argument_probe_beats_reflexive_bare_infinitive() -> None:
    transitive = provider_confidence(0, "verb_argument", base_confidence=0.98, effective_pos="VERB", target="Разделить")
    reflexive = provider_confidence(0, "verb_infinitive", base_confidence=0.84, effective_pos="VERB", target="разделиться")
    assert transitive > reflexive
