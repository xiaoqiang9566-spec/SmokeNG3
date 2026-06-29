# watch-ui-automation

基于 `SDSApplicationServer` 的手表 UI 自动化脚手架，用于在真机上执行 watchface、settings、widget、workout 的 smoke / regression / stability 校验。

## 启动

1. 使用 Python 3.9 安装依赖。

```powershell
python -m pip install -e ".[dev]"
```

2. 启动 SDS 服务，并确认 `configs/default.yaml` 中的 `device.serial`、`device.sds_url`、`input` 坐标和 `navigation` 动作与当前设备一致。

## 当前导航口径

- `current_page_uri` 使用 `Ui/View/Stack/-1/ViewName`，watchface 基线严格是 `main`。
- baseline recovery 统一使用 `press_bottom`；除 maps widget 外，任何脏状态都应能借此回到 `main`。
- settings 校验当前走 `Ui/Control/Open/Close` 直开直关，因此它验证的是“view 名称和返回链路”，不是 swipe 校准。
- widget 校验当前以 `Ui/View/Stack/Path` 为主证据。真机进入 widget list 的默认动作是上滑屏幕，即 `open_widget: [swipe_up]`；路径应该不再停留在 watchface 基线。
- workout 校验当前以 `current_page/current_widget/workout_state` 联合判断为主证据；默认导航使用下滑手势，即 `open_workout: [swipe_down]`。
- 物理按键短按默认 `duration: 0.1`；需要长按时显式传 `duration: 2`，不要用触摸事件间隔模拟长按。
- 2026-06-25 的现有真机产物已经证明旧版 widget/workout 断言存在假阳性：
- `smoke_widget` / `regression_widget` 通过时，`actual` 仍然是 `/_watch-face(c)/main`
- `smoke_workout` / `regression_workout` 通过时，`actual` 仍然是 `0`
- 因此仓库现在把 widget/workout smoke/regression 收紧成“必须看到视图切换证据”，否则直接失败。
- `swipe_up` 打开 widget list，widget 校验当前以 `Ui/View/Stack/Path` 为主证据。
- `swipe_left` 打开 pinned widget 快捷入口，不再作为默认 widget list 入口。
- `swipe_down` 目标语义是打开 workout list，但截至 2026-06-29 真机尚未验证成功；workout 探测当前仍以 `current_page/current_widget/workout_state` 联合判断为准。
- 2026-06-27 的真机 smoke 已验证 baseline recovery 与 settings 链路通过；widget/workout 仍需继续按新语义校准断言与手势行为。

## 运行

先跑 unit：

```powershell
python -m pytest tests/unit -v
```

不打开真机开关时，device tests 会被跳过：

```powershell
python -m pytest tests/smoke -v
python -m pytest tests/regression -v
```

真机 smoke：

```powershell
$env:WATCH_UI_RUN_DEVICE_TESTS='1'
python -m pytest tests/smoke -v --device-config configs/default.yaml
```

YAML 场景离线校验：

```powershell
$env:PYTHONPATH='src'
python -m watch_ui_automation.scenarios.loader validate tests/yaml_cases --suite smoke
python -m pytest tests/scenario --collect-only -q --scenario-suite smoke
```

真机对比前的离线预检：

```powershell
$env:PYTHONPATH='src'
python -m watch_ui_automation.scenarios.loader validate tests/yaml_cases --suite smoke
python -m pytest tests/scenario --collect-only -q --scenario-suite smoke
python -m watch_ui_automation.artifacts.compare <python_compare_run_dir> <yaml_run_dir> --suggest-case-map
```

先跑一个可 compare 的 Python smoke 子集 run，只包含 `smoke_widget` 和 `smoke_workout`：

```powershell
$env:WATCH_UI_RUN_DEVICE_TESTS='1'
python -m pytest tests/smoke/test_widget_smoke.py tests/smoke/test_workout_smoke.py -v --device-config configs/default.yaml
```

`--suggest-case-map` 只适用于这个 compare-scope 子集 run；如果 Python run 来自 full `tests/smoke`，当前会因为 `smoke_device_connection`、`smoke_settings`、`smoke_settings_views` 没有对应 YAML case 而 unmatched。full smoke 仍然可以单独作为更宽的健康检查来跑，但不要把它直接拿去做 `--suggest-case-map`。

这一步只用于确认 YAML 场景可加载、pytest 可收集，并为 run 级 compare 生成候选映射建议；它不会自动执行任何真实设备测试。当前建议生成规则会按 `_yaml` 后缀补全映射，例如 `smoke_widget -> smoke_widget_yaml`。`--suggest-case-map` 只输出建议映射，不替代正式 compare；正式对比仍需在拿到 Python run 与 YAML run 产物后执行 `watch_ui_automation.artifacts.compare`，必要时再显式传入 `--case-map`。

YAML 场景真机 smoke：

```powershell
$env:WATCH_UI_RUN_DEVICE_TESTS='1'
python -m pytest tests/scenario -v --device-config configs/default.yaml --scenario-suite smoke
```

真机跑完 Python smoke 和 YAML smoke 后，可对比核心产物结构：

```powershell
$env:PYTHONPATH='src'
python -m watch_ui_automation.artifacts.compare <python_case_dir> <yaml_case_dir>
python -m watch_ui_automation.artifacts.compare <python_full_smoke_run_dir> <yaml_run_dir> --case-map smoke_widget:smoke_widget_yaml --case-map smoke_workout:smoke_workout_yaml
```

真机验收结束后，如果要回到离线命令，先清理 `WATCH_UI_RUN_DEVICE_TESTS` 或新开一个 PowerShell 会话：
```powershell
Remove-Item Env:WATCH_UI_RUN_DEVICE_TESTS -ErrorAction SilentlyContinue
```

这里的 `case_map` 用于 compare 阶段显式指定 Python case 与 YAML case 的对应关系；如果你在 `run_manifest` 里看到 `selected_tests`，它表示的是标签列表而不是 case id，使用 compare 时也不要把它当成 `case_map`。

真机 regression：

```powershell
$env:WATCH_UI_RUN_DEVICE_TESTS='1'
python -m pytest tests/regression -v --device-config configs/default.yaml
```

真机 stability：

```powershell
$env:WATCH_UI_RUN_DEVICE_TESTS='1'
python -m pytest tests/stability -v --device-config configs/default.yaml
```

## 证据产物

- `artifacts/run-*/run_manifest.json`
- `artifacts/run-*/cases/*/steps.jsonl`
- `artifacts/run-*/cases/*/assertions.jsonl`
- 失败时额外生成 `artifacts/run-*/cases/*/state_snapshot.json`
- `artifacts/run-*/cases/*/result.json`
