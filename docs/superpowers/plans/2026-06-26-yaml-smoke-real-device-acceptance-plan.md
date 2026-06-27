# YAML Smoke 真机验收计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 在显式 opt-in 的前提下，收集 Python smoke 与 YAML smoke 的真机运行证据，并完成第一阶段 artifact compare 验收，确认两条路径的核心产物可以按显式 `case_map` 对齐。

**Architecture:** 先做纯离线预检，确认 YAML 场景能加载、pytest 能收集、真机开关默认不会误触设备；再分别跑用于 compare 的 Python smoke 子集 run 和 YAML smoke 真机运行，保留完整 run 目录；如需更宽的健康检查，可以另跑完整 Python smoke，但不把它直接喂给 `--suggest-case-map`。最后用 `watch_ui_automation.artifacts.compare` 做 run-level 对比，先看 `--suggest-case-map`，再用显式 `--case-map` 走正式 compare。整个过程中把 run 目录、compare 输出和失败 case 的 snapshot/result 当作固定证据，不做自动清理。

**Tech Stack:** PowerShell、Python 3、pytest、`watch_ui_automation.scenarios.loader`、`watch_ui_automation.artifacts.compare`、JSON artifact 目录、YAML 场景文件。

---

### Task 1: 真机前预检

**Files:**
- Reference: `C:\Users\3681\.codex\worktrees\2ab4\FT-automation\README.md`
- Reference: `C:\Users\3681\.codex\worktrees\2ab4\FT-automation\configs\default.yaml`
- Reference: `C:\Users\3681\.codex\worktrees\2ab4\FT-automation\tests\yaml_cases`
- Reference: `C:\Users\3681\.codex\worktrees\2ab4\FT-automation\tests\smoke`

- [ ] **Step 1: 先跑纯离线校验，确认场景与收集链路可用**

Run:

```powershell
$env:PYTHONPATH='src'
python -m watch_ui_automation.scenarios.loader validate tests/yaml_cases --suite smoke
python -m pytest tests/scenario --collect-only -q --scenario-suite smoke
python -m pytest tests/smoke --collect-only -q
```

Expected:

- YAML validate 通过，能明确看到 smoke 场景可加载
- `tests/scenario --collect-only` 只做收集，不触碰真机
- `tests/smoke --collect-only` 只做收集，不触碰真机

- [ ] **Step 2: 检查真机 opt-in 变量，确认当前 shell 不会自动开跑设备测试**

Run:

```powershell
Get-Item Env:WATCH_UI_RUN_DEVICE_TESTS -ErrorAction SilentlyContinue
```

Expected:

- 这一步只做只读检查
- 若环境变量不存在，或其值不是 `1`，说明当前 shell 还没有进入真机执行模式
- 在正式跑真机前，不要在预检阶段手工设置 `WATCH_UI_RUN_DEVICE_TESTS=1`

- [ ] **Step 3: 只读核对设备配置，确认目标和输入链路没有写错**

Run:

```powershell
Get-Content configs/default.yaml | Select-String -Pattern '^\s*device:\s*$|^\s*serial:|^\s*sds_url:|^\s*input:\s*$|^\s*navigation:\s*$' -Context 0,2
```

Expected:

- 能看到当前默认设备序列号、SDS 地址、输入动作与导航配置
- 这里只确认配置是否指向授权的测试机，不执行任何设备操作
- 如果看到明显不该触达的设备、占位值或不确定的地址，先停下来，不进入真机步骤

- [ ] **Step 4: 在预检结论里明确“这一步不触设备”**

说明：

- 预检阶段只允许 `validate`、`collect-only`、配置只读检查
- 预检阶段不设置 `WATCH_UI_RUN_DEVICE_TESTS=1`
- 预检阶段不运行任何会打开真机链路的 pytest 命令

### Task 2: Python smoke 真机对照 run

**Files:**
- Reference: `C:\Users\3681\.codex\worktrees\2ab4\FT-automation\tests\smoke`
- Reference: `C:\Users\3681\.codex\worktrees\2ab4\FT-automation\artifacts`
- Reference: `C:\Users\3681\.codex\worktrees\2ab4\FT-automation\README.md`

- [ ] **Step 1: 显式打开真机开关，跑 Python smoke 对照 run**

Run:

```powershell
$env:WATCH_UI_RUN_DEVICE_TESTS='1'
python -m pytest tests/smoke/test_widget_smoke.py tests/smoke/test_workout_smoke.py -v --device-config configs/default.yaml
```

Expected:

- 这次运行明确带有 `WATCH_UI_RUN_DEVICE_TESTS=1`
- 这次运行只生成可 compare 的 Python smoke 子集，目标是 `smoke_widget` 和 `smoke_workout`
- 运行结束后，保留本次生成的完整 `artifacts/run-*/` 目录
- 如果还想跑完整 `tests/smoke -v` 作为更宽的健康检查，可以另跑一条命令，但不要把 full smoke run 直接拿去做 `--suggest-case-map`

- [ ] **Step 2: 记录 Python smoke 的产物目录**

需要保留的证据：

- 本次 Python smoke 对应的 `artifacts/run-*/` 整个目录
- `artifacts/run-*/run_manifest.json`
- `artifacts/run-*/cases/*/steps.jsonl`
- `artifacts/run-*/cases/*/assertions.jsonl`
- `artifacts/run-*/cases/*/result.json`
- 若有失败，再保留 `artifacts/run-*/cases/*/state_snapshot.json`

- [ ] **Step 3: 写清 Python smoke 的最小成功标准**

最小成功标准：

- `pytest` 退出码为 `0`
- 目标 Python smoke case 都有对应 `result.json`
- `smoke_widget` 与 `smoke_workout` 的 `result.json` 里能看到期望的 case 名与成功状态
- 这次基线的 run 目录没有被后续清理动作覆盖

### Task 3: YAML smoke 真机运行

**Files:**
- Reference: `C:\Users\3681\.codex\worktrees\2ab4\FT-automation\tests\scenario`
- Reference: `C:\Users\3681\.codex\worktrees\2ab4\FT-automation\artifacts`
- Reference: `C:\Users\3681\.codex\worktrees\2ab4\FT-automation\README.md`

- [ ] **Step 1: 显式打开真机开关，跑 YAML smoke 真机**

Run:

```powershell
$env:WATCH_UI_RUN_DEVICE_TESTS='1'
python -m pytest tests/scenario -v --device-config configs/default.yaml --scenario-suite smoke
```

Expected:

- 这次运行也必须显式带 `WATCH_UI_RUN_DEVICE_TESTS=1`
- YAML smoke 会真的走真机链路
- 运行结束后，保留本次生成的完整 `artifacts/run-*/` 目录

- [ ] **Step 2: 记录 YAML smoke 的产物目录**

需要保留的证据：

- 本次 YAML smoke 对应的 `artifacts/run-*/` 整个目录
- `artifacts/run-*/run_manifest.json`
- `artifacts/run-*/cases/*/steps.jsonl`
- `artifacts/run-*/cases/*/assertions.jsonl`
- `artifacts/run-*/cases/*/result.json`
- 若有失败，再保留 `artifacts/run-*/cases/*/state_snapshot.json`

- [ ] **Step 3: 写清 YAML smoke 的最小成功标准**

最小成功标准：

- `pytest` 退出码为 `0`
- 目标 YAML smoke case 都有对应 `result.json`
- `smoke_widget_yaml` 与 `smoke_workout_yaml` 的 `result.json` 里能看到期望的 case 名与成功状态
- 这次 YAML run 的目录和 Python run 目录是两份独立证据，不混用

### Task 4: artifact compare 验收

**Files:**
- Reference: `C:\Users\3681\.codex\worktrees\2ab4\FT-automation\README.md`
- Reference: `C:\Users\3681\.codex\worktrees\2ab4\FT-automation\artifacts`
- Reference: `C:\Users\3681\.codex\worktrees\2ab4\FT-automation\src\watch_ui_automation\artifacts\compare.py`

- [ ] **Step 1: 先用 `--suggest-case-map` 看候选映射**

Run:

```powershell
$env:PYTHONPATH='src'
python -m watch_ui_automation.artifacts.compare <python_compare_run_dir> <yaml_run_dir> --suggest-case-map
```

Expected:

- 这一步只输出建议映射，不替代正式 compare
- 先确认候选映射里是否能看到 `smoke_widget:smoke_widget_yaml`
- 先确认候选映射里是否能看到 `smoke_workout:smoke_workout_yaml`
- 如果候选映射和预期不一致，先记录输出，再回到 run 目录和 case 名核对，不要直接把 `selected_tests` 当成映射
- 这里的 Python 侧必须是只包含 `smoke_widget` / `smoke_workout` 的 compare-scope run；如果喂进去的是 full `tests/smoke` run，当前会因为 `smoke_device_connection`、`smoke_settings`、`smoke_settings_views` 没有对应 YAML case 而 unmatched

- [ ] **Step 2: 用显式 `--case-map` 跑正式 compare**

Run:

```powershell
$env:PYTHONPATH='src'
python -m watch_ui_automation.artifacts.compare <python_run_dir> <yaml_run_dir> --case-map smoke_widget:smoke_widget_yaml --case-map smoke_workout:smoke_workout_yaml
```

Expected:

- 正式 compare 必须显式传 `--case-map`
- `selected_tests` 只是标签列表，不是 case_map，不能拿来代替参数
- compare 退出码为 `0` 才算这一轮映射和核心 artifact 对齐通过

- [ ] **Step 3: 把 compare 输出当作验收证据的一部分保留**

需要保留的证据：

- `--suggest-case-map` 的输出
- 正式 compare 的完整输出
- compare 使用的 Python run 目录
- compare 使用的 YAML run 目录
- 明确写出本次使用的映射：`smoke_widget -> smoke_widget_yaml`、`smoke_workout -> smoke_workout_yaml`

### 验收完成条件

- Python smoke 真机 run 已完成，且对应 `artifacts/run-*/` 目录完整保留
- YAML smoke 真机 run 已完成，且对应 `artifacts/run-*/` 目录完整保留
- 两边都能拿到目标 case 的 `result.json`、`steps.jsonl`、`assertions.jsonl`
- `watch_ui_automation.artifacts.compare` 先跑过 `--suggest-case-map`
- `watch_ui_automation.artifacts.compare` 再用显式 `--case-map smoke_widget:smoke_widget_yaml --case-map smoke_workout:smoke_workout_yaml` 跑过正式 compare
- compare 退出码为 `0`
- 这一轮正式 run-level compare 通过时，也意味着本轮 compare 所依赖的 `run_manifest.device_serial`、`sds_url`、`framework_version` 一致性校验已通过
- 明确没有把 `run_manifest.selected_tests` 误当成 `case_map`
- 明确没有在未显式 opt-in 的情况下自动触发真机测试
- 真机验收结束后，如果要回到离线命令，先清理 `WATCH_UI_RUN_DEVICE_TESTS` 或新开一个 PowerShell 会话

### 失败时怎么收口

- 先保留失败那次的完整 `artifacts/run-*/` 目录，不要在比对前清理
- 保留 compare 的完整输出，尤其是候选映射、差异文本和退出码
- 保留失败 case 的 `result.json`
- 如果有失败 case，再保留 `state_snapshot.json`
- 保留 `steps.jsonl` 和 `assertions.jsonl`，用于回看是步骤问题、断言问题还是环境问题
- 报告里至少写清楚：失败发生在哪个 run、哪个 case、哪个 compare 命令、当前 `case_map` 用了什么
