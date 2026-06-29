# 真机手势调用与排坑指南

本文档沉淀本次 `swipe_up`、`swipe_down`、`swipe_left`、`swipe_right` 4 个动作在真机上的实际调试结论，目标是避免以后重复踩坑。

## 1. 先说结论

截至 2026-06-29，在当前项目和当前真机环境下：

- `swipe_up`：已验证有效。
- `swipe_left`：已验证有效。
- `swipe_down`：当前未验证出有效调用方法。
- `swipe_right`：当前未验证出有效调用方法。

对应导航语义当前应理解为：

- `open_widget -> swipe_up`
- `open_pinned_widget_shortcut -> swipe_left`
- `open_workout -> swipe_down`

注意：

- 上面第 3 条只是当前产品语义约定，不等于 `swipe_down` 已经被真机验证可用。
- 当前证据说明：`swipe_down` 在严格 `main` 基线下仍然无效，不能再把它当作“已经校准完成”的入口。

## 2. 这次排查确认的关键事实

### 2.1 SDS 连上后 touch 失效，不等于 SDS 本身有问题

真正的根因是 bypass 残留。

- 一旦对 `Touch/Event` 做了 bypass，真实触摸可能会被 SDS 接管。
- 如果脚本退出前没有清理 bypass，后续手动 touch 会表现成“连上 SDS 后触摸失效”。
- 清理方式必须是删除整机 bypass：

```text
DEL suunto://SDS/BypassRouter/{serial}
```

当前项目已经把这个动作落在：

- [`src/watch_ui_automation/device/controller.py`](C:/Users/3681/.codex/worktrees/aa16/FT-automation/src/watch_ui_automation/device/controller.py)
- [`src/watch_ui_automation/session/runtime.py`](C:/Users/3681/.codex/worktrees/aa16/FT-automation/src/watch_ui_automation/session/runtime.py)
- [`tools/gesture_sweep.py`](C:/Users/3681/.codex/worktrees/aa16/FT-automation/tools/gesture_sweep.py)

另外要保留这个行为：

- `release_bypasses()` 对 `404` 视为正常。
- 含义是“本来就没有残留 bypass”，不是错误。

### 2.2 `Touch/Event` 的 SDS body 形状必须是 `{\"\": {...}}`

之前一个根因是报文形状写错了。

错误思路：

- 直接把 `x/y/data/type` 平铺到 `Body`

正确思路：

- `Body` 必须包成：

```json
{
  "": {
    "x": 101,
    "y": 350,
    "data": { "x": 34.78, "y": -139.13 },
    "type": 2
  }
}
```

同类规则也适用于 knob：

```json
{
  "": {
    "angle": 15,
    "timestamp": 123456
  }
}
```

### 2.3 真机有效手势不能只发 4 个简化事件

以下这种“简化版”在真机上不可靠：

- `TOUCHDOWN`
- `TOUCHMOVE`
- `LIFTOFF`
- `IDLE`

这次验证下来的经验是：

- 真机有效手势通常要包含 `DRAG_START`
- 很多场景还需要多个 `MOVE`
- 有效 flick 类动作还要补 `FLICK`
- 事件间隔约 `50ms` 更稳定

当前项目里这个稳定节奏常量是：

- `VERIFIED_TOUCH_EVENT_DELAY_SECONDS = 0.05`

### 2.4 `Ui/Input/Gesture/Progress` 不能作为主证据

这次真机排查里，一个很重要的坑是：

- 即便手势生效，`Gesture/Progress` 也可能一直是 `0`

因此后续判断手势是否成功，优先级应该是：

1. `Ui/View/Stack/-1/ViewName`
2. `Ui/View/Stack/Path`
3. `Activity/Exercise/State`

不要再把 `Gesture/Progress` 当主判断依据。

## 3. 4 个动作当前正确的调用结论

## 3.1 `swipe_up`

用途：

- 打开 widget list

当前真机已验证有效。

当前项目内置有效序列在：

- [`src/watch_ui_automation/device/controller.py`](C:/Users/3681/.codex/worktrees/aa16/FT-automation/src/watch_ui_automation/device/controller.py)

可概括为：

1. `TOUCHDOWN`
2. 一个带速度的 `TOUCHMOVE`
3. `DRAG_START`
4. 多个连续 `TOUCHMOVE`
5. `LIFTOFF`
6. `FLICK`
7. `IDLE`

当前真机证据：

- `current_page` 可能仍然保持 `main`
- 但 `current_widget_path` 会发生明显变化

典型变化示例：

```text
before: /_watch-face(c)/main
after:  /_watch-face(c)/:widgm-ctrlp(c)/:widgm-logbook(c)/main
```

因此：

- `swipe_up` 成功与否主要看 `current_widget_path`
- 不要要求 `current_page` 必须离开 `main`

## 3.2 `swipe_left`

用途：

- 打开 pinned widget 快捷入口

当前真机已验证有效。

当前项目内置有效序列同样已经固化在：

- [`src/watch_ui_automation/device/controller.py`](C:/Users/3681/.codex/worktrees/aa16/FT-automation/src/watch_ui_automation/device/controller.py)

它也是完整序列，而不是简化 4 事件。

当前真机证据：

- `current_page` 会变化
- `current_widget_path` 也会变化

典型落点包括：

- `widg-ctrlp`
- `widg-pinguid`

这说明：

- `swipe_left` 的入口结果和当前 UI 状态有关
- 只要它稳定进入 pinned widget 相关链路，就算动作有效
- 不要把某一个固定 view name 当成唯一正确结果

## 3.3 `swipe_down`

语义约定：

- 目标是打开 workout list

但截至当前，**没有真机验证出有效调用方法**。

已验证过但无效的方式包括：

- 当前控制器里的简化 `swipe_down`
- 参考项目 `swipe_down_from_top`
- 参考项目 `swipe_down_from_top_medium`
- 参考项目 `swipe_down_from_top_slow`

在严格 `main` 基线下，这些动作的共同结果是：

- `current_page` 不变
- `current_widget_path` 不变
- `workout_state` 不变

也就是：

```text
changed_page = false
changed_widget_path = false
changed_workout_state = false
```

所以当前阶段必须明确：

- 不能说 `swipe_down` 已经校准成功
- 不能再把“参考库里有下滑实现”当成“本项目真机可用”
- 后续排查重点应转向“workout 入口前提或产品语义是否变化”

## 3.4 `swipe_right`

截至当前，**没有真机验证出有效调用方法**。

当前控制器里的 `swipe_right` 仍是简化序列：

1. `TOUCHDOWN`
2. `TOUCHMOVE`
3. `LIFTOFF`
4. `IDLE`

在真机严格 `main` 基线下，当前结果是：

- `current_page` 不变
- `current_widget_path` 不变
- `workout_state` 不变

因此：

- `swipe_right` 目前只能算“占位实现”
- 不能把它当成已校准动作

## 4. 真机调用时必须遵守的约束

### 4.1 每轮探测前必须恢复到严格 `main`

本次一个大坑是：

- 以前很多 sweep 样本其实起点是 `c-lowp`
- 这样会把手势结果污染掉

现在必须遵守：

- 基线严格是 `main`
- 恢复动作默认用 `press_bottom`
- 恢复后还要等待 `current_page == main`，再采 `before_state`

相关实现已经补到：

- [`src/watch_ui_automation/diagnostics/gesture_sweep.py`](C:/Users/3681/.codex/worktrees/aa16/FT-automation/src/watch_ui_automation/diagnostics/gesture_sweep.py)

### 4.2 真机脚本退出前必须释放 bypass

无论是手工临时脚本，还是 `gesture_sweep.py`，都要遵守：

1. `device.release_bypasses()`
2. `transport.close()`

顺序不要反过来。

### 4.3 sweep 结果至少同时看 3 个信号

不要只看一个字段。

最少同时观察：

- `current_page_uri`
- `current_widget_uri`
- `workout_state_uri`

现在 `gesture_sweep` 已经支持把这三类状态一起写入 probe 结果。

## 5. 推荐的真机排查顺序

以后如果再遇到“手势失效”或“某个方向突然不工作”，建议按这个顺序来：

1. 先确认真机手动触摸在断开 SDS 后是否正常。
2. 连上 SDS 后先查 `BypassRouter` 是否有残留 touch bypass。
3. 确认 `Touch/Event` body 是否仍是 `{\"\": {...}}` 形状。
4. 确认动作是否使用完整事件序列，而不是简化 4 事件。
5. 每轮前先恢复到 `main`，并等待恢复完成。
6. 用 `gesture_sweep` 同时观察 `page/widget/workout_state` 三个信号。
7. 如果 `swipe_up`、`swipe_left` 有效但 `swipe_down`、`swipe_right` 无效，优先怀疑语义或前提变了，不要先怀疑 SDS 总链路坏掉。

## 6. 当前项目里哪些结论可以直接复用

已经可以直接复用的内容：

- `swipe_up` 完整有效序列
- `swipe_left` 完整有效序列
- `release_bypasses()` 清理逻辑
- `Touch/Event` / `Knob/Event` 的正确 body 形状
- `gesture_sweep` 的严格 `main` 基线与三路状态采样

当前不要直接复用为“正确方案”的内容：

- `swipe_down` 当前实现
- `swipe_right` 当前实现
- 任何只靠 `Gesture/Progress` 得出的结论
- 任何起点不是 `main` 的 sweep 结论

## 7. 后续建议

下一轮如果继续攻 workout 入口，建议不要再从“调下滑参数”开始，而是先查：

1. `main` 之外是否存在特定前置态。
2. `c-lowp -> main` 之间是否有额外动作前提。
3. workout 是否已改成非 touch 入口或组合入口。
4. 是否存在稳定的 `view name` / `exercise state` / `sport mode state` 可作为入口判据。

在没有新证据前，项目口径应保持：

- `swipe_up`：已验证有效
- `swipe_left`：已验证有效
- `swipe_down`：目标语义已定义，但真机尚未验证成功
- `swipe_right`：尚未验证成功
