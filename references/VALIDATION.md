# 客户端 × 操作系统 适配验证矩阵

状态：✅ 本机实测通过 · 🟡 路径命中但格式为通用启发式（实验性） · ⬜ 候选路径未验证 · ❌ 未适配

| 客户端 | Mac 路径 | Mac 状态 | Windows 路径 | Win 状态 |
|---|---|---|---|---|
| Claude Code | ~/.claude/projects | ✅ 精确解析 | %USERPROFILE%\.claude\projects | ⬜（跨平台 CLI，路径规则同源，大概率直通） |
| WorkBuddy | ~/.workbuddy/projects | ✅ 精确解析 | %USERPROFILE%\.workbuddy\projects 或 %APPDATA%\WorkBuddy | ⬜ |
| ChatGPT Work / Codex | ~/.codex/sessions | ✅ 通用解析实测通过 | %USERPROFILE%\.codex\sessions 或 %APPDATA%\ChatGPT | ⬜ |
| QoderWork | ~/.qoderwork（也探 ~/.qoder-cli、~/.qoder） | 🟡 实测 13 真人会话解析正常 | %APPDATA%\Qoder 等 | ⬜ |
| TRAE Work | ~/.trae、~/Library/Application Support/Trae | ⬜ 本机无会话样本 | %APPDATA%\Trae | ⬜ |

| KimiWork | ~/.kimi、~/Library/Application Support/kimi-desktop | 🟡 内容可解析，时间戳字段不同 | %APPDATA%\Kimi | ⬜ |
| OpenClaw | ~/.openclaw/agents/*/sessions | 🟡 实测 3240 会话解析正常（自动化分离精准） | %USERPROFILE%\.openclaw | ⬜ |
| Gemini / Antigravity | ~/.gemini/antigravity/brain（隐藏子目录精确匹配） | 🟡 2 会话可解析 | 同构路径 | ⬜ |
| Hermes Agent | ~/.hermes | ⬜ 仅 3 文件，样本不足 | — | ⬜ |
| 豆包工作 DoubaoWork | ~/Library/Application Support/DoubaoWork | ❌ **本地无明文会话**（Electron 壳，会话在云端/IndexedDB）——需官方导出方案，评估暂不可用 | %APPDATA%\DoubaoWork | ❌ 同左 |
| KroWork | ~/Library/Application Support/krow-app | ❌ 同上，本地无明文会话 | %APPDATA%\krow-app | ❌ 同左 |
| Domate | ~/.domate、~/Library/Application Support/Domate | ❌ 无任何样本，纯候选 | %APPDATA%\Domate | ❌ |

**重要口径**：豆包工作、KroWork 这类"本地无明文"客户端不是漏配——本机确认装了但翻不到会话文件。对用户话术："该产品会话存云端，本地评估暂不支持，已反馈"。

## Mac / Windows 已知差异（脚本已处理）

1. **数据根目录**：Mac 用 `~` 与 `~/Library/Application Support`；Windows 用 `%USERPROFILE%`、`%APPDATA%`、`%LOCALAPPDATA%`——注册表按当前 OS 自动选候选路径
2. **Python 命令名**：Mac 是 `python3`；**Windows 通常只有 `python` 或 `py`**——SKILL.md 已按 OS 给出不同命令
3. 路径分隔符、编码（utf-8 errors=replace）、时间戳（ISO / 秒 / 毫秒）均已兼容

## 怎么补一个 ⬜ / ❌

在目标机器上跑：

```
python collect_stats.py --list
python collect_stats.py --probe-deep
```

把两段输出发回来即可：--list 命中说明候选路径正确；没命中时 --probe-deep 会列出所有含会话文件的可疑目录，据此在 CLIENTS 注册表加一行（约 1 分钟）。格式解析不对时，另发该目录下任意一个 .jsonl 的前 3 行（脱敏后）。

**验证优先级**：按你所在环境的主力客户端优先。补充一格适配约 1 分钟，欢迎按 CONTRIBUTING.md 提交。
