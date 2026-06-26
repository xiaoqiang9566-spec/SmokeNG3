# watch-ui-automation

基于 `SDSApplicationServer` 的手表 UI 自动化脚手架，用于在真机上执行 watchface、settings、widget、workout 的 smoke / regression / stability 校验。

## 启动

1. 使用 Python 3.9 安装依赖。

```powershell
python -m pip install -e ".[dev]"
```

2. 启动 SDS 服务，并确认 `configs/default.yaml` 中的 `device.serial`、`device.sds_url`、`input` 坐标和 `navigation` 动作与当前设备一致。

## 当前导航口径

- `current_page_uri` 使用 `Ui/View/Stack/-1/ViewName`，watchface 基线通常是 `main` 或 `c-lowp`。
- settings 校验当前走 `Ui/Control/Open/Close` 直开直关，因此它验证的是“view 名称和返回链路”，不是 swipe 校准。
- widget 校验当前以 `Ui/View/Stack/Path` 为主证据。若 `swipe_left` 成功离开 watchface，路径应该不再停留在 watchface 基线。
- workout 校验当前以 `current_page` 是否离开 `main` 为主证据；默认导航已切到 `swipe_up`，不再用 `press_top_left` 绕过手势问题。
- 2026-06-25 的现有真机产物已经证明旧版 widget/workout 断言存在假阳性：
- `smoke_widget` / `regression_widget` 通过时，`actual` 仍然是 `/_watch-face(c)/main`
- `smoke_workout` / `regression_workout` 通过时，`actual` 仍然是 `0`
- 因此仓库现在把 widget/workout smoke/regression 收紧成“必须看到视图切换证据”，否则直接失败。

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
