"""One fail-closed application facade for verified DebugMate result operations."""

from __future__ import annotations

import json
import re
import threading
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path, PurePosixPath

from pydantic import Field

from debugmate.diagnosis.correction import CorrectionOverlay
from debugmate.diagnosis.extraction import FieldId
from debugmate.diagnosis.workflow import (
    DiagnosisRunOutcome,
    DiagnosisWorkflow,
    WorkflowStatus,
    validate_diagnosis_outcome,
)
from debugmate.evidence import publish_diagnosis_evidence
from debugmate.gateway import rerun_diagnosis_json
from debugmate.hashing import canonical_json_bytes, sha256_bytes
from debugmate.privacy.models import ApprovedRedactedInput
from debugmate.results.contracts import (
    ArtifactAvailability,
    ResultManifest,
    ResultMode,
    ResultStatus,
    ResultViewState,
    SafeFailure,
    StrictFrozenModel,
)
from debugmate.results.loader import LoadedDiagnosisSource, ResultLoadError, load_verified_outcome
from debugmate.results.outcome_store import DiagnosisOutcomeStore
from debugmate.results.publisher import (
    PublishedResultBundle,
    TrustedResultRoot,
    _trusted_root_path,
)
from debugmate.results.verifier import (
    ResultVerificationError,
    VerifiedDownload,
    resolve_verified_download,
    verify_result_bundle,
)

_CASE_ID = re.compile(r"^case_[0-9a-f]{32}$")
_RUN_ID = re.compile(r"^run_[0-9a-f]{32}$")
_RESULT_ID = re.compile(r"^result_[0-9a-f]{32}$")
_FIXTURE_ID = re.compile(r"^[a-z0-9][a-z0-9-]{1,63}$")
_SAFE_FAILURE_CODES = {
    "replay_bundle_invalid": ("replay", "replay"),
    "source_bundle_invalid": ("source", "source"),
    "source_outcome_invalid": ("source", "source"),
    "diagnosis_identity_mismatch": ("identity", "source"),
    "outcome_store_invalid": ("store", "store"),
    "result_bundle_invalid": ("result", "result"),
    "download_invalid": ("download", "download"),
    "workflow_not_configured": ("workflow", "input"),
    "workflow_not_completed": ("workflow", "input"),
    "result_composition_failed": ("result", "result"),
    "correction_invalid": ("correction", "correction"),
}


class ResultServiceError(ValueError):
    """Fixed service failure; never retain provider, path, or exception values."""

    def __init__(self, code: str = "result_composition_failed") -> None:
        self.code = code if code in _SAFE_FAILURE_CODES else "result_composition_failed"
        super().__init__(self.code)


class CorrectionDraft(StrictFrozenModel):
    """One explicit edit to a verified Phase 3 extraction fact."""

    field_id: FieldId
    replacement: str = Field(min_length=1, max_length=2_000, repr=False)
    reason: str = Field(min_length=1, max_length=1_000, repr=False)


@dataclass(frozen=True, slots=True)
class ServiceStageEvent:
    """Queue-safe progress payload carrying only a strict view state."""

    state: ResultViewState


ResultComposer = Callable[
    [LoadedDiagnosisSource], PublishedResultBundle
]


class ResultApplicationService:
    """The only façade exposed to the UI for result composition and recovery.

    The service accepts approved redacted input or controlled replay identifiers;
    it never accepts a caller-provided workflow outcome, result path, or media
    member path.  Every terminal result is rebuilt from a freshly checked
    source and reverified from disk before its view state is returned.
    """

    def __init__(
        self,
        *,
        workflow: DiagnosisWorkflow | None,
        evidence_root: Path,
        outcome_store: DiagnosisOutcomeStore,
        results_root: TrustedResultRoot,
        replay_root: Path,
        composer: Callable[..., PublishedResultBundle] | None = None,
    ) -> None:
        if not isinstance(outcome_store, DiagnosisOutcomeStore):
            raise TypeError("ResultApplicationService requires DiagnosisOutcomeStore")
        if not isinstance(results_root, TrustedResultRoot):
            raise TypeError("ResultApplicationService requires TrustedResultRoot")
        self._workflow = workflow
        self._evidence_root = Path(evidence_root)
        self._outcome_store = outcome_store
        self._results_root = results_root
        self._replay_root = Path(replay_root)
        self._composer = composer
        self._lock = threading.RLock()
        self._case_locks: dict[str, threading.RLock] = {}
        self._live_cache: dict[tuple[str, str], ResultViewState] = {}
        self._run_results: dict[str, ResultViewState] = {}

    def _case_lock(self, case_id: str) -> threading.RLock:
        with self._lock:
            return self._case_locks.setdefault(case_id, threading.RLock())

    @staticmethod
    def _failure(
        code: str,
        *,
        mode: ResultMode = ResultMode.LIVE,
        fixture_id: str | None = None,
        fixture_name: str | None = None,
    ) -> ResultViewState:
        stage, retry = _SAFE_FAILURE_CODES.get(
            code, _SAFE_FAILURE_CODES["result_composition_failed"]
        )
        safe_code = code if code in _SAFE_FAILURE_CODES else "result_composition_failed"
        return ResultViewState(
            mode=mode,
            status=ResultStatus.FAILED,
            fixture_id=fixture_id,
            fixture_name=fixture_name,
            availability=ArtifactAvailability(),
            failure=SafeFailure(
                code=safe_code, failed_stage=stage, retry_scope=retry
            ),
        )

    @staticmethod
    def _state_from_manifest(manifest: ResultManifest) -> ResultViewState:
        return ResultViewState(
            mode=manifest.mode,
            status=manifest.status,
            fixture_id=manifest.fixture_id,
            fixture_name=manifest.fixture_name,
            identity=manifest.identity,
            result_id=manifest.result_id,
            availability=manifest.availability,
            failure=manifest.failure,
            audio=manifest.audio,
            completed_stages=manifest.completed_stages,
            inherited_stages=manifest.inherited_stages,
        )

    @staticmethod
    def _strict_approved(value: ApprovedRedactedInput | str) -> ApprovedRedactedInput:
        if isinstance(value, ApprovedRedactedInput):
            return ApprovedRedactedInput.model_validate_json(
                canonical_json_bytes(value.model_dump(mode="json")), strict=True
            )
        if isinstance(value, str):
            return ApprovedRedactedInput.model_validate_json(value, strict=True)
        raise TypeError("diagnose_and_compose accepts only ApprovedRedactedInput or strict JSON")

    @staticmethod
    def _strict_draft(value: CorrectionDraft | str) -> CorrectionDraft:
        if isinstance(value, CorrectionDraft):
            return CorrectionDraft.model_validate_json(
                canonical_json_bytes(value.model_dump(mode="json")), strict=True
            )
        if isinstance(value, str):
            return CorrectionDraft.model_validate_json(value, strict=True)
        raise TypeError("correction requires CorrectionDraft or strict JSON")

    @staticmethod
    def _controlled_relative(value: object) -> PurePosixPath:
        if not isinstance(value, str) or not value or "\\" in value or ":" in value:
            raise ValueError("relative")
        path = PurePosixPath(value)
        if path.is_absolute() or any(part in {"", ".", ".."} for part in path.parts):
            raise ValueError("relative")
        return path

    def _fixture_row(self, fixture_id: str) -> dict[str, object]:
        if _FIXTURE_ID.fullmatch(fixture_id) is None:
            raise ResultServiceError("replay_bundle_invalid")
        try:
            raw = (self._replay_root / "index.json").read_bytes()
            payload = json.loads(raw.decode("utf-8"))
            if not isinstance(payload, dict) or set(payload) != {"index_version", "fixtures"}:
                raise ValueError("index")
            rows = payload["fixtures"]
            if payload["index_version"] != "1.0.0" or not isinstance(rows, list):
                raise ValueError("index")
            row = next(
                item
                for item in rows
                if isinstance(item, dict) and item.get("fixture_id") == fixture_id
            )
            expected = {
                "fixture_id",
                "display_label",
                "outcome_path",
                "source_path",
                "case_id",
                "run_id",
            }
            if set(row) != expected or not all(isinstance(row[name], str) for name in expected):
                raise ValueError("row")
            if (
                _CASE_ID.fullmatch(row["case_id"]) is None
                or _RUN_ID.fullmatch(row["run_id"]) is None
            ):
                raise ValueError("identity")
            outcome_path = self._controlled_relative(row["outcome_path"])
            source_path = self._controlled_relative(row["source_path"])
            expected_outcome = f"{fixture_id}/outcome.json"
            expected_source = f"{fixture_id}/source/{row['case_id']}/{row['run_id']}"
            if (
                outcome_path.as_posix() != expected_outcome
                or source_path.as_posix() != expected_source
            ):
                raise ValueError("shape")
            return row
        except (OSError, StopIteration, UnicodeError, TypeError, ValueError, json.JSONDecodeError):
            raise ResultServiceError("replay_bundle_invalid") from None

    def _load_fixture_source(
        self, fixture_id: str
    ) -> tuple[dict[str, object], DiagnosisRunOutcome, LoadedDiagnosisSource]:
        row = self._fixture_row(fixture_id)
        try:
            outcome_relative = self._controlled_relative(row["outcome_path"])
            source_relative = self._controlled_relative(row["source_path"])
            outcome_path = self._replay_root / Path(*outcome_relative.parts)
            source_path = self._replay_root / Path(*source_relative.parts)
            outcome = DiagnosisRunOutcome.model_validate_json(
                outcome_path.read_bytes(), strict=True
            )
            validate_diagnosis_outcome(outcome)
            if outcome.status is not WorkflowStatus.COMPLETED:
                raise ValueError("outcome")
            if outcome.case_id != row["case_id"] or outcome.run_id != row["run_id"]:
                raise ValueError("identity")
            expected_source = (
                self._replay_root / fixture_id / "source" / outcome.case_id / outcome.run_id
            )
            if source_path != expected_source:
                raise ValueError("source")
            source = load_verified_outcome(outcome, evidence_root=source_path.parents[1])
            return row, outcome, source
        except (OSError, ValueError, ResultLoadError):
            raise ResultServiceError("replay_bundle_invalid") from None

    def _store_outcome(self, outcome: DiagnosisRunOutcome) -> None:
        try:
            self._outcome_store.write(outcome)
            return
        except ResultLoadError:
            try:
                stored = self._outcome_store.read(outcome.run_id)
                if canonical_json_bytes(stored.model_dump(mode="json")) != canonical_json_bytes(
                    outcome.model_dump(mode="json")
                ):
                    raise ValueError("identity")
            except Exception:
                raise ResultServiceError("outcome_store_invalid") from None

    def _compose(
        self,
        source: LoadedDiagnosisSource,
        *,
        mode: ResultMode,
        fixture_id: str | None,
        fixture_name: str | None,
    ) -> ResultViewState:
        try:
            if self._composer is None:
                raise ResultServiceError("result_composition_failed")
            published = self._composer(
                source,
                mode=mode,
                fixture_id=fixture_id,
                fixture_name=fixture_name,
            )
            if not isinstance(published, PublishedResultBundle):
                raise ValueError("publisher")
            verified = verify_result_bundle(published.path)
            if (
                verified.manifest != published.manifest
                or verified.manifest.mode is not mode
                or verified.manifest.fixture_id != fixture_id
                or verified.manifest.fixture_name != fixture_name
                or verified.manifest.identity.source_run_id != source.source_run_id
            ):
                raise ValueError("verification")
            state = self._state_from_manifest(verified.manifest)
            self._run_results[source.source_run_id] = state
            return state
        except ResultServiceError:
            raise
        except (ResultVerificationError, ResultLoadError, ValueError, TypeError):
            raise ResultServiceError("result_composition_failed") from None

    def diagnose_and_compose(self, approved: ApprovedRedactedInput | str) -> ResultViewState:
        """Run Phase 3 from approved input, then persist and compose Phase 4."""

        checked = self._strict_approved(approved)
        key = (checked.case_id, checked.preview_hash)
        with self._case_lock(checked.case_id):
            cached = self._live_cache.get(key)
            if cached is not None:
                return cached
            if self._workflow is None:
                return self._failure("workflow_not_configured")
            try:
                outcome = self._workflow.run(checked)
                validate_diagnosis_outcome(outcome)
                if outcome.status is not WorkflowStatus.COMPLETED:
                    return self._failure("workflow_not_completed")
                publish_diagnosis_evidence(outcome, self._evidence_root)
                self._store_outcome(outcome)
                source = load_verified_outcome(outcome, evidence_root=self._evidence_root)
                state = self._compose(
                    source, mode=ResultMode.LIVE, fixture_id=None, fixture_name=None
                )
            except ResultServiceError as error:
                return self._failure(error.code)
            except ResultLoadError as error:
                return self._failure(error.code)
            except Exception:
                return self._failure("result_composition_failed")
            self._live_cache[key] = state
            return state

    def load_replay(self, fixture_id: str) -> ResultViewState:
        """Allowlist a fixture, reverify source, then publish a new replay result."""

        try:
            row, outcome, source = self._load_fixture_source(fixture_id)
            with self._case_lock(source.case_id):
                self._store_outcome(outcome)
                return self._compose(
                    source,
                    mode=ResultMode.REPLAY,
                    fixture_id=str(row["fixture_id"]),
                    fixture_name=str(row["display_label"]),
                )
        except ResultServiceError as error:
            if _FIXTURE_ID.fullmatch(fixture_id):
                return self._failure(error.code, mode=ResultMode.REPLAY)
            return self._failure(error.code)
        except Exception:
            return self._failure("replay_bundle_invalid")

    def _source_for_verified_result(
        self, manifest: ResultManifest
    ) -> LoadedDiagnosisSource:
        try:
            outcome = self._outcome_store.read(manifest.identity.source_run_id)
            if manifest.mode is ResultMode.REPLAY:
                if manifest.fixture_id is None:
                    raise ValueError("fixture")
                row, indexed, fixture_source = self._load_fixture_source(manifest.fixture_id)
                if row["display_label"] != manifest.fixture_name:
                    raise ValueError("replay identity")
                if indexed.run_id == outcome.run_id:
                    indexed_bytes = canonical_json_bytes(indexed.model_dump(mode="json"))
                    outcome_bytes = canonical_json_bytes(outcome.model_dump(mode="json"))
                    if indexed_bytes != outcome_bytes:
                        raise ValueError("replay identity")
                    source = fixture_source
                else:
                    # A confirmed correction of a fixed replay remains a replay
                    # in the UI, but its new immutable source lives in evidence.
                    source = load_verified_outcome(outcome, evidence_root=self._evidence_root)
            else:
                source = load_verified_outcome(outcome, evidence_root=self._evidence_root)
            if (
                source.case_id != manifest.identity.case_id
                or source.source_run_id != manifest.identity.source_run_id
                or source.diagnosis_sha256 != manifest.identity.diagnosis_sha256
            ):
                raise ValueError("source identity")
            return source
        except ResultServiceError:
            raise
        except ResultLoadError as error:
            raise ResultServiceError(error.code) from None
        except Exception:
            raise ResultServiceError("source_bundle_invalid") from None

    def _source_for_stored_outcome(
        self, outcome: DiagnosisRunOutcome, state: ResultViewState | None
    ) -> LoadedDiagnosisSource:
        """Recover a source for correction without accepting a caller path."""

        if state is not None and state.mode is ResultMode.REPLAY and state.fixture_id is not None:
            _row, indexed, fixture_source = self._load_fixture_source(state.fixture_id)
            if indexed.run_id == outcome.run_id:
                if canonical_json_bytes(indexed.model_dump(mode="json")) != canonical_json_bytes(
                    outcome.model_dump(mode="json")
                ):
                    raise ResultServiceError("source_bundle_invalid")
                return fixture_source
        try:
            return load_verified_outcome(outcome, evidence_root=self._evidence_root)
        except ResultLoadError as error:
            raise ResultServiceError(error.code) from None

    def restore_result(self, case_id: str, result_id: str) -> ResultViewState:
        """Freshly verify a public result and its complete source before display."""

        if _CASE_ID.fullmatch(case_id) is None or _RESULT_ID.fullmatch(result_id) is None:
            return self._failure("result_bundle_invalid")
        try:
            root = _trusted_root_path(self._results_root)
            verified = verify_result_bundle(root / case_id / result_id)
            if verified.manifest.identity.case_id != case_id:
                raise ValueError("case")
            self._source_for_verified_result(verified.manifest)
            state = self._state_from_manifest(verified.manifest)
            self._run_results[verified.manifest.identity.source_run_id] = state
            return state
        except ResultServiceError as error:
            return self._failure(error.code)
        except (ResultVerificationError, ValueError):
            return self._failure("result_bundle_invalid")

    def correct_and_compose(
        self, previous_run_id: str, draft: CorrectionDraft | str, confirmed: bool
    ) -> ResultViewState:
        """Create a new immutable source/result only after explicit confirmation."""

        if _RUN_ID.fullmatch(previous_run_id) is None:
            return self._failure("correction_invalid")
        checked = self._strict_draft(draft)
        if not isinstance(confirmed, bool):
            raise TypeError("confirmed must be bool")
        existing = self._run_results.get(previous_run_id)
        if not confirmed:
            return existing if existing is not None else self._failure("correction_invalid")
        if self._workflow is None:
            return self._failure("workflow_not_configured")
        try:
            previous = self._outcome_store.read(previous_run_id)
            source = self._source_for_stored_outcome(previous, existing)
            target = next(
                item for item in previous.facts.facts if item.field_id is checked.field_id
            )
            from debugmate.diagnosis.extraction import normalize_value

            if normalize_value(checked.field_id, checked.replacement) == target.value:
                return existing if existing is not None else self._failure("correction_invalid")
            if existing is not None and existing.mode is ResultMode.REPLAY:
                # The fixture remains the read-only replay source.  Phase 3's
                # correction evidence contract also requires an immutable local
                # parent bundle, so publish an identical verified source copy
                # before creating the distinct corrected run.
                publish_diagnosis_evidence(previous, self._evidence_root)
            overlay = CorrectionOverlay(
                case_id=previous.case_id,
                base_revision=previous.revision,
                base_facts_sha256=previous.facts_sha256,
                field_id=target.field_id,
                fact_id=target.fact_id,
                old_value_sha256=sha256_bytes(target.value.encode("utf-8")),
                replacement=checked.replacement,
                reason=checked.reason,
            )
            # The gateway function is the only correction-rerun JSON boundary.
            outcome = rerun_diagnosis_json(
                self._workflow, previous.model_dump_json(), overlay.model_dump_json()
            )
            validate_diagnosis_outcome(outcome)
            if outcome.status is not WorkflowStatus.COMPLETED or outcome.run_id == previous.run_id:
                raise ValueError("correction")
            publish_diagnosis_evidence(outcome, self._evidence_root)
            self._store_outcome(outcome)
            revised = load_verified_outcome(outcome, evidence_root=self._evidence_root)
            del source
            return self._compose(
                revised,
                mode=existing.mode if existing is not None else ResultMode.LIVE,
                fixture_id=existing.fixture_id if existing is not None else None,
                fixture_name=existing.fixture_name if existing is not None else None,
            )
        except (ResultLoadError, ResultServiceError, StopIteration, ValueError, TypeError):
            return self._failure("correction_invalid")
        except Exception:
            return self._failure("correction_invalid")

    def retry_stage(self, case_id: str, result_id: str) -> ResultViewState:
        """Retry only from a freshly verified terminal partial source/result."""

        restored = self.restore_result(case_id, result_id)
        if restored.status is not ResultStatus.PARTIAL:
            return restored
        try:
            root = _trusted_root_path(self._results_root)
            manifest = verify_result_bundle(root / case_id / result_id).manifest
            source = self._source_for_verified_result(manifest)
            return self._compose(
                source,
                mode=manifest.mode,
                fixture_id=manifest.fixture_id,
                fixture_name=manifest.fixture_name,
            )
        except ResultServiceError as error:
            return self._failure(error.code)
        except Exception:
            return self._failure("result_composition_failed")

    def resolve_download(self, case_id: str, result_id: str, member_id: str) -> VerifiedDownload:
        """Return only a one-shot verified-byte capability, never a path."""

        if (
            _CASE_ID.fullmatch(case_id) is None
            or _RESULT_ID.fullmatch(result_id) is None
            or member_id not in {"bundle", "report", "card", "audio", "citations"}
        ):
            raise ResultServiceError("download_invalid")
        try:
            root = _trusted_root_path(self._results_root)
            # Verify the source first, then issue the one-shot member bytes.
            verified = verify_result_bundle(root / case_id / result_id)
            self._source_for_verified_result(verified.manifest)
            return resolve_verified_download(root, case_id, result_id, member_id)
        except ResultServiceError:
            raise
        except (ResultVerificationError, ValueError):
            raise ResultServiceError("download_invalid") from None
