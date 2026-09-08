from pathlib import Path

path = Path(__file__).with_name("stage12_block_section_identifier_migration.py")
text = path.read_text(encoding="utf-8")
old = '''def replace_once(text: str, old: str, new: str, *, label: str) -> str:\n    count = text.count(old)\n    if count != 1:\n        raise RuntimeError(f"{label}: expected exactly one match, found {count}")\n    return text.replace(old, new, 1)\n'''
new = '''def replace_once(text: str, old: str, new: str, *, label: str) -> str:\n    count = text.count(old)\n    expected = 2 if label == "request exclusion" else 1\n    if count != expected:\n        raise RuntimeError(f"{label}: expected exactly {expected} match(es), found {count}")\n    return text.replace(old, new, 1)\n'''
if text.count(old) != 1:
    raise RuntimeError("migration helper definition drift")
path.write_text(text.replace(old, new, 1), encoding="utf-8")
print("migration request-exclusion anchor fixed")
