# 🗣️ Conversation Council — 多视角 AI 讨论

> 历史 AI 会话中藏着大量未被利用的知识。Conversation Council 将这些历史会话转化为「AI 专家」小组，以第一人称视角参与新讨论 —— 让你的历史会话终于能「开口说话」。

> **Your past AI conversations contain answers you're not using.** Conversation Council turns your historical sessions into a panel of AI "experts" who advise you in first-person — so your history finally speaks back.

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Python 3.10+](https://img.shields.io/badge/Python-3.10%2B-blue)](https://python.org)
[![Reasonix Skill](https://img.shields.io/badge/Reasonix-Skill-58a6ff)](https://github.com/CS-Faith/reasonix-portakit)

---

## 🎯 问题

你有 **139+ 个历史 AI 会话**，跨越数周的工作。但新对话时，这些知识被锁在孤岛中。

## 💡 解决方案

**Conversation Council** 将你的聊天历史转化为专家小组：

1. **扫描**你的 Reasonix 会话历史
2. **提取**每个会话的结构化摘要
3. **匹配**哪些历史会话与你的问题相关
4. **生成**每位相关「议员」的第一人称回复
5. **以群聊格式**呈现

## 🏗️ 架构

Reasonix 会话文件 (.jsonl)
  → 会话扫描器 → 摘要提取器
  → 议会配置 → 匹配引擎
  → 发言人生成器 → 群聊格式输出

## 🚀 快速开始

### 前置条件
- [Reasonix](https://github.com/CS-Faith/reasonix-portakit)（含会话历史）
- Python 3.10+（Reasonix 便携版已包含）
- DeepSeek API Key（用于 LLM 调用）

### 安装

git clone https://github.com/CS-Faith/conversation-council.git
~/.reasonix/skills/conversation-council/

### 首次运行

在任意 Reasonix 会话中：/skill conversation-council

可选择：编号（1,2,4,6）、关键词（"LLM WIKI"）、日期范围（"上周"）

### 日常使用

/skill conversation-council 问其中输入问题

## 📋 CLI 命令

- council.py scan --recent 20 — 列出最近会话
- council.py init --sessions "id1,id2" — 选择议员
- council.py speak "问题" — 运行讨论
- council.py manage --list — 列出当前成员
- council.py manage --add "id" / --remove "id" — 管理成员
- council.py extract --force — 刷新所有摘要

## 💰 成本

- 初始扫描（139 会话）：~5,000 tokens（一次性）
- 每位议员摘要：~500 tokens（一次性，缓存）
- 每次讨论：~3,000-5,000 tokens

DeepSeek 定价下，每次讨论成本不到 0.01 元。

## 🔌 兼容性

支持 Reasonix v0.53 / v1.X (Go 重写) / Codex — 自动检测格式，无需手动配置。

## 📜 许可证
MIT © 2026 [CS-Faith](https://cs-faith.github.io)

---

## Next step

管理跨设备 AI 工作区？ → [Portakit](https://github.com/CS-Faith/reasonix-portakit)

清理知识库重复？ → [knowledge-cleanup](https://github.com/CS-Faith/knowledge-cleanup)

## 🔗 相关项目

| 项目 | 描述 |
|------|------|
| [reasonix-portakit](https://github.com/CS-Faith/reasonix-portakit) | Reasonix 便携工具箱 |
| [knowledge-cleanup](https://github.com/CS-Faith/knowledge-cleanup) | AI 驱动的知识库去重 |
| [llm-wiki-pipeline](https://github.com/CS-Faith/llm-wiki-pipeline) | 端到端知识库构建 |

---

# Conversation Council (English)

> **Your past AI conversations contain answers you're not using.** Conversation Council turns your historical sessions into a panel of AI "experts" who advise you in first-person.

## The Problem

You have **139+ past AI conversations** spanning weeks of work — each contains valuable context, decisions, and domain knowledge. But when you start a new conversation, that knowledge is **trapped in silos**.

## The Solution

1. **Scan** your Reasonix session history
2. **Extract** structured summaries from each conversation
3. **Match** which past conversations are relevant
4. **Generate** first-person responses from each "council member"
5. **Present** in group-chat format

## Architecture

Reasonix Session Files → Session Scanner → Summary Extractor → Council Config → Match Engine → Spokesperson Generator → Group-Chat Output

## Quick Start

Prerequisites: Reasonix, Python 3.10+, DeepSeek API key

git clone https://github.com/CS-Faith/conversation-council.git
cp -r conversation-council/ ~/.reasonix/skills/conversation-council/

In any Reasonix conversation: /skill conversation-council

## CLI Commands

- council.py scan --recent 20 — List recent sessions
- council.py init --sessions "id1,id2" — Select members
- council.py speak "question" — Run discussion
- council.py manage --list / --add / --remove — Manage members
- council.py extract --force — Refresh summaries

## Cost

- Initial scan: ~5,000 tokens (one-time)
- Per member: ~500 tokens (one-time, cached)
- Per discussion: ~3,000-5,000 tokens
- At DeepSeek pricing: less than ¥0.01 per discussion

## Compatibility

Supports Reasonix v0.53 / v1.X (Go) / Codex — automatic format detection.

## License
MIT © 2026 CS-Faith
