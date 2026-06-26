# settings traverse 用例说明

本文档只描述 settings 相关 traversal / regression 的口径。它验证的是 SDS `Ui/Control/Open/Close` 链路是否稳定，不承担 `swipe_left` / `swipe_up` 手势校准职责。

## 设计目标

针对 `Race 2` 当前可用的 settings 入口，确认以下链路稳定：

1. `Ui/Control/Open(name="s-main")` 可以进入 settings root。
2. 指定 settings view 可以通过 `Open -> current_page 校验 -> Close -> 返回 main` 完成闭环。

当前覆盖的 view 名称：

- `s-main`
- `s-ge`
- `s-cu`
- `s-power-saving`
- `s-alarmclock`

## 当前 regression 切片

```python
import pytest

from tests.conftest import read_content


@pytest.mark.device
def test_open_multiple_settings_views_regression(device_dsl) -> None:
    case_name = "regression_settings_views"
    view_names = ["s-main", "s-ge", "s-cu"]
    with device_dsl.session.case(case_name, expected_page="main"):
        for view_name in view_names:
            device_dsl.settings.open_view(case_name, view_name=view_name)
            current_page = read_content(device_dsl, "current_page")
            device_dsl.session.assert_condition(
                case_name,
                f"entered_{view_name}",
                current_page == view_name,
                actual=current_page,
                expected=view_name,
            )
            device_dsl.settings.close_view(case_name, view_name=view_name)
            current_page = read_content(device_dsl, "current_page")
            device_dsl.session.assert_condition(
                case_name,
                f"returned_to_watchface_after_{view_name}",
                current_page == "main",
                actual=current_page,
                expected="main",
            )
```

## 和导航校准的边界

- settings smoke / regression 目前不调用 `watchface.open_settings()`，而是直接走 `settings.open_view()` / `settings.close_view()`。
- 这意味着它们能证明 `current_page` 与目标 settings view 一致，也能证明能回到 `main`。
- 这组用例不能证明 `swipe_left` 或 `swipe_up` 能切出 widget / workout。
- 真机导航校准应优先看 widget/workout smoke/regression，因为那两组现在分别绑定 `swipe_left` 和 `swipe_up`。

## 本地验证

```powershell
python -m pytest tests/unit/pages/test_pages_and_flows.py -q
python -m pytest tests/unit tests/smoke tests/regression tests/stability -q
```

## 真机验证

```powershell
$env:WATCH_UI_RUN_DEVICE_TESTS='1'
python -m pytest tests/smoke/test_settings_smoke.py tests/smoke/test_settings_traverse_smoke.py tests/regression/test_settings_regression.py -v --device-config configs/default.yaml
```
