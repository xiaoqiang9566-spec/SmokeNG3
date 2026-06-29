# FT-automation 项目规则

本文件补充当前项目在真机 UI 自动化上的稳定约束。若与用户当次指令冲突，以用户指令为准；若与更底层代码实现冲突，应先修正文档或实现，再继续推进。

## 默认上下文

- 开始任何真机相关修改或排查前，先读取 [README.md](C:/Users/3681/.codex/worktrees/aa16/FT-automation/README.md)。
- 手势真机排查与调用约束，优先读取 [gesture-real-device-debugging-guide.md](C:/Users/3681/.codex/worktrees/aa16/FT-automation/docs/gesture-real-device-debugging-guide.md)。
- settings 相关 traversal / regression 只验证 `Ui/Control/Open/Close` 链路，不承担 swipe 手势校准职责。

## 真机手势规则

- `swipe_up` 当前已真机验证有效，语义是 `open_widget`。
- `swipe_left` 当前已真机验证有效，语义是 `open_pinned_widget_shortcut`。
- `swipe_down` 当前只有目标语义 `open_workout`，截至 2026-06-29 仍未真机验证成功。
- `swipe_right` 截至 2026-06-29 仍未真机验证成功。
- 不要把 `swipe_down` 或 `swipe_right` 的现状描述成“已校准可用”。

## SDS Touch 约束

- `Touch/Event` 和 `Knob/Event` 的 SDS body 必须使用 `{"": {...}}` 形状，不能平铺字段。
- 真机有效 swipe 不要默认用简化 4 事件；优先沿用控制器里已经验证过的完整事件序列。
- 真机手势判断优先看 `Ui/View/Stack/-1/ViewName`、`Ui/View/Stack/Path`、`Activity/Exercise/State`，不要把 `Gesture/Progress` 当主证据。

## Bypass 与清理规则

- 连上 SDS 后 touch 失效时，优先怀疑 bypass 残留，不要先怀疑 SDS 总链路坏掉。
- 每次脚本退出前，先 `release_bypasses()`，再关闭 transport。
- `release_bypasses()` 对 `404` 视为正常，不要改回报错。

## 基线与探测规则

- 真机 gesture probe 前必须先恢复到严格 `main` 基线，不能接受 `c-lowp` 或其他脏态起跑。
- baseline recovery 当前统一使用 `press_bottom`。
- 做 sweep 或专项探测时，至少同时采 `current_page`、`current_widget`、`workout_state` 三个信号。
- 如果 `swipe_up`、`swipe_left` 有效，但 `swipe_down`、`swipe_right` 无效，优先怀疑入口语义或前置状态变化。
