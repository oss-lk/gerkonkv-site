from __future__ import annotations

import argparse
import hashlib
import html
import json
from pathlib import Path
import re
import sys
from typing import Any

from rocketdict.database import (
    bootstrap_database,
    canonical_sha256,
    connect,
    database_path,
    get_import_event,
    utcnow,
)

SCHEMA = "rocketdict-product-core-interpretation/1"
SUPPORTED_FORMATS = {"txt", "srt", "vtt", "ass", "ssa"}
_TAG = re.compile(r"<[^>]+>")
_ASS_OVERRIDE = re.compile(r"\{[^}]*\}")
_TIMESTAMP = re.compile(
    r"^\s*(?P<h>\d{1,2}):(?P<m>\d{2}):(?P<s>\d{2})[,.](?P<ms>\d{3})\s*$"
)
_VTT_TIMESTAMP = re.compile(
    r"^\s*(?:(?P<h>\d{1,2}):)?(?P<m>\d{2}):(?P<s>\d{2})\.(?P<ms>\d{3})\s*$"
)


def _decode(raw: bytes, declared: str | None) -> tuple[str, str]:
    if declared:
        try:
            return raw.decode(declared), declared
        except (LookupError, UnicodeDecodeError) as exc:
            raise RuntimeError(f"Source cannot be decoded as declared encoding {declared!r}: {exc}") from exc
    if raw.startswith(b"\xef\xbb\xbf"):
        return raw.decode("utf-8-sig"), "utf-8-sig"
    if raw.startswith((b"\xff\xfe", b"\xfe\xff")):
        return raw.decode("utf-16"), "utf-16"
    try:
        return raw.decode("utf-8"), "utf-8"
    except UnicodeDecodeError as exc:
        raise RuntimeError(
            "Source is not valid UTF-8 and has no supported BOM; pass --encoding explicitly"
        ) from exc


def _visible_text(value: str) -> str:
    value = html.unescape(_TAG.sub("", value))
    value = value.replace("\r\n", "\n").replace("\r", "\n")
    lines = [re.sub(r"[ \t]+", " ", line).strip() for line in value.split("\n")]
    return "\n".join(line for line in lines if line).strip()


def _timestamp_ms(value: str, *, vtt: bool = False) -> int:
    match = (_VTT_TIMESTAMP if vtt else _TIMESTAMP).match(value)
    if not match:
        raise ValueError(value)
    hours = int(match.group("h") or 0)
    return (((hours * 60 + int(match.group("m"))) * 60 + int(match.group("s"))) * 1000 + int(match.group("ms")))


def _parse_arrow(value: str, *, vtt: bool = False) -> tuple[int, int]:
    if "-->" not in value:
        raise ValueError(value)
    left, right = value.split("-->", 1)
    # VTT cue settings follow the end timestamp.
    right_ts = right.strip().split()[0]
    start = _timestamp_ms(left.strip(), vtt=vtt)
    end = _timestamp_ms(right_ts, vtt=vtt)
    if end < start:
        raise RuntimeError(f"Subtitle cue ends before it starts: {value!r}")
    return start, end


def _parse_srt(text: str) -> list[dict[str, Any]]:
    blocks = re.split(r"\n\s*\n", text.replace("\r\n", "\n").replace("\r", "\n").strip())
    result: list[dict[str, Any]] = []
    for block_index, block in enumerate(blocks):
        lines = [line.rstrip() for line in block.split("\n")]
        if not lines or not any(line.strip() for line in lines):
            continue
        cursor = 0
        cue_id = None
        if re.fullmatch(r"\d+", lines[0].strip()):
            cue_id = lines[0].strip()
            cursor = 1
        if cursor >= len(lines) or "-->" not in lines[cursor]:
            raise RuntimeError(f"Invalid SRT block {block_index + 1}: missing timestamp line")
        try:
            start_ms, end_ms = _parse_arrow(lines[cursor], vtt=False)
        except ValueError as exc:
            raise RuntimeError(f"Invalid SRT timestamp in block {block_index + 1}: {lines[cursor]!r}") from exc
        raw_text = "\n".join(lines[cursor + 1 :])
        visible = _visible_text(raw_text)
        if not visible:
            continue
        result.append(
            {
                "text": visible,
                "start_ms": start_ms,
                "end_ms": end_ms,
                "metadata": {"cue_id": cue_id, "raw_text": raw_text},
            }
        )
    if text.strip() and not result:
        raise RuntimeError("SRT source contains no valid non-empty cues")
    return result


def _parse_vtt(text: str) -> list[dict[str, Any]]:
    normalized = text.replace("\r\n", "\n").replace("\r", "\n")
    lines = normalized.split("\n")
    i = 0
    if lines and lines[0].lstrip("\ufeff").strip().startswith("WEBVTT"):
        i = 1
    result: list[dict[str, Any]] = []
    while i < len(lines):
        line = lines[i].strip()
        if not line:
            i += 1
            continue
        if line.startswith(("NOTE", "STYLE", "REGION")):
            i += 1
            while i < len(lines) and lines[i].strip():
                i += 1
            continue
        cue_id = None
        timestamp_line = line
        if "-->" not in timestamp_line:
            cue_id = line
            i += 1
            if i >= len(lines):
                raise RuntimeError("VTT cue identifier is not followed by a timestamp")
            timestamp_line = lines[i].strip()
        if "-->" not in timestamp_line:
            raise RuntimeError(f"Invalid VTT cue near line {i + 1}: missing timestamp")
        try:
            start_ms, end_ms = _parse_arrow(timestamp_line, vtt=True)
        except ValueError as exc:
            raise RuntimeError(f"Invalid VTT timestamp near line {i + 1}: {timestamp_line!r}") from exc
        i += 1
        text_lines: list[str] = []
        while i < len(lines) and lines[i].strip():
            text_lines.append(lines[i])
            i += 1
        raw_text = "\n".join(text_lines)
        visible = _visible_text(raw_text)
        if visible:
            result.append(
                {
                    "text": visible,
                    "start_ms": start_ms,
                    "end_ms": end_ms,
                    "metadata": {"cue_id": cue_id, "raw_text": raw_text},
                }
            )
    if text.strip() and not result:
        raise RuntimeError("VTT source contains no valid non-empty cues")
    return result


def _split_ass_fields(value: str, count: int) -> list[str]:
    return value.split(",", max(0, count - 1))


def _ass_time_ms(value: str) -> int:
    # ASS/SSA uses H:MM:SS.cc (centiseconds).
    match = re.fullmatch(r"\s*(\d+):(\d{2}):(\d{2})[.](\d{2})\s*", value)
    if not match:
        raise ValueError(value)
    h, m, s, cs = (int(part) for part in match.groups())
    return (((h * 60 + m) * 60 + s) * 1000) + cs * 10


def _parse_ass(text: str) -> list[dict[str, Any]]:
    lines = text.replace("\r\n", "\n").replace("\r", "\n").split("\n")
    in_events = False
    fields: list[str] = []
    result: list[dict[str, Any]] = []
    for line_number, line in enumerate(lines, start=1):
        stripped = line.strip()
        if stripped.startswith("[") and stripped.endswith("]"):
            in_events = stripped.casefold() == "[events]"
            continue
        if not in_events or not stripped:
            continue
        if stripped.casefold().startswith("format:"):
            fields = [part.strip().casefold() for part in stripped.split(":", 1)[1].split(",")]
            continue
        if not stripped.casefold().startswith("dialogue:"):
            continue
        if not fields:
            raise RuntimeError("ASS/SSA [Events] section contains Dialogue before Format")
        values = _split_ass_fields(stripped.split(":", 1)[1].lstrip(), len(fields))
        if len(values) != len(fields):
            raise RuntimeError(f"ASS/SSA Dialogue field count mismatch at line {line_number}")
        row = {fields[index]: values[index] for index in range(len(fields))}
        if "text" not in row or "start" not in row or "end" not in row:
            raise RuntimeError("ASS/SSA Format must include Start, End and Text")
        try:
            start_ms = _ass_time_ms(row["start"])
            end_ms = _ass_time_ms(row["end"])
        except ValueError as exc:
            raise RuntimeError(f"Invalid ASS/SSA timestamp at line {line_number}") from exc
        if end_ms < start_ms:
            raise RuntimeError(f"ASS/SSA cue ends before it starts at line {line_number}")
        raw_text = row["text"].replace(r"\N", "\n").replace(r"\n", "\n")
        raw_text = _ASS_OVERRIDE.sub("", raw_text)
        visible = _visible_text(raw_text)
        if not visible:
            continue
        metadata = {
            key: value
            for key, value in row.items()
            if key not in {"text", "start", "end"}
        }
        metadata["raw_text"] = row["text"]
        result.append(
            {
                "text": visible,
                "start_ms": start_ms,
                "end_ms": end_ms,
                "metadata": metadata,
            }
        )
    if text.strip() and not result:
        raise RuntimeError("ASS/SSA source contains no valid non-empty Dialogue events")
    return result


def _segments(selected_format: str, text: str) -> list[dict[str, Any]]:
    if selected_format == "txt":
        normalized = text.replace("\r\n", "\n").replace("\r", "\n")
        if not normalized.strip():
            raise RuntimeError("Text source is empty")
        return [{"text": normalized, "start_ms": None, "end_ms": None, "metadata": {}}]
    if selected_format == "srt":
        return _parse_srt(text)
    if selected_format == "vtt":
        return _parse_vtt(text)
    if selected_format in {"ass", "ssa"}:
        return _parse_ass(text)
    raise RuntimeError(f"Unsupported Product interpretation format {selected_format!r}")


def interpret_source(
    import_event_id: int,
    *,
    data_root: Path | str,
    declared_format: str | None = None,
    declared_encoding: str | None = None,
    force_text: bool = False,
) -> dict[str, Any]:
    root = Path(data_root).expanduser().resolve()
    db = database_path(root)
    bootstrap_database(db)
    with connect(db) as connection:
        imported = get_import_event(connection, int(import_event_id))
        object_path = (root / str(imported["object_path"])).resolve()
        try:
            object_path.relative_to(root)
        except ValueError as exc:
            raise RuntimeError("Import event object path escapes data root") from exc
        if not object_path.is_file():
            raise RuntimeError(f"Immutable imported object is missing: {object_path}")
        raw = object_path.read_bytes()
        observed_sha = hashlib.sha256(raw).hexdigest()
        if observed_sha != str(imported["source_sha256"]):
            raise RuntimeError("Immutable imported object SHA-256 changed")
        text, encoding = _decode(raw, declared_encoding)
        selected_format = "txt" if force_text else str(declared_format or "txt").casefold()
        if selected_format not in SUPPORTED_FORMATS:
            raise RuntimeError(
                f"Unsupported Product interpretation format {selected_format!r}; "
                f"supported: {sorted(SUPPORTED_FORMATS)}"
            )
        parsed = _segments(selected_format, text)
        content_parts: list[str] = []
        stored_segments: list[dict[str, Any]] = []
        cursor = 0
        for sequence, segment in enumerate(parsed):
            visible = str(segment["text"])
            if sequence:
                content_parts.append("\n")
                cursor += 1
            start = cursor
            content_parts.append(visible)
            cursor += len(visible)
            stored_segments.append(
                {
                    "sequence_number": sequence,
                    "start_char": start,
                    "end_char": cursor,
                    "start_ms": segment.get("start_ms"),
                    "end_ms": segment.get("end_ms"),
                    "text": visible,
                    "metadata": dict(segment.get("metadata") or {}),
                }
            )
        content = "".join(content_parts)
        text_sha = hashlib.sha256(content.encode("utf-8")).hexdigest()
        interpretation_identity = {
            "import_event_id": int(import_event_id),
            "source_sha256": str(imported["source_sha256"]),
            "selected_format": selected_format,
            "selected_encoding": encoding,
            "force_text": bool(force_text),
            "text_sha256": text_sha,
            "segments_sha256": canonical_sha256(
                [
                    {
                        "sequence_number": row["sequence_number"],
                        "start_char": row["start_char"],
                        "end_char": row["end_char"],
                        "start_ms": row["start_ms"],
                        "end_ms": row["end_ms"],
                        "text": row["text"],
                    }
                    for row in stored_segments
                ]
            ),
        }
        interpretation_key = canonical_sha256(interpretation_identity)
        existing = connection.execute(
            "SELECT * FROM document_versions WHERE interpretation_key=?",
            (interpretation_key,),
        ).fetchone()
        cache_hit = existing is not None
        if existing is None:
            cursor_db = connection.execute(
                """
                INSERT INTO document_versions(
                    import_event_id,selected_format,selected_encoding,interpretation_key,
                    text_sha256,char_count,segment_count,content_text,created_at
                ) VALUES(?,?,?,?,?,?,?,?,?)
                """,
                (
                    int(import_event_id),
                    selected_format,
                    encoding,
                    interpretation_key,
                    text_sha,
                    len(content),
                    len(stored_segments),
                    content,
                    utcnow(),
                ),
            )
            document_version_id = int(cursor_db.lastrowid)
            for row in stored_segments:
                connection.execute(
                    """
                    INSERT INTO document_segments(
                        document_version_id,sequence_number,start_char,end_char,start_ms,end_ms,text,metadata_json
                    ) VALUES(?,?,?,?,?,?,?,?)
                    """,
                    (
                        document_version_id,
                        row["sequence_number"],
                        row["start_char"],
                        row["end_char"],
                        row["start_ms"],
                        row["end_ms"],
                        row["text"],
                        json.dumps(row["metadata"], ensure_ascii=False, sort_keys=True),
                    ),
                )
            connection.commit()
        else:
            document_version_id = int(existing["id"])
            if int(existing["segment_count"]) != len(stored_segments):
                raise RuntimeError("Cached interpretation segment count drift")
            if str(existing["text_sha256"]) != text_sha:
                raise RuntimeError("Cached interpretation text hash drift")

    return {
        "schema": SCHEMA,
        "status": "interpreted",
        "import_event_id": int(import_event_id),
        "document_version_id": document_version_id,
        "selected_format": selected_format,
        "selected_encoding": encoding,
        "source_sha256": str(imported["source_sha256"]),
        "text_sha256": text_sha,
        "char_count": len(content),
        "segment_count": len(stored_segments),
        "interpretation_key": interpretation_key,
        "cache_hit": cache_hit,
    }


def parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="python -m rocketdict.interpretation.cli")
    p.add_argument("import_event_id", type=int)
    p.add_argument("--data-root", type=Path, required=True)
    p.add_argument("--format", dest="declared_format")
    p.add_argument("--encoding", dest="declared_encoding")
    p.add_argument("--force-text", action="store_true")
    return p


def main(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    try:
        payload = interpret_source(
            args.import_event_id,
            data_root=args.data_root,
            declared_format=args.declared_format,
            declared_encoding=args.declared_encoding,
            force_text=args.force_text,
        )
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
