# Widget Traverse Smoke 设计

## 1. 背景

当前仓库中的 `tests/smoke/test_widget_smoke.py` 和 `tests/regression/test_widget_regression.py` 只验证三类事实：

- 从 watchface 触发了一次 `open_widget`
- 读取到一个“非空”的 widget 字段
- 返回后重新回到 watchface

`2026-06-25` 的真实产物已经证明这套口径不可靠：`current_widget_uri` 多次返回的仍然是 watchface path，例如 `/_watch-face(c)/main` 或 `/3404076681(c)/main`。这意味着“字段非空”“字段稳定”“字段变化”都可能是假阳性，无法证明设备真的进入了 widget list，更无法证明遍历到了不同 widget。

这次设计的目标是把 widget smoke case 收紧成真正的 traversal case：从 watchface 进入 widget list，遍历小组件列表，并按小组件类别执行对应断言。

## 2. 目标

本次设计要达成以下目标：

- 从 watchface 明确进入 widget list，而不是只发送一次手势动作
- 在 widget list 中持续遍历，直到能够判定列表已经回环
- 为每个已识别 widget 关联一个 `widget -> category -> assertion profile` 映射
- 按 widget 类别执行恰当断言，而不是继续使用“非空字符串”这类弱口径
- 产出可复用的 DSL / page / flow 能力，供 smoke 与后续 regression 复用
- 保留真实设备运行证据，便于确认 traversal 是否真的发生

## 3. 非目标

本次不解决以下问题：

- 不尝试通过当前 SDS 返回值自动推断 widget 类别
- 不引入视觉识别、截图比对或 OCR
- 不一次性覆盖所有可能 widget，只覆盖映射表中声明的 widget
- 不在首版中设计复杂的“自动恢复到指定 widget”能力

## 4. 约束与现状

### 4.1 已确认约束

- 用户已确认：widget 类别来源采用仓库内维护的映射表，而不是自动推断
- 真实设备断言优先使用稳定证据，不能继续使用已被真机否定的弱断言
- smoke case 的目标是“遍历 + 分类断言”，不是“单次进入 + 返回”

### 4.2 当前已知问题

- `current_widget_uri` 在真机上经常返回 watchface path
- `settings_focus_uri` 也有类似问题，说明“读到字符串”本身不能证明视图切换成功
- 当前 DSL 中没有 widget list、widget traversal、widget evidence capture 这些能力
- 当前 smoke / regression 只覆盖单次 open/back，不覆盖列表遍历

## 5. 方案对比

### 方案 A：映射表驱动的 widget traversal

做法：

- 新增一份 widget profile 配置
- traversal 过程中识别当前 widget key
- 通过 profile 取 category 和 assertion profile
- 按 profile 执行断言

优点：

- 类别口径稳定，可审计
- 配置与断言解耦，后续新增 widget 只需补 profile
- 可复用到 regression / stability

缺点：

- 首版需要先沉淀一份映射表
- 识别 widget key 的证据链需要额外设计

### 方案 B：把映射和断言硬编码在测试文件中

做法：

- 在 smoke case 内直接写 widget 名称分支和断言逻辑

优点：

- 改动路径短

缺点：

- 维护性差
- 不利于后续复用
- 容易把测试文件变成配置文件

### 推荐

采用方案 A。因为这次需求本质上是在建立“widget 类别口径”，而不是临时补一个特例测试。

## 6. 设计总览

本次实现新增四层能力：

1. widget profile 配置层
2. widget 证据采集层
3. widget traversal flow 层
4. 类别断言分发层

对应关系如下：

```text
smoke case
  -> widget traversal flow
    -> widget page actions + evidence capture
      -> widget profile lookup
        -> category assertion runner
```

## 7. 数据模型设计

### 7.1 Widget Profile

新增 widget profile 配置，建议放在 `src/watch_ui_automation` 内的独立模块中，首版使用 Python 常量维护，避免引入额外配置解析复杂度。

建议结构：

```python
WidgetProfile(
    key="weather",
    display_names={"Weather", "天气"},
    category="glance",
    expected_signals={
        "page_path_contains": ["weather", "glance-weather"],
        "content_contains_any": ["Weather", "Temperature"],
    },
    assertion_profile="glance_basic",
)
```

### 7.2 字段定义

- `key`
  - widget 的稳定内部标识，作为遍历去重主键
- `display_names`
  - 允许的展示名集合，用于从文本证据映射到 `key`
- `category`
  - widget 类别，如 `glance`、`activity`、`navigation`、`control`
- `expected_signals`
  - 当前 widget 的稳定证据约束
- `assertion_profile`
  - 使用哪套断言模板

### 7.3 类别与断言模板

首版不直接按 `category` 写死断言，而是使用 `assertion_profile`。原因是同一类别下也可能存在强弱不同的证据。

建议首版内置的断言模板：

- `entry_only`
  - 只验证成功离开 watchface、成功返回 watchface
- `glance_basic`
  - 验证离开 watchface，且文本或路径证据命中 profile
- `activity_basic`
  - 验证离开 watchface，且活动类关键字命中
- `navigation_basic`
  - 验证离开 watchface，且导航类关键字命中
- `control_basic`
  - 验证离开 watchface，且控制类关键字命中

这样后续新增 widget 时，优先复用模板，而不是重复发明新断言。

## 8. 证据采集设计

### 8.1 核心原则

因为现有 `current_widget_uri` 不稳定，证据采集必须是多源的，不能只读一个资源。

首版证据对象建议包含：

```python
WidgetEvidence(
    page_name=...,
    page_path=...,
    widget_path=...,
    focused_content=...,
    raw_samples={...},
)
```

### 8.2 采集来源

优先采集下列信息：

- `current_page_uri`
- `current_widget_uri`
- 若可行，widget 顶层元素信息或当前 view 文本
- traversal 前后的 page path 差异

如果仓库当前没有足够资源 URI，首版允许先基于已有 URI 做组合证据，并把缺口显式保留在 profile 设计中。

### 8.3 当前 widget key 识别

识别顺序建议如下：

1. 用 evidence 中的文本命中 `display_names`
2. 用 `page_path_contains` 命中 profile
3. 用 `content_contains_any` 命中 profile
4. 若仍无法识别，标记为 `unknown`

`unknown` 不是通过条件，而是一个显式失败分支。这样 smoke 结果能真实反映“设备进入了某个 widget，但当前映射表还无法识别”。

## 9. Traversal 设计

### 9.1 新增 flow

新增专用 flow，例如：

```python
device_dsl.flows.traverse_widgets_with_profiles(case_name)
```

### 9.2 流程步骤

1. 校验当前位于 watchface baseline
2. 从 watchface 执行 `open_widget`
3. 采集当前 widget evidence
4. 识别当前 widget key
5. 根据 profile 执行断言
6. 记录本轮访问结果
7. 执行“切到下一个 widget”的动作
8. 再次采集 evidence
9. 若识别到的 key 已访问过，则认为列表回环并结束
10. 退出 widget list，返回 watchface

### 9.3 终止条件

首版遍历终止条件采用：

- 识别到已访问的 `widget key`，视为回环

同时加一个保护上限，例如最大遍历次数 `max_steps`，防止无法识别时死循环。若超过上限仍未回环，case 失败。

### 9.4 成功条件

case 成功需要同时满足：

- 确实离开过 watchface
- 至少识别到 2 个不同 widget
- 每个识别到的 widget 都命中了 profile
- 每个 widget 的类别断言通过
- 遍历结束后成功返回 watchface

## 10. 断言设计

### 10.1 基础断言

所有 widget 共用的基础断言：

- `left_watchface_after_open_widget`
- `widget_key_is_known`
- `widget_profile_assertions_passed`
- `returned_to_watchface_after_widget_traverse`

### 10.2 类别断言

按 `assertion_profile` 分发：

- `entry_only`
  - 要求当前证据不再停留在 watchface baseline path
- `glance_basic`
  - 在基础断言上，再要求 evidence 命中 profile 的文本或路径信号
- `activity_basic`
  - 命中活动类关键字或路径信号
- `navigation_basic`
  - 命中导航类关键字或路径信号
- `control_basic`
  - 命中控制类关键字或路径信号

### 10.3 失败语义

失败时要区分：

- 没有离开 watchface
- 离开了 watchface，但无法识别 widget
- 识别到了 widget，但类别断言失败
- 遍历未形成回环
- 返回 watchface 失败

这样能避免把所有失败都混成“widget traverse failed”。

## 11. 代码结构建议

建议增量修改，不重构现有总架构：

- `src/watch_ui_automation/pages/widget.py`
  - 增加 evidence 读取与下一项切换能力
- `src/watch_ui_automation/flows/core.py`
  - 增加 traversal flow
- `src/watch_ui_automation/...`
  - 新增 widget profile / classifier / assertion runner 模块
- `tests/smoke/test_widget_smoke.py`
  - 改为 traversal smoke
- `tests/unit/...`
  - 新增 profile、classifier、traversal 的单元测试

首版不要求把所有断言都抽成全局框架，只要边界清晰即可。

## 12. 测试策略

### 12.1 单元测试

先写失败用例，再实现：

- profile lookup
- evidence -> widget key 分类
- 遍历遇到重复 key 时终止
- 未识别 widget 时失败
- 超过 `max_steps` 时失败
- 不同 `assertion_profile` 的断言分发

### 12.2 真机 smoke

新的 smoke case 至少验证：

- 从 watchface 进入 widget list
- 成功识别多个 widget
- 逐个按 profile 断言
- 最终返回 watchface

### 12.3 回归影响

`test_widget_regression.py` 后续可复用 traversal 能力，但本轮优先把 smoke 改成真实 traversal；是否同步升级 regression，取决于实现完成后的代码规模与验证成本。

## 13. 风险与应对

### 风险 1：现有资源仍不足以识别 widget

应对：

- 明确把 `unknown widget` 作为失败结果
- 用映射表聚焦先支持一批已知 widget
- 后续根据真机证据继续补 profile 或资源

### 风险 2：遍历动作本身未推动列表变化

应对：

- 通过“已离开 watchface”“访问到至少 2 个不同 widget”“形成回环”三道条件联动判断
- 不再接受“非空字符串”作为成功证据

### 风险 3：类别断言过强导致 smoke 不稳定

应对：

- 首版用 `assertion_profile` 控制强弱
- 对证据不足的 widget 使用保守模板，而不是伪造强断言

## 14. 验收标准

本设计对应的实现完成后，应能提供以下证据：

- `tests/smoke/test_widget_smoke.py` 已从“单次打开”升级为“widget list 遍历”
- 仓库内存在 widget profile 映射表
- 单元测试覆盖 profile lookup、classifier、traversal stop condition、assertion dispatch
- 真实设备 smoke 失败时，能从产物中看出失败在“未离开 watchface / 未识别 / 未回环 / 类别断言失败”中的哪一类

## 15. 结论

本次推荐使用“映射表驱动的 widget traversal”方案，把 widget smoke case 从弱口径的单次 open/back，升级为基于遍历、识别、分类断言的真实链路验证。这样既符合当前真机证据，也为后续 regression 复用保留了稳定边界。
