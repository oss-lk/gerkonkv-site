from __future__ import annotations

import json
from types import SimpleNamespace

import pytest

from rocketdict_workbench.cli import parser
from rocketdict_workbench.sense_translation_arbitration import (
    POLICY_KEY,
    arbitrate_lexical_primaries,
    desired_primary_map,
    write_arbitration_evidence,
)


def _provider() -> dict:
    return {
        "snapshot": {
            "entries": {
                "plane": [
                    {
                        "translation": "Плоскость.",
                        "confidence": 0.97,
                        "target_pos": "NOUN",
                    }
                ]
            }
        }
    }


def _stage20() -> dict:
    return {
        "results": [
            {
                "sense_id": 17,
                "selection_revision_id": 31,
                "lemma": "Plane",
                "normalized_lemma": "plane",
            }
        ]
    }


def test_desired_primary_map_uses_frozen_provider_headword() -> None:
    rows = desired_primary_map(_provider(), _stage20())
    assert rows == [
        {
            "sense_id": 17,
            "automatic_selection_revision_id": 31,
            "lemma": "plane",
            "desired_translation": "Плоскость.",
            "desired_normalized": "плоскость",
            "provider_confidence": 0.97,
            "provider_target_pos": "NOUN",
        }
    ]


def test_desired_primary_map_fails_closed_when_provider_has_no_candidate() -> None:
    with pytest.raises(RuntimeError, match="has no candidates"):
        desired_primary_map({"snapshot": {"entries": {}}}, _stage20())


class _FakeCore:
    def __init__(self, payload: dict) -> None:
        self.payload = payload
        self.command = None
        self.timeout = None

    def _run(self, command, timeout):  # type: ignore[no-untyped-def]
        self.command = command
        self.timeout = timeout
        return SimpleNamespace(stdout=json.dumps(self.payload, ensure_ascii=False))

    def _parse_json(self, stdout, *, context):  # type: ignore[no-untyped-def]
        assert context == "Stage20 lexical primary arbitration"
        return json.loads(stdout)


def test_arbitration_wrapper_requires_exact_approved_coverage(tmp_path) -> None:
    core = _FakeCore(
        {
            "policy": POLICY_KEY,
            "results": [
                {
                    "sense_id": 17,
                    "selection_revision_id": 44,
                    "candidate_id": 9,
                    "translation": "плоскость",
                    "status": "approved",
                    "cache_hit": False,
                    "model_evidence_id": 12,
                }
            ],
        }
    )
    result = arbitrate_lexical_primaries(core, tmp_path / "rocketdict.sqlite", _provider(), _stage20())
    assert result["policy"] == POLICY_KEY
    assert result["results"][0]["translation"] == "плоскость"
    assert core.timeout == 600
    requests = json.loads(core.command[3])
    assert requests[0]["sense_id"] == 17
    assert requests[0]["desired_normalized"] == "плоскость"


def test_arbitration_wrapper_rejects_wrong_sense_order(tmp_path) -> None:
    core = _FakeCore(
        {
            "results": [
                {
                    "sense_id": 18,
                    "translation": "плоскость",
                    "status": "approved",
                }
            ]
        }
    )
    with pytest.raises(RuntimeError, match="sense-order mismatch"):
        arbitrate_lexical_primaries(core, tmp_path / "rocketdict.sqlite", _provider(), _stage20())


def test_arbitration_wrapper_rejects_changed_primary(tmp_path) -> None:
    core = _FakeCore(
        {
            "results": [
                {
                    "sense_id": 17,
                    "translation": "план",
                    "status": "approved",
                }
            ]
        }
    )
    with pytest.raises(RuntimeError, match="changed the frozen lexical primary"):
        arbitrate_lexical_primaries(core, tmp_path / "rocketdict.sqlite", _provider(), _stage20())


def test_arbitration_evidence_is_durable_json(tmp_path) -> None:
    target = tmp_path / "evidence" / "arbitration.json"
    payload = {"policy": POLICY_KEY, "requests": [{"sense_id": 17}], "results": [{"sense_id": 17}]}
    assert write_arbitration_evidence(target, payload) == target.resolve()
    assert json.loads(target.read_text(encoding="utf-8")) == payload


def test_cli_exposes_explicit_stage20_arbitration_flags() -> None:
    args = parser().parse_args(
        [
            "lexical-opus",
            "/tmp/project",
            "--model-path",
            "/tmp/model",
            "--revision",
            "opus-r1",
            "--archive-sha256",
            "a" * 64,
            "--source-uri",
            "https://example.invalid/opus.zip",
            "--apply-stage20",
            "--arbitrate-primaries",
            "--arbitration-output",
            "/tmp/arbitration.json",
        ]
    )
    assert args.apply_stage20 is True
    assert args.arbitrate_primaries is True
    assert str(args.arbitration_output).endswith("arbitration.json")
