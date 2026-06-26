# pytest + POM + YAML 场景编排设计

## 背景

当前项目已经具备可运行的 pytest 设备测试骨架：

- `tests/conftest.py` 负责读取设备配置、创建 `WatchSession`、装配 `WatchDsl`。
- `pages/*` 已经承担基础 POM 职责，封装 watchface、settings、widget、workout 页面操作。
- `flows/core.py` 已经承担跨页面业务动作编排。
- `WatchSession` 统一处理 case 生命周期、步骤记录、断言记录、失败快照和 result 输出。

这次重构不推翻现有底层连接、设备控制和 artifact writer。目标是在 pytest 之上落一个中间态骨架：Python 保留 POM 与动作执行能力，YAML 负责维护场景步骤序列。

## 目标

1. 继续使用 pytest 作为测试执行框架，保留现有 `--device-config` 和 `WATCH_UI_RUN_DEVICE_TESTS=1` 开关。
2. 将测试表达从“测试函数直接调用页面对象”逐步迁移为“YAML 场景 + Python 执行器”。
3. 保留并强化 POM 边界：页面对象只描述单页能力，flow/action 层描述业务动作，runner 层负责执行 YAML。
4. 保留现有 artifact 语义：每个 YAML case 仍输出 `steps.jsonl`、`assertions.jsonl`、失败快照和 `result.json`。
5. 允许现有 Python smoke/regression case 与 YAML case 在一段时间内共存，降低迁移风险。

## 非目标

1. 不重构 `SdsTransportClient`、`SdsDeviceController` 的协议实现。
2. 不在第一阶段引入自定义 pytest collector，先使用普通 pytest 参数化加载 YAML。
3. 不一次性把全部现有用例迁到 YAML，先选 widget/workout smoke 作为样板。
4. 不让 YAML 直接描述低层 SDS URI 或坐标输入，低层细节仍由配置、页面对象和动作库承接。

## 推荐目录结构

```text
src/watch_ui_automation/
  actions/
    __init__.py
    registry.py
    watch_actions.py
  scenarios/
    __init__.py
    models.py
    loader.py
    runner.py
  pages/
    base.py
    watchface.py
    settings.py
    widget.py
    workout.py
  flows/
    core.py
tests/
  yaml_cases/
    smoke/
      widget.yaml
      workout.yaml
  scenario/
    test_yaml_scenarios.py
```

说明：

- `pages` 保持 POM 入口，页面对象不解析 YAML。
- `flows` 保留跨页面组合动作，后续可被 action 层复用。
- `actions` 是 YAML 可调用动作注册表，负责把稳定动作名映射到 Python callable。
- `scenarios` 负责 YAML schema、加载、校验和执行。
- `tests/scenario/test_yaml_scenarios.py` 是 pytest 接入层，负责参数化生成 case。

## 分层职责

### pytest 层

pytest 继续负责：

- 命令行参数和 fixture 装配。
- 根据路径加载 YAML case。
- 将每个 YAML case 参数化成一个 pytest 测试。
- 复用 `device_dsl` fixture 获取真实设备能力。

建议新增参数：

```text
--scenario-dir tests/yaml_cases
--scenario-suite smoke
```

第一阶段也可以只固定读取 `tests/yaml_cases/smoke/*.yaml`，等样板稳定后再扩展参数。

### POM 层

页面对象继续负责单页动作和状态读取：

- `WatchfacePage`：打开 widget、打开 workout、判断 watchface 可见。
- `SettingsPage`：打开/关闭设置视图、读取焦点、遍历焦点。
- `WidgetPage`：读取当前 widget path/name，返回 watchface。
- `WorkoutPage`：读取运动状态，暂停/恢复，停止。

约束：

- 页面对象不感知 YAML case 格式。
- 页面对象可以记录低层步骤，但业务语义优先放到 action 层记录。
- 页面对象方法名保持稳定，避免 YAML 动作频繁跟着底层实现变化。

### Action 层

Action 层是 YAML 与 POM 的桥接层。每个 action 接收 `WatchDsl`、`case_name` 和参数：

```python
def open_widget(dsl: WatchDsl, case_name: str, **params) -> object:
    ...
```

首批建议支持这些动作：

| action | 说明 |
| --- | --- |
| `watchface.open_widget` | 从 watchface 进入 widget |
| `watchface.open_workout` | 从 watchface 进入 workout |
| `widget.go_back` | 从 widget 返回 |
| `workout.pause_or_resume` | 暂停或恢复运动 |
| `workout.stop` | 结束或退出运动 |
| `assert.current_page_equals` | 断言当前页面等于期望值 |
| `assert.current_page_changed` | 断言当前页面相对变量已变化 |
| `assert.widget_changed` | 断言 widget path/name 相对变量已变化 |
| `assert.workout_state_non_empty` | 断言 workout state 非空 |
| `capture.current_page` | 将当前页面保存为变量 |
| `capture.current_widget` | 将当前 widget 保存为变量 |

Action 层负责把执行结果写入 runner context，供后续断言引用。

### Scenario 层

Scenario 层负责：

- 读取 YAML 文件。
- 校验必填字段和步骤格式。
- 将 YAML 转为 `ScenarioCase`、`ScenarioStep` 等 Python 模型。
- 执行步骤，并把失败定位到具体 case 和 step。

建议模型：

```python
@dataclass(frozen=True)
class ScenarioCase:
    id: str
    title: str
    markers: list[str]
    baseline: str
    steps: list[ScenarioStep]

@dataclass(frozen=True)
class ScenarioStep:
    name: str
    action: str
    params: dict[str, object]
```

### Artifact 层

继续由 `WatchSession` 统一产物输出。Scenario runner 不直接写文件，而是通过：

- `session.case(case.id, expected_page=case.baseline)`
- `session.record_step(...)`
- `session.assert_condition(...)`

这样 YAML case 与现有 Python case 的证据结构保持一致。

## YAML Case 格式

推荐第一版 YAML 使用列表格式，一个文件可以包含一个或多个 case：

```yaml
cases:
  - id: smoke_widget
    title: Open widget and return to watchface
    markers:
      - device
      - smoke
    baseline: main
    steps:
      - name: remember baseline widget
        action: capture.current_widget
        save_as: baseline_widget

      - name: open widget
        action: watchface.open_widget

      - name: widget changed after open
        action: assert.widget_changed
        params:
          from: baseline_widget

      - name: return to watchface
        action: widget.go_back

      - name: watchface is visible again
        action: assert.current_page_equals
        params:
          expected: main
```

字段规则：

- `id` 必填，并作为 artifact case_name。
- `title` 用于报告和 pytest id。
- `markers` 映射到 pytest marker，第一阶段至少支持 `device`、`smoke`、`regression`、`stability`。
- `baseline` 传入 `WatchSession.case(..., expected_page=baseline)`。
- `steps[].action` 必须存在于 action registry。
- `steps[].params` 可选，默认为空字典。
- `steps[].save_as` 可选，用于保存 action 返回值到 runner context。

## 执行流程

```text
pytest 启动
  -> 读取 --device-config
  -> device_dsl fixture 装配 WatchDsl
  -> loader 读取 YAML case
  -> pytest 参数化生成 test_yaml_scenario[case_id]
  -> runner 进入 session.case(case.id, baseline)
  -> 逐步执行 ScenarioStep
  -> action 调用 POM/flow/session
  -> assertion 失败时由 WatchSession 记录失败证据
  -> pytest 呈现具体 case 失败
```

## 首批迁移范围

第一阶段建议只迁移两个样板：

- `tests/smoke/test_widget_smoke.py`
- `tests/smoke/test_workout_smoke.py`

保留原 Python 测试一段时间，用于对比 YAML runner 的行为与产物。等样板稳定后，再迁移：

- `tests/regression/test_widget_regression.py`
- `tests/regression/test_workout_regression.py`
- settings traverse 相关场景

## 测试策略

单元测试：

- loader 能读取一个或多个 YAML case。
- loader 能拒绝缺失 `id`、未知 action、非法 `steps` 的文件。
- runner 能按顺序调用 action registry。
- runner 能保存 `save_as` 变量并传给后续断言。
- action registry 能正确调用现有 POM 方法。

设备测试：

- 不设置 `WATCH_UI_RUN_DEVICE_TESTS=1` 时 YAML 设备 case 继续 skip。
- 设置真实设备开关后，widget/workout YAML smoke 能输出与现有 Python case 等价的 artifact。

回归验证：

```powershell
python -m pytest tests/unit -v
python -m pytest tests/smoke -v
```

真实设备验证仍需要显式开启：

```powershell
$env:WATCH_UI_RUN_DEVICE_TESTS='1'
python -m pytest tests/scenario -v --device-config configs/default.yaml
```

## 风险与约束

1. YAML DSL 不能过早变复杂。第一阶段只支持顺序步骤、参数、变量保存和基础断言。
2. Action 名称要稳定，不能暴露临时 Python 方法名。
3. 失败信息必须包含 case id、step name、action name，否则 YAML case 排错会变困难。
4. 现有 Python case 与 YAML case 共存时，要避免重复执行真实设备场景导致时间变长。后续可以通过 marker 或 suite 参数控制。
5. YAML 文件要只描述业务步骤，不承载坐标、URI、SDS payload 等底层细节。

## 实施顺序

1. 新增 `scenarios.models`、`scenarios.loader`，先完成 YAML schema 与单元测试。
2. 新增 `actions.registry`、`actions.watch_actions`，把首批 POM 动作注册进去。
3. 新增 `scenarios.runner`，打通 step 执行、变量上下文和错误定位。
4. 新增 `tests/yaml_cases/smoke/widget.yaml`、`workout.yaml` 样板。
5. 新增 `tests/scenario/test_yaml_scenarios.py`，用 pytest 参数化执行 YAML case。
6. 补充 unit 测试和离线 smoke skip 验证。
