# 项目复盘与清理说明

## 复盘范围

本次复盘基于以下信息源进行抽样和归纳：

- 项目仓库当前代码、测试与文档
- `C:\Users\3681\.codex\sessions` 与 `archived_sessions` 中和 `D:\3681\Documents\FT-automation` 相关的会话记录
- 当前仓库中的运行产物与调试产物目录

复盘目标不是复制历史对话，而是提炼已经验证过的稳定结论，并据此清理无效文件与调试残留。

## 已确认的稳定结论

### 1. 当前项目已经从最小脚手架演进为可运行框架

以下模块已经形成有效依赖链，不能按“中间调试代码”处理：

- `src/watch_ui_automation/assertions`
- `src/watch_ui_automation/dsl`
- `src/watch_ui_automation/flows`
- `src/watch_ui_automation/pages`
- `src/watch_ui_automation/session`
- 对应的 `tests/unit/*`、`tests/smoke/*`、`tests/regression/*`、`tests/stability/*`

这些目录已经被测试和夹具真实引用，属于当前项目结构的一部分。

### 2. 真机导航口径已经发生过一次重要收紧

从历史会话与现有代码可确认，项目近期已经完成以下调整：

- `widget` 的主证据从“非空字段”收紧为“必须看见离开 watchface 的视图切换证据”
- `workout` 的主证据从旧状态读取口径切换为更贴近当前设备行为的资源
- `open_workout` 默认导航从 `press_top_left` 切换为 `swipe_up`
- settings 校验目前走 `Ui/Control/Open/Close` 链路，验证的是视图切换与返回闭环

这部分调整已经体现在 `README.md`、`configs/default.yaml`、设备控制器与单元测试中，属于应保留的有效演进。

### 3. 运行产物与过程文档需要从项目主线中剥离

当前仓库里存在两类不应继续留在主线中的内容：

- 运行产物与缓存：`artifacts/`、`__pycache__/`、`.pytest_cache/`
- Codex 过程文档：`docs/superpowers/` 下的设计稿与实现计划

这些文件对复现过程有帮助，但不是项目用户文档，也不应和业务代码一起长期维护。

## 本次清理原则

### 保留

- 已进入源码主结构并被测试覆盖的模块
- 能帮助后续维护者理解真实设备口径的项目文档
- 当前仍然有效的配置与测试

### 删除

- 本仓库内缓存文件
- 本仓库内运行产物
- 仅服务于当次 Codex 执行过程的设计/计划文档

### 谨慎不动

- `.worktrees/`

原因：该目录虽然被忽略，但可能仍承载人工隔离中的工作区，直接删除有误伤风险。

## 后续维护约定

1. 项目级说明优先写入 `README.md` 或 `docs/`，不要把临时设计过程长期留在 `docs/superpowers/`。
2. 真机调试产物默认只留在本地 `artifacts/`，不要纳入仓库主线。
3. 清理前先区分“被测试覆盖的实现”与“仅为一次调试存在的残留”，避免误删真实能力。
4. 完成声明前必须重新跑项目测试，并明确说明已验证与未验证范围。
