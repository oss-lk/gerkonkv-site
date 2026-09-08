from __future__ import annotations

"""One-shot, assertion-heavy migration for bounded Product Stage12 request batches.

The full contiguous Opticks Product Stage12 audit reached the first complete
planner-v7 inference attempt only after structural boundary fixes.  Two
independent hosted runners then terminated the monolithic CTranslate2 request
batch with exit 143 / runner shutdown.  This migration changes only execution
batching: planner/source units and raw model requests remain byte-for-byte the
same and their output order is preserved.
"""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TRANSLATION = ROOT / "rocketdict-product-core/src/rocketdict/translation_stage.py"
REGISTRY = ROOT / "rocketdict-product-core/src/rocketdict/api/registry.py"
TEST = ROOT / "rocketdict-product-core/tests/test_translation_stage_batching.py"
HEAVY = ROOT / ".github/workflows/rocketdict-full-opticks-numeric-stress.yml"


def replace_once(text: str, old: str, new: str, *, label: str) -> str:
    count = text.count(old)
    if count != 1:
        raise RuntimeError(f"{label}: expected exactly one match, found {count}")
    return text.replace(old, new, 1)


def migrate_translation() -> None:
    text = TRANSLATION.read_text(encoding="utf-8")
    text = replace_once(
        text,
        'labels stay ordinary prose; table spans remain unchanged.\n"""',
        'labels stay ordinary prose; table spans remain unchanged.\n\n'
        'Primary OPUS requests are executed in bounded, ordered batches. This is an\n'
        'execution/resource contract only: it does not change planner-v7 source units,\n'
        'model inputs, generation settings, raw hypotheses or output ordering.\n"""',
        label="translation module doc",
    )
    text = replace_once(
        text,
        'PLANNER_CONTRACT = "rocketdict-stage12-protected-split/7"\n',
        'PLANNER_CONTRACT = "rocketdict-stage12-protected-split/7"\n'
        'REQUEST_BATCH_CONTRACT = "rocketdict-stage12-bounded-request-batch/1"\n'
        'DEFAULT_REQUEST_BATCH_SIZE = 48\n'
        'MAX_REQUEST_BATCH_SIZE = 128\n',
        label="translation constants",
    )
    anchor = '''def _translate_structural_label_units(\n    translator: OpusTranslator,\n    labels: dict[int, StructuralLabel],\n) -> dict[str, Any]:\n'''
    helper = '''def _translate_primary_request_batches(\n    translator: OpusTranslator,\n    texts: list[str],\n    *,\n    batch_size: int,\n    beam_size: int,\n    num_hypotheses: int,\n    max_decoding_length: int,\n) -> list[list[dict[str, Any]]]:\n    \"\"\"Translate primary Stage12 requests in bounded order-preserving batches.\n\n    Batch boundaries are not source/planner boundaries and never enter target\n    assembly. A backend cardinality drift fails closed before any result can be\n    persisted.\n    \"\"\"\n    if batch_size < 1 or batch_size > MAX_REQUEST_BATCH_SIZE:\n        raise StageExecutionError(\n            f\"Stage12 request batch size must be in 1..{MAX_REQUEST_BATCH_SIZE}\"\n        )\n    output: list[list[dict[str, Any]]] = []\n    for start in range(0, len(texts), batch_size):\n        batch = texts[start : start + batch_size]\n        translated = translator.translate(\n            batch,\n            beam_size=beam_size,\n            num_hypotheses=num_hypotheses,\n            max_decoding_length=max_decoding_length,\n        )\n        if len(translated) != len(batch):\n            raise StageExecutionError(\n                \"OPUS returned a different Stage12 request batch cardinality\"\n            )\n        output.extend(translated)\n    if len(output) != len(texts):\n        raise StageExecutionError(\n            \"OPUS returned a different Stage12 total request cardinality\"\n        )\n    return output\n\n\n'''
    if helper not in text:
        text = replace_once(text, anchor, helper + anchor, label="batch helper insertion")
    text = replace_once(
        text,
        '''    beam_size = int(effective.get("beam_size") or 6)\n    num_hypotheses = int(effective.get("num_hypotheses") or 1)\n\n    with connect(database, readonly=True) as connection:\n''',
        '''    beam_size = int(effective.get("beam_size") or 6)\n    num_hypotheses = int(effective.get("num_hypotheses") or 1)\n    requested_batch_contract = str(\n        effective.get("request_batch_contract") or REQUEST_BATCH_CONTRACT\n    )\n    if requested_batch_contract != REQUEST_BATCH_CONTRACT:\n        raise StageExecutionError(\n            f"Unsupported Stage12 request batch contract {requested_batch_contract!r}; "\n            f"expected {REQUEST_BATCH_CONTRACT!r}"\n        )\n    effective["request_batch_contract"] = REQUEST_BATCH_CONTRACT\n    raw_batch_size = effective.get("request_batch_size", DEFAULT_REQUEST_BATCH_SIZE)\n    if isinstance(raw_batch_size, bool):\n        raise StageExecutionError("Stage12 request_batch_size must be an integer")\n    try:\n        request_batch_size = int(raw_batch_size)\n    except (TypeError, ValueError) as exc:\n        raise StageExecutionError("Stage12 request_batch_size must be an integer") from exc\n    if request_batch_size < 1 or request_batch_size > MAX_REQUEST_BATCH_SIZE:\n        raise StageExecutionError(\n            f"Stage12 request_batch_size must be in 1..{MAX_REQUEST_BATCH_SIZE}"\n        )\n    effective["request_batch_size"] = request_batch_size\n\n    with connect(database, readonly=True) as connection:\n''',
        label="batch parameter validation",
    )
    text = replace_once(
        text,
        '''        translator = OpusTranslator(device=device, compute_type=compute_type)\n        translated = translator.translate(\n            request_texts,\n            beam_size=beam_size,\n            num_hypotheses=num_hypotheses,\n            max_decoding_length=max(128, max(preferred, max_request_tokens) * 8),\n        ) if request_texts else []\n        if len(translated) != len(request_refs):\n            raise StageExecutionError("OPUS returned a different Stage12 request cardinality")\n''',
        '''        translator = OpusTranslator(device=device, compute_type=compute_type)\n        translated = _translate_primary_request_batches(\n            translator,\n            request_texts,\n            batch_size=request_batch_size,\n            beam_size=beam_size,\n            num_hypotheses=num_hypotheses,\n            max_decoding_length=max(128, max(preferred, max_request_tokens) * 8),\n        ) if request_texts else []\n        if len(translated) != len(request_refs):\n            raise StageExecutionError("OPUS returned a different Stage12 request cardinality")\n''',
        label="bounded primary translation",
    )
    text = replace_once(
        text,
        '''            "compute_type": compute_type,\n            "planner_contract": PLANNER_CONTRACT,\n''',
        '''            "compute_type": compute_type,\n            "planner_contract": PLANNER_CONTRACT,\n            "request_batch_contract": REQUEST_BATCH_CONTRACT,\n            "request_batch_size": request_batch_size,\n            "primary_model_batch_count": (\n                (len(request_texts) + request_batch_size - 1) // request_batch_size\n                if request_texts\n                else 0\n            ),\n''',
        label="batch output provenance",
    )
    TRANSLATION.write_text(text, encoding="utf-8")


def migrate_registry() -> None:
    text = REGISTRY.read_text(encoding="utf-8")
    text = replace_once(
        text,
        'STAGE12_STRUCTURAL_LABEL_CONTRACT = "rocketdict-stage12-block-structural-label-opus/1"\n',
        'STAGE12_STRUCTURAL_LABEL_CONTRACT = "rocketdict-stage12-block-structural-label-opus/1"\n'
        'STAGE12_REQUEST_BATCH_CONTRACT = "rocketdict-stage12-bounded-request-batch/1"\n',
        label="registry batch contract",
    )
    text = replace_once(
        text,
        '"tags": ["real-mt", "offline", "opus", "ctranslate2", "structure-aware-planner", "structural-label-aware"],',
        '"tags": ["real-mt", "offline", "opus", "ctranslate2", "structure-aware-planner", "structural-label-aware", "bounded-batch"],',
        label="registry tags",
    )
    text = replace_once(
        text,
        '''                    _control("structural_label_contract", STAGE12_STRUCTURAL_LABEL_CONTRACT),\n                    _control("plan_preferred_unit_tokens", 64),\n''',
        '''                    _control("structural_label_contract", STAGE12_STRUCTURAL_LABEL_CONTRACT),\n                    _control("request_batch_contract", STAGE12_REQUEST_BATCH_CONTRACT),\n                    _control("request_batch_size", 48),\n                    _control("plan_preferred_unit_tokens", 64),\n''',
        label="registry controls",
    )
    REGISTRY.write_text(text, encoding="utf-8")


def write_test() -> None:
    TEST.write_text(
        '''from __future__ import annotations\n\nimport pytest\n\nfrom rocketdict.api.registry import STAGE12_REQUEST_BATCH_CONTRACT, lab_manifest\nfrom rocketdict.stages import StageExecutionError\nfrom rocketdict.translation_stage import (\n    DEFAULT_REQUEST_BATCH_SIZE,\n    MAX_REQUEST_BATCH_SIZE,\n    REQUEST_BATCH_CONTRACT,\n    _translate_primary_request_batches,\n)\n\n\nclass _FakeTranslator:\n    def __init__(self, *, drift: bool = False) -> None:\n        self.drift = drift\n        self.calls: list[list[str]] = []\n\n    def translate(\n        self,\n        texts: list[str],\n        *,\n        beam_size: int,\n        num_hypotheses: int,\n        max_decoding_length: int,\n    ) -> list[list[dict]]:\n        assert beam_size == 6\n        assert num_hypotheses == 1\n        assert max_decoding_length == 512\n        self.calls.append(list(texts))\n        rows = [[{"rank": 0, "text": f"target:{text}"}] for text in texts]\n        return rows[:-1] if self.drift and rows else rows\n\n\ndef test_bounded_primary_batches_preserve_request_order_and_cardinality() -> None:\n    translator = _FakeTranslator()\n    texts = [f"source-{index}" for index in range(101)]\n    rows = _translate_primary_request_batches(\n        translator,\n        texts,\n        batch_size=48,\n        beam_size=6,\n        num_hypotheses=1,\n        max_decoding_length=512,\n    )\n    assert [len(batch) for batch in translator.calls] == [48, 48, 5]\n    assert [row[0]["text"] for row in rows] == [f"target:{text}" for text in texts]\n\n\ndef test_bounded_primary_batches_fail_closed_on_backend_cardinality_drift() -> None:\n    with pytest.raises(StageExecutionError, match="batch cardinality"):\n        _translate_primary_request_batches(\n            _FakeTranslator(drift=True),\n            ["one", "two"],\n            batch_size=48,\n            beam_size=6,\n            num_hypotheses=1,\n            max_decoding_length=512,\n        )\n\n\ndef test_bounded_primary_batches_reject_unbounded_sizes() -> None:\n    with pytest.raises(StageExecutionError, match="batch size"):\n        _translate_primary_request_batches(\n            _FakeTranslator(),\n            ["one"],\n            batch_size=MAX_REQUEST_BATCH_SIZE + 1,\n            beam_size=6,\n            num_hypotheses=1,\n            max_decoding_length=512,\n        )\n\n\ndef test_registry_publishes_bounded_stage12_execution_identity() -> None:\n    assert REQUEST_BATCH_CONTRACT == "rocketdict-stage12-bounded-request-batch/1"\n    assert STAGE12_REQUEST_BATCH_CONTRACT == REQUEST_BATCH_CONTRACT\n    assert DEFAULT_REQUEST_BATCH_SIZE == 48\n    manifest = lab_manifest(probe_runtime=False)\n    stage12 = next(row for row in manifest["stages"] if int(row["number"]) == 12)\n    implementation = next(\n        row\n        for row in stage12["implementations"]\n        if row["implementation_key"] == "opus-en-ru-ct2"\n    )\n    controls = {row["key"]: row.get("default") for row in implementation["controls"]}\n    assert controls["request_batch_contract"] == REQUEST_BATCH_CONTRACT\n    assert controls["request_batch_size"] == 48\n    assert "bounded-batch" in implementation["tags"]\n''',
        encoding="utf-8",
    )


def migrate_heavy_workflow() -> None:
    text = HEAVY.read_text(encoding="utf-8")
    text = replace_once(
        text,
        '''      - name: Run full Product Stage12 and numeric audit on contiguous Opticks\n        run: python -u rocketdict-workbench/tests/real_translation_full_opticks_numeric_stress.py\n''',
        '''      - name: Run full Product Stage12 and numeric audit on contiguous Opticks\n        shell: bash\n        run: |\n          set -euo pipefail\n          python -u rocketdict-workbench/tests/real_translation_full_opticks_numeric_stress.py &\n          child=$!\n          while kill -0 "$child" 2>/dev/null; do\n            echo "[heartbeat] full Opticks Product Stage12/numeric audit active at $(date -u +%Y-%m-%dT%H:%M:%SZ)"\n            sleep 30\n          done\n          wait "$child"\n''',
        label="heavy heartbeat",
    )
    HEAVY.write_text(text, encoding="utf-8")


def main() -> int:
    migrate_translation()
    migrate_registry()
    write_test()
    migrate_heavy_workflow()
    print("Stage12 bounded batch execution migration applied")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
