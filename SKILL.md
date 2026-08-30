---
name: ai-maturity
description: AI 协作成熟度评估（AI Collaboration Maturity Assessment）：自动探测本机 AI 客户端（Claude Code / WorkBuddy / QoderWork / TRAE Work / ChatGPT Work(Codex) / KimiWork / 豆包工作 / KroWork / OpenClaw / Gemini / Hermes / Domate，Mac 与 Windows）并读取完整会话记录，六维评分 + AI 范式段位（聊天框玩家→提示词工程师→工具调用者→智能体指挥→多智能体编排者→人机合一，含冷启动新手保护与硬成就门槛），生成带揭晓交互的 HTML 段位报告。当用户说"成熟度评估""AI协作评估""段位测评""测评我的使用""我的段位""给我打个分"时使用。
---

# AI 协作成熟度评估

对外正式名称「AI 协作成熟度评估」；段位/称号/稀有度是报告内部的呈现层，对外文案不称"游戏"或"段位测评"。

三层架构：**脚本统计（确定性）→ 模型判读（定性）→ 模板渲染（固定）**。你只负责第二层的判断，数字和图表都不许自己造。

## 第 0 步：意向收集（AskUserQuestion）

用 AskUserQuestion 一次问三题（若环境无此工具，用括号内默认值直接继续并告知用户）：

1. **分析范围**：全量（推荐，默认）/ 近 90 天 / 近 30 天
2. **行业模板**：证券金融（默认）/ 法律 / 通用
3. **报告口味**：完整版——含专属称号与"名场面"吐槽（默认）/ 温和版——称号取鼓励向、不含名场面（适合准备分享给同事或领导看的场合）

## 第 1 步：跑统计脚本（禁止手工统计）

先探测本机有哪些客户端的数据（**Windows 下把 `python3` 换成 `python` 或 `py`**，路径注册表会按 OS 自动选 %USERPROFILE%/%APPDATA% 候选）：

```bash
python3 <skill_dir>/scripts/collect_stats.py --list
```

--list 每个客户端带 verified 标记：true=格式实测过；false=候选路径命中（用通用解析，报告需注明"实验性支持"）。一个都没命中时跑 `--probe-deep`，把输出发给管理员补适配。各端验证状态见 references/VALIDATION.md。

若发现多个客户端，把"测哪个"并入第 0 步的 AskUserQuestion，选项：各客户端 + **「全家桶（合并所有端）」**——多端混用的用户（分摊费用/套餐是常态）推荐全家桶，采集用 `--tool all`，评分判读基于合并后的三类消息（first_messages 等已带 [客户端] 标签），报告自动出多端分布图与跨端并行证据。然后采集：

```bash
python3 <skill_dir>/scripts/collect_stats.py --tool <客户端|auto> --days <0|30|90> --out <scratch_dir>
```

已注册适配见 references/VALIDATION.md 的矩阵（Mac/Windows 各自的路径与验证状态）。脚本自动分离自动化会话与真人会话，输出到 out 目录：
- `stats.json` — 全部数值指标（会话数、活跃、月度、24h、轮次、并行度、沉淀实存、重复组）
- `first_messages.txt` / `feedback.txt` / `closings.txt` — 三类高信号消息全量

**先向用户报告数据规模**（找到多少文件、多少会话、自动化/真人各多少、时间跨度），再继续。脚本失败就直说卡在哪，不许凭记忆编造统计。

**新手保护**：若 stats.json 里 `human_sessions < 15`，进入定级赛模式——跳过第 2 步评分，按 references/rubric.md 的「定级赛报告」章节产出新手引导版，然后直接到第 3 步渲染（rank_mode=placement）。

## 第 2 步：定性判读与评分

通读三个 txt（**逐条，不许抽样**），按 `references/rubric.md` 的六维细则打分。产出 `scores.json`（结构见 rubric.md 末尾），要点：

- 每个子项分数必须有证据支撑，证据引用带日期 + 原话大意，按行业模块的脱敏红线处理
- 三枚硬成就（自动化运行 / 并行编排 / 固化率≥60%）从 stats.json 实证判定，不许推测
- 专属称号从真实数据来，不套模板；温和版口味下称号取鼓励向
- 「对你提升最大的三件事」按（权重 × 失分 × 易改度）选，各标【快赢】/【进阶】，含可照抄话术；重复未固化的事直接给固化草稿
- 问题归因：你的原因 vs 工具的原因占比，工具的锅要明说

## 第 3 步：渲染报告（禁止手写 HTML）

```bash
python3 <skill_dir>/scripts/render_report.py <scratch_dir>/scores.json <scratch_dir>/stats.json
```

模板已内置：LOL 式段位计算、**得分与称号的点击揭晓交互**、六维雷达、四张画像图、归因条、参照系、名场面沉底（温和版自动隐藏）。输出到桌面「我的AI使用段位报告.html」。

最后告诉用户文件路径，并提醒：报告里的分数和称号是盖着的，点击揭晓。

## 第 4 步：自进化（每次运行后必做）

按 EVOLUTION.md 协议执行：把本次运行的信号（分类误判 / 新数据路径 / 判读困难 / 用户异议 / 渲染问题）追加到 evolution/log.md；数据层问题（任务分类关键词、客户端路径注册表、负反馈词表）直接修补并记 CHANGELOG；评分层问题（权重、阈值、档位、成就条件）只写入 evolution/proposals.md 提案，不许直接改。修补后对既有客户端跑一次回归再收工。
