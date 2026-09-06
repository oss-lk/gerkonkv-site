from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import shutil
import sys

from rocketdict.database import bootstrap_database, connect, database_path, utcnow

SCHEMA = "rocketdict-product-core-import/1"
CHUNK = 1024 * 1024


def _sha256(path: Path) -> tuple[str, int]:
    digest = hashlib.sha256()
    total = 0
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(CHUNK), b""):
            digest.update(block)
            total += len(block)
    return digest.hexdigest(), total


def import_source(source: Path | str, *, data_root: Path | str) -> dict[str, object]:
    source = Path(source).expanduser().resolve()
    root = Path(data_root).expanduser().resolve()
    if not source.is_file():
        raise FileNotFoundError(source)
    root.mkdir(parents=True, exist_ok=True)
    db = database_path(root)
    bootstrap_database(db)

    sha256, byte_size = _sha256(source)
    object_rel = Path("objects") / sha256[:2] / sha256
    object_path = root / object_rel
    object_path.parent.mkdir(parents=True, exist_ok=True)
    if object_path.exists():
        observed_sha, observed_bytes = _sha256(object_path)
        if observed_sha != sha256 or observed_bytes != byte_size:
            raise RuntimeError(
                "Existing immutable object path has different bytes; refusing overwrite"
            )
    else:
        temporary = object_path.with_suffix(".tmp")
        if temporary.exists():
            temporary.unlink()
        shutil.copyfile(source, temporary)
        copied_sha, copied_bytes = _sha256(temporary)
        if copied_sha != sha256 or copied_bytes != byte_size:
            temporary.unlink(missing_ok=True)
            raise RuntimeError("Immutable object copy verification failed")
        temporary.replace(object_path)

    with connect(db) as connection:
        existing = connection.execute(
            "SELECT * FROM import_events WHERE source_sha256=? AND byte_size=?",
            (sha256, byte_size),
        ).fetchone()
        cache_hit = existing is not None
        if existing is None:
            cursor = connection.execute(
                """
                INSERT INTO import_events(
                    source_name,source_sha256,byte_size,object_path,imported_at
                ) VALUES(?,?,?,?,?)
                """,
                (source.name, sha256, byte_size, object_rel.as_posix(), utcnow()),
            )
            import_event_id = int(cursor.lastrowid)
            connection.commit()
        else:
            import_event_id = int(existing["id"])
            if str(existing["object_path"]) != object_rel.as_posix():
                raise RuntimeError("Immutable import identity points at unexpected object path")

    return {
        "schema": SCHEMA,
        "status": "imported",
        "import_event_id": import_event_id,
        "source_name": source.name,
        "source_sha256": sha256,
        "byte_size": byte_size,
        "object_path": object_rel.as_posix(),
        "cache_hit": cache_hit,
    }


def parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="python -m rocketdict.importing.cli")
    p.add_argument("source", type=Path)
    p.add_argument("--data-root", type=Path, required=True)
    return p


def main(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    try:
        payload = import_source(args.source, data_root=args.data_root)
    except Exception as exc:
        print(
            json.dumps(
                {
                    "schema": SCHEMA,
                    "status": "error",
                    "type": type(exc).__name__,
                    "error": str(exc),
                },
                ensure_ascii=False,
            ),
            file=sys.stderr,
        )
        return 2
    print(json.dumps(payload, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
