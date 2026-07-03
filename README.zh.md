# 🗣️ 对话议会 — 让 AI 历史会话以"群聊"参与新讨论

> 你的 139 段历史对话不再是沉默的存档。它们可以像专家团一样，在新对话中发表意见、碰撞观点、帮你决策。

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Python 3.10+](https://img.shields.io/badge/Python-3.10%2B-blue)](https://python.org)
[![Reasonix Skill](https://img.shields.io/badge/Reasonix-Skill-58a6ff)](https://github.com/CS-Faith/reasonix-portakit)

---

## 🎯 解决什么问题

你用 Reasonix 跟 AI 聊了几百轮——聊过系统架构、聊过需求设计、聊过技术选型。每段对话都积累了独特的知识、立场和决策。

但当你开一个新对话时，这些知识被锁在历史存档里。你可以手动复制粘贴上下文，但那又累又漏。

**对话议会**让历史对话"活过来"——每个对话变成一个**有立场的议员**，用第一人称（"我这边"、"我当时"）参与你的新讨论。

---

## 💬 效果演示

```
你: "升级到 Spring Boot 3.2 对各系统有什么影响？"

【对话议会·议长】
  已召集 3 位相关议员发言——

**【Spring Boot升级经验 - 2026-06-24】**
  我这边经历过这个。javax→jakarta 是最大的坑，光命名空间迁移就搞了
  3 天。建议让 3.0 的系统先升级验证，2.7 的等我这边踩完坑再跟进。
  保守估计 5 人日。

**【LLM WIKI 知识库 - 2026-06-30】**
  @Spring Boot升级经验 说得对，但我补充一点：代码不是最大问题，
  文档才是。所有内部 Wiki 里的旧包名引用全部会失效。
  建议先跑一遍文档批量扫描。

**【禅道需求管理 - 2026-06-24】**
  别光讨论技术。我可以在禅道建升级跟踪迭代，每个系统一个需求，
  进度一目了然。之前 IVP 和 DSMS 的需求批量创建流程已经验证过了。
```

---

## 🏗️ 工作原理

```
Reasonix 会话目录 (.jsonl + .meta.json)
        │
        ▼
  扫描引擎 (自动发现 139 个有效会话，按时间排序)
        │
        ▼
  摘要提取器 (DeepSeek 提取结构化摘要：领域、实体、决策、立场)
        │
        ▼
  议会配置 (用户选定哪些会话成为"议员"，可随时增减)
        │
        ▼
  匹配引擎 (当前问题与哪些议员相关？LLM 自动判断)
        │
        ▼
  代言生成器 (每个相关议员以第一人称回应，基于其历史上下文)
        │
        ▼
  群聊呈现 (议长串场 + 议员发言 + 观点碰撞 + 结构化总结)
```

---

## 🚀 快速开始

### 环境要求

- [Reasonix](https://github.com/CS-Faith/reasonix-portakit)（含历史会话记录）
- Python 3.10+（Reasonix 便携版已自带）
- DeepSeek API Key

### 安装

```bash
# 复制到 Reasonix skills 目录
cp -r conversation-council/ ~/.reasonix/skills/conversation-council/

# 或直接 clone
git clone https://github.com/CS-Faith/reasonix-conversation-council.git \
  ~/.reasonix/skills/conversation-council/
```

### 第一次：组建议会

在任何 Reasonix 对话中输入：

```
/skill conversation-council
```

Skill 会自动扫描你的历史会话，列出最近 20 个让你选择。你可以：
- **按编号**：`1, 2, 4, 6`
- **按关键词**："所有关于 LLM WIKI 的对话"
- **按日期**："最近一周的"
- **自由组合**

### 之后：随时召集

```
/skill conversation-council
我们这个季度的技术债务优先级怎么排？
```

---

## 📋 CLI 命令

```bash
# 扫描历史会话
python council.py scan --recent 20

# 初始化议会（选择议员）
python council.py init --sessions "desktop-20260630...,desktop-20260629..."

# 召集讨论
python council.py speak "你的问题"

# 议员管理
python council.py manage --list              # 查看当前议员
python council.py manage --add "session_id" --as "自定义昵称"  # 添加
python council.py manage --remove "session_id"                  # 移除

# 刷新摘要（某段对话有大更新后）
python council.py extract --force
```

---

## 💰 成本极低

| 操作 | Token 消耗 | 频率 |
|------|-----------|------|
| 首次扫描 139 会话 | ~5,000 | 一次性 |
| 每个议员摘要提取 | ~500 | 仅首次（之后命中缓存） |
| 每次议会讨论 | ~3,000-5,000 | 每次提问 |

DeepSeek 定价约 ¥0.001/千 token，**每次"开会"不到 1 分钱**。

---

## 🔌 兼容性

**同时支持 Reasonix v0.53 和 v1.X（Go 重写版）**。council.py 启动时自动检测会话存储格式并采用对应的解析策略。

### v0.53 格式

- 会话文件：`desktop-YYYYMMDDHHMM-N.jsonl`
- 元数据：`desktop-YYYYMMDDHHMM-N.meta.json`（含 `summary`、`totalCostUsd` 等）
- 数据目录：`{reasonix_home}/.reasonix/sessions/`

### v1.X 格式（Go 重写版）

- 会话文件：`YYYYMMDD-HHMMSS-model.jsonl` 或 `*.events.jsonl`
- 元数据：`*.meta`（BranchMeta JSON，含 `Preview`、`Turns`、`Scope` 等）
- 数据目录：`%APPDATA%/reasonix/sessions/`（Windows）或 `~/.reasonix/sessions/`（macOS/Linux）
- 支持 `REASONIX_HOME` 环境变量覆盖

### 自动检测

无需手动指定版本。`scan` 命令扫描 sessions 目录中的文件，根据扩展名（`.meta` vs `.meta.json`）自动判断格式。

### 会话文件格式

两版共用相同的 JSONL 消息格式：

```jsonl
{"role":"user","content":"..."}
{"role":"assistant","content":"...","tool_calls":[...]}
{"role":"tool","tool_call_id":"...","content":"..."}
```

- 每行一个 JSON 对象（JSONL 格式）
- 包含标准的 `role` 字段：`user`（用户）、`assistant`（助手）、`tool`（工具调用）
- 助手消息可携带 `tool_calls` 数组，记录工具调用信息

### 扩展到其他 AI Agent 平台

核心架构是**平台无关的**——摘要提取、议员匹配、代言生成这些重活，全部运行在标准化后的消息列表上，与原始平台无关。要接入其他 Agent 平台，只需三步：

1. **编写格式适配器** — 新增一个类似 `read_session_messages()` 的函数，将该平台的原生会话格式转换为统一的 `[{role, content}]` 消息列表
2. **提供会话元数据** — 实现会话列表功能（含时间戳和简短摘要，功能等价于 Reasonix 的 `.meta.json` 文件）
3. **其余代码完全不变** — `extract_summary()`（摘要提取）、`match_members()`（相关性匹配）、`generate_spokesperson_response()`（代言生成）、`run_council()`（讨论流程）全部基于标准化消息格式运行，不感知来源平台

| 平台 | 适配难度 | 具体做法 |
|------|:--:|------|
| Reasonix v0.53 | ✅ 内置 | 自动检测，无需额外开发 |
| Reasonix v1.X (Go) | ✅ 内置 | 自动检测，含 REASONIX_HOME 和 APPDATA 感知 |
| ChatGPT 导出 | 低 | 解析 `conversations.json`，提取 `role` + `content` |
| Claude 导出 | 低 | 解析 Claude 的 JSON 导出格式 |
| LibreChat | 中 | 读取 MongoDB 中的对话文档 |
| 自定义 Agent 日志 | 低 | 任何含 `role` + `content` 字段的 JSONL 或 JSON |
| Loop Agent 线程 | 中 | 读取 mesh 引擎的 `threads/*.json` 文件 |

**核心认知**：一个对话一旦被压缩成 500 字的结构化摘要，它来自哪个平台就不再重要。议会只读摘要，不碰原始日志。

---

## 🧩 生态整合

对话议会的设计故意与以下项目兼容：

| 项目 | 整合方式 |
|------|---------|
| **Conversation Mesh** (Loop Agent) | 每个议员 = 一个 mesh 子对话，议会 = 总对话 UI |
| **multi-agent-discuss** | 输出格式完全一致（`**【角色】**` + 议长串场） |
| **engine.py** | 复用 `extract_summary()` 结构化摘要提取 prompt |

---

## 🔗 相关项目

| 项目 | 说明 |
|------|------|
| [reasonix-portakit](https://github.com/CS-Faith/reasonix-portakit) | Reasonix 便携工具链 |
| [knowledge-cleanup](https://github.com/CS-Faith/knowledge-cleanup) | AI 驱动的文件查重清理 |
| [llm-wiki-pipeline](https://github.com/CS-Faith/llm-wiki-pipeline) | 端到端知识库构建流水线 |
| [reasonix-migration-assistant](https://github.com/CS-Faith/reasonix-migration-assistant) | Reasonix 配置迁移助手 |

---

## 📄 许可证

MIT © 2026 [CS-Faith](https://cs-faith.github.io)

---

**标签**: `reasonix` `ai-skill` `multi-agent` `对话历史` `群聊` `第一人称AI` `大模型编排` `知识管理` `DeepSeek` `个人AI工具`
