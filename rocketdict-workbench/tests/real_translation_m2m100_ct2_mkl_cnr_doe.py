from __future__ import annotations

"""Focused cross-host CTranslate2/MKL numerical reproducibility DOE.

Research-only.  Forces the documented cross-vendor MKL CNR mode in fresh
processes and records raw rank0/token identities for the already authenticated
M2M100 arithmetic source.  It never authorizes promotion by itself.
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

from real_translation_m2m100_ct2_determinism_doe import (
    BASE_TARGET,
    PARITY_EVIDENCE_SHA256,
    _canonical_sha,
    _load_parity,
    _low_level_translate,
    _text_sha,
)

EXPECTED_SOURCE_START = 483234
PROCESSES_PER_CONFIG = 2
REPEATS_PER_PROCESS = 3
CONFIGS: tuple[dict[str, Any], ...] = (
    {"name": "mkl-compatible-384", "max_decoding_length": 384},
    {"name": "mkl-compatible-512", "max_decoding_length": 512},
)
CNR_ENV = {
    "CT2_USE_MKL": "1",
    "CT2_PACKED_GEMM": "0",
    "CT2_FORCE_CPU_ISA": "AVX2",
    "MKL_CBWR": "COMPATIBLE",
    "MKL_DYNAMIC": "FALSE",
    "MKL_NUM_THREADS": "1",
    "OMP_DYNAMIC": "FALSE",
    "OMP_NUM_THREADS": "1",
}


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


def _child(config_name: str, parity_path: Path, output_path: Path) -> int:
    config = next((row for row in CONFIGS if row["name"] == config_name), None)
    if config is None:
        raise RuntimeError(f"unknown config {config_name!r}")
    for key, expected in CNR_ENV.items():
        if os.environ.get(key) != expected:
            raise RuntimeError(f"CNR environment drift for {key}: {os.environ.get(key)!r}")

    parity = _load_parity(parity_path)
    source = str(parity["source_text"])
    expected_parity_target = str(parity["ct2_rank0_target"])

    import ctranslate2
    from rocketdict.m2m100_runtime import m2m100_status

    if ctranslate2.__version__ != "4.8.2":
        raise RuntimeError(f"CTranslate2 version drift: {ctranslate2.__version__}")
    status = m2m100_status()
    if status.get("available") is not True:
        raise RuntimeError(f"M2M100 runtime unavailable: {status}")

    records = _low_level_translate(
        source,
        inter_threads=1,
        intra_threads=1,
        max_decoding_length=int(config["max_decoding_length"]),
        repeats=REPEATS_PER_PROCESS,
    )
    payload: dict[str, Any] = {
        "schema": "rocketdict-m2m100-ct2-mkl-cnr-child/1",
        "config": config,
        "cpu": _cpu_identity(),
        "ctranslate2_version": ctranslate2.__version__,
        "runtime": status,
        "cnr_environment": {key: os.environ.get(key) for key in sorted(CNR_ENV)},
        "expected_parity_target_sha256": _text_sha(expected_parity_target),
        "base_target_sha256": _text_sha(BASE_TARGET),
        "records": records,
        "all_repeats_same_target": len({r["target_sha256"] for r in records}) == 1,
        "all_repeats_same_tokens": len({r["tokens_sha256"] for r in records}) == 1,
        "all_repeats_exact_parity_target": all(
            r["target"] == expected_parity_target for r in records
        ),
        "all_repeats_selector_accepted": all(
            r["selector_accepted"] is True for r in records
        ),
    }
    payload["evidence_sha256"] = _canonical_sha(payload)
    output_path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(
        json.dumps(
            {
                "config": config_name,
                "cpu": payload["cpu"].get("model_name"),
                "same_target": payload["all_repeats_same_target"],
                "same_tokens": payload["all_repeats_same_tokens"],
                "exact_parity": payload["all_repeats_exact_parity_target"],
                "selector_accepted": payload["all_repeats_selector_accepted"],
                "target_sha256": sorted({r["target_sha256"] for r in records}),
                "evidence_sha256": payload["evidence_sha256"],
            },
            ensure_ascii=False,
            sort_keys=True,
        )
    )
    return 0


def _cnr_environment() -> dict[str, str]:
    env = dict(os.environ)
    env.update(CNR_ENV)
    env["CT2_VERBOSE"] = "1"
    return env


def _parent(parity_path: Path, root: Path) -> int:
    parity = _load_parity(parity_path)
    root.mkdir(parents=True, exist_ok=True)
    children: list[dict[str, Any]] = []
    for config in CONFIGS:
        for process_index in range(PROCESSES_PER_CONFIG):
            output = root / f"{config['name']}-process-{process_index}.json"
            completed = subprocess.run(
                [
                    sys.executable,
                    str(Path(__file__).resolve()),
                    "--child",
                    str(config["name"]),
                    "--parity-evidence",
                    str(parity_path),
                    "--output",
                    str(output),
                ],
                env=_cnr_environment(),
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
                    f"CNR child failed for {config['name']} process {process_index}: "
                    f"{completed.stderr[-5000:]}"
                )
            child = json.loads(output.read_text(encoding="utf-8"))
            child["process_index"] = process_index
            children.append(child)

    expected = str(parity["ct2_rank0_target"])
    summaries: dict[str, Any] = {}
    for config in CONFIGS:
        rows = [row for row in children if row["config"]["name"] == config["name"]]
        records = [record for row in rows for record in row["records"]]
        target_shas = sorted({r["target_sha256"] for r in records})
        token_shas = sorted({r["tokens_sha256"] for r in records})
        summaries[str(config["name"])] = {
            "process_count": len(rows),
            "record_count": len(records),
            "unique_target_sha256": target_shas,
            "unique_tokens_sha256": token_shas,
            "deterministic_within_runner": len(target_shas) == 1 and len(token_shas) == 1,
            "all_exact_parity_target": all(r["target"] == expected for r in records),
            "all_selector_accepted": all(r["selector_accepted"] is True for r in records),
            "cpu_identities": [row["cpu"] for row in rows],
            "child_evidence_sha256": [row["evidence_sha256"] for row in rows],
            "runtime_payload_tree_sha256": sorted(
                {str(row["runtime"].get("asset_payload_tree_sha256")) for row in rows}
            ),
        }

    evidence: dict[str, Any] = {
        "schema": "rocketdict-m2m100-ct2-mkl-cnr-doe/1",
        "purpose": "test forced MKL COMPATIBLE numerical reproducibility across fresh processes before any arithmetic promotion",
        "promotion_allowed": False,
        "automatic_product_default_allowed": False,
        "parity_evidence_sha256": PARITY_EVIDENCE_SHA256,
        "source_start": EXPECTED_SOURCE_START,
        "processes_per_config": PROCESSES_PER_CONFIG,
        "repeats_per_process": REPEATS_PER_PROCESS,
        "cnr_environment": CNR_ENV,
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
    (root / "m2m100-ct2-mkl-cnr-doe.json").write_text(
        json.dumps(evidence, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(
        json.dumps(
            {
                "evidence_sha256": evidence["evidence_sha256"],
                "configs": {
                    name: {
                        "deterministic_within_runner": row["deterministic_within_runner"],
                        "all_exact_parity_target": row["all_exact_parity_target"],
                        "all_selector_accepted": row["all_selector_accepted"],
                        "unique_target_sha256": row["unique_target_sha256"],
                    }
                    for name, row in summaries.items()
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
        default=Path(os.environ.get("ROCKETDICT_M2M100_MKL_CNR_ROOT", "work/m2m100-mkl-cnr")),
    )
    args = parser.parse_args(argv)
    parity = args.parity_evidence.expanduser().resolve()
    if args.child:
        if args.output is None:
            raise RuntimeError("--output required in child mode")
        return _child(str(args.child), parity, args.output.expanduser().resolve())
    return _parent(parity, args.root.expanduser().resolve())


if __name__ == "__main__":
    raise SystemExit(main())
