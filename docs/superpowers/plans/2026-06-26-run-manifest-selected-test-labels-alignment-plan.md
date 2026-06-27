# Run Manifest Selected Test Labels Alignment Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

> **Status (2026-06-26):** Task 1-4 的离线验证已完成；剩余主阻塞是真机运行与 Python/YAML artifact 等价验收，需要用户显式授权并开启真机开关后继续。

**Goal:** 让 `run_manifest.selected_tests` 在真实 pytest 运行链路里稳定表示“本次运行的标签集合”，而不是 case id、测试文件路径或临时占位值，从而让 Python/YAML 真机产物的 run-level provenance 更贴近第一阶段验收口径。

**Architecture:** 先补齐 Python smoke/regression/stability 用例缺失的 suite markers，让 pytest 运行本身具备可收集的标签信号；再在 `tests/conftest.py` 中增加一个纯 helper，从 session 已收集的 pytest items 提取允许的运行标签，并把它写入 `RunManifest.selected_tests`。最后把仍然使用 case id 或文件路径示例的单元测试数据对齐到标签语义，避免项目内部继续传播旧口径。

**Tech Stack:** Python 3、pytest、PowerShell、本地 unit/collect-only 验证

---

### Task 1: 补齐 Python 设备用例的 suite marker 语义

**Files:**
- Create: `C:\Users\3681\.codex\worktrees\2ab4\FT-automation\tests\unit\test_pytest_suite_markers.py`
- Modify: `C:\Users\3681\.codex\worktrees\2ab4\FT-automation\tests\smoke\test_device_connection.py`
- Modify: `C:\Users\3681\.codex\worktrees\2ab4\FT-automation\tests\smoke\test_settings_smoke.py`
- Modify: `C:\Users\3681\.codex\worktrees\2ab4\FT-automation\tests\smoke\test_settings_traverse_smoke.py`
- Modify: `C:\Users\3681\.codex\worktrees\2ab4\FT-automation\tests\smoke\test_widget_smoke.py`
- Modify: `C:\Users\3681\.codex\worktrees\2ab4\FT-automation\tests\smoke\test_workout_smoke.py`
- Modify: `C:\Users\3681\.codex\worktrees\2ab4\FT-automation\tests\regression\test_settings_regression.py`
- Modify: `C:\Users\3681\.codex\worktrees\2ab4\FT-automation\tests\regression\test_widget_regression.py`
- Modify: `C:\Users\3681\.codex\worktrees\2ab4\FT-automation\tests\regression\test_workout_regression.py`
- Modify: `C:\Users\3681\.codex\worktrees\2ab4\FT-automation\tests\stability\test_interaction_loop.py`

- [ ] **Step 1: 先写 marker 级别的失败测试**

在 `tests/unit/test_pytest_suite_markers.py` 新增 3 个 subprocess 级别测试，直接验证 Python 设备用例可以被 suite marker 选中：

```python
from __future__ import annotations

import subprocess
import sys


def test_python_smoke_suite_is_selectable_by_smoke_marker() -> None:
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "pytest",
            "tests/smoke",
            "--collect-only",
            "-q",
            "-m",
            "smoke",
        ],
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0
    assert "test_open_widget_and_return" in result.stdout
    assert "test_workout_happy_path_smoke" in result.stdout
    assert "test_device_connection_and_watchface_baseline" in result.stdout
```

```python
def test_python_regression_suite_is_selectable_by_regression_marker() -> None:
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "pytest",
            "tests/regression",
            "--collect-only",
            "-q",
            "-m",
            "regression",
        ],
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0
    assert "test_switch_widget_and_return_watchface_regression" in result.stdout
    assert "test_start_pause_resume_stop_workout_regression" in result.stdout
    assert "test_toggle_focused_setting_regression" in result.stdout
```

```python
def test_python_stability_suite_is_selectable_by_stability_marker() -> None:
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "pytest",
            "tests/stability",
            "--collect-only",
            "-q",
            "-m",
            "stability",
        ],
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0
    assert "test_watchface_widget_settings_loop" in result.stdout
```

- [ ] **Step 2: 运行聚焦测试，确认 RED**

Run:

```powershell
python -m pytest tests/unit/test_pytest_suite_markers.py -v
```

Expected: 至少 smoke / regression 测试失败，因为现有 Python 设备用例只有 `device` marker，没有 `smoke` / `regression` / `stability` suite marker。

- [ ] **Step 3: 做最小实现**

只给现有 Python 设备用例补 suite marker，不改测试主体逻辑：

- `tests/smoke/*` 里的设备用例同时标记 `@pytest.mark.device` 和 `@pytest.mark.smoke`
- `tests/regression/*` 里的设备用例同时标记 `@pytest.mark.device` 和 `@pytest.mark.regression`
- `tests/stability/test_interaction_loop.py` 保持 `@pytest.mark.device`，并确认 `@pytest.mark.stability` 在函数上

例如：

```python
@pytest.mark.device
@pytest.mark.smoke
def test_open_widget_and_return(device_dsl) -> None:
    ...
```

- [ ] **Step 4: 运行聚焦测试，确认 GREEN**

Run:

```powershell
python -m pytest tests/unit/test_pytest_suite_markers.py -v
```

Expected: 3 个测试全部通过。

- [ ] **Step 5: 跑本任务必要回归**

Run:

```powershell
python -m pytest tests/smoke --collect-only -q -m smoke
python -m pytest tests/regression --collect-only -q -m regression
python -m pytest tests/stability --collect-only -q -m stability
python -m pytest tests/scenario --collect-only -q -m yaml
```

Expected:

- smoke collect-only 仍只收集 smoke 目录里的 5 个 Python 用例
- regression collect-only 仍只收集 regression 目录里的 4 个 Python 用例
- stability collect-only 仍只收集 `test_watchface_widget_settings_loop`
- scenario collect-only 仍收集 `smoke_widget_yaml`、`smoke_workout_yaml`

- [ ] **Step 6: 汇报结果**

汇报中必须包含：

- 哪些 Python 设备测试文件新增了 suite marker
- RED / GREEN 跑了什么
- collect-only 回归是否仍符合 smoke / regression / stability / yaml 的预期范围


### Task 2: 让 `run_manifest.selected_tests` 真实落为运行标签列表

**Files:**
- Modify: `C:\Users\3681\.codex\worktrees\2ab4\FT-automation\tests\conftest.py`
- Create: `C:\Users\3681\.codex\worktrees\2ab4\FT-automation\tests\unit\test_run_manifest_selected_labels.py`
- Modify: `C:\Users\3681\.codex\worktrees\2ab4\FT-automation\tests\unit\test_artifact_writer.py`
- Modify: `C:\Users\3681\.codex\worktrees\2ab4\FT-automation\tests\unit\test_artifact_compare.py`

- [ ] **Step 1: 先写 helper 的失败测试**

在 `tests/unit/test_run_manifest_selected_labels.py` 新增针对纯 helper 的单元测试，避免直接耦合真实设备：

```python
from __future__ import annotations

from tests.conftest import _selected_test_labels_from_items


class FakeMarker:
    def __init__(self, name: str) -> None:
        self.name = name


class FakeItem:
    def __init__(self, *marker_names: str) -> None:
        self._markers = [FakeMarker(name) for name in marker_names]

    def iter_markers(self):
        return iter(self._markers)


def test_selected_test_labels_from_items_returns_stable_allowed_union() -> None:
    labels = _selected_test_labels_from_items(
        [
            FakeItem("device", "smoke"),
            FakeItem("device", "yaml", "smoke"),
            FakeItem("device", "unknown-marker"),
        ]
    )

    assert labels == ["device", "yaml", "smoke"]
```

```python
def test_selected_test_labels_from_items_ignores_untracked_markers() -> None:
    labels = _selected_test_labels_from_items(
        [FakeItem("device", "custom"), FakeItem("device", "regression")]
    )

    assert labels == ["device", "regression"]
```

```python
def test_selected_test_labels_from_items_keeps_device_only_when_no_suite_marker() -> None:
    labels = _selected_test_labels_from_items([FakeItem("device")])

    assert labels == ["device"]
```

- [ ] **Step 2: 运行聚焦测试，确认 RED**

Run:

```powershell
python -m pytest tests/unit/test_run_manifest_selected_labels.py -v
```

Expected: 失败，原因是 helper 尚不存在。

- [ ] **Step 3: 写最小实现**

在 `tests/conftest.py` 中增加一个纯 helper，并把 fixture 的 `RunManifest.selected_tests` 改成读取 session items 的标签集合：

```python
RUN_LABEL_MARKERS = ("device", "yaml", "smoke", "regression", "stability")


def _selected_test_labels_from_items(items) -> list[str]:
    marker_names = {
        marker.name
        for item in items
        for marker in item.iter_markers()
    }
    return [name for name in RUN_LABEL_MARKERS if name in marker_names]
```

`device_dsl` fixture 改为接收 `request`，并使用：

```python
selected_tests=_selected_test_labels_from_items(request.session.items),
```

约束：

- 不要把 `selected_tests` 重新写回 case id
- 不要读取 YAML case id 或 Python 测试函数名
- 不要改变 `framework_version` / `device_serial` / `sds_url` 的生成方式

- [ ] **Step 4: 把陈旧的单元测试示例数据对齐到标签语义**

更新 `tests/unit/test_artifact_writer.py` 与 `tests/unit/test_artifact_compare.py` 中仍然使用文件路径或 case id 的 `selected_tests` 示例数据，使它们符合“标签列表”口径。

建议最小替换原则：

- `tests/unit/test_artifact_writer.py` 里用 `["device", "smoke"]`、`["device", "regression"]`
- `tests/unit/test_artifact_compare.py` 里把 `["smoke_widget"]`、`["smoke_widget_yaml"]` 这类值换成不带 case id 语义的标签列表示例，例如：

```python
"selected_tests": ["device", "smoke"]
"selected_tests": ["device", "yaml", "smoke"]
```

不要改动这些测试原本想验证的断言主题；这里只是把示例数据从旧口径收成新口径。

- [ ] **Step 5: 运行聚焦测试，确认 GREEN**

Run:

```powershell
python -m pytest tests/unit/test_run_manifest_selected_labels.py -v
python -m pytest tests/unit/test_artifact_writer.py -v
python -m pytest tests/unit/test_artifact_compare.py -v
```

Expected:

- helper 新测试全绿
- `test_artifact_writer.py` 全绿
- `test_artifact_compare.py` 全绿

- [ ] **Step 6: 跑本轮必要回归**

Run:

```powershell
python -m pytest tests/unit -v
$env:PYTHONPATH='src'; python -m watch_ui_automation.scenarios.loader validate tests/yaml_cases --suite smoke
python -m pytest tests/scenario --collect-only -q
python -m pytest tests/scenario --collect-only -q -m yaml
python -m pytest tests/scenario -v
python -m pytest tests/smoke -v
```

Expected:

- `tests/unit` 全绿
- YAML validate 输出 `Validated 2 scenario cases`
- `tests/scenario --collect-only -q` 仍收集 `smoke_widget_yaml` 与 `smoke_workout_yaml`
- `tests/scenario --collect-only -q -m yaml` 结果与上面一致
- `tests/scenario -v` 仍为 2 skipped
- `tests/smoke -v` 仍为 5 skipped

- [ ] **Step 7: 汇报结果**

汇报中必须包含：

- `tests/conftest.py` 是如何从 session items 提取运行标签的
- 哪些测试数据已从 case id / 文件路径示例收成标签列表示例
- 离线验证结果
- 明确说明：这次仍未做真实设备验证，也未完成 Python/YAML 真机 artifact 等价验收


### Task 3: 为 session 级标签并集语义补一层 fixture 集成回归

**Files:**
- Modify: `C:\Users\3681\.codex\worktrees\2ab4\FT-automation\tests\unit\test_run_manifest_selected_labels.py`

- [ ] **Step 1: 先写 fixture 集成级失败测试**

在 `tests/unit/test_run_manifest_selected_labels.py` 新增一个聚焦测试，直接调用 `tests.conftest.device_dsl.__wrapped__`，通过 monkeypatch fake 掉设备依赖，验证 fixture 真正把 `request.session.items` 的 marker 并集写进 `RunManifest.selected_tests`。

建议测试形态：

```python
def test_device_dsl_uses_session_item_labels_for_run_manifest(monkeypatch, tmp_path: Path) -> None:
    captured_manifest = {}

    class FakeWriter:
        def __init__(self, root_dir) -> None:
            self.root_dir = root_dir

        def start_run(self, manifest) -> None:
            captured_manifest["selected_tests"] = manifest.selected_tests

    class FakeTransport:
        def __init__(self, url: str) -> None:
            self.url = url

        def close(self) -> None:
            return None

    class FakeDevice:
        def __init__(self, **kwargs) -> None:
            self.kwargs = kwargs

        def assert_connected(self) -> None:
            return None

    class FakeSession:
        def __init__(self, **kwargs) -> None:
            self.kwargs = kwargs

    class FakeDsl:
        def __init__(self, **kwargs) -> None:
            self.kwargs = kwargs

    request = type(
        "Request",
        (),
        {
            "session": type(
                "Session",
                (),
                {
                    "items": [
                        FakeItem("device", "smoke"),
                        FakeItem("device", "yaml", "smoke"),
                    ]
                },
            )()
        },
    )()
```

断言至少包括：

```python
assert captured_manifest["selected_tests"] == ["device", "yaml", "smoke"]
```

- [ ] **Step 2: 运行聚焦测试，确认 RED**

Run:

```powershell
python -m pytest tests/unit/test_run_manifest_selected_labels.py -k session_item_labels -v
```

Expected: 新测试失败，原因是当前还没有对 fixture 集成路径的覆盖，或需要先补 fake/monkeypatch 连接。

- [ ] **Step 3: 用最小实现让测试变绿**

优先原则：

- 如果新测试只缺测试辅助代码，就只改测试文件，不改生产代码
- 只有当测试暴露 `tests/conftest.py` 的真实语义缺口时，才修改生产实现

目标是让测试明确锁定当前意图：

- `selected_tests` 是 session 级 artifact 的运行标签并集
- 允许同时包含 `device`、`yaml`、`smoke`
- 不从 case id、文件路径或函数名派生标签

- [ ] **Step 4: 运行聚焦测试，确认 GREEN**

Run:

```powershell
python -m pytest tests/unit/test_run_manifest_selected_labels.py -k session_item_labels -v
python -m pytest tests/unit/test_run_manifest_selected_labels.py -v
```

Expected:

- 聚焦测试通过
- `test_run_manifest_selected_labels.py` 全绿

- [ ] **Step 5: 跑本轮必要回归**

Run:

```powershell
python -m pytest tests/unit -v
$env:PYTHONPATH='src'; python -m watch_ui_automation.scenarios.loader validate tests/yaml_cases --suite smoke
python -m pytest tests/scenario --collect-only -q
python -m pytest tests/scenario -v
python -m pytest tests/smoke -v
```

Expected:

- `tests/unit` 全绿
- YAML validate 输出 `Validated 2 scenario cases`
- `tests/scenario --collect-only -q` 仍收集 `smoke_widget_yaml` 与 `smoke_workout_yaml`
- `tests/scenario -v` 仍为 2 skipped
- `tests/smoke -v` 仍为 5 skipped

- [ ] **Step 6: 汇报结果**

汇报中必须包含：

- 这次是否只修改了 `tests/unit/test_run_manifest_selected_labels.py`
- fixture 集成测试如何证明 `selected_tests` 的 session 级并集语义
- 是否需要改生产代码；如果没有，需要明确说明“这次只是补集成回归锁”


### Task 4: 为未开启真机开关时的 YAML scenario skip 行为补自动化证据

**Files:**
- Modify: `C:\Users\3681\.codex\worktrees\2ab4\FT-automation\tests\unit\scenarios\test_pytest_integration.py`

- [ ] **Step 1: 先写 skip 行为集成测试**

在 `tests/unit/scenarios/test_pytest_integration.py` 新增一个 subprocess 级别测试，名称固定为 `test_scenario_runtime_skips_device_cases_without_real_device_opt_in`，直接验证在未设置 `WATCH_UI_RUN_DEVICE_TESTS=1` 时运行 `tests/scenario` 会走 skip，而不是失败或误执行。

建议测试形态：

```python
def test_scenario_runtime_skips_device_cases_without_real_device_opt_in() -> None:
    env = os.environ.copy()
    env.pop("WATCH_UI_RUN_DEVICE_TESTS", None)

    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "pytest",
            "tests/scenario",
            "-v",
        ],
        check=False,
        capture_output=True,
        text=True,
        env=env,
    )

    output = result.stdout + result.stderr
    assert result.returncode == 0
    assert "test_yaml_scenario[smoke_widget_yaml]" in output
    assert "test_yaml_scenario[smoke_workout_yaml]" in output
    assert "SKIPPED" in output
    assert "Set WATCH_UI_RUN_DEVICE_TESTS=1 to run real-device tests" in output
```

如果输出不稳定，可额外断言：

```python
assert "2 skipped" in output or "SKIPPED [2]" in output
```

- [ ] **Step 2: 运行聚焦测试，确认 RED**

Run:

```powershell
python -m pytest tests/unit/scenarios/test_pytest_integration.py -k real_device_opt_in -v
```

Expected: 新增测试先失败，因为当前还没有这条 runtime skip 保护。

- [ ] **Step 3: 用最小实现让测试变绿**

优先原则：

- 优先只改测试文件，不改生产代码
- 只有当新测试暴露真实行为与预期不符时，才修改生产实现

目标：

- 为“未开启真机开关时 YAML scenario runtime 正常 skip”补一条稳定自动化证据
- 不改变 `tests/scenario/test_yaml_scenarios.py` 或 `tests/conftest.py` 的既有 skip 语义，除非测试证明它们有问题

- [ ] **Step 4: 运行聚焦测试，确认 GREEN**

Run:

```powershell
python -m pytest tests/unit/scenarios/test_pytest_integration.py -k real_device_opt_in -v
python -m pytest tests/unit/scenarios/test_pytest_integration.py -v
```

Expected:

- 聚焦测试通过
- `test_pytest_integration.py` 全绿

- [ ] **Step 5: 跑本轮必要回归**

Run:

```powershell
python -m pytest tests/unit -v
$env:PYTHONPATH='src'; python -m watch_ui_automation.scenarios.loader validate tests/yaml_cases --suite smoke
python -m pytest tests/scenario --collect-only -q
python -m pytest tests/scenario -v
python -m pytest tests/smoke -v
```

Expected:

- `tests/unit` 全绿
- YAML validate 输出 `Validated 2 scenario cases`
- `tests/scenario --collect-only -q` 仍收集 `smoke_widget_yaml` 与 `smoke_workout_yaml`
- `tests/scenario -v` 仍为 2 skipped
- `tests/smoke -v` 仍为 5 skipped

- [ ] **Step 6: 汇报结果**

汇报中必须包含：

- 这次是否只修改了 `tests/unit/scenarios/test_pytest_integration.py`
- skip 集成测试如何证明“未开真机开关时 YAML scenario runtime 正常 skip”
- 是否需要改生产代码；如果没有，需要明确说明“这次只是补自动化证据”
