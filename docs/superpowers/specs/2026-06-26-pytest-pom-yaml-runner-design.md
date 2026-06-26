# pytest + POM + YAML 场景编排设计

## 背景

当前项目已经具备可运行的 pytest 设备测试骨架：

- `tests/conftest.py` 负责读取设备配置、创建 `WatchSession`、装配 `WatchDsl`。
- `pages/*` 已经承担基础 POM 职责，封装 watchface、settings、widget、workout 页面操作。
- `flows/core.py` 已经承担跨页面业务动作编排。
- `WatchSession` 统一处理 case 生命周期、步骤记录、断言记录、失败快照和 result 输出。

本次重构不推翻现有底层连接、设备控制和 artifact writer。目标是在 pytest 之上落一个中间态骨架：Python 保留 POM 与动作执行能力，YAML 负责维护场景步骤序列。

## 目标

1. 继续使用 pytest 作为测试执行框架，保留现有 `--device-config` 和 `WATCH_UI_RUN_DEVICE_TESTS=1` 开关。
2. 将测试表达从“测试函数直接调用页面对象”逐步迁移为“YAML 场景 + Python 执行器”。
3. 保留并强化 POM 边界：页面对象只描述单页能力，flow/action 层描述业务动作，runner 层负责执行 YAML。
4. 保留现有 artifact 语义：每个 YAML case 仍输出 `steps.jsonl`、`assertions.jsonl`、失败快照和 `result.json`。
5. 允许现有 Python smoke/regression case 与 YAML case 在一段时间内共存，降低迁移风险。
6. 建立可离线校验的 YAML schema，尽量在连接设备前发现用例配置问题。
7. 建立统一的错误定位机制，确保失败信息能定位到 YAML 文件、case、step 和 action。

## 非目标

1. 不重构 `SdsTransportClient`、`SdsDeviceController` 的协议实现。
2. 不在第一阶段引入自定义 pytest collector，先使用普通 pytest 参数化加载 YAML。
3. 不一次性把全部现有用例迁到 YAML，先选 widget/workout smoke 作为样板。
4. 不让 YAML 直接描述低层 SDS URI、坐标输入、payload 或 transport 细节。
5. 不在第一阶段支持复杂控制流，例如循环、条件分支、重试策略嵌套、并发场景。

## 推荐目录结构

```text
src/watch_ui_automation/
  actions/
    __init__.py
    registry.py
    navigation_actions.py
    capture_actions.py
    assertion_actions.py
    workout_actions.py
  scenarios/
    __init__.py
    models.py
    schema.py
    loader.py
    context.py
    errors.py
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
  unit/
    scenarios/
      test_loader.py
      test_schema.py
      test_runner.py
      test_context.py
    actions/
      test_registry.py
```

说明：

- `pages` 保持 POM 入口，页面对象不解析 YAML，也不感知场景执行上下文。
- `flows` 保留跨页面组合动作，后续可被 action 层复用。
- `actions` 是 YAML 可调用动作注册表，负责把稳定动作名映射到 Python callable。
- `scenarios` 负责 YAML schema、加载、校验、变量上下文、错误包装和执行。
- `tests/scenario/test_yaml_scenarios.py` 是 pytest 接入层，负责参数化生成 case。

## 分层职责

### pytest 层

pytest 继续负责：

- 命令行参数和 fixture 装配。
- 根据路径加载 YAML case。
- 将每个 YAML case 参数化成一个 pytest 测试。
- 根据 marker、环境变量和 suite 参数控制执行范围。
- 复用 `device_dsl` fixture 获取真实设备能力。

建议新增参数：

```text
--scenario-dir tests/yaml_cases
--scenario-suite smoke
```

第一阶段可以固定读取 `tests/yaml_cases/smoke/*.yaml`，等样板稳定后再扩展参数。

### POM 层

页面对象继续负责单页动作和状态读取：

- `WatchfacePage`：打开 widget、打开 workout、判断 watchface 可见。
- `SettingsPage`：打开/关闭设置视图、读取焦点、遍历焦点。
- `WidgetPage`：读取当前 widget path/name，返回 watchface。
- `WorkoutPage`：读取运动状态，暂停/恢复，停止。

约束：

- 页面对象不感知 YAML case 格式。
- 页面对象不读取或写入 runner context。
- 页面对象不直接承担业务级 artifact 记录。
- 页面对象可以保留必要的低层调试日志，但不能替代 action 层的业务步骤记录。
- 页面对象方法名应保持稳定，避免 YAML 或 action 频繁跟随底层实现变化。

建议边界：

```text
Page：单页操作、状态读取、等待页面稳定
Flow：跨页面组合动作
Action：业务动作入口、参数校验、调用 Page/Flow、记录业务步骤、返回结构化结果
Runner：顺序执行 step、管理变量、错误定位
WatchSession：统一输出 artifact
```

### Action 层

Action 层是 YAML 与 POM/Flow 的桥接层。YAML 只能调用 action registry 中注册过的稳定动作名，不能直接调用页面对象方法。

每个 action 建议接收统一参数：

```python
def action_name(ctx: ScenarioContext, **params) -> object:
    ...
```

其中 `ScenarioContext` 至少包含：

```python
@dataclass
class ScenarioContext:
    dsl: WatchDsl
    session: WatchSession
    case_id: str
    variables: dict[str, object]
```

Action 负责：

- 校验业务参数。
- 调用 POM 或 Flow。
- 记录业务语义步骤。
- 调用 `session.assert_condition(...)` 记录断言。
- 返回可保存到变量上下文的结构化结果。

Action 不负责：

- 解析 YAML 文件。
- 处理 pytest marker。
- 决定 case 是否 skip。
- 直接写 `steps.jsonl`、`assertions.jsonl`、`result.json` 文件。

### Action 命名规范

第一阶段建议按动作类别命名，避免暴露具体页面对象名称：

| action | 说明 |
| --- | --- |
| `navigation.open_widget` | 从当前主表盘进入 widget |
| `navigation.open_workout` | 从当前主表盘进入 workout |
| `navigation.back_to_watchface` | 从当前页面返回主表盘 |
| `workout.pause_or_resume` | 暂停或恢复运动 |
| `workout.stop` | 结束或退出运动 |
| `capture.current_page` | 读取当前页面并返回结构化页面状态 |
| `capture.current_widget` | 读取当前 widget 并返回结构化 widget 状态 |
| `capture.workout_state` | 读取当前 workout 状态 |
| `assert.equals` | 断言实际值等于期望值 |
| `assert.not_equals` | 断言实际值不等于期望值 |
| `assert.non_empty` | 断言实际值非空 |
| `assert.changed` | 断言两个值发生变化 |
| `assert.contains` | 断言集合或字符串包含目标值 |

说明：

- 第一阶段保留少量通用断言，避免 `assert.widget_changed`、`assert.current_page_changed` 等动作无限膨胀。
- 如确实需要领域断言，可以在后续增加 `assert.widget_changed` 这类高阶断言，但不作为第一阶段默认设计。
- action 名称一旦进入 YAML，应视为对用例作者的稳定 API。

### Scenario 层

Scenario 层负责：

- 读取 YAML 文件。
- 校验必填字段、字段类型、marker 白名单、action 是否存在、变量引用是否合法。
- 将 YAML 转为 `ScenarioCase`、`ScenarioStep` 等 Python 模型。
- 管理 runner context 和变量引用解析。
- 执行步骤，并把失败定位到具体文件、case、step 和 action。

建议模型：

```python
@dataclass(frozen=True)
class ScenarioCase:
    id: str
    title: str
    markers: list[str]
    baseline: str
    steps: list[ScenarioStep]
    source_file: str | None = None

@dataclass(frozen=True)
class ScenarioStep:
    name: str
    action: str
    params: dict[str, object]
    save_as: str | None = None
```

`save_as` 必须出现在模型中，因为 YAML 示例和 runner context 都依赖该字段。

### Artifact 层

继续由 `WatchSession` 统一产物输出。Scenario runner 不直接写文件，而是通过：

- `session.case(case.id, expected_page=case.baseline)`
- `session.record_step(...)`
- `session.assert_condition(...)`

这样 YAML case 与现有 Python case 的证据结构保持一致。

建议 artifact 记录策略：

- Runner 记录每个 YAML step 的开始、成功、失败。
- Action 记录业务动作的核心证据。
- Assertion action 必须通过 `session.assert_condition(...)` 记录断言结果。
- Page 层不重复记录业务步骤，避免 artifact 语义重复。

## YAML Case 格式

推荐第一版 YAML 使用列表格式，一个文件可以包含一个或多个 case：

```yaml
cases:
  - id: smoke_widget
    title: Open widget and return to watchface
    markers:
      - yaml
      - device
      - smoke
    baseline: main
    steps:
      - name: remember baseline widget
        action: capture.current_widget
        save_as: baseline_widget

      - name: open widget
        action: navigation.open_widget

      - name: capture widget after open
        action: capture.current_widget
        save_as: widget_after_open

      - name: widget changed after open
        action: assert.changed
        params:
          actual: ${widget_after_open}
          from: ${baseline_widget}

      - name: return to watchface
        action: navigation.back_to_watchface

      - name: capture page after back
        action: capture.current_page
        save_as: page_after_back

      - name: watchface is visible again
        action: assert.equals
        params:
          actual: ${page_after_back.name}
          expected: main
```

字段规则：

- `id` 必填，并作为 artifact case_name。
- `title` 用于报告和 pytest id。
- `markers` 映射到 pytest marker，第一阶段只允许白名单 marker。
- `baseline` 传入 `WatchSession.case(..., expected_page=baseline)`。
- `steps[].name` 必填，用于报告和失败定位。
- `steps[].action` 必须存在于 action registry。
- `steps[].params` 可选，默认为空字典。
- `steps[].save_as` 可选，用于保存 action 返回值到 runner context。

## 变量上下文设计

### 变量保存

当 step 配置了 `save_as` 时，runner 将 action 返回值保存到上下文：

```yaml
- name: capture current widget
  action: capture.current_widget
  save_as: current_widget
```

等价于：

```python
ctx.variables["current_widget"] = action_result
```

### 变量引用

变量引用统一使用 `${...}` 语法：

```yaml
params:
  actual: ${widget_after_open}
  from: ${baseline_widget}
```

禁止直接使用变量名作为引用：

```yaml
params:
  from: baseline_widget
```

原因：无法区分字符串常量 `baseline_widget` 和变量 `baseline_widget`。

### 字段访问

结构化对象支持字段访问：

```yaml
params:
  actual: ${page_after_back.name}
  expected: main
```

第一阶段建议只支持简单点号访问，不支持复杂表达式：

```text
支持：${page.name}
支持：${widget.path}
不支持：${widgets[0].name}
不支持：${page.name == "main"}
不支持：${len(widget.path)}
```

### 变量命名规则

`save_as` 必须满足：

```text
^[a-zA-Z_][a-zA-Z0-9_]*$
```

不允许覆盖内置变量。第一阶段建议保留这些内置变量名：

```text
case_id
baseline
current_step
```

### 允许保存的返回值类型

第一阶段只允许 action 返回这些类型：

```text
str
int
float
bool
None
dict
list
PageState
WidgetState
WorkoutState
```

建议使用结构化状态对象：

```python
@dataclass(frozen=True)
class PageState:
    name: str
    raw: dict[str, object] | None = None

@dataclass(frozen=True)
class WidgetState:
    name: str | None
    path: str | None
    raw: dict[str, object] | None = None

@dataclass(frozen=True)
class WorkoutState:
    status: str | None
    raw: dict[str, object] | None = None
```

避免 action 返回页面对象、设备连接对象、transport client 等不可序列化对象。

## YAML Schema 校验

第一阶段建议使用 `pydantic`、`jsonschema` 或项目内轻量校验器做强校验。若引入新依赖，需要同步更新 `pyproject.toml` 并确认离线单元测试覆盖；若不引入依赖，则 `scenarios.schema` 必须集中承接所有结构与引用校验。

### 必须校验的内容

loader/schema 至少校验：

- YAML 顶层必须是对象。
- 顶层必须包含 `cases`，且 `cases` 必须是非空列表。
- `case.id` 必填、唯一，并满足命名规则。
- `case.title` 必填。
- `case.markers` 必须是字符串列表。
- `case.markers` 只能使用白名单 marker。
- `case.baseline` 必填。
- `case.steps` 必须是非空列表。
- `step.name` 必填。
- `step.action` 必填，并且必须存在于 action registry。
- `step.params` 可选，但存在时必须是对象。
- `step.save_as` 可选，但存在时必须满足变量命名规则。
- 所有 `${var}` 引用必须能在执行到该 step 前被定义，或属于内置变量。
- 同一 case 中不允许重复 `save_as`，除非明确允许变量覆盖。

### marker 白名单

第一阶段允许：

```text
yaml
device
smoke
regression
stability
```

`pytest.ini` 必须声明：

```ini
[pytest]
markers =
    yaml: YAML scenario cases
    device: cases requiring real device
    smoke: smoke test cases
    regression: regression test cases
    stability: stability test cases
```

如果 YAML 中出现未知 marker，loader 应直接失败，而不是交给 pytest 运行时警告。

### action 校验

loader 加载 YAML 时应持有 action registry，并校验：

```python
if step.action not in registry:
    raise ScenarioSchemaError(
        f"Unknown action '{step.action}' in {source_file}, case={case.id}, step={step.name}"
    )
```

这样可以在不连接设备的情况下发现 action 拼写错误。

## Runner 设计

Runner 负责顺序执行 case 中的每个 step。

伪代码：

```python
def run_case(case: ScenarioCase, ctx: ScenarioContext, registry: ActionRegistry) -> None:
    with ctx.session.case(case.id, expected_page=case.baseline):
        for index, step in enumerate(case.steps, start=1):
            resolved_params = resolve_params(step.params, ctx.variables)
            ctx.current_step = step
            try:
                ctx.session.record_step(
                    case.id,
                    "yaml_step_start",
                    "running",
                    step_index=index,
                    step_name=step.name,
                    action=step.action,
                )
                result = registry.call(step.action, ctx, **resolved_params)
                if step.save_as:
                    ctx.variables[step.save_as] = result
                ctx.session.record_step(
                    case.id,
                    "yaml_step_end",
                    "passed",
                    step_index=index,
                    step_name=step.name,
                    action=step.action,
                )
            except Exception as exc:
                ctx.session.record_step(
                    case.id,
                    "yaml_step_end",
                    "failed",
                    step_index=index,
                    step_name=step.name,
                    action=step.action,
                    error=str(exc),
                )
                raise ScenarioStepError.from_exception(case, step, index, exc) from exc
```

## Runner 错误语义

失败信息必须包含：

```text
source_file
case_id
step_index
step_name
action
params
原始异常类型
原始异常信息
```

建议错误格式：

```text
ScenarioStepError:
  file: tests/yaml_cases/smoke/widget.yaml
  case: smoke_widget
  step: 4 - widget changed after open
  action: assert.changed
  params:
    actual: ${widget_after_open}
    from: ${baseline_widget}
  cause: AssertionError: expected value to change
```

这样 pytest 输出和 artifact 都能定位到同一处失败。

建议错误类型：

```python
class ScenarioError(Exception):
    pass

class ScenarioSchemaError(ScenarioError):
    pass

class ScenarioVariableError(ScenarioError):
    pass

class ScenarioActionError(ScenarioError):
    pass

class ScenarioStepError(ScenarioError):
    pass
```

## pytest 接入设计

`tests/scenario/test_yaml_scenarios.py` 负责：

- 读取 `--scenario-dir` 和 `--scenario-suite`。
- 调用 loader 收集 YAML cases。
- 将每个 case 参数化为一个 pytest test。
- 根据 YAML markers 动态添加 pytest markers。
- 复用 `device_dsl` fixture 执行真实设备 case。

示例：

```python
def pytest_generate_tests(metafunc):
    if "scenario_case" not in metafunc.fixturenames:
        return
    cases = load_scenarios(
        scenario_dir=metafunc.config.getoption("--scenario-dir"),
        suite=metafunc.config.getoption("--scenario-suite"),
        registry=ACTION_REGISTRY,
    )
    params = []
    for case in cases:
        marks = [getattr(pytest.mark, marker) for marker in case.markers]
        params.append(pytest.param(case, id=case.id, marks=marks))
    metafunc.parametrize("scenario_case", params)


def test_yaml_scenario(device_dsl, scenario_case):
    run_case(scenario_case, device_dsl, ACTION_REGISTRY)
```

设备开关策略保持现有语义：

- 未设置 `WATCH_UI_RUN_DEVICE_TESTS=1` 时，带 `device` marker 的 YAML case skip。
- 设置真实设备开关后，YAML case 才执行。

## YAML 与 Python Case 共存策略

共存阶段要避免重复跑设备场景导致时间变长。

建议执行策略：

```text
本地默认：只跑 unit 和非设备 case
Python smoke：继续保留，用于稳定性对照
YAML smoke：通过 tests/scenario 或 -m yaml 显式执行
CI：Python smoke 与 YAML smoke 分成不同 job
```

示例命令：

```powershell
python -m pytest tests/unit -v
python -m pytest tests/smoke -v -m "not yaml"
python -m pytest tests/scenario -v -m yaml --scenario-suite smoke
```

真实设备验证：

```powershell
$env:WATCH_UI_RUN_DEVICE_TESTS='1'
python -m pytest tests/scenario -v --device-config configs/default.yaml --scenario-suite smoke
```

## Dry-run 与离线校验

为降低设备调试成本，建议补充 dry-run 或 collect-only 能力。

目标：不连接设备也能验证：

- YAML 能被发现。
- case id 正确。
- marker 合法。
- action 都存在。
- step 格式合法。
- 变量引用在执行顺序上可解析。

可选方案一：复用 pytest collect-only。

```powershell
python -m pytest tests/scenario --scenario-suite smoke --collect-only
```

可选方案二：提供独立校验命令。

```powershell
python -m watch_ui_automation.scenarios.loader validate tests/yaml_cases/smoke
```

第一阶段建议至少通过 unit test 覆盖 loader 校验能力。

## 首批迁移范围

第一阶段只迁移两个样板：

- `tests/smoke/test_widget_smoke.py`
- `tests/smoke/test_workout_smoke.py`

保留原 Python 测试一段时间，用于对比 YAML runner 的行为与产物。等样板稳定后，再迁移：

- `tests/regression/test_widget_regression.py`
- `tests/regression/test_workout_regression.py`
- settings traverse 相关场景

## 测试策略

### 单元测试

loader/schema：

- 能读取一个或多个 YAML case。
- 能拒绝缺失 `id` 的 case。
- 能拒绝重复 `id` 的 case。
- 能拒绝未知 action。
- 能拒绝未知 marker。
- 能拒绝非法 `steps`。
- 能拒绝非法 `save_as`。
- 能拒绝未定义变量引用。

runner/context：

- runner 能按顺序调用 action registry。
- runner 能保存 `save_as` 变量。
- runner 能解析 `${var}` 和 `${var.field}`。
- runner 遇到 action 异常时能抛出 `ScenarioStepError`。
- 失败信息包含 case id、step index、step name、action。

registry/action：

- action registry 能正确注册和查找动作。
- 重复注册 action 时应失败。
- action 能正确调用现有 POM 或 Flow 方法。
- assertion action 能调用 `session.assert_condition(...)`。

### 设备测试

- 不设置 `WATCH_UI_RUN_DEVICE_TESTS=1` 时，YAML 设备 case 继续 skip。
- 设置真实设备开关后，widget/workout YAML smoke 能输出与现有 Python case 等价的 artifact。
- YAML case 失败时，必须能生成失败快照和 result 输出。

### 回归验证

```powershell
python -m pytest tests/unit -v
python -m pytest tests/smoke -v
```

真实设备验证：

```powershell
$env:WATCH_UI_RUN_DEVICE_TESTS='1'
python -m pytest tests/scenario -v --device-config configs/default.yaml --scenario-suite smoke
```

## 风险与约束

1. YAML DSL 不能过早变复杂。第一阶段只支持顺序步骤、参数、变量保存和基础断言。
2. Action 名称要稳定，不能暴露临时 Python 方法名。
3. 失败信息必须包含 source file、case id、step index、step name、action name。
4. 现有 Python case 与 YAML case 共存时，要避免重复执行真实设备场景导致时间变长。
5. YAML 文件只描述业务步骤，不承载坐标、URI、SDS payload 等底层细节。
6. POM 不应承担 YAML 解析、runner context 管理或业务级 artifact 记录。
7. Action 返回值必须结构化，避免不可序列化对象进入 runner context。
8. YAML 变量引用必须显式使用 `${...}`，避免字符串常量和变量引用混淆。

## 实施顺序

1. 新增 `scenarios.models`，补齐 `ScenarioCase`、`ScenarioStep`、`PageState`、`WidgetState`、`WorkoutState` 等模型。
2. 新增 `scenarios.errors`，定义 `ScenarioSchemaError`、`ScenarioVariableError`、`ScenarioActionError`、`ScenarioStepError`。
3. 新增 `actions.registry`，完成 action 注册、查找、重复注册校验。
4. 新增 `scenarios.schema` 和 `scenarios.loader`，完成 YAML schema 校验、marker 白名单校验、action 校验、变量引用校验。
5. 新增 `scenarios.context`，实现变量保存、`${var}`、`${var.field}` 解析。
6. 新增 `actions.navigation_actions`、`actions.capture_actions`、`actions.assertion_actions`、`actions.workout_actions`，接入首批 POM/Flow 动作。
7. 新增 `scenarios.runner`，打通 step 执行、变量上下文、artifact 记录和错误定位。
8. 新增 `tests/yaml_cases/smoke/widget.yaml`、`workout.yaml` 样板。
9. 新增 `tests/scenario/test_yaml_scenarios.py`，用 pytest 参数化执行 YAML case。
10. 补充 unit 测试和离线 collect-only 验证。
11. 打开真实设备开关，验证 YAML smoke 与现有 Python smoke 的 artifact 等价性。

## 第一阶段完成标准

满足以下条件后，认为第一阶段可合入主干：

- YAML loader 能稳定加载 widget/workout smoke 样板。
- 未知 action、未知 marker、非法变量引用能在离线阶段失败。
- `ScenarioStep` 已支持 `save_as`。
- runner 失败信息能定位到文件、case、step、action。
- POM 不解析 YAML，不管理 runner context。
- Action 统一承担业务语义记录和断言记录。
- 未设置 `WATCH_UI_RUN_DEVICE_TESTS=1` 时设备 case 正常 skip。
- 设置真实设备开关后 YAML smoke 能生成完整 artifact。
- Python smoke 与 YAML smoke 可以通过 marker 或 suite 参数分开执行。
