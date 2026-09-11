from __future__ import annotations

"""Provision verified external model assets for RocketDict Product Core.

Processing itself is offline. Provisioning is a separate explicit step. The
accepted baseline OPUS builder consumes the official archive already downloaded
by the operator/installer. The optional independent TC-big builder consumes an
already-downloaded pinned Hugging Face snapshot. Both builders verify immutable
source identities before creating CTranslate2 float32 assets; neither downloads
anything during the build operation.
"""

import argparse
import hashlib
import json
from pathlib import Path, PurePosixPath
import shutil
import tempfile
from typing import Any
import zipfile

from .runtime import OPUS_ARCHIVE_SHA256, OPUS_ASSET_SCHEMA, OPUS_REVISION


def _file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _safe_name(name: str) -> bool:
    path = PurePosixPath(name)
    return bool(name) and not path.is_absolute() and ".." not in path.parts and "\\" not in name


def _tree_identity(root: Path) -> dict[str, Any]:
    rows = []
    total = 0
    for path in sorted(p for p in root.rglob("*") if p.is_file()):
        size = path.stat().st_size
        total += size
        rows.append(
            {
                "path": path.relative_to(root).as_posix(),
                "bytes": size,
                "sha256": _file_sha256(path),
            }
        )
    raw = json.dumps(rows, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return {
        "file_count": len(rows),
        "bytes": total,
        "sha256": hashlib.sha256(raw).hexdigest(),
        "files": rows,
    }


def _discover_opus_model_dir(source_root: Path) -> tuple[Path, list[Path]]:
    """Locate the actual OPUS model directory without assuming model.npz."""
    candidate_dirs = {source_root}
    candidate_dirs.update(path.parent for path in source_root.rglob("decoder.yml"))
    candidate_dirs.update(path.parent for path in source_root.rglob("*.npz"))
    rows: list[tuple[Path, list[Path], list[Path]]] = []
    for directory in sorted(candidate_dirs):
        if not (directory / "decoder.yml").is_file():
            continue
        weights = sorted(directory.glob("*.npz"))
        spm_files = sorted(directory.glob("*.spm"))
        if weights and len(spm_files) >= 2:
            rows.append((directory, weights, spm_files))
    exact = [
        row
        for row in rows
        if (row[0] / "source.spm").is_file() and (row[0] / "target.spm").is_file()
    ]
    selected = exact if len(exact) == 1 else rows
    if len(selected) != 1:
        inventory = [
            {
                "directory": str(directory.relative_to(source_root)),
                "npz": [path.name for path in weights],
                "spm": [path.name for path in spm_files],
            }
            for directory, weights, spm_files in rows
        ]
        raise RuntimeError(
            "Could not uniquely locate OPUS Marian model directory from decoder.yml/NPZ/SPM evidence: "
            + json.dumps(inventory, ensure_ascii=False, sort_keys=True)
        )
    directory, weights, _spm = selected[0]
    return directory, weights


def build_opus_asset(
    archive: Path | str,
    destination: Path | str,
    *,
    force: bool = False,
) -> dict[str, Any]:
    archive = Path(archive).expanduser().resolve()
    destination = Path(destination).expanduser().resolve()
    if not archive.is_file():
        raise FileNotFoundError(archive)
    archive_sha = _file_sha256(archive)
    if archive_sha != OPUS_ARCHIVE_SHA256:
        raise RuntimeError(
            f"Official OPUS archive SHA-256 mismatch: {archive_sha} != {OPUS_ARCHIVE_SHA256}"
        )
    if destination.exists() and any(destination.iterdir()) and not force:
        raise RuntimeError(
            f"Destination is not empty: {destination}; pass --force for an explicit rebuild"
        )
    destination.mkdir(parents=True, exist_ok=True)

    import ctranslate2

    with tempfile.TemporaryDirectory(prefix="rocketdict-opus-") as temp_name:
        temp = Path(temp_name)
        source_root = temp / "source"
        source_root.mkdir()
        with zipfile.ZipFile(archive) as zf:
            bad = zf.testzip()
            if bad is not None:
                raise RuntimeError(f"Official OPUS ZIP CRC failure at {bad}")
            infos = [info for info in zf.infolist() if not info.is_dir()]
            unsafe = [info.filename for info in infos if not _safe_name(info.filename)]
            if unsafe:
                raise RuntimeError(f"Official OPUS ZIP contains unsafe paths: {unsafe[:5]}")
            for info in infos:
                target = source_root / PurePosixPath(info.filename)
                target.parent.mkdir(parents=True, exist_ok=True)
                with zf.open(info) as source_handle, target.open("wb") as target_handle:
                    shutil.copyfileobj(source_handle, target_handle, 1024 * 1024)

        model_dir, weight_files = _discover_opus_model_dir(source_root)
        spm_files = sorted(model_dir.glob("*.spm"))
        source_spm = next(
            (path for path in spm_files if path.name.casefold() == "source.spm"),
            next((path for path in spm_files if "source" in path.name.casefold()), spm_files[0]),
        )
        target_spm = next(
            (path for path in spm_files if path.name.casefold() == "target.spm" and path != source_spm),
            None,
        ) or next(
            (
                path
                for path in spm_files
                if "target" in path.name.casefold() and path != source_spm
            ),
            None,
        ) or next(path for path in spm_files if path != source_spm)

        build_root = temp / "asset"
        ct2_root = build_root / "ct2"
        ct2_root.mkdir(parents=True)
        ctranslate2.converters.OpusMTConverter(str(model_dir)).convert(
            str(ct2_root), quantization="float32", force=True
        )
        shutil.copy2(source_spm, build_root / "source.spm")
        shutil.copy2(target_spm, build_root / "target.spm")
        if not (ct2_root / "model.bin").is_file():
            raise RuntimeError("CTranslate2 conversion did not create model.bin")

        tree = _tree_identity(build_root)
        manifest = {
            "schema": OPUS_ASSET_SCHEMA,
            "revision": OPUS_REVISION,
            "source_archive_sha256": OPUS_ARCHIVE_SHA256,
            "source_archive_bytes": archive.stat().st_size,
            "source_model": {
                "directory": str(model_dir.relative_to(source_root)),
                "weight_files": [path.name for path in weight_files],
                "decoder": "decoder.yml",
            },
            "ct2_model_dir": "ct2",
            "source_sentencepiece": "source.spm",
            "target_sentencepiece": "target.spm",
            "compute_type": "float32",
            "converter": {
                "name": "ctranslate2.converters.OpusMTConverter",
                "ctranslate2_version": str(ctranslate2.__version__),
            },
            "payload_tree": {
                "file_count": tree["file_count"],
                "bytes": tree["bytes"],
                "sha256": tree["sha256"],
            },
        }
        (build_root / "rocketdict-opus-asset.json").write_text(
            json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )

        if destination.exists() and force:
            for child in list(destination.iterdir()):
                if child.is_dir():
                    shutil.rmtree(child)
                else:
                    child.unlink()
        for child in build_root.iterdir():
            target = destination / child.name
            if child.is_dir():
                shutil.copytree(child, target)
            else:
                shutil.copy2(child, target)

    return {
        "schema": "rocketdict-opus-asset-build/1",
        "status": "completed",
        "destination": str(destination),
        "source_archive_sha256": archive_sha,
        "source_model_weight_files": [path.name for path in weight_files],
        "manifest_sha256": _file_sha256(destination / "rocketdict-opus-asset.json"),
        "payload_tree_sha256": manifest["payload_tree"]["sha256"],
        "payload_file_count": manifest["payload_tree"]["file_count"],
        "payload_bytes": manifest["payload_tree"]["bytes"],
        "network_used_by_builder": False,
    }


def parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="rocketdict-assets")
    commands = p.add_subparsers(dest="command", required=True)
    opus = commands.add_parser("build-opus-en-ru")
    opus.add_argument("archive", type=Path)
    opus.add_argument("destination", type=Path)
    opus.add_argument("--force", action="store_true")
    tc_big = commands.add_parser("build-tc-big-en-ru")
    tc_big.add_argument("source_snapshot", type=Path)
    tc_big.add_argument("destination", type=Path)
    tc_big.add_argument("--force", action="store_true")
    return p


def main(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    try:
        if args.command == "build-opus-en-ru":
            payload = build_opus_asset(args.archive, args.destination, force=args.force)
        elif args.command == "build-tc-big-en-ru":
            from .alternative_mt_assets import build_tc_big_asset
            payload = build_tc_big_asset(args.source_snapshot, args.destination, force=args.force)
        else:
            raise AssertionError(args.command)
    except Exception as exc:
        print(
            json.dumps(
                {"status": "error", "type": type(exc).__name__, "error": str(exc)},
                ensure_ascii=False,
            )
        )
        return 2
    print(json.dumps(payload, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
