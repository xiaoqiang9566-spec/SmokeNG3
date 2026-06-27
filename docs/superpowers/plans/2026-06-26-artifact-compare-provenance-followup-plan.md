# Artifact Compare Provenance Follow-up Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 让 Python smoke artifact 与 YAML smoke artifact 的 run-level provenance 对比继续贴近真实验收场景，补上 `run_manifest.framework_version` 一致性校验。

**Architecture:** 继续沿用现有 `watch_ui_automation.artifacts.compare` 的 run-level 比较入口，不引入新抽象。先在 `tests/unit/test_artifact_compare.py` 写一个只验证 `framework_version` 不一致时失败的 RED 用例，再在 `_compare_run_manifest_environment(...)` 中补最小实现，最后跑聚焦回归和离线场景验证。

**Tech Stack:** Python 3、pytest、本地 JSON artifact fixture、PowerShell

---

### Task 1: 补齐 run_manifest framework_version provenance 校验

**Files:**
- Modify: `C:\Users\3681\.codex\worktrees\2ab4\FT-automation\tests\unit\test_artifact_compare.py`
- Modify: `C:\Users\3681\.codex\worktrees\2ab4\FT-automation\src\watch_ui_automation\artifacts\compare.py`
- Verify: `C:\Users\3681\.codex\worktrees\2ab4\FT-automation\tests\unit\scenarios\test_runner_artifacts.py`

- [ ] **Step 1: 写失败测试**

在 `tests/unit/test_artifact_compare.py` 新增一个聚焦用例，名称固定为 `test_compare_run_artifacts_rejects_framework_version_mismatch`。测试模式和现有 `test_compare_run_artifacts_rejects_environment_manifest_mismatch` 保持一致，但只制造 `framework_version` 不一致，`device_serial` 与 `sds_url` 保持一致。

```python
def test_compare_run_artifacts_rejects_framework_version_mismatch(
    tmp_path: Path,
) -> None:
    python_run = tmp_path / "python-run"
    yaml_run = tmp_path / "yaml-run"
    python_case = make_run_case_dir(python_run, "smoke_widget")
    yaml_case = make_run_case_dir(yaml_run, "smoke_widget_yaml")
    write_json(
        python_case / "result.json",
        {
            "case_name": "smoke_widget",
            "status": "passed",
            "error_type": None,
            "evidence_refs": ["steps.jsonl", "assertions.jsonl", "result.json"],
        },
    )
    write_json(
        yaml_case / "result.json",
        {
            "case_name": "smoke_widget_yaml",
            "status": "passed",
            "error_type": None,
            "evidence_refs": ["steps.jsonl", "assertions.jsonl", "result.json"],
        },
    )
    write_json(
        python_run / "run_manifest.json",
        {
            "device_serial": "TEST123",
            "sds_url": "ws://localhost:65534",
            "selected_tests": ["device"],
            "framework_version": "0.1.0",
        },
    )
    write_json(
        yaml_run / "run_manifest.json",
        {
            "device_serial": "TEST123",
            "sds_url": "ws://localhost:65534",
            "selected_tests": ["yaml"],
            "framework_version": "0.2.0",
        },
    )

    result = compare_run_artifacts(
        python_run,
        yaml_run,
        {"smoke_widget": "smoke_widget_yaml"},
    )

    assert result.ok is False
    assert (
        "run_manifest.json framework_version mismatch: "
        "python='0.1.0', yaml='0.2.0'"
    ) in result.differences
```

- [ ] **Step 2: 运行聚焦测试，确认 RED**

Run:

```powershell
python -m pytest tests/unit/test_artifact_compare.py -k framework_version_mismatch -v
```

Expected: 新增测试失败，失败原因是当前实现还没有报告 `run_manifest.json framework_version mismatch`。

- [ ] **Step 3: 写最小实现**

仅修改 `src/watch_ui_automation/artifacts/compare.py` 的 `_compare_run_manifest_environment(...)`，把比较字段从：

```python
for field in ("device_serial", "sds_url"):
```

改为：

```python
for field in ("device_serial", "sds_url", "framework_version"):
```

不要引入 `selected_tests` 与 `case_map` 的新耦合，也不要改动 `_RUN_MANIFEST_STRING_FIELDS` 之外的校验语义。

- [ ] **Step 4: 运行聚焦测试，确认 GREEN**

Run:

```powershell
python -m pytest tests/unit/test_artifact_compare.py -k framework_version_mismatch -v
```

Expected: 该测试通过。

- [ ] **Step 5: 运行本轮必要回归**

依次执行下列命令并检查退出码与关键输出：

```powershell
python -m pytest tests/unit/test_artifact_compare.py -v
python -m pytest tests/unit -v
$env:PYTHONPATH='src'; python -m watch_ui_automation.scenarios.loader validate tests/yaml_cases --suite smoke
python -m pytest tests/scenario --collect-only -q
python -m pytest tests/scenario -v
python -m pytest tests/smoke -v
```

Expected:

- `tests/unit/test_artifact_compare.py` 全绿
- `tests/unit` 全绿
- YAML validate 输出 `Validated 2 scenario cases`
- `tests/scenario --collect-only` 仍能收集 `smoke_widget_yaml` 和 `smoke_workout_yaml`
- `tests/scenario -v` 仍为 2 skipped
- `tests/smoke -v` 仍为 5 skipped

- [ ] **Step 6: 汇报结果**

汇报中必须包含：

- 实现状态：DONE / DONE_WITH_CONCERNS / BLOCKED / NEEDS_CONTEXT
- 具体修改了哪些文件
- RED 和 GREEN 分别跑了什么
- 回归验证结果
- 明确说明未做真实设备验证、未完成 Python/YAML 真机 artifact 等价验收

### Task 2: 补齐 framework_version mismatch 的 CLI 用户入口回归

**Files:**
- Modify: `C:\Users\3681\.codex\worktrees\2ab4\FT-automation\tests\unit\test_artifact_compare.py`

- [ ] **Step 1: 写失败测试**

在 `tests/unit/test_artifact_compare.py` 新增一个 CLI 级别用例，名称固定为 `test_artifact_compare_cli_reports_framework_version_mismatch_for_run_compare`。它应复用现有 `subprocess.run(... python -m watch_ui_automation.artifacts.compare ...)` 模式，通过 `--case-map smoke_widget:smoke_widget_yaml` 调用 run-level compare，并制造 `framework_version` 不一致。

断言至少包括：

```python
assert result.returncode != 0
assert "Artifact comparison failed" in result.stderr
assert (
    "run_manifest.json framework_version mismatch: "
    "python='python-framework', yaml='yaml-framework'"
) in result.stderr
```

- [ ] **Step 2: 运行聚焦测试，确认 RED**

Run:

```powershell
python -m pytest tests/unit/test_artifact_compare.py -k framework_version_mismatch_for_run_compare -v
```

Expected: 新增测试失败，失败原因是 CLI 入口当前还没有这条回归保护。

- [ ] **Step 3: 用最小实现让测试变绿**

优先选择“只补测试夹具数据，不动生产代码”的方案。因为 CLI 入口本身已经走 `compare_run_artifacts()`，如果新增测试是正确的，理论上不应需要改 `src/watch_ui_automation/artifacts/compare.py`。

- [ ] **Step 4: 运行聚焦测试，确认 GREEN**

Run:

```powershell
python -m pytest tests/unit/test_artifact_compare.py -k framework_version_mismatch_for_run_compare -v
```

Expected: 测试通过。

- [ ] **Step 5: 运行本轮必要回归**

Run:

```powershell
python -m pytest tests/unit/test_artifact_compare.py -v
python -m pytest tests/unit -v
```

Expected:

- `tests/unit/test_artifact_compare.py` 全绿
- `tests/unit` 全绿

- [ ] **Step 6: 汇报结果**

汇报中必须包含：

- 这次是否只修改了 `tests/unit/test_artifact_compare.py`
- RED/GREEN 命令与结果
- 是否需要改生产代码；如果没有，需要明确说明“CLI 入口已受现有实现覆盖，这次只是补回归锁”
