from __future__ import annotations

import base64
import hashlib
import io
import lzma
from pathlib import Path, PurePosixPath
import shutil
import sqlite3
import tarfile

ROOT = Path(__file__).resolve().parent
PAYLOAD = ROOT / "payload"
ACTIVE = ROOT / "active_source"
RESEARCH = ROOT / "research"

OVERLAY_SHA256 = "ddf5f409a5690fa4d2141c8a3bd30ef73f82cc9e75c27b66716791afbc6f97b7"
OVERLAY_PARTS = 8
VAULT_XZ_SHA256 = "394ffcfe399deb1f83ad445cc3ac2e727c8f684a29fd06c757eee16612cfe4ab"
VAULT_SQLITE_SHA256 = "106fc9d7bee42a53b34412267923d17b3331019d2eef16300b539de8929927a1"
VAULT_PARTS = 11
EXPECTED_OVERLAY_MEMBERS = {
    "src/rocketdict/__init__.py",
    "src/rocketdict/nlp/registry.py",
    "src/rocketdict/lab/stage12_pilot.py",
    "src/rocketdict/lab/builtin_adapters.py",
    "src/rocketdict/translation/registry.py",
    "src/rocketdict/translation/service.py",
    "src/rocketdict/translation/structural.py",
    "src/rocketdict/translation/backends.py",
    "src/rocketdict/translation/adaptive_batch.py",
    "src/rocketdict/translation/opus_runtime_bundle.py",
    "src/rocketdict/translation/planner.py",
    "src/rocketdict/translation/integrity.py",
    "src/rocketdict/research/__init__.py",
    "src/rocketdict/research/vault.py",
    "src/rocketdict/research/integrity_doe.py",
    "scripts/stage8_rescore_integrity_doe.py",
    "tests/test_stage8_integrity_research.py",
    "tests/test_stage7c_opus_runtime_bundle.py",
    "tests/test_stage8_readonly_registries.py",
}


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def read_parts(directory: Path, suffix: str, expected: int) -> str:
    parts = sorted(directory.glob(f"part-*{suffix}"))
    if len(parts) != expected:
        raise RuntimeError(f"{directory}: expected {expected} parts, found {len(parts)}")
    expected_names = [f"part-{i:03d}{suffix}" for i in range(expected)]
    actual_names = [p.name for p in parts]
    if actual_names != expected_names:
        raise RuntimeError(f"non-canonical part inventory: {actual_names}")
    return "".join(p.read_text(encoding="ascii").strip() for p in parts)


def safe_member(name: str) -> bool:
    p = PurePosixPath(name)
    return bool(name) and not p.is_absolute() and ".." not in p.parts and ":" not in p.parts[0]


def materialize_overlay() -> tuple[str, int]:
    encoded = read_parts(PAYLOAD / "stage8-overlay", ".b64", OVERLAY_PARTS)
    archive = base64.b64decode(encoded, validate=True)
    digest = sha256(archive)
    if digest != OVERLAY_SHA256:
        raise RuntimeError(f"overlay SHA mismatch: {digest}")

    with tarfile.open(fileobj=io.BytesIO(archive), mode="r:gz") as tf:
        members = tf.getmembers()
        names = {m.name for m in members if m.isfile()}
        if names != EXPECTED_OVERLAY_MEMBERS:
            raise RuntimeError(f"unexpected overlay inventory: {sorted(names ^ EXPECTED_OVERLAY_MEMBERS)}")
        for member in members:
            if not safe_member(member.name):
                raise RuntimeError(f"unsafe tar path: {member.name!r}")
            if member.issym() or member.islnk() or member.isdev():
                raise RuntimeError(f"unsupported tar member type: {member.name!r}")

        if ACTIVE.exists():
            shutil.rmtree(ACTIVE)
        ACTIVE.mkdir(parents=True)
        tf.extractall(ACTIVE, filter="data")

    return digest, len(EXPECTED_OVERLAY_MEMBERS)


def materialize_vault() -> tuple[str, int]:
    encoded = read_parts(PAYLOAD / "research-vault", ".b85", VAULT_PARTS)
    compressed = base64.b85decode(encoded.encode("ascii"))
    compressed_digest = sha256(compressed)
    if compressed_digest != VAULT_XZ_SHA256:
        raise RuntimeError(f"vault XZ SHA mismatch: {compressed_digest}")
    raw = lzma.decompress(compressed)
    raw_digest = sha256(raw)
    if raw_digest != VAULT_SQLITE_SHA256:
        raise RuntimeError(f"vault SQLite SHA mismatch: {raw_digest}")

    RESEARCH.mkdir(parents=True, exist_ok=True)
    target = RESEARCH / "research-vault.sqlite"
    target.write_bytes(raw)

    con = sqlite3.connect(f"file:{target}?mode=ro", uri=True)
    try:
        quick = con.execute("PRAGMA quick_check").fetchone()[0]
        fk = con.execute("PRAGMA foreign_key_check").fetchall()
        if quick != "ok" or fk:
            raise RuntimeError(f"Research Vault integrity failed: quick={quick!r}, fk={len(fk)}")
        tables = con.execute(
            "SELECT COUNT(*) FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"
        ).fetchone()[0]
    finally:
        con.close()
    return raw_digest, int(tables)


def main() -> None:
    overlay_sha, overlay_files = materialize_overlay()
    vault_sha, vault_tables = materialize_vault()
    checks = ROOT / "MATERIALIZED_CHECKSUMS.txt"
    checks.write_text(
        "\n".join(
            [
                f"stage8_overlay_tar_gz_sha256={overlay_sha}",
                f"stage8_overlay_files={overlay_files}",
                f"research_vault_sqlite_sha256={vault_sha}",
                f"research_vault_tables={vault_tables}",
                "privacy_scope=project-only-public-handoff",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    print(checks.read_text(encoding="utf-8"), end="")


if __name__ == "__main__":
    main()
