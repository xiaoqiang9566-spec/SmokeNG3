# 手势 Sweep 探测设计

## 目标

新增一个独立的真机手势 sweep 探测脚本，用于批量尝试不同滑动动作与事件序列模板，记录每次探测前后的页面状态、底层 SDS 请求和是否发生视图切换，为后续校准 `swipe_up`、`swipe_down`、`swipe_left` 提供可复核证据。

## 范围

- 读取 `configs/default.yaml` 与当前设备资源配置。
- 支持预定义动作：`swipe_up`、`swipe_down`、`swipe_left`。
- 支持预定义模板：`baseline`、`drag_start`、`multi_move`、`flick_like`。
- 为每次探测记录：
  - 执行前 `current_page`、`current_widget_path`
  - 实际 touch 事件序列
  - 执行后多次采样状态
  - 对应底层 SDS request/response 记录
  - 是否发生页面或路径变化
- 产物写入 `artifacts/run-*/gesture-sweep/`。

## 不做的事

- 本轮不自动修改 `configs/default.yaml`
- 本轮不改现有 smoke/regression/stability 用例
- 本轮不自动推导“最佳参数”，只负责证据采集

## 实现结构

- `src/watch_ui_automation/diagnostics/gesture_sweep.py`
  - 探测数据模型
  - 手势模板生成逻辑
  - sweep runner
  - 结果落盘逻辑
- `tools/gesture_sweep.py`
  - 命令行入口
- `tests/unit/test_gesture_sweep.py`
  - 模板构造与 runner 行为测试

## 关键设计

### 1. 手势模板与动作解耦

动作负责定义起点、终点和中点几何信息，模板负责定义事件形状。这样后续新增模板时不需要改动作定义，新增动作时也不需要重复模板逻辑。

### 2. 统一结果模型

每次探测输出一个独立 JSON，包含：

- `probe_id`
- `action_name`
- `profile_name`
- `before_state`
- `after_samples`
- `touch_events`
- `transport_entries`
- `changed_page`
- `changed_widget_path`
- `changed_any`

这样可以直接对单次探测复盘，不依赖终端输出。

### 3. 复用现有运行产物结构

通过 `ArtifactWriter.start_run()` 创建标准 `run-*` 目录，再在其下新增 `gesture-sweep/` 子目录，保持与现有真机产物一致，方便统一追踪。

## 验证

- 离线：
  - 单元测试覆盖模板生成、runner 状态采样和结果写盘
- 真机：
  - 至少运行一次默认 sweep，确认产物完整生成
  - 核对探测摘要与底层 SDS 记录一致
