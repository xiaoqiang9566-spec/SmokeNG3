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
