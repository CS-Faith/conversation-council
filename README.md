# 🗣️ Conversation Council — Multi-Perspective AI Discussion

> Turn your Reasonix chat history into a panel of AI experts. Each past conversation becomes a "council member" that speaks in first-person, bringing its accumulated knowledge and stance to your current discussion.

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Python 3.10+](https://img.shields.io/badge/Python-3.10%2B-blue)](https://python.org)
[![Reasonix Skill](https://img.shields.io/badge/Reasonix-Skill-58a6ff)](https://github.com/CS-Faith/reasonix-portakit)

---

## 🎯 The Problem

You have **139+ past AI conversations** spanning weeks of work — each one contains valuable context, decisions, and domain knowledge. But when you start a new conversation, that knowledge is **trapped in silos**. You can manually copy-paste context, but that's tedious and incomplete.

## 💡 The Solution

**Conversation Council** turns your chat history into an expert panel. When you ask a question, it:

1. **Scans** your Reasonix session history
2. **Extracts** structured summaries from each conversation (domain, entities, decisions, stance)
3. **Matches** which past conversations are relevant to your question
4. **Generates** first-person responses from each relevant "council member"
5. **Presents** them in a group-chat format with a coordinator

```
You: "Should we upgrade to Spring Boot 3.2?"

【Council Coordinator】
  I've convened 3 relevant council members...

**【Backend Migration Expert - 2026-06-24】**
  I've been through this. javax→jakarta is the biggest pain point.
  My system has 3 modules that need rewriting — plan for 5 person-days.
  Let the 3.0 systems upgrade first as validation.

**【LLM WIKI Pipeline - 2026-06-30】**
  The real problem isn't code — it's documentation. All internal wiki
  references with old package names will break. Run a batch scan first.

**【Zentao PM - 2026-06-24】**
  I can create tracking tickets in Zentao. Let me set up an iteration
  to track upgrade progress across all systems.
```

---

## 🏗️ Architecture

```
Reasonix Session Files (.jsonl)
        │
        ▼
  Session Scanner (139 sessions → ranked by recency)
        │
        ▼
  Summary Extractor (DeepSeek LLM → structured persona per session)
        │
        ▼
  Council Config (user selects which sessions become members)
        │
        ▼
  Match Engine (LLM: which members are relevant to the question?)
        │
        ▼
  Spokesperson Generator (LLM: each member responds in first-person)
        │
        ▼
  Group-Chat Format (multi-agent-discuss style presentation)
```

---

## 🚀 Quick Start

### Prerequisites

- [Reasonix](https://github.com/CS-Faith/reasonix-portakit) v0.53 or v1.X (with session history)
- Python 3.10+ (built into Reasonix v0.53 portable; must be installed separately for v1.X)
- DeepSeek API key — set as `DEEPSEEK_API_KEY` environment variable

### Installation

```bash
# 1. Copy skill files to Reasonix skills directory
cp -r conversation-council/ ~/.reasonix/skills/conversation-council/

# 2. Or clone directly
git clone https://github.com/CS-Faith/reasonix-conversation-council.git \
  ~/.reasonix/skills/conversation-council/
```

### First Run

In any Reasonix conversation:

```
/skill conversation-council
```

The skill will scan your session history and ask which conversations to invite as council members. You can select by:
- **Number**: `1, 2, 4, 6`
- **Keyword**: "all about LLM WIKI"
- **Date range**: "last week's conversations"
- **Custom**: any combination

### Daily Use

After setup, anytime you want multi-perspective input:

```
/skill conversation-council
Should we migrate from MySQL to PostgreSQL?
```

---

## 📋 CLI Commands

```bash
python council.py scan --recent 20        # List recent sessions
python council.py init --sessions "id1,id2"  # Select council members
python council.py speak "your question"   # Run a council discussion
python council.py manage --list           # List current members
python council.py manage --add "id"       # Add a member
python council.py manage --remove "id"    # Remove a member
python council.py extract --force         # Refresh all summaries
```

---

## 💰 Cost

| Operation | Tokens | When |
|-----------|--------|------|
| Initial scan (139 sessions) | ~5,000 | One-time |
| Summary extraction per member | ~500/member | One-time (cached) |
| Each council discussion | ~3,000-5,000 | Per question |

With DeepSeek pricing (~¥0.001/1K tokens), each council discussion costs **less than ¥0.005** — essentially free.

---

## 🔌 Compatibility

**Supports Reasonix v0.53 and v1.X (Go rewrite)** with automatic format detection. The session scanner auto-detects the storage format on startup and applies the correct parsing strategy — no manual configuration needed.

### v0.53 Format

- Session files: `desktop-YYYYMMDDHHMM-N.jsonl`
- Metadata: `desktop-YYYYMMDDHHMM-N.meta.json` (contains `summary`, `totalCostUsd`, etc.)
- Data directory: `{reasonix_home}/.reasonix/sessions/`

### v1.X Format (Go Rewrite)

- Session files: `YYYYMMDD-HHMMSS-model.jsonl` or `*.events.jsonl`
- Metadata: `*.meta` (BranchMeta JSON with `Preview`, `Turns`, `Scope`, etc.)
- Data directory: `%APPDATA%/reasonix/sessions/` (Windows) or `~/.reasonix/sessions/` (macOS/Linux)
- Honors `REASONIX_HOME` environment variable

### Auto-Detection

The `scan` command inspects files in the sessions directory and determines the format by extension (`.meta` vs `.meta.json`). The user never needs to specify a version.

### Format Assumptions

The `read_session_messages()` adapter expects:

```jsonl
{"role":"user","content":"..."}
{"role":"assistant","content":"...","tool_calls":[...]}
{"role":"tool","tool_call_id":"...","content":"..."}
```

- One JSON object per line (JSONL)
- Standard `role` field: `user` / `assistant` / `tool`
- Optional `tool_calls` array on assistant messages
- Companion metadata file: `.meta.json` (v0.53) or `.meta` (v1.X) with summary/preview fields

### Extending to Other AI Agents

The core architecture is **platform-agnostic** — the heavy lifting (summary extraction, member matching, spokesperson generation) works on any structured conversation data. To support a different agent platform, you only need to:

1. **Write a format adapter** — a new `read_*_messages()` function that converts the platform's native session format into the common `[{role, content}]` message list
2. **Provide session metadata** — a way to list sessions with timestamps and short summaries (like Reasonix's `.meta.json`)
3. **The rest is unchanged** — `extract_summary()`, `match_members()`, `generate_spokesperson_response()`, and `run_council()` all operate on the normalized message format

| Platform | Effort | What You Need |
|----------|:--:|------|
| Reasonix v0.53 | ✅ Built-in | Auto-detected, no extra work |
| Reasonix v1.X (Go) | ✅ Built-in | Auto-detected, REASONIX_HOME + APPDATA aware |
| ChatGPT exports | Low | Parse `conversations.json` to extract `role` + `content` |
| Claude exports | Low | Parse Claude's JSON export format |
| LibreChat | Medium | Read conversation documents from MongoDB |
| Custom agent logs | Low | Any JSONL or JSON file with `role` + `content` fields |
| Loop Agent threads | Medium | Read `threads/*.json` from the mesh engine |

**The key insight**: once a conversation is reduced to a 500-character structured summary, its origin platform doesn't matter. The council only reads summaries, never raw logs.

---

## 🧩 Integration

- **Loop Agent (Conversation Mesh)**: Conversation Council can serve as the "master thread UI" — each council member corresponds to a mesh sub-thread
- **multi-agent-discuss**: Council output follows the same `**【Role】**` + coordinator format
- **engine.py**: Reuses `extract_summary()` prompts for structured persona extraction

---

## 🔗 Related Projects

| Project | Description |
|---------|-------------|
| [reasonix-portakit](https://github.com/CS-Faith/reasonix-portakit) | Reasonix portable toolkit |
| [knowledge-cleanup](https://github.com/CS-Faith/knowledge-cleanup) | AI-powered file deduplication |
| [llm-wiki-pipeline](https://github.com/CS-Faith/llm-wiki-pipeline) | End-to-end knowledge base pipeline |

---

## 📄 License

MIT © 2026 [CS-Faith](https://cs-faith.github.io)

---

**Tags**: `reasonix` `ai-skill` `multi-agent` `conversation-history` `group-chat` `first-person-ai` `llm-orchestration` `knowledge-management` `deepseek`
