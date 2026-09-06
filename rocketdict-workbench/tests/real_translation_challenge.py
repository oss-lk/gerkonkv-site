from __future__ import annotations

"""Run the current maintained Product translation boundary on frozen Opticks R1.

This is a research/selection harness, not a release acceptance gate.  It
reconstructs the source-only independent R1 selection that was frozen before
its first historical MT evaluation, verifies the exact selection identity, and
then measures the *current* maintained Product Stage8→15 defaults.  Historical
v9/F96 outputs are never imported as Product output or treated as current
implementation evidence.
"""

from collections import Counter, defaultdict
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
from typing import Any

from nltk.stem import PorterStemmer

from rocketdict.database import connect, get_run_items
from rocketdict_workbench.core import RocketDictCore
from rocketdict_workbench.product_preflight import build_product_preflight
from rocketdict_workbench.project import WorkbenchProject

SCHEMA = "rocketdict-maintained-r1-translation-challenge/1"
OPTICKS_SHA256 = "1e25ec2c54fc6e9fa05d7f0a663e05cf2ee671231c65731f4845df2539dfb217"
EXPECTED_R0_SELECTION_SHA256 = "ea193d5f589dd053b768536c9f8bb4bac90316eed79f5244592357607e02b3fe"
EXPECTED_R1_SELECTION_SHA256 = "665f1ee5ad1778ac8ab1b1b2ae0da7e17a05a0321b8a25cb6d47d74294f4af32"
R1_SALT = "rocketdict-stage8-independent-validation-r1-2026-08-27"
TARGET_WORDS = 5000
R1_QUOTAS = {
    "technical": 1200,
    "numeric_dense": 1200,
    "mixed_case_term": 1200,
    "numeric": 700,
    "general": 700,
}

WORD_RE = re.compile(r"\b[\w’'-]+\b", flags=re.UNICODE)
SELECT_NUMERIC_RE = re.compile(
    r"(?<!\w)(?:\d+-\d+/\d+|\d+/\d+|\d{1,3}(?:[\s\u00a0\u202f]\d{3})+|\d+)(?!\w)",
    flags=re.UNICODE,
)
EVAL_NUMERIC_RE = re.compile(
    r"(?<!\d)("
    r"\d+\s*-\s*\d+\s*/\s*\d+(?:st|nd|rd|th)?"
    r"|\d+\s*/\s*\d+(?:st|nd|rd|th)?"
    r"|\d{1,3}(?:(?:,\d{3})|(?:[\s\u00a0\u202f]\d{3}))+(?:st|nd|rd|th)?"
    r"|\d+(?:st|nd|rd|th)?"
    r")(?!\d)",
    flags=re.IGNORECASE | re.UNICODE,
)
FIG_RE = re.compile(r"\[in\s+_Fig\._\s+(?P<number>\d+)\.\]", flags=re.IGNORECASE)
EXTREME_CLAUSE_RE = re.compile(
    r"at\s+the\s+height\s+of\s+"
    r"(?P<h1>\d+)\s*,\s*(?P<h2>\d+)\s*,\s*(?P<h3>\d+)\s+Miles\s*,\s*"
    r"it\s+is\s+about\s+"
    r"(?P<x>\d{7,})\s*,\s*(?P<y>\d{7,})\s*,\s*or\s+(?P<z>\d{7,})\s+"
    r"times\s+rarer",
    flags=re.IGNORECASE,
)
STRUCTURAL_ID_RE = re.compile(r"(?ms)(?:^|\n)\d+(?:\.[A-Za-z]+)+\.\d+\.\s*$")
TABLE_RULE_RE = re.compile(r"(?m)^[\-+]{12,}\s*$")
GREEK_SOURCE_RE = re.compile(r"\[Greek:\s*([^\]]*)\]", flags=re.IGNORECASE)
GREEK_TARGET_RE = re.compile(
    r"\[(?:Greek|греч\.?|греческ[^:\]]*)\s*:\s*([^\]]*)\]",
    flags=re.IGNORECASE,
)
ILLUSTRATION_SOURCE_RE = re.compile(r"\[Illustration:\s*([^\]]*)\]", flags=re.IGNORECASE)
ILLUSTRATION_TARGET_RE = re.compile(
    r"\[(?:Illustration|Иллюстрация)\s*:\s*([^\]]*)\]", flags=re.IGNORECASE
)
FOOTNOTE_RE = re.compile(r"\[([A-Z])\]")
EMPH_RE = re.compile(r"_([^_\n]{1,80})_")
COMBINED_GREEK_SOURCE_RE = re.compile(r"_([A-Za-z]{1,3})\[Greek:\s*([^\]]+)\]_", flags=re.IGNORECASE)
COMBINED_GREEK_TARGET_RE = re.compile(
    r"_([A-Za-z]{1,3})\[(?:Greek|греч\.?|греческ[^:\]]*)\s*:\s*([^\]]+)\]_",
    flags=re.IGNORECASE,
)
CYR_RE = re.compile(r"[А-Яа-яЁё]")
ALPHA_RE = re.compile(r"[A-Za-zА-Яа-яЁё]")
STEMMER = PorterStemmer()


def _sha_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _sha_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def word_count(text: str) -> int:
    return len(WORD_RE.findall(text))


def _protect_fig_dots(text: str) -> str:
    return re.sub(
        r"(_Fig)_\.(?=\s+\d+\.\])",
        lambda match: match.group(1) + "_§FIGDOT§",
        text,
        flags=re.IGNORECASE,
    )


def split_units(text: str) -> list[dict[str, Any]]:
    protected = _protect_fig_dots(text.replace("\r\n", "\n"))
    raw = re.split(r"(?<=[.!?])\s+(?=[A-Z_\[\"'])", protected)
    units: list[dict[str, Any]] = []
    for occurrence, item in enumerate(raw):
        item = item.replace("§FIGDOT§", ".").strip()
        words = word_count(item)
        if 4 <= words <= 220:
            units.append({"occurrence": occurrence, "source": item, "words": words})
    return units


def _r0_category(source: str) -> str:
    if EXTREME_CLAUSE_RE.search(source):
        return "I-extreme"
    if FIG_RE.search(source):
        return "H-figure"
    if SELECT_NUMERIC_RE.search(source):
        return "G-numeric"
    return "general"


def _rank(unit: dict[str, Any], salt: str) -> str:
    return _sha_text(f"{salt}\0{unit['occurrence']}\0{unit['source']}")


def select_r0(units: list[dict[str, Any]]) -> list[dict[str, Any]]:
    buckets: dict[str, list[dict[str, Any]]] = {
        key: [] for key in ("I-extreme", "H-figure", "G-numeric", "general")
    }
    for item in units:
        row = dict(item)
        row["category"] = _r0_category(str(row["source"]))
        buckets[row["category"]].append(row)
    quotas = {"I-extreme": 500, "H-figure": 900, "G-numeric": 2400, "general": 1200}
    selected: dict[int, dict[str, Any]] = {}
    for name in ("I-extreme", "H-figure", "G-numeric", "general"):
        used = 0
        for row in sorted(buckets[name], key=lambda value: _rank(value, f"stage8-ghi-{name}-v1")):
            if int(row["occurrence"]) in selected:
                continue
            if used >= quotas[name] and selected:
                break
            selected[int(row["occurrence"])] = row
            used += int(row["words"])
    current = sum(int(row["words"]) for row in selected.values())
    if current < TARGET_WORDS:
        remaining = [row for row in units if int(row["occurrence"]) not in selected]
        for raw in sorted(remaining, key=lambda value: _rank(value, "stage8-ghi-fill-v1")):
            row = dict(raw)
            row["category"] = _r0_category(str(row["source"]))
            selected[int(row["occurrence"])] = row
            current += int(row["words"])
            if current >= TARGET_WORDS:
                break
    result = sorted(selected.values(), key=lambda value: int(value["occurrence"]))
    serialized = "".join(f"{row['occurrence']}\t{row['category']}\t{row['source']}\n" for row in result)
    observed = _sha_text(serialized)
    if observed != EXPECTED_R0_SELECTION_SHA256:
        raise RuntimeError(f"Frozen R0 selector drift: {observed} != {EXPECTED_R0_SELECTION_SHA256}")
    return result


def _protected_mask(text: str) -> list[bool]:
    mask = [False] * len(text)
    square = 0
    emphasis = False
    for index, char in enumerate(text):
        if char == "_" and square == 0:
            emphasis = not emphasis
            mask[index] = True
            continue
        if char == "[" and not emphasis:
            square += 1
        if square or emphasis:
            mask[index] = True
        if char == "]" and square and not emphasis:
            square -= 1
    return mask


def _mixed_case_stems(source: str) -> dict[str, dict[str, Any]]:
    mask = _protected_mask(source)
    by_stem: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for match in re.finditer(r"(?<![A-Za-z])([A-Za-z]+)(?![A-Za-z])", source):
        if any(mask[match.start():match.end()]):
            continue
        word = match.group(1)
        if len(word) < 5:
            continue
        stem = STEMMER.stem(word.casefold())
        by_stem[stem].append(
            {
                "surface": word,
                "titlecase": word[0].isupper() and word[1:].islower(),
                "lowercase": word.islower(),
            }
        )
    return {
        stem: {"surfaces": [row["surface"] for row in rows]}
        for stem, rows in by_stem.items()
        if len(rows) >= 2
        and any(row["titlecase"] for row in rows)
        and any(row["lowercase"] for row in rows)
    }


def _is_symbolic_emphasis(inner: str) -> bool:
    value = inner.strip()
    if re.fullmatch(r"[A-Za-z]{1,3}", value):
        return True
    atom = r"(?:\d+[A-Za-z]|[A-Za-z]\d+)"
    return bool(re.fullmatch(rf"{atom}(?:\s+{atom})*", value))


def _symbolic_emphasis_sequence(text: str) -> list[str]:
    return [
        match.group(1).strip()
        for match in EMPH_RE.finditer(text)
        if _is_symbolic_emphasis(match.group(1))
    ]


def _normalize_numeric(token: str) -> str:
    value = token.casefold()
    value = re.sub(r"(?:st|nd|rd|th)$", "", value)
    return re.sub(r"[\s,\u00a0\u202f]", "", value)


def _numeric_sequence(text: str) -> list[str]:
    return [_normalize_numeric(match.group(1)) for match in EVAL_NUMERIC_RE.finditer(text)]


def _numeric_counter(text: str) -> Counter[str]:
    return Counter(_numeric_sequence(text))


def _is_technical(source: str) -> bool:
    return bool(
        GREEK_SOURCE_RE.search(source)
        or ILLUSTRATION_SOURCE_RE.search(source)
        or FOOTNOTE_RE.search(source)
        or _symbolic_emphasis_sequence(source)
        or FIG_RE.search(source)
        or TABLE_RULE_RE.search(source)
        or STRUCTURAL_ID_RE.search(source)
    )


def _r1_category(source: str) -> str:
    if _is_technical(source):
        return "technical"
    numeric_count = sum(_numeric_counter(source).values())
    if numeric_count >= 4:
        return "numeric_dense"
    if _mixed_case_stems(source):
        return "mixed_case_term"
    if numeric_count:
        return "numeric"
    return "general"


def select_r1(units: list[dict[str, Any]], excluded: set[int]) -> tuple[list[dict[str, Any]], str]:
    eligible: list[dict[str, Any]] = []
    for raw in units:
        if int(raw["occurrence"]) in excluded:
            continue
        row = dict(raw)
        row["category"] = _r1_category(str(row["source"]))
        eligible.append(row)
    buckets = {name: [] for name in R1_QUOTAS}
    for row in eligible:
        buckets[row["category"]].append(row)
    selected: dict[int, dict[str, Any]] = {}
    for name, budget in R1_QUOTAS.items():
        used = 0
        for row in sorted(buckets[name], key=lambda value: _rank(value, f"{R1_SALT}:{name}")):
            if used >= budget and used > 0:
                break
            selected[int(row["occurrence"])] = row
            used += int(row["words"])
    current = sum(int(row["words"]) for row in selected.values())
    if current < TARGET_WORDS:
        remaining = [row for row in eligible if int(row["occurrence"]) not in selected]
        for row in sorted(remaining, key=lambda value: _rank(value, f"{R1_SALT}:fill")):
            selected[int(row["occurrence"])] = row
            current += int(row["words"])
            if current >= TARGET_WORDS:
                break
    result = sorted(selected.values(), key=lambda value: int(value["occurrence"]))
    serialized = "".join(
        f"{row['occurrence']}\t{row['category']}\t{row['words']}\t{row['source']}\n"
        for row in result
    )
    observed = _sha_text(serialized)
    if observed != EXPECTED_R1_SELECTION_SHA256:
        raise RuntimeError(f"Frozen R1 selector drift: {observed} != {EXPECTED_R1_SELECTION_SHA256}")
    if len(result) != 103 or sum(int(row["words"]) for row in result) != 5143:
        raise RuntimeError("Frozen R1 cardinality/word count drift")
    return result, serialized


def _call(core: RocketDictCore, database: Path, operation: str, **params: Any) -> dict[str, Any]:
    return dict(
        core.api(
            database,
            "call",
            operation,
            "--params",
            json.dumps(params, ensure_ascii=False, sort_keys=True, separators=(",", ":")),
            timeout=1800,
        )
    )


def _profile_stage(preflight: dict[str, Any], stage_number: int) -> tuple[str, dict[str, Any]]:
    row = ((preflight.get("profile") or {}).get("stages") or {}).get(str(stage_number))
    if not isinstance(row, dict):
        raise RuntimeError(f"Product profile lost stage {stage_number}")
    return str(row["implementation"]), dict(row.get("parameters") or {})


def _is_subsequence(required: list[str], observed: list[str]) -> bool:
    cursor = 0
    for value in observed:
        if cursor < len(required) and value == required[cursor]:
            cursor += 1
    return cursor == len(required)


def _payloads(regex: re.Pattern[str], text: str) -> list[str]:
    return [match.group(1).strip() for match in regex.finditer(text)]


def _combined(regex: re.Pattern[str], text: str) -> list[list[str]]:
    return [[match.group(1), match.group(2).strip()] for match in regex.finditer(text)]


def _critical_token_guard(source: str, target: str) -> dict[str, Any]:
    checks = {
        "greek_payloads": {"source": _payloads(GREEK_SOURCE_RE, source), "target": _payloads(GREEK_TARGET_RE, target)},
        "combined_greek_variables": {"source": _combined(COMBINED_GREEK_SOURCE_RE, source), "target": _combined(COMBINED_GREEK_TARGET_RE, target)},
        "symbolic_emphasis": {"source": _symbolic_emphasis_sequence(source), "target": _symbolic_emphasis_sequence(target)},
        "footnote_markers": {"source": _payloads(FOOTNOTE_RE, source), "target": _payloads(FOOTNOTE_RE, target)},
        "illustration_payloads": {"source": _payloads(ILLUSTRATION_SOURCE_RE, source), "target": _payloads(ILLUSTRATION_TARGET_RE, target)},
    }
    failed = [name for name, row in checks.items() if row["source"] != row["target"]]
    return {"contract": "stage8-critical-technical-token-integrity/1", "checks": checks, "failed_checks": failed, "passed": not failed}


def _delimiter_guard(source: str, target: str) -> dict[str, Any]:
    rows: dict[str, Any] = {}
    passed = True
    for name, left, right in (("square", "[", "]"), ("round", "(", ")")):
        source_counts = (source.count(left), source.count(right))
        target_counts = (target.count(left), target.count(right))
        source_balanced = source_counts[0] == source_counts[1]
        exact = target_counts == source_counts if source_balanced else target_counts[0] == target_counts[1]
        rows[name] = {
            "source": list(source_counts),
            "target": list(target_counts),
            "source_balanced": source_balanced,
            "passed": exact,
        }
        passed = passed and exact
    return {"contract": "stage8-balanced-delimiter-integrity/1", "delimiters": rows, "passed": passed}


def _prose_cyrillic_share(text: str) -> float:
    # Historical R-v1 measurement surface: ignore source-derived [] and _..._
    # payloads instead of penalizing their required Latin content as Russian prose.
    prose = re.sub(r"\[[^\]]*\]", " ", text)
    prose = re.sub(r"_[^_\n]*_", " ", prose)
    alpha = ALPHA_RE.findall(prose)
    if not alpha:
        return 0.0
    return len(CYR_RE.findall(prose)) / len(alpha)


def _extended_diagnostics(rows: list[dict[str, Any]]) -> dict[str, Any]:
    order_failures: list[dict[str, Any]] = []
    critical_failures: list[dict[str, Any]] = []
    delimiter_failures: list[dict[str, Any]] = []
    shares: list[float] = []
    for row in rows:
        source = str(row.get("source_text") or "")
        target = str(row.get("target_text") or "")
        required = _numeric_sequence(source)
        observed = _numeric_sequence(target)
        if not _is_subsequence(required, observed):
            order_failures.append(
                {
                    "segment_sequence": int(row["sequence_number"]),
                    "source_text": source,
                    "target_text": target,
                    "required_sequence": required,
                    "observed_sequence": observed,
                }
            )
        critical = _critical_token_guard(source, target)
        if not critical["passed"]:
            critical_failures.append(
                {
                    "segment_sequence": int(row["sequence_number"]),
                    "source_text": source,
                    "target_text": target,
                    "failed_checks": critical["failed_checks"],
                    "checks": critical["checks"],
                }
            )
        delimiters = _delimiter_guard(source, target)
        if not delimiters["passed"]:
            delimiter_failures.append(
                {
                    "segment_sequence": int(row["sequence_number"]),
                    "source_text": source,
                    "target_text": target,
                    "detail": delimiters,
                }
            )
        shares.append(_prose_cyrillic_share(target))
    return {
        "numeric_order_contract": "stage8-explicit-numeric-order/1",
        "numeric_order_failure_count": len(order_failures),
        "numeric_order_failures": order_failures,
        "critical_token_contract": "stage8-critical-technical-token-integrity/1",
        "critical_token_failure_count": len(critical_failures),
        "critical_token_failures": critical_failures,
        "delimiter_contract": "stage8-balanced-delimiter-integrity/1",
        "delimiter_failure_count": len(delimiter_failures),
        "delimiter_failures": delimiter_failures,
        "protected_aware_language_contract": "stage8-protected-aware-language-share/1-measurement-only",
        "mean_prose_cyrillic_share": sum(shares) / len(shares) if shares else 0.0,
    }


def main() -> int:
    root = Path(os.environ.get("ROCKETDICT_TRANSLATION_CHALLENGE_ROOT", "work/translation-challenge")).resolve()
    opticks = Path(os.environ["ROCKETDICT_OPTICKS_SOURCE"]).resolve()
    if root.exists():
        shutil.rmtree(root)
    root.mkdir(parents=True)
    if _sha_file(opticks) != OPTICKS_SHA256:
        raise RuntimeError(f"Opticks source hash drift: {_sha_file(opticks)} != {OPTICKS_SHA256}")
    corpus = opticks.read_text(encoding="utf-8-sig", errors="replace")
    if word_count(corpus) != 104275:
        raise RuntimeError(f"Opticks historical regex word count drift: {word_count(corpus)} != 104275")
    units = split_units(corpus)
    r0 = select_r0(units)
    r1, serialized = select_r1(units, {int(row["occurrence"]) for row in r0})
    selection = {
        "schema": "rocketdict-maintained-r1-source-selection/1",
        "source_sha256": OPTICKS_SHA256,
        "source_regex_words": 104275,
        "selection_sha256": EXPECTED_R1_SELECTION_SHA256,
        "actual_words": sum(int(row["words"]) for row in r1),
        "units": len(r1),
        "overlap_with_r0": [],
        "category_unit_counts": dict(Counter(str(row["category"]) for row in r1)),
        "category_word_counts": {
            category: sum(int(row["words"]) for row in r1 if row["category"] == category)
            for category in R1_QUOTAS
        },
        "historical_freeze": "source-only before first R1 MT evaluation on 2026-08-27",
        "promotion_allowed": False,
    }
    (root / "selection.json").write_text(json.dumps(selection, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (root / "selection.tsv").write_text(serialized, encoding="utf-8")

    challenge_source = root / "challenge-source.txt"
    challenge_source.write_text("\n\n".join(str(row["source"]) for row in r1) + "\n", encoding="utf-8")
    challenge_source_sha = _sha_file(challenge_source)

    core = RocketDictCore()
    project = WorkbenchProject.create(root / "project", name="maintained-r1-translation-challenge", core=core)
    imported = project.import_source(challenge_source)
    preflight = build_product_preflight(project, source_kind="text")
    if preflight.get("status") != "ready":
        raise RuntimeError(f"Maintained R1 Product preflight is not ready: {preflight}")
    database = project.paths.database
    document_version_id = int(imported["interpretation"]["document_version_id"])

    impl8, params8 = _profile_stage(preflight, 8)
    s8 = _call(core, database, "product.stage8.run", document_version_id=document_version_id, parameters=params8, implementation=impl8)
    impl10, params10 = _profile_stage(preflight, 10)
    s10 = _call(core, database, "product.stage10.run", nlp_run_id=int(s8["nlp_run_id"]), parameters=params10, implementation=impl10)
    impl12, params12 = _profile_stage(preflight, 12)
    s12 = _call(core, database, "product.stage12.run", context_run_id=int(s10["context_run_id"]), parameters=params12, implementation=impl12)
    if s12.get("real_mt") is not True or s12.get("network_used") is not False:
        raise RuntimeError(f"Maintained R1 Stage12 lost offline real-MT lineage: {s12}")
    impl14, params14 = _profile_stage(preflight, 14)
    s14 = _call(core, database, "product.stage14.run", translation_run_id=int(s12["translation_run_id"]), parameters=params14, implementation=impl14)

    gate_operations = {
        "rocketdict-numeric-symbol-preservation": "product.stage15.numeric-symbol",
        "rocketdict-punctuation-preservation": "product.stage15.punctuation",
        "rocketdict-length-ratio-proxy": "product.stage15.length-ratio",
    }
    gate_results: dict[str, Any] = {}
    for gate in preflight["profile"]["quality_gates"]:
        implementation = str(gate["implementation"])
        result = _call(
            core,
            database,
            gate_operations[implementation],
            assembly_id=int(s14["assembly_id"]),
            parameters=dict(gate.get("parameters") or {}),
            implementation=implementation,
        )
        with connect(database, readonly=True) as connection:
            issue_rows = get_run_items(connection, int(result["quality_gate_run_id"]), kind="quality_issue")
        gate_results[implementation] = {
            "passed": result.get("passed") is True,
            "failure_count": int(result.get("failure_count") or 0),
            "quality_gate_run_id": int(result["quality_gate_run_id"]),
            "issues_sha256": str(result.get("issues_sha256") or ""),
            "issues": [dict(row.get("payload") or {}) for row in issue_rows],
        }

    with connect(database, readonly=True) as connection:
        translations = get_run_items(connection, int(s12["translation_run_id"]), kind="translation_segment")
        assembly_rows = get_run_items(connection, int(s14["assembly_id"]), kind="assembly_segment")
    if not translations or not assembly_rows:
        raise RuntimeError("Maintained R1 challenge produced no translation/assembly rows")
    extended = _extended_diagnostics(assembly_rows)
    translation_evidence = [
        {
            "sequence_number": int(row["sequence_number"]),
            "source_start": row.get("source_start"),
            "source_end": row.get("source_end"),
            "source_text": row.get("source_text"),
            "target_text": row.get("target_text"),
            "selected_rank": (row.get("payload") or {}).get("selected_rank"),
            "hypothesis_count": len(list((row.get("payload") or {}).get("hypotheses") or [])),
        }
        for row in translations
    ]
    (root / "translations.jsonl").write_text(
        "".join(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n" for row in translation_evidence),
        encoding="utf-8",
    )

    hard_failures = sum(int(row["failure_count"]) for row in gate_results.values())
    diagnostic_failures = (
        int(extended["numeric_order_failure_count"])
        + int(extended["critical_token_failure_count"])
        + int(extended["delimiter_failure_count"])
    )
    evidence = {
        "schema": SCHEMA,
        "status": "baseline_clean_on_measured_contracts" if hard_failures == 0 and diagnostic_failures == 0 else "baseline_requires_candidate_work",
        "promotion_allowed": False,
        "purpose": "measure current maintained Product translation defaults before any challenge-driven intervention",
        "selection": selection,
        "challenge_source_sha256": challenge_source_sha,
        "challenge_source_words": word_count(challenge_source.read_text(encoding="utf-8")),
        "preflight_fingerprint": str(preflight["identity"]["fingerprint"]),
        "core": dict(preflight["identity"]["core"]),
        "registry_hash": str(preflight["identity"]["registry_hash"]),
        "product_profile_schema": str(preflight["profile"]["schema"]),
        "stage8": {
            "implementation": impl8,
            "parameters": params8,
            "nlp_run_id": int(s8["nlp_run_id"]),
            "token_count": int(s8.get("token_count") or 0),
            "coverage_complete": s8.get("coverage_complete") is True,
        },
        "stage12": {
            "implementation": impl12,
            "parameters": params12,
            "translation_run_id": int(s12["translation_run_id"]),
            "segment_count": int(s12.get("segment_count") or 0),
            "source_character_sum": int(s12.get("source_character_sum") or 0),
            "empty_output_count": int(s12.get("empty_output_count") or 0),
            "backend_error_count": int(s12.get("backend_error_count") or 0),
            "real_mt": s12.get("real_mt") is True,
            "network_used": s12.get("network_used") is True,
            "model_archive_sha256": str(s12.get("model_archive_sha256") or ""),
            "model_manifest_sha256": str(s12.get("model_manifest_sha256") or ""),
            "compute_type": str(s12.get("compute_type") or ""),
            "hypothesis_count_distribution": dict(Counter(row["hypothesis_count"] for row in translation_evidence)),
            "selected_rank_distribution": dict(Counter(str(row["selected_rank"]) for row in translation_evidence)),
        },
        "stage14": {
            "implementation": impl14,
            "parameters": params14,
            "assembly_id": int(s14["assembly_id"]),
            "changed_segment_count": int(s14.get("changed_segment_count") or 0),
        },
        "stage15_hard_gates": gate_results,
        "stage15_hard_failure_count": hard_failures,
        "extended_research_diagnostics": extended,
        "extended_diagnostic_failure_count": diagnostic_failures,
        "next_rule": "Do not promote a translation intervention from this baseline. Use the frozen evidence to compare source-only, integrity-preserving candidates and require no measured hard-gate regression.",
    }
    evidence_path = root / "maintained-r1-baseline.json"
    evidence_path.write_text(json.dumps(evidence, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(evidence, ensure_ascii=False, indent=2), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
