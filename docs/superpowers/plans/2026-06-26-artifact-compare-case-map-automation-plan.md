# Artifact Compare Case Map Automation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 为 Python smoke artifact 与 YAML smoke artifact 的 run-level 对比补一个离线 `case_map` 建议工具，降低真机验收时手工映射出错的概率。

**Architecture:** 在现有 `watch_ui_automation.artifacts.compare` CLI 上增量增加一个“建议 case_map”的只读入口，不改现有 compare 成功/失败语义。建议逻辑只基于 run 目录下实际产出的 `result.json.case_name` 建索引，并优先按当前已存在的 `_yaml` 后缀命名约定配对，例如 `smoke_widget -> smoke_widget_yaml`。CLI 只负责输出建议映射或未匹配错误，不直接替代正式 compare。

**Tech Stack:** Python 3、pytest、PowerShell、本地 artifact fixture

---

### Task 1: 在 compare CLI 中增加 case_map 建议入口

**Files:**
- Modify: `C:\Users\3681\.codex\worktrees\2ab4\FT-automation\src\watch_ui_automation\artifacts\compare.py`
- Modify: `C:\Users\3681\.codex\worktrees\2ab4\FT-automation\tests\unit\test_artifact_compare.py`

- [ ] **Step 1: 先写失败测试**

在 `tests/unit/test_artifact_compare.py` 新增以下测试，覆盖 helper 和 CLI 两层真实行为：

1. `test_suggest_case_map_pairs_cases_by_yaml_suffix`
2. `test_suggest_case_map_rejects_unmatched_python_case`
3. `test_artifact_compare_cli_suggests_run_case_map`
4. `test_artifact_compare_cli_rejects_unmatched_case_map_suggestion`

建议测试要点：

```python
mapping = suggest_case_map(python_run, yaml_run)
assert mapping == {
    "smoke_widget": "smoke_widget_yaml",
    "smoke_workout": "smoke_workout_yaml",
}
```

CLI 成功路径断言：

```python
assert result.returncode == 0
assert "smoke_widget:smoke_widget_yaml" in result.stdout
assert "smoke_workout:smoke_workout_yaml" in result.stdout
```

CLI 失败路径断言：

```python
assert result.returncode != 0
assert "Unable to suggest case_map" in result.stderr
assert "python unmatched cases" in result.stderr
```

- [ ] **Step 2: 运行聚焦测试，确认 RED**

Run:

```powershell
python -m pytest tests/unit/test_artifact_compare.py -k "suggest_case_map or case_map_suggestion" -v
```

Expected: 新增测试失败，失败原因是 helper / CLI 入口尚不存在。

- [ ] **Step 3: 写最小实现**

只在 `src/watch_ui_automation/artifacts/compare.py` 中补最小实现：

1. 新增一个纯函数：

```python
def suggest_case_map(
    python_run_dir: str | Path,
    yaml_run_dir: str | Path,
    *,
    yaml_suffix: str = "_yaml",
) -> dict[str, str]:
    ...
```

2. 逻辑要求：
- 基于 run 目录的 `cases/*/result.json` 建 `case_name -> case_dir` 索引
- 对每个 Python case，优先尝试 `${python_case}${yaml_suffix}`
- 若后缀匹配不存在，再尝试同名匹配
- 任一 Python case 无法唯一匹配时抛出 `ValueError`
- 若 YAML run 里存在未被匹配的 case，也抛出 `ValueError`
- 不要读取或比较 `selected_tests`
- 不要改变现有 `compare_case_artifacts()` / `compare_run_artifacts()` 语义

3. CLI 增量参数：

```python
parser.add_argument(
    "--suggest-case-map",
    action="store_true",
    help="Print suggested python_case:yaml_case mappings for two run directories.",
)
parser.add_argument(
    "--yaml-case-suffix",
    default="_yaml",
    help="Suffix used when suggesting YAML case names from Python case names.",
)
```

4. CLI 行为：
- 当传入 `--suggest-case-map` 时，打印每行一个 `python_case:yaml_case`
- 成功返回 `0`
- 若建议失败，打印 `Unable to suggest case_map: ...` 到 stderr 并返回 `1`
- `--suggest-case-map` 与正式 compare 互斥；优先走建议逻辑，不执行 artifact compare

- [ ] **Step 4: 运行聚焦测试，确认 GREEN**

Run:

```powershell
python -m pytest tests/unit/test_artifact_compare.py -k "suggest_case_map or case_map_suggestion" -v
```

Expected: 以上新增测试通过。

- [ ] **Step 5: 运行本轮必要回归**

Run:

```powershell
python -m pytest tests/unit/test_artifact_compare.py -v
python -m pytest tests/unit -v
$env:PYTHONPATH='src'; python -m watch_ui_automation.scenarios.loader validate tests/yaml_cases --suite smoke
python -m pytest tests/scenario --collect-only -q
```

Expected:

- `tests/unit/test_artifact_compare.py` 全绿
- `tests/unit` 全绿
- YAML validate 输出 `Validated 2 scenario cases`
- `tests/scenario --collect-only` 仍收集 `smoke_widget_yaml` 与 `smoke_workout_yaml`

- [ ] **Step 6: 汇报结果**

汇报中必须包含：

- 实现状态：DONE / DONE_WITH_CONCERNS / BLOCKED / NEEDS_CONTEXT
- 修改了哪些文件
- RED / GREEN / 回归分别跑了什么
- 是否保持了 `selected_tests` 与 `case_map` 解耦

### Task 2: 更新 README 的真机对比前离线预检说明

**Files:**
- Modify: `C:\Users\3681\.codex\worktrees\2ab4\FT-automation\README.md`

- [ ] **Step 1: 补 README 命令示例**

在 README 的 artifact compare 段落中补一段离线建议流程，至少包含：

```powershell
$env:PYTHONPATH='src'
python -m watch_ui_automation.scenarios.loader validate tests/yaml_cases --suite smoke
python -m pytest tests/scenario --collect-only -q
python -m watch_ui_automation.artifacts.compare <python_run_dir> <yaml_run_dir> --suggest-case-map
```

并说明当前默认按 `_yaml` 后缀建议映射，例如 `smoke_widget -> smoke_widget_yaml`。

- [ ] **Step 2: 手动复核 README 文案**

要求：
- 不暗示会自动执行真实设备测试
- 不把 `selected_tests` 描述成 case id
- 明确 `--suggest-case-map` 只是建议映射，不替代正式 compare

- [ ] **Step 3: 汇报结果**

说明：
- README 更新了哪些命令
- 文案里如何约束 `selected_tests` / `case_map` 语义
