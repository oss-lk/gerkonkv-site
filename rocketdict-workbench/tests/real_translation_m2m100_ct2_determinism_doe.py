from __future__ import annotations

"""Bounded reproducibility DOE for the one source-verified M2M100 arithmetic case.

This is research-only infrastructure.  It compares the current Product runtime
shape with explicitly pinned CPU/thread variants over the exact immutable source
already authenticated by the CT2 parity evidence.  No target rewriting or
promotion is performed.
"""

import argparse
import hashlib
import json
import os
from pathlib import Path
import platform
import subprocess
import sys
from typing import Any

PARITY_SCHEMA = "rocketdict-m2m100-ct2-arithmetic-restatement-parity/1"
PARITY_EVIDENCE_SHA256 = "bc739df0594e5f73331c2a2d5301bdb6d6eb27d9ab3921703dc99a16237dac57"
EXPECTED_SOURCE_START = 483234
BASE_TARGET = (
    "Таким образом, эластичная сила этого Среднего, пропорциональная его плотности, "
    "должна быть более 700000 х 700 000 (т.е. более 490 000 000 000 000) в раз больше, "
    "чем эластичная сила воздуха пропорционально его плотности."
)
BASE_TARGET_SHA256 = "6d4279ea763b9fcba95e9f68aed848225a28526fe8559ef7be49b99facd678ba"
REPEATS_PER_PROCESS = 4
PROCESSES_PER_CONFIG = 2
CONFIGS: tuple[dict[str, Any], ...] = (
    {
        "name": "current-auto-512",
        "inter_threads": None,
        "intra_threads": None,
        "max_decoding_length": 512,
        "portable_cpu": False,
    },
    {
        "name": "single-auto-512",
        "inter_threads": 1,
        "intra_threads": 1,
        "max_decoding_length": 512,
        "portable_cpu": False,
    },
    {
        "name": "single-auto-384",
        "inter_threads": 1,
        "intra_threads": 1,
        "max_decoding_length": 384,
        "portable_cpu": False,
    },
    {
        "name": "single-portable-512",
        "inter_threads": 1,
        "intra_threads": 1,
        "max_decoding_length": 512,
        "portable_cpu": True,
    },
    {
        "name": "single-portable-384",
        "inter_threads": 1,
        "intra_threads": 1,
        "max_decoding_length": 384,
        "portable_cpu": True,
    },
)


def _canonical_sha(value: Any) -> str:
    raw = json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def _text_sha(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _cpu_identity() -> dict[str, Any]:
    identity: dict[str, Any] = {
        "platform": platform.platform(),
        "machine": platform.machine(),
        "processor": platform.processor(),
        "python": sys.version,
    }
    cpuinfo = Path("/proc/cpuinfo")
    if cpuinfo.is_file():
        first: dict[str, str] = {}
        for line in cpuinfo.read_text(encoding="utf-8", errors="replace").splitlines():
            if not line.strip():
                if first:
                    break
                continue
            if ":" in line:
                key, value = line.split(":", 1)
                first[key.strip()] = value.strip()
        identity.update(
            {
                "vendor_id": first.get("vendor_id"),
                "model_name": first.get("model name"),
                "cpu_family": first.get("cpu family"),
                "model": first.get("model"),
                "stepping": first.get("stepping"),
                "flags_sha256": _text_sha(first.get("flags", "")),
            }
        )
    return identity


def _load_parity(path: Path) -> dict[str, Any]:
    evidence = json.loads(path.read_text(encoding="utf-8"))
    if evidence.get("schema") != PARITY_SCHEMA:
        raise RuntimeError("parity evidence schema drift")
    copy = dict(evidence)
    recorded = str(copy.pop("evidence_sha256"))
    actual = _canonical_sha(copy)
    if recorded != PARITY_EVIDENCE_SHA256 or actual != recorded:
        raise RuntimeError("parity evidence SHA drift")
    if int(evidence.get("source_start", -1)) != EXPECTED_SOURCE_START:
        raise RuntimeError("parity source identity drift")
    if _text_sha(BASE_TARGET) != BASE_TARGET_SHA256:
        raise RuntimeError("embedded run58 base-target identity drift")
    return evidence


def _low_level_translate(
    source: str,
    *,
    inter_threads: int | None,
    intra_threads: int | None,
    max_decoding_length: int,
    repeats: int,
) -> list[dict[str, Any]]:
    from rocketdict.m2m100_runtime import (
        M2M100_SOURCE_LANGUAGE,
        M2M100_TARGET_LANGUAGE,
        load_m2m100_asset,
    )
    from rocketdict.translation_m2m100_arithmetic_rules import (
        evaluate_m2m100_arithmetic_candidate,
        parse_source_arithmetic_restatement,
    )
    import ctranslate2
    from transformers import M2M100Tokenizer

    asset = load_m2m100_asset()
    tokenizer = M2M100Tokenizer.from_pretrained(
        str(asset.tokenizer_dir), local_files_only=True
    )
    tokenizer.src_lang = M2M100_SOURCE_LANGUAGE
    target_prefix_token = tokenizer.lang_code_to_token[M2M100_TARGET_LANGUAGE]
    ids = tokenizer.encode(source, add_special_tokens=True)
    encoded = list(tokenizer.convert_ids_to_tokens(ids))
    if not encoded:
        raise RuntimeError("empty tokenized source")

    kwargs: dict[str, Any] = {
        "device": "cpu",
        "compute_type": "float32",
    }
    if inter_threads is not None:
        kwargs["inter_threads"] = int(inter_threads)
    if intra_threads is not None:
        kwargs["intra_threads"] = int(intra_threads)
    translator = ctranslate2.Translator(str(asset.ct2_model_dir), **kwargs)
    restatement = parse_source_arithmetic_restatement(source)
    if restatement is None or restatement.get("arithmetic_verified") is not True:
        raise RuntimeError("source arithmetic restatement drift")

    records: list[dict[str, Any]] = []
    for index in range(repeats):
        results = translator.translate_batch(
            [encoded],
            target_prefix=[[target_prefix_token]],
            beam_size=6,
            num_hypotheses=1,
            max_decoding_length=int(max_decoding_length),
            length_penalty=1.0,
            return_scores=True,
        )
        if len(results) != 1 or len(results[0].hypotheses) != 1:
            raise RuntimeError("rank0 cardinality drift")
        raw_tokens = list(results[0].hypotheses[0])
        if not raw_tokens or raw_tokens[0] != target_prefix_token:
            raise RuntimeError("target prefix drift")
        token_ids = tokenizer.convert_tokens_to_ids(raw_tokens[1:])
        target = tokenizer.decode(token_ids, skip_special_tokens=True).strip()
        if not target:
            raise RuntimeError("empty decoded target")
        score = None
        scores = list(getattr(results[0], "scores", []) or [])
        if scores:
            score = float(scores[0])
        selection = evaluate_m2m100_arithmetic_candidate(
            source,
            target,
            base_target=BASE_TARGET,
            restatement=restatement,
        )
        records.append(
            {
                "repeat": index,
                "target": target,
                "target_sha256": _text_sha(target),
                "tokens_sha256": _canonical_sha(raw_tokens),
                "score": score,
                "selector_accepted": selection.get("accepted") is True,
                "selector": selection,
            }
        )
    return records


def _child(config_name: str, parity_path: Path, output_path: Path) -> int:
    config = next((row for row in CONFIGS if row["name"] == config_name), None)
    if config is None:
        raise RuntimeError(f"unknown config {config_name!r}")
    parity = _load_parity(parity_path)
    source = str(parity["source_text"])
    expected_target = str(parity["ct2_rank0_target"])

    import ctranslate2
    from rocketdict.m2m100_runtime import m2m100_status

    status = m2m100_status()
    if status.get("available") is not True:
        raise RuntimeError(f"M2M100 runtime unavailable: {status}")
    records = _low_level_translate(
        source,
        inter_threads=config["inter_threads"],
        intra_threads=config["intra_threads"],
        max_decoding_length=int(config["max_decoding_length"]),
        repeats=REPEATS_PER_PROCESS,
    )
    payload = {
        "config": config,
        "cpu": _cpu_identity(),
        "ctranslate2_version": ctranslate2.__version__,
        "runtime": status,
        "environment": {
            key: os.environ.get(key)
            for key in (
                "CT2_FORCE_CPU_ISA",
                "CT2_USE_MKL",
                "CT2_PACKED_GEMM",
                "OMP_NUM_THREADS",
                "OMP_DYNAMIC",
                "OMP_PROC_BIND",
            )
        },
        "expected_parity_target_sha256": _text_sha(expected_target),
        "records": records,
    }
    payload["all_repeats_same_target"] = len(
        {record["target_sha256"] for record in records}
    ) == 1
    payload["all_repeats_same_tokens"] = len(
        {record["tokens_sha256"] for record in records}
    ) == 1
    payload["all_repeats_exact_parity_target"] = all(
        record["target"] == expected_target for record in records
    )
    payload["all_repeats_selector_accepted"] = all(
        record["selector_accepted"] is True for record in records
    )
    output_path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(
        json.dumps(
            {
                "config": config_name,
                "same_target": payload["all_repeats_same_target"],
                "same_tokens": payload["all_repeats_same_tokens"],
                "exact_parity": payload["all_repeats_exact_parity_target"],
                "selector_accepted": payload["all_repeats_selector_accepted"],
                "target_shas": sorted({r["target_sha256"] for r in records}),
                "cpu": payload["cpu"].get("model_name"),
            },
            ensure_ascii=False,
            sort_keys=True,
        )
    )
    return 0


def _portable_environment(base: dict[str, str], enabled: bool) -> dict[str, str]:
    env = dict(base)
    if enabled:
        env.update(
            {
                "CT2_USE_MKL": "0",
                "CT2_FORCE_CPU_ISA": "AVX2",
                "CT2_PACKED_GEMM": "0",
                "OMP_NUM_THREADS": "1",
                "OMP_DYNAMIC": "FALSE",
            }
        )
    else:
        for key in (
            "CT2_USE_MKL",
            "CT2_FORCE_CPU_ISA",
            "CT2_PACKED_GEMM",
            "OMP_NUM_THREADS",
            "OMP_DYNAMIC",
        ):
            env.pop(key, None)
    env["CT2_VERBOSE"] = "1"
    return env


def _parent(parity_path: Path, root: Path) -> int:
    parity = _load_parity(parity_path)
    root.mkdir(parents=True, exist_ok=True)
    children: list[dict[str, Any]] = []
    for config in CONFIGS:
        for process_index in range(PROCESSES_PER_CONFIG):
            output_path = root / f"{config['name']}-process-{process_index}.json"
            command = [
                sys.executable,
                str(Path(__file__).resolve()),
                "--child",
                str(config["name"]),
                "--parity-evidence",
                str(parity_path),
                "--output",
                str(output_path),
            ]
            completed = subprocess.run(
                command,
                env=_portable_environment(os.environ, bool(config["portable_cpu"])),
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=False,
            )
            (root / f"{config['name']}-process-{process_index}.stdout.txt").write_text(
                completed.stdout, encoding="utf-8"
            )
            (root / f"{config['name']}-process-{process_index}.stderr.txt").write_text(
                completed.stderr, encoding="utf-8"
            )
            if completed.returncode != 0:
                raise RuntimeError(
                    f"determinism child failed for {config['name']} process {process_index}: "
                    f"{completed.stderr[-4000:]}"
                )
            child = json.loads(output_path.read_text(encoding="utf-8"))
            child["process_index"] = process_index
            children.append(child)

    summaries: dict[str, Any] = {}
    expected_target = str(parity["ct2_rank0_target"])
    for config in CONFIGS:
        rows = [row for row in children if row["config"]["name"] == config["name"]]
        records = [record for row in rows for record in row["records"]]
        summaries[str(config["name"])] = {
            "process_count": len(rows),
            "record_count": len(records),
            "unique_target_sha256": sorted({r["target_sha256"] for r in records}),
            "unique_tokens_sha256": sorted({r["tokens_sha256"] for r in records}),
            "all_exact_parity_target": all(r["target"] == expected_target for r in records),
            "all_selector_accepted": all(r["selector_accepted"] is True for r in records),
            "cpu_identities": [row["cpu"] for row in rows],
            "ctranslate2_versions": sorted({str(row["ctranslate2_version"]) for row in rows}),
            "runtime_payload_tree_sha256": sorted(
                {str(row["runtime"].get("asset_payload_tree_sha256")) for row in rows}
            ),
        }
        summaries[str(config["name"])]["deterministic_within_runner"] = bool(
            len(summaries[str(config["name"])]["unique_target_sha256"]) == 1
            and len(summaries[str(config["name"])]["unique_tokens_sha256"]) == 1
        )

    evidence: dict[str, Any] = {
        "schema": "rocketdict-m2m100-ct2-determinism-doe/1",
        "purpose": "bound CPU/backend/thread/generation sources of raw-rank0 variation before any run58 arithmetic promotion",
        "promotion_allowed": False,
        "automatic_product_default_allowed": False,
        "parity_evidence_sha256": PARITY_EVIDENCE_SHA256,
        "source_start": EXPECTED_SOURCE_START,
        "expected_parity_target_sha256": _text_sha(expected_target),
        "repeats_per_process": REPEATS_PER_PROCESS,
        "processes_per_config": PROCESSES_PER_CONFIG,
        "configs": summaries,
        "source_bytes_rewritten": False,
        "model_input_source_rewritten": False,
        "target_rewriting": False,
        "placeholders": False,
        "post_translation_literal_injection": False,
        "corpus_specific_target_patches": False,
        "evaluator_weakened": False,
        "n_best_cherry_picking": False,
        "automatic_n_best_cherry_picking": False,
    }
    evidence["evidence_sha256"] = _canonical_sha(evidence)
    (root / "m2m100-ct2-determinism-doe.json").write_text(
        json.dumps(evidence, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(
        json.dumps(
            {
                "evidence_sha256": evidence["evidence_sha256"],
                "configs": {
                    name: {
                        "deterministic_within_runner": value["deterministic_within_runner"],
                        "all_exact_parity_target": value["all_exact_parity_target"],
                        "all_selector_accepted": value["all_selector_accepted"],
                        "unique_target_sha256": value["unique_target_sha256"],
                    }
                    for name, value in summaries.items()
                },
            },
            ensure_ascii=False,
            sort_keys=True,
        )
    )
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--child")
    parser.add_argument("--parity-evidence", type=Path, required=True)
    parser.add_argument("--output", type=Path)
    parser.add_argument(
        "--root",
        type=Path,
        default=Path(os.environ.get("ROCKETDICT_M2M100_DETERMINISM_ROOT", "work/m2m100-determinism")),
    )
    args = parser.parse_args(argv)
    parity = args.parity_evidence.expanduser().resolve()
    if args.child:
        if args.output is None:
            raise RuntimeError("--output is required in child mode")
        return _child(str(args.child), parity, args.output.expanduser().resolve())
    return _parent(parity, args.root.expanduser().resolve())


if __name__ == "__main__":
    raise SystemExit(main())
