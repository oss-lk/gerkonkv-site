from __future__ import annotations

import pytest

from rocketdict.api.registry import STAGE12_REQUEST_BATCH_CONTRACT, lab_manifest
from rocketdict.stages import StageExecutionError
from rocketdict.translation_stage import (
    DEFAULT_REQUEST_BATCH_SIZE,
    MAX_REQUEST_BATCH_SIZE,
    REQUEST_BATCH_CONTRACT,
    _translate_primary_request_batches,
)


class _FakeTranslator:
    def __init__(self, *, drift: bool = False) -> None:
        self.drift = drift
        self.calls: list[list[str]] = []

    def translate(
        self,
        texts: list[str],
        *,
        beam_size: int,
        num_hypotheses: int,
        max_decoding_length: int,
    ) -> list[list[dict]]:
        assert beam_size == 6
        assert num_hypotheses == 1
        assert max_decoding_length == 512
        self.calls.append(list(texts))
        rows = [[{"rank": 0, "text": f"target:{text}"}] for text in texts]
        return rows[:-1] if self.drift and rows else rows


def test_bounded_primary_batches_preserve_request_order_and_cardinality() -> None:
    translator = _FakeTranslator()
    texts = [f"source-{index}" for index in range(101)]
    rows = _translate_primary_request_batches(
        translator,
        texts,
        batch_size=48,
        beam_size=6,
        num_hypotheses=1,
        max_decoding_length=512,
    )
    assert [len(batch) for batch in translator.calls] == [48, 48, 5]
    assert [row[0]["text"] for row in rows] == [f"target:{text}" for text in texts]


def test_bounded_primary_batches_fail_closed_on_backend_cardinality_drift() -> None:
    with pytest.raises(StageExecutionError, match="batch cardinality"):
        _translate_primary_request_batches(
            _FakeTranslator(drift=True),
            ["one", "two"],
            batch_size=48,
            beam_size=6,
            num_hypotheses=1,
            max_decoding_length=512,
        )


def test_bounded_primary_batches_reject_unbounded_sizes() -> None:
    with pytest.raises(StageExecutionError, match="batch size"):
        _translate_primary_request_batches(
            _FakeTranslator(),
            ["one"],
            batch_size=MAX_REQUEST_BATCH_SIZE + 1,
            beam_size=6,
            num_hypotheses=1,
            max_decoding_length=512,
        )


def test_registry_publishes_bounded_stage12_execution_identity() -> None:
    assert REQUEST_BATCH_CONTRACT == "rocketdict-stage12-bounded-request-batch/1"
    assert STAGE12_REQUEST_BATCH_CONTRACT == REQUEST_BATCH_CONTRACT
    assert DEFAULT_REQUEST_BATCH_SIZE == 48
    manifest = lab_manifest(probe_runtime=False)
    stage12 = next(row for row in manifest["stages"] if int(row["number"]) == 12)
    implementation = next(
        row
        for row in stage12["implementations"]
        if row["implementation_key"] == "opus-en-ru-ct2"
    )
    controls = {row["key"]: row.get("default") for row in implementation["controls"]}
    assert controls["request_batch_contract"] == REQUEST_BATCH_CONTRACT
    assert controls["request_batch_size"] == 48
    assert "bounded-batch" in implementation["tags"]
