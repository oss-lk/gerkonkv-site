from __future__ import annotations

import base64
import hashlib
import json
from pathlib import Path
import zlib

ROOT = Path(__file__).resolve().parents[1]
PART = ROOT / "rocketdict/payload/stage8-overlay/part-000.b64"
OUT = ROOT / "rocketdict-recovery-prefix"


def parse_tar_prefix(data: bytes) -> list[dict]:
    out: list[dict] = []
    off = 0
    while off + 512 <= len(data):
        hdr = data[off:off+512]
        if hdr == b"\0" * 512:
            break
        name = hdr[:100].split(b"\0", 1)[0].decode("utf-8", "replace")
        size_raw = hdr[124:136].split(b"\0", 1)[0].strip() or b"0"
        try:
            size = int(size_raw, 8)
        except ValueError:
            out.append({"offset": off, "name": name, "header_valid": False, "size_raw": size_raw.decode("ascii", "replace")})
            break
        typeflag = hdr[156:157].decode("ascii", "replace")
        body_start = off + 512
        body_end = body_start + size
        complete = body_end <= len(data)
        entry = {
            "offset": off,
            "name": name,
            "size": size,
            "typeflag": typeflag,
            "complete": complete,
        }
        if complete and typeflag in ("", "0", "\x00"):
            body = data[body_start:body_end]
            entry["sha256"] = hashlib.sha256(body).hexdigest()
            p = OUT / "members" / name
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_bytes(body)
        out.append(entry)
        if not complete:
            break
        off = body_start + ((size + 511) // 512) * 512
    return out


def main() -> None:
    encoded = PART.read_text(encoding="ascii").strip()
    raw = base64.b64decode(encoded, validate=True)
    d = zlib.decompressobj(16 + zlib.MAX_WBITS)
    try:
        decoded = d.decompress(raw)
        error = None
    except zlib.error as exc:
        decoded = b""
        error = repr(exc)
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "part-000.decoded-prefix.gz").write_bytes(raw)
    (OUT / "decompressed-tar-prefix.bin").write_bytes(decoded)
    members = parse_tar_prefix(decoded)
    report = {
        "schema": "rocketdict-stage8-overlay-prefix-recovery/1",
        "part_path": str(PART.relative_to(ROOT)),
        "encoded_chars": len(encoded),
        "decoded_bytes": len(raw),
        "part_decoded_sha256": hashlib.sha256(raw).hexdigest(),
        "decompressed_prefix_bytes": len(decoded),
        "decompressed_prefix_sha256": hashlib.sha256(decoded).hexdigest(),
        "zlib_error": error,
        "gzip_eof": bool(d.eof) if error is None else False,
        "unused_data_bytes": len(d.unused_data) if error is None else 0,
        "members": members,
    }
    (OUT / "report.json").write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
