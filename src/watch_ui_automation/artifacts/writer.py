from __future__ import annotations

import hashlib
import json
import re
from collections.abc import Mapping
from datetime import datetime
from pathlib import Path
from typing import Any

from watch_ui_automation.models import CaseResult, RunManifest

DEFAULT_ARTIFACT_ROOT = Path("artifacts")
_UNSAFE_PATH_CHARS = re.compile(r'[^A-Za-z0-9._-]+')


class ArtifactWriter:
    def __init__(self, root_dir: Path | str = DEFAULT_ARTIFACT_ROOT) -> None:
        self.root_dir = Path(root_dir)
        self.run_dir: Path | None = None

    def start_run(self, manifest: RunManifest) -> Path:
        timestamp = datetime.utcnow().strftime("%Y%m%d-%H%M%S")
        run_name = self._safe_dir_name(manifest.device_serial)
        root_dir = self.root_dir
        if not root_dir.is_absolute():
            root_dir = Path.cwd() / root_dir
        self.run_dir = root_dir / f"run-{timestamp}-{run_name}"
        self.run_dir.mkdir(parents=True, exist_ok=False)
        (self.run_dir / "cases").mkdir()
        self._write_json(self.run_dir / "run_manifest.json", manifest.to_dict())
        return self.run_dir

    def write_step(self, case_name: str, payload: dict[str, Any]) -> Path:
        return self._append_jsonl(self._case_dir(case_name) / "steps.jsonl", payload)

    def write_transport(self, case_name: str, payload: dict[str, Any]) -> Path:
        return self._append_jsonl(self._case_dir(case_name) / "transport.jsonl", payload)

    def write_assertion(self, case_name: str, payload: dict[str, Any]) -> Path:
        return self._append_jsonl(self._case_dir(case_name) / "assertions.jsonl", payload)

    def write_snapshot(self, case_name: str, payload: dict[str, Any]) -> Path:
        return self._write_json(self._case_dir(case_name) / "state_snapshot.json", payload)

    def write_case_result(self, result: CaseResult) -> Path:
        return self._write_json(self._case_dir(result.case_name) / "result.json", result.to_dict())

    def write_failure_summary(self, case_name: str, markdown: str) -> Path:
        path = self._case_dir(case_name) / "failure_summary.md"
        path.write_text(markdown, encoding="utf-8")
        return path

    def _append_jsonl(self, path: Path, payload: Mapping[str, Any]) -> Path:
        self._validate_payload(payload)
        with path.open("a", encoding="utf-8", newline="\n") as handle:
            handle.write(json.dumps(payload, ensure_ascii=False))
            handle.write("\n")
        return path

    def _write_json(self, path: Path, payload: Mapping[str, Any]) -> Path:
        self._validate_payload(payload)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        return path

    def _case_dir(self, case_name: str) -> Path:
        if self.run_dir is None:
            raise RuntimeError("start_run() must be called before writing artifacts")
        case_dir = self.run_dir / "cases" / self._case_dir_name(case_name)
        case_dir.mkdir(parents=True, exist_ok=True)
        return case_dir

    def _case_dir_name(self, case_name: str) -> str:
        normalized = self._safe_dir_name(case_name)
        suffix = hashlib.sha256(case_name.encode("utf-8")).hexdigest()[:8]
        return f"{normalized}-{suffix}"

    def _safe_dir_name(self, raw_name: str) -> str:
        normalized = _UNSAFE_PATH_CHARS.sub("-", raw_name).strip(".-")
        if not normalized:
            raise ValueError("artifact directory name is empty after normalization")
        return normalized

    def _validate_payload(self, payload: Mapping[str, Any] | object) -> None:
        if not isinstance(payload, Mapping):
            raise TypeError("payload must be a mapping")
        try:
            json.dumps(payload, ensure_ascii=False)
        except TypeError as exc:
            raise TypeError("payload must be JSON serializable") from exc
