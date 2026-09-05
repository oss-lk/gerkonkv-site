"""Persistent spaCy model registry and executable compatibility checks."""

from __future__ import annotations

import hashlib
import importlib.util
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

import spacy
from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker
from spacy.language import Language

from rocketdict.database.base import ComponentKind, LicenseClass
from rocketdict.database.models.execution import Component, ComponentLicense
from rocketdict.database.models.linguistic import NlpModelCheck, NlpModelProfile
from rocketdict.nlp.errors import NlpModelCompatibilityError, NlpModelUnavailableError
from rocketdict.nlp.types import LoadedSpaCyModel, ModelAvailability


_SMOKE_TEXTS = {
    "en": "Alice opened the technical manual in London.",
    "ru": "Алиса открыла техническое руководство в Москве.",
}


class SpaCyModelRegistry:
    """Discovers packages/paths, loads them and persists why they are usable or not."""

    REGISTRY_VERSION = "spacy-registry/1.0"

    def __init__(self, session_factory: sessionmaker[Session]):
        self.session_factory = session_factory
        self._runtime_models: dict[str, Language] = {}

    def register_runtime_model(
        self,
        *,
        profile_key: str,
        display_name: str,
        language: str,
        nlp: Language,
        expected_capabilities: dict[str, bool] | None = None,
        priority: int = 0,
    ) -> int:
        """Register an in-memory pipeline, primarily useful for tests and plug-ins."""
        self._runtime_models[profile_key] = nlp
        with self.session_factory.begin() as session:
            profile = session.scalar(
                select(NlpModelProfile).where(NlpModelProfile.profile_key == profile_key)
            )
            if profile is None:
                profile = NlpModelProfile(
                    profile_key=profile_key,
                    display_name=display_name,
                    language=language,
                    package_name=None,
                    model_path=None,
                    model_size="runtime",
                    priority=priority,
                    is_builtin=False,
                    is_enabled=True,
                    expected_capabilities_json=expected_capabilities or {"tokenizer": True},
                    config_json={"source": "runtime"},
                )
                session.add(profile)
                session.flush()
            else:
                profile.display_name = display_name
                profile.language = language
                profile.priority = priority
                profile.is_enabled = True
                if expected_capabilities is not None:
                    profile.expected_capabilities_json = expected_capabilities
            return profile.id

    def register_path_model(
        self,
        *,
        profile_key: str,
        display_name: str,
        language: str,
        model_path: Path | str,
        expected_capabilities: dict[str, bool] | None = None,
        priority: int = 50,
    ) -> int:
        path = str(Path(model_path).expanduser().resolve())
        with self.session_factory.begin() as session:
            profile = session.scalar(
                select(NlpModelProfile).where(NlpModelProfile.profile_key == profile_key)
            )
            if profile is None:
                profile = NlpModelProfile(
                    profile_key=profile_key,
                    display_name=display_name,
                    language=language,
                    package_name=None,
                    model_path=path,
                    model_size="custom",
                    priority=priority,
                    is_builtin=False,
                    is_enabled=True,
                    expected_capabilities_json=expected_capabilities or {"tokenizer": True},
                    config_json={"source": "path"},
                )
                session.add(profile)
                session.flush()
            else:
                profile.display_name = display_name
                profile.language = language
                profile.model_path = path
                profile.package_name = None
                profile.is_enabled = True
                if expected_capabilities is not None:
                    profile.expected_capabilities_json = expected_capabilities
            return profile.id

    def list_profiles(self, language: str | None = None) -> list[dict[str, Any]]:
        with self.session_factory() as session:
            stmt = select(NlpModelProfile).order_by(
                NlpModelProfile.language, NlpModelProfile.priority, NlpModelProfile.profile_key
            )
            if language:
                stmt = stmt.where(NlpModelProfile.language == language)
            return [
                {
                    "id": row.id,
                    "profile_key": row.profile_key,
                    "display_name": row.display_name,
                    "language": row.language,
                    "package_name": row.package_name,
                    "model_path": row.model_path,
                    "model_size": row.model_size,
                    "priority": row.priority,
                    "is_enabled": row.is_enabled,
                    "expected_capabilities": row.expected_capabilities_json,
                    "config": row.config_json,
                }
                for row in session.scalars(stmt).all()
            ]

    @staticmethod
    def _tree_sha256(path: Path) -> str | None:
        """Hash exact model package bytes in a deterministic path/size/digest manifest."""
        if not path.exists():
            return None
        root = path if path.is_dir() else path.parent
        files = []
        if path.is_file():
            files = [path]
        else:
            files = sorted(
                item for item in path.rglob("*")
                if item.is_file()
                and "__pycache__" not in item.parts
                and item.suffix not in {".pyc", ".pyo"}
            )
        rows: list[tuple[str, int, str]] = []
        for item in files:
            digest = hashlib.sha256()
            with item.open("rb") as stream:
                for chunk in iter(lambda: stream.read(1024 * 1024), b""):
                    digest.update(chunk)
            rows.append((item.relative_to(root).as_posix(), item.stat().st_size, digest.hexdigest()))
        if not rows:
            return None
        payload = json.dumps(rows, ensure_ascii=False, separators=(",", ":"))
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()

    @classmethod
    def _model_byte_fingerprint(cls, profile: NlpModelProfile, source: str) -> tuple[str | None, str | None]:
        if profile.model_path:
            path = Path(profile.model_path).expanduser().resolve()
            return cls._tree_sha256(path), str(path)
        if profile.package_name:
            spec = importlib.util.find_spec(profile.package_name)
            if spec is None:
                return None, None
            if spec.submodule_search_locations:
                path = Path(next(iter(spec.submodule_search_locations))).resolve()
            elif spec.origin:
                path = Path(spec.origin).resolve()
            else:
                return None, None
            return cls._tree_sha256(path), str(path)
        return None, source if source != "<runtime>" else None

    @staticmethod
    def _capabilities(nlp: Language, doc) -> dict[str, Any]:
        pipes = set(nlp.pipe_names)
        capabilities: dict[str, Any] = {
            "tokenizer": True,
            "sentence_boundaries": doc.has_annotation("SENT_START"),
            "pos": doc.has_annotation("POS"),
            "fine_pos": doc.has_annotation("TAG"),
            "morphology": doc.has_annotation("MORPH"),
            "lemma": doc.has_annotation("LEMMA"),
            "dependency": doc.has_annotation("DEP"),
            "entities": doc.has_annotation("ENT_IOB"),
            "vectors": nlp.vocab.vectors_length > 0,
            "vector_dimensions": int(nlp.vocab.vectors_length),
            "transformer": bool({"transformer", "curated_transformer"} & pipes),
            "noun_chunks": False,
        }
        try:
            list(doc.noun_chunks)
            capabilities["noun_chunks"] = True
        except Exception:
            capabilities["noun_chunks"] = False
        return capabilities

    @staticmethod
    def _model_source(profile: NlpModelProfile) -> tuple[str, bool]:
        if profile.model_path:
            return profile.model_path, Path(profile.model_path).exists()
        if profile.package_name:
            return profile.package_name, spacy.util.is_package(profile.package_name)
        return "<runtime>", False

    def _load_and_inspect(
        self, profile: NlpModelProfile, *, disable: Iterable[str] = ()
    ) -> tuple[Language | None, dict[str, Any]]:
        source, installed = self._model_source(profile)
        if profile.profile_key in self._runtime_models:
            nlp = self._runtime_models[profile.profile_key]
            installed = True
        elif installed:
            nlp = spacy.load(source)
        else:
            return None, {
                "installed": False,
                "loadable": False,
                "compatible": False,
                "source": source,
                "error": {
                    "type": "ModelNotInstalled",
                    "message": f"spaCy model is not installed: {source}",
                    "installation_command": profile.config_json.get("installation_command"),
                },
            }

        meta = dict(nlp.meta or {})
        constraint = meta.get("spacy_version")
        version_compatible = True
        if constraint:
            compatibility = spacy.util.is_compatible_version(spacy.__version__, str(constraint))
            version_compatible = compatibility is not False
        model_language = str(meta.get("lang") or nlp.lang or "")
        language_compatible = model_language == profile.language
        unknown_disabled = sorted(set(disable) - set(nlp.pipe_names))
        if unknown_disabled:
            raise ValueError(f"Unknown spaCy pipeline components to disable: {unknown_disabled}")
        smoke = _SMOKE_TEXTS.get(profile.language, "Test sentence.")
        doc = nlp(smoke)
        capabilities = self._capabilities(nlp, doc)
        expected = {
            key: bool(value)
            for key, value in profile.expected_capabilities_json.items()
            if bool(value)
        }
        missing = sorted(key for key in expected if not bool(capabilities.get(key)))
        model_version = str(meta.get("version") or "runtime")
        model_tree_sha256, resolved_model_path = self._model_byte_fingerprint(profile, source)
        loadable = True
        compatible = bool(version_compatible and language_compatible)
        return nlp, {
            "installed": installed,
            "loadable": loadable,
            "compatible": compatible,
            "source": source,
            "resolved_model_path": resolved_model_path,
            "model_tree_sha256": model_tree_sha256,
            "model_version": model_version,
            "model_language": model_language,
            "pipeline": list(nlp.pipe_names),
            "disabled_pipes": list(disable),
            "capabilities": capabilities,
            "missing_capabilities": missing,
            "meta": meta,
            "spacy_constraint": constraint,
            "language_compatible": language_compatible,
            "version_compatible": version_compatible,
            "error": None,
        }

    @staticmethod
    def _component_revision(profile: NlpModelProfile, details: dict[str, Any]) -> str:
        payload = {
            "profile": profile.profile_key,
            "source": details.get("source"),
            "model_version": details.get("model_version"),
            "pipeline": details.get("pipeline", []),
            "spacy_constraint": details.get("spacy_constraint"),
            "capabilities": details.get("capabilities", {}),
            "model_tree_sha256": details.get("model_tree_sha256"),
        }
        return hashlib.sha256(
            json.dumps(payload, sort_keys=True, ensure_ascii=False).encode("utf-8")
        ).hexdigest()

    @staticmethod
    def _license_from_model_meta(value: Any) -> dict[str, Any] | None:
        if not value:
            return None
        expression = str(value).strip()
        key = expression.casefold().replace("_", "-").replace(" ", "-")
        if key in {"mit", "apache-2.0", "apache-2", "bsd-2-clause", "bsd-3-clause"}:
            license_class = LicenseClass.COMMERCIAL_OK
            commercial = True; attribution = True; share_alike = False; noncommercial = False
        elif key in {"cc0", "cc0-1.0", "public-domain"}:
            license_class = LicenseClass.COMMERCIAL_OK
            commercial = True; attribution = False; share_alike = False; noncommercial = False
        elif "noncommercial" in key or "-nc" in key:
            license_class = LicenseClass.NONCOMMERCIAL_ONLY
            commercial = False; attribution = True; share_alike = "-sa" in key; noncommercial = True
        elif "cc-by-sa" in key:
            license_class = LicenseClass.SHARE_ALIKE_DATA
            commercial = True; attribution = True; share_alike = True; noncommercial = False
        elif "cc-by" in key:
            license_class = LicenseClass.ATTRIBUTION_REQUIRED
            commercial = True; attribution = True; share_alike = False; noncommercial = False
        else:
            license_class = LicenseClass.UNKNOWN
            commercial = False; attribution = False; share_alike = False; noncommercial = False
        return {
            "spdx_expression": expression, "license_class": license_class,
            "commercial_allowed": commercial, "attribution_required": attribution,
            "share_alike": share_alike, "noncommercial": noncommercial,
        }

    def _persist_check(
        self,
        session: Session,
        profile: NlpModelProfile,
        details: dict[str, Any],
    ) -> tuple[NlpModelCheck, Component | None]:
        component: Component | None = None
        if details.get("loadable"):
            revision = self._component_revision(profile, details)
            component = session.scalar(
                select(Component).where(
                    Component.name == (profile.package_name or profile.profile_key),
                    Component.kind == ComponentKind.NLP_MODEL,
                    Component.version == str(details.get("model_version") or "unknown"),
                    Component.revision == revision,
                )
            )
            if component is None:
                meta = details.get("meta", {})
                component = Component(
                    name=profile.package_name or profile.profile_key,
                    kind=ComponentKind.NLP_MODEL,
                    version=str(details.get("model_version") or "unknown"),
                    revision=revision,
                    source_uri=meta.get("url"),
                    installed_path=None
                    if details.get("source") == "<runtime>"
                    else str(details.get("source")),
                    metadata_json={
                        "profile_key": profile.profile_key,
                        "language": details.get("model_language"),
                        "spacy_version": spacy.__version__,
                        "spacy_constraint": details.get("spacy_constraint"),
                        "pipeline": details.get("pipeline", []),
                        "capabilities": details.get("capabilities", {}),
                        "license": meta.get("license"),
                        "labels": meta.get("labels", {}),
                        "vectors": meta.get("vectors", {}),
                        "registry_version": self.REGISTRY_VERSION,
                        "model_tree_sha256": details.get("model_tree_sha256"),
                        "resolved_model_path": details.get("resolved_model_path"),
                    },
                )
                session.add(component)
                session.flush()

            # Persist only what the actually loaded model metadata states.
            # An uninstalled profile is deliberately left licence-unknown.
            meta_license = self._license_from_model_meta((details.get("meta") or {}).get("license"))
            existing_license = session.scalar(
                select(ComponentLicense).where(ComponentLicense.component_id == component.id).limit(1)
            )
            if meta_license is not None and existing_license is None:
                session.add(ComponentLicense(
                    component_id=component.id,
                    spdx_expression=meta_license["spdx_expression"],
                    license_class=meta_license["license_class"],
                    commercial_allowed=meta_license["commercial_allowed"],
                    attribution_required=meta_license["attribution_required"],
                    share_alike=meta_license["share_alike"],
                    noncommercial=meta_license["noncommercial"],
                    license_expression_source="spacy-model-meta",
                    redistribution_allowed=None,
                    modification_allowed=None,
                    source_disclosure_required=False,
                    review_status="machine_assessed",
                    evidence_json={
                        "profile_key": profile.profile_key,
                        "model_version": details.get("model_version"),
                        "model_tree_sha256": details.get("model_tree_sha256"),
                        "metadata_license": (details.get("meta") or {}).get("license"),
                    },
                ))

        check = NlpModelCheck(
            model_profile_id=profile.id,
            component_id=component.id if component else None,
            spacy_version=spacy.__version__,
            checked_at=datetime.now(timezone.utc),
            installed=bool(details.get("installed")),
            loadable=bool(details.get("loadable")),
            compatible=bool(details.get("compatible")),
            model_version=details.get("model_version"),
            model_language=details.get("model_language"),
            pipeline_json=list(details.get("pipeline", [])),
            disabled_pipes_json=list(details.get("disabled_pipes", [])),
            capabilities_json=dict(details.get("capabilities", {})),
            missing_capabilities_json=list(details.get("missing_capabilities", [])),
            error_json=details.get("error"),
            metadata_json={
                "source": details.get("source"),
                "spacy_constraint": details.get("spacy_constraint"),
                "language_compatible": details.get("language_compatible"),
                "version_compatible": details.get("version_compatible"),
                "model_tree_sha256": details.get("model_tree_sha256"),
                "resolved_model_path": details.get("resolved_model_path"),
            },
        )
        session.add(check)
        session.flush()
        return check, component

    def inspect_profile(
        self, profile_key: str, *, disable: Iterable[str] = (), force_load: bool = False
    ) -> ModelAvailability:
        """Read-only runtime/model probe.

        Unlike :meth:`check_profile`, this method never persists ``NlpModelCheck``,
        ``Component`` or licence evidence.  It is intended for preflight,
        dashboards and adapter availability checks where observation must not
        mutate the user's project database.
        """
        with self.session_factory() as session:
            profile = session.scalar(
                select(NlpModelProfile).where(NlpModelProfile.profile_key == profile_key)
            )
            if profile is None:
                raise NlpModelUnavailableError(f"Unknown NLP model profile: {profile_key}")
            try:
                _nlp, details = self._load_and_inspect(profile, disable=disable)
            except Exception as exc:
                details = {
                    "installed": True,
                    "loadable": False,
                    "compatible": False,
                    "source": profile.model_path or profile.package_name or "<runtime>",
                    "error": {"type": type(exc).__name__, "message": str(exc)},
                    "pipeline": [],
                    "capabilities": {},
                    "missing_capabilities": [],
                    "disabled_pipes": list(disable),
                }
            component_id = None
            if details.get("loadable"):
                revision = self._component_revision(profile, details)
                component = session.scalar(
                    select(Component).where(
                        Component.name == (profile.package_name or profile.profile_key),
                        Component.kind == ComponentKind.NLP_MODEL,
                        Component.version == str(details.get("model_version") or "unknown"),
                        Component.revision == revision,
                    )
                )
                component_id = component.id if component is not None else None
            result = ModelAvailability(
                profile_id=profile.id,
                profile_key=profile.profile_key,
                display_name=profile.display_name,
                language=profile.language,
                package_name=profile.package_name,
                model_path=profile.model_path,
                installed=bool(details.get("installed")),
                loadable=bool(details.get("loadable")),
                compatible=bool(details.get("compatible")),
                model_version=details.get("model_version"),
                model_language=details.get("model_language"),
                pipeline=tuple(details.get("pipeline", [])),
                capabilities=dict(details.get("capabilities", {})),
                missing_capabilities=tuple(details.get("missing_capabilities", [])),
                component_id=component_id,
                check_id=0,
                error=details.get("error"),
                metadata={
                    "source": details.get("source"),
                    "spacy_constraint": details.get("spacy_constraint"),
                    "language_compatible": details.get("language_compatible"),
                    "version_compatible": details.get("version_compatible"),
                    "model_tree_sha256": details.get("model_tree_sha256"),
                    "resolved_model_path": details.get("resolved_model_path"),
                    "read_only_probe": True,
                },
            )
        if force_load and not result.loadable:
            raise NlpModelUnavailableError(result.error.get("message") if result.error else profile_key)
        return result

    def check_profile(
        self, profile_key: str, *, disable: Iterable[str] = (), force_load: bool = False
    ) -> ModelAvailability:
        with self.session_factory.begin() as session:
            profile = session.scalar(
                select(NlpModelProfile).where(NlpModelProfile.profile_key == profile_key)
            )
            if profile is None:
                raise NlpModelUnavailableError(f"Unknown NLP model profile: {profile_key}")
            try:
                _nlp, details = self._load_and_inspect(profile, disable=disable)
            except Exception as exc:
                details = {
                    "installed": True,
                    "loadable": False,
                    "compatible": False,
                    "source": profile.model_path or profile.package_name or "<runtime>",
                    "error": {"type": type(exc).__name__, "message": str(exc)},
                }
            check, component = self._persist_check(session, profile, details)
            result = ModelAvailability(
                profile_id=profile.id,
                profile_key=profile.profile_key,
                display_name=profile.display_name,
                language=profile.language,
                package_name=profile.package_name,
                model_path=profile.model_path,
                installed=check.installed,
                loadable=check.loadable,
                compatible=check.compatible,
                model_version=check.model_version,
                model_language=check.model_language,
                pipeline=tuple(check.pipeline_json),
                capabilities=dict(check.capabilities_json),
                missing_capabilities=tuple(check.missing_capabilities_json),
                component_id=component.id if component else None,
                check_id=check.id,
                error=check.error_json,
                metadata=dict(check.metadata_json),
            )
        if force_load and not result.loadable:
            raise NlpModelUnavailableError(result.error.get("message") if result.error else profile_key)
        return result

    def scan(self, language: str | None = None) -> list[ModelAvailability]:
        profiles = self.list_profiles(language)
        return [self.check_profile(item["profile_key"]) for item in profiles if item["is_enabled"]]

    def choose_default(self, language: str) -> ModelAvailability:
        checks = self.scan(language)
        for item in checks:
            if item.loadable and item.compatible:
                return item
        commands = [
            profile["config"].get("installation_command")
            for profile in self.list_profiles(language)
            if profile["config"].get("installation_command")
        ]
        raise NlpModelUnavailableError(
            f"No compatible spaCy model is installed for language {language}. "
            f"Available installation commands: {commands}"
        )

    def load(
        self,
        profile_key: str,
        *,
        disable: Iterable[str] = (),
        allow_language_mismatch: bool = False,
        allow_missing_capabilities: bool = True,
    ) -> LoadedSpaCyModel:
        disable_tuple = tuple(disable)
        with self.session_factory.begin() as session:
            profile = session.scalar(
                select(NlpModelProfile).where(NlpModelProfile.profile_key == profile_key)
            )
            if profile is None:
                raise NlpModelUnavailableError(f"Unknown NLP model profile: {profile_key}")
            try:
                nlp, details = self._load_and_inspect(profile, disable=disable_tuple)
            except Exception as exc:
                details = {
                    "installed": True,
                    "loadable": False,
                    "compatible": False,
                    "source": profile.model_path or profile.package_name or "<runtime>",
                    "error": {"type": type(exc).__name__, "message": str(exc)},
                }
                nlp = None
            check, component = self._persist_check(session, profile, details)
            if nlp is None or component is None or not check.loadable:
                message = check.error_json.get("message") if check.error_json else profile_key
                raise NlpModelUnavailableError(message)
            if not check.compatible and not allow_language_mismatch:
                raise NlpModelCompatibilityError(
                    f"Model {profile_key} is incompatible: expected {profile.language}, "
                    f"loaded {check.model_language}, spaCy {spacy.__version__}"
                )
            if check.missing_capabilities_json and not allow_missing_capabilities:
                raise NlpModelCompatibilityError(
                    f"Model {profile_key} misses required capabilities: "
                    f"{check.missing_capabilities_json}"
                )
            signature_payload = {
                "component_revision": component.revision,
                "disabled": disable_tuple,
                "pipeline": check.pipeline_json,
                "spacy": spacy.__version__,
                "model_tree_sha256": check.metadata_json.get("model_tree_sha256"),
            }
            signature = hashlib.sha256(
                json.dumps(signature_payload, sort_keys=True).encode("utf-8")
            ).hexdigest()
            return LoadedSpaCyModel(
                profile_id=profile.id,
                profile_key=profile.profile_key,
                language=profile.language,
                component_id=component.id,
                check_id=check.id,
                model_version=check.model_version or "unknown",
                model_signature_hash=signature,
                pipeline=tuple(check.pipeline_json),
                capabilities=dict(check.capabilities_json),
                nlp=nlp,
            )
