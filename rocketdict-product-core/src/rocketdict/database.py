from __future__ import annotations

"""Durable SQLite storage for the maintained RocketDict Product Core.

The schema intentionally starts small and explicit.  Large stage payloads are
split into run metadata plus ordered ``run_items`` so a 90k+ word run does not
require one ever-growing JSON cell.  All IDs returned to Workbench are durable
SQLite row IDs.
"""

from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sqlite3
from typing import Any, Iterable, Iterator

SCHEMA_VERSION = 1
DATABASE_NAME = "rocketdict.sqlite"


def utcnow() -> str:
    return datetime.now(timezone.utc).isoformat()


def canonical_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False)


def canonical_sha256(value: Any) -> str:
    return hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class DatabaseHandle:
    path: Path

    def dispose(self) -> None:
        """Compatibility with the Workbench bridge's engine-like lifecycle."""


def database_path(data_root: Path | str) -> Path:
    return Path(data_root).expanduser().resolve() / DATABASE_NAME


def _configure(connection: sqlite3.Connection) -> None:
    connection.execute("PRAGMA foreign_keys=ON")
    connection.execute("PRAGMA busy_timeout=30000")


def connect(path: Path | str, *, readonly: bool = False) -> sqlite3.Connection:
    path = Path(path).expanduser().resolve()
    if readonly:
        if not path.is_file():
            raise FileNotFoundError(path)
        connection = sqlite3.connect(f"file:{path.as_posix()}?mode=ro", uri=True)
    else:
        path.parent.mkdir(parents=True, exist_ok=True)
        connection = sqlite3.connect(path)
    connection.row_factory = sqlite3.Row
    _configure(connection)
    return connection


_SCHEMA = """
CREATE TABLE IF NOT EXISTS rocketdict_meta (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS import_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    source_name TEXT NOT NULL,
    source_sha256 TEXT NOT NULL,
    byte_size INTEGER NOT NULL CHECK(byte_size >= 0),
    object_path TEXT NOT NULL,
    imported_at TEXT NOT NULL,
    UNIQUE(source_sha256, byte_size)
);

CREATE TABLE IF NOT EXISTS document_versions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    import_event_id INTEGER NOT NULL REFERENCES import_events(id),
    selected_format TEXT NOT NULL,
    selected_encoding TEXT NOT NULL,
    interpretation_key TEXT NOT NULL UNIQUE,
    text_sha256 TEXT NOT NULL,
    char_count INTEGER NOT NULL CHECK(char_count >= 0),
    segment_count INTEGER NOT NULL CHECK(segment_count >= 0),
    content_text TEXT NOT NULL,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS document_segments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    document_version_id INTEGER NOT NULL REFERENCES document_versions(id) ON DELETE CASCADE,
    sequence_number INTEGER NOT NULL,
    start_char INTEGER NOT NULL,
    end_char INTEGER NOT NULL,
    start_ms INTEGER,
    end_ms INTEGER,
    text TEXT NOT NULL,
    metadata_json TEXT NOT NULL,
    UNIQUE(document_version_id, sequence_number)
);
CREATE INDEX IF NOT EXISTS idx_document_segments_version
    ON document_segments(document_version_id, sequence_number);

CREATE TABLE IF NOT EXISTS stage_runs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    stage_number INTEGER NOT NULL,
    stage_key TEXT NOT NULL,
    implementation TEXT NOT NULL,
    input_identity_json TEXT NOT NULL,
    input_identity_sha256 TEXT NOT NULL,
    parameters_json TEXT NOT NULL,
    parameters_sha256 TEXT NOT NULL,
    status TEXT NOT NULL,
    output_json TEXT,
    output_sha256 TEXT,
    created_at TEXT NOT NULL,
    completed_at TEXT,
    UNIQUE(stage_number, implementation, input_identity_sha256, parameters_sha256)
);
CREATE INDEX IF NOT EXISTS idx_stage_runs_stage
    ON stage_runs(stage_number, id);

CREATE TABLE IF NOT EXISTS run_items (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id INTEGER NOT NULL REFERENCES stage_runs(id) ON DELETE CASCADE,
    sequence_number INTEGER NOT NULL,
    kind TEXT NOT NULL,
    source_start INTEGER,
    source_end INTEGER,
    source_text TEXT,
    target_text TEXT,
    payload_json TEXT NOT NULL,
    payload_sha256 TEXT NOT NULL,
    UNIQUE(run_id, sequence_number, kind)
);
CREATE INDEX IF NOT EXISTS idx_run_items_run_kind
    ON run_items(run_id, kind, sequence_number);
"""


def bootstrap_database(path: Path | str) -> DatabaseHandle:
    path = Path(path).expanduser().resolve()
    path.parent.mkdir(parents=True, exist_ok=True)
    with connect(path) as connection:
        connection.execute("PRAGMA journal_mode=WAL")
        connection.execute("PRAGMA synchronous=FULL")
        connection.executescript(_SCHEMA)
        current = connection.execute(
            "SELECT value FROM rocketdict_meta WHERE key='schema_version'"
        ).fetchone()
        if current is None:
            connection.execute(
                "INSERT INTO rocketdict_meta(key,value) VALUES('schema_version',?)",
                (str(SCHEMA_VERSION),),
            )
        elif int(current["value"]) != SCHEMA_VERSION:
            raise RuntimeError(
                f"Unsupported RocketDict Product Core database schema {current['value']}; "
                f"expected {SCHEMA_VERSION}"
            )
        connection.commit()
    return DatabaseHandle(path)


@contextmanager
def transaction(path: Path | str) -> Iterator[sqlite3.Connection]:
    bootstrap_database(path)
    connection = connect(path)
    try:
        connection.execute("BEGIN IMMEDIATE")
        yield connection
        connection.commit()
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()


def meta(path: Path | str) -> dict[str, str]:
    with connect(path, readonly=True) as connection:
        rows = connection.execute("SELECT key,value FROM rocketdict_meta ORDER BY key").fetchall()
    return {str(row["key"]): str(row["value"]) for row in rows}


def project_summary(path: Path | str) -> dict[str, Any]:
    path = Path(path).expanduser().resolve()
    bootstrap_database(path)
    with connect(path, readonly=True) as connection:
        imports = int(connection.execute("SELECT COUNT(*) FROM import_events").fetchone()[0])
        documents = int(connection.execute("SELECT COUNT(*) FROM document_versions").fetchone()[0])
        stage_runs = int(connection.execute("SELECT COUNT(*) FROM stage_runs").fetchone()[0])
        completed = int(
            connection.execute("SELECT COUNT(*) FROM stage_runs WHERE status='completed'").fetchone()[0]
        )
    return {
        "schema": "rocketdict-product-core-project/1",
        "database": str(path),
        "database_exists": path.is_file(),
        "database_bytes": path.stat().st_size if path.is_file() else 0,
        "schema_version": SCHEMA_VERSION,
        "import_event_count": imports,
        "document_version_count": documents,
        "stage_run_count": stage_runs,
        "completed_stage_run_count": completed,
    }


def get_import_event(connection: sqlite3.Connection, import_event_id: int) -> dict[str, Any]:
    row = connection.execute("SELECT * FROM import_events WHERE id=?", (int(import_event_id),)).fetchone()
    if row is None:
        raise KeyError(f"Unknown import_event_id {import_event_id}")
    return dict(row)


def get_document(connection: sqlite3.Connection, document_version_id: int) -> dict[str, Any]:
    row = connection.execute(
        "SELECT * FROM document_versions WHERE id=?", (int(document_version_id),)
    ).fetchone()
    if row is None:
        raise KeyError(f"Unknown document_version_id {document_version_id}")
    return dict(row)


def get_document_segments(
    connection: sqlite3.Connection, document_version_id: int
) -> list[dict[str, Any]]:
    rows = connection.execute(
        "SELECT * FROM document_segments WHERE document_version_id=? ORDER BY sequence_number",
        (int(document_version_id),),
    ).fetchall()
    result: list[dict[str, Any]] = []
    for row in rows:
        item = dict(row)
        item["metadata"] = json.loads(item.pop("metadata_json"))
        result.append(item)
    return result


def find_completed_run(
    connection: sqlite3.Connection,
    *,
    stage_number: int,
    implementation: str,
    input_identity: dict[str, Any],
    parameters: dict[str, Any],
) -> dict[str, Any] | None:
    input_sha = canonical_sha256(input_identity)
    parameters_sha = canonical_sha256(parameters)
    row = connection.execute(
        """
        SELECT * FROM stage_runs
        WHERE stage_number=? AND implementation=?
          AND input_identity_sha256=? AND parameters_sha256=?
          AND status='completed'
        """,
        (int(stage_number), str(implementation), input_sha, parameters_sha),
    ).fetchone()
    if row is None:
        return None
    value = dict(row)
    value["input_identity"] = json.loads(value.pop("input_identity_json"))
    value["parameters"] = json.loads(value.pop("parameters_json"))
    value["output"] = json.loads(value["output_json"]) if value.get("output_json") else None
    return value


def begin_run(
    connection: sqlite3.Connection,
    *,
    stage_number: int,
    stage_key: str,
    implementation: str,
    input_identity: dict[str, Any],
    parameters: dict[str, Any],
) -> tuple[int, bool]:
    cached = find_completed_run(
        connection,
        stage_number=stage_number,
        implementation=implementation,
        input_identity=input_identity,
        parameters=parameters,
    )
    if cached is not None:
        return int(cached["id"]), True
    input_json = canonical_json(input_identity)
    params_json = canonical_json(parameters)
    input_sha = hashlib.sha256(input_json.encode("utf-8")).hexdigest()
    params_sha = hashlib.sha256(params_json.encode("utf-8")).hexdigest()
    existing = connection.execute(
        """
        SELECT id,status FROM stage_runs
        WHERE stage_number=? AND implementation=?
          AND input_identity_sha256=? AND parameters_sha256=?
        """,
        (int(stage_number), str(implementation), input_sha, params_sha),
    ).fetchone()
    if existing is not None:
        if str(existing["status"]) == "running":
            raise RuntimeError(
                f"Stage {stage_number} run {existing['id']} is already marked running; "
                "manual reconciliation is required before replay"
            )
        connection.execute("DELETE FROM stage_runs WHERE id=?", (int(existing["id"]),))
    cursor = connection.execute(
        """
        INSERT INTO stage_runs(
            stage_number,stage_key,implementation,input_identity_json,input_identity_sha256,
            parameters_json,parameters_sha256,status,created_at
        ) VALUES(?,?,?,?,?,?,?,?,?)
        """,
        (
            int(stage_number),
            str(stage_key),
            str(implementation),
            input_json,
            input_sha,
            params_json,
            params_sha,
            "running",
            utcnow(),
        ),
    )
    return int(cursor.lastrowid), False


def finish_run(
    connection: sqlite3.Connection,
    run_id: int,
    output: dict[str, Any],
) -> None:
    output_json = canonical_json(output)
    output_sha = hashlib.sha256(output_json.encode("utf-8")).hexdigest()
    cursor = connection.execute(
        """
        UPDATE stage_runs
        SET status='completed', output_json=?, output_sha256=?, completed_at=?
        WHERE id=? AND status='running'
        """,
        (output_json, output_sha, utcnow(), int(run_id)),
    )
    if cursor.rowcount != 1:
        raise RuntimeError(f"Stage run {run_id} is not in running state")


def fail_run(connection: sqlite3.Connection, run_id: int, error: dict[str, Any]) -> None:
    error_json = canonical_json({"error": error})
    connection.execute(
        """
        UPDATE stage_runs
        SET status='failed', output_json=?, output_sha256=?, completed_at=?
        WHERE id=? AND status='running'
        """,
        (
            error_json,
            hashlib.sha256(error_json.encode("utf-8")).hexdigest(),
            utcnow(),
            int(run_id),
        ),
    )


def get_run(connection: sqlite3.Connection, run_id: int) -> dict[str, Any]:
    row = connection.execute("SELECT * FROM stage_runs WHERE id=?", (int(run_id),)).fetchone()
    if row is None:
        raise KeyError(f"Unknown stage run id {run_id}")
    value = dict(row)
    value["input_identity"] = json.loads(value.pop("input_identity_json"))
    value["parameters"] = json.loads(value.pop("parameters_json"))
    value["output"] = json.loads(value["output_json"]) if value.get("output_json") else None
    return value


def replace_run_items(
    connection: sqlite3.Connection,
    run_id: int,
    items: Iterable[dict[str, Any]],
) -> int:
    connection.execute("DELETE FROM run_items WHERE run_id=?", (int(run_id),))
    count = 0
    for sequence, item in enumerate(items):
        kind = str(item.get("kind") or "item")
        payload = dict(item.get("payload") or {})
        payload_json = canonical_json(payload)
        connection.execute(
            """
            INSERT INTO run_items(
                run_id,sequence_number,kind,source_start,source_end,source_text,target_text,
                payload_json,payload_sha256
            ) VALUES(?,?,?,?,?,?,?,?,?)
            """,
            (
                int(run_id),
                int(item.get("sequence_number", sequence)),
                kind,
                item.get("source_start"),
                item.get("source_end"),
                item.get("source_text"),
                item.get("target_text"),
                payload_json,
                hashlib.sha256(payload_json.encode("utf-8")).hexdigest(),
            ),
        )
        count += 1
    return count


def get_run_items(
    connection: sqlite3.Connection,
    run_id: int,
    *,
    kind: str | None = None,
) -> list[dict[str, Any]]:
    if kind is None:
        rows = connection.execute(
            "SELECT * FROM run_items WHERE run_id=? ORDER BY sequence_number,id",
            (int(run_id),),
        ).fetchall()
    else:
        rows = connection.execute(
            "SELECT * FROM run_items WHERE run_id=? AND kind=? ORDER BY sequence_number,id",
            (int(run_id), str(kind)),
        ).fetchall()
    result: list[dict[str, Any]] = []
    for row in rows:
        item = dict(row)
        item["payload"] = json.loads(item.pop("payload_json"))
        result.append(item)
    return result
