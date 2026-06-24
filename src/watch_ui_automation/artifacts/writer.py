import json
from pathlib import Path
from typing import Any, Optional, Union

from watch_ui_automation.models import CaseResult, RunManifest


class ArtifactWriter:
    def __init__(self, root_dir: Union[Path, str]) -> None:
        self._root_dir = Path(root_dir)
        self._run_dir: Optional[Path] = None

    def start_run(self, manifest: RunManifest) -> Path:
        run_dir = self._root_dir / manifest.run_id
        run_dir.mkdir(parents=True, exist_ok=True)
        self._write_json(run_dir / "run_manifest.json", manifest.to_dict())
        self._run_dir = run_dir
        return run_dir

    def write_step(self, case_id: str, payload: dict[str, Any]) -> Path:
        return self._append_jsonl(case_id, "steps.jsonl", payload)

    def write_transport(self, case_id: str, payload: dict[str, Any]) -> Path:
        return self._append_jsonl(case_id, "transport.jsonl", payload)

    def write_assertion(self, case_id: str, payload: dict[str, Any]) -> Path:
        return self._append_jsonl(case_id, "assertions.jsonl", payload)

    def write_snapshot(self, case_id: str, payload: dict[str, Any]) -> Path:
        return self._write_json(self._case_dir(case_id) / "state_snapshot.json", payload)

    def write_case_result(self, result: CaseResult) -> Path:
        return self._write_json(
            self._case_dir(result.case_id) / "result.json", result.to_dict()
        )

    def write_failure_summary(self, case_id: str, markdown: str) -> Path:
        path = self._case_dir(case_id) / "failure_summary.md"
        path.write_text(markdown, encoding="utf-8")
        return path

    def _append_jsonl(self, case_id: str, name: str, payload: dict[str, Any]) -> Path:
        path = self._case_dir(case_id) / name
        with path.open("a", encoding="utf-8", newline="\n") as handle:
            handle.write(json.dumps(payload, ensure_ascii=False))
            handle.write("\n")
        return path

    def _write_json(self, path: Path, payload: dict[str, Any]) -> Path:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        return path

    def _case_dir(self, case_id: str) -> Path:
        if self._run_dir is None:
            raise RuntimeError("start_run() must be called before writing artifacts")
        case_dir = self._run_dir / "cases" / case_id
        case_dir.mkdir(parents=True, exist_ok=True)
        return case_dir
