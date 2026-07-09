# Conversation Council - 多视角 AI 讨论

> 会顶嘴的聊天记录：历史AI会话，用第一人称当场回答你。
> Conversation Council 把这些散落的答案变成一场「AI 圆桌」，让历史会话用**第一人称**开口说话——无需翻阅历史，直接获得一场由过去的自己（AI）主持的专家圆桌会。

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Reasonix](https://img.shields.io/badge/Reasonix-Ecosystem-58a6ff)](https://github.com/CS-Faith/reasonix-ecosystem)

---

## 一句话定位

| 输入 | 输出 |
|------|------|
| 你的 AI 会话历史（Reasonix / Codex / Claude） | 多位「AI 议员」从各自角度回答当前问题 |

---

## 30 秒体验

在 Reasonix 或支持 Skill 的 AI 环境中：

```
/skill conversation-council
# → 自动扫描历史会话 → 匹配相关议题 → 生成多视角讨论

/skill conversation-council "要不要把知识库从 Notion 迁到 Obsidian？"
# → 多位议员各抒己见，群聊格式输出
```

---

## 为什么不是「自己翻聊天记录」？

- 数百个会话，每条平均数百行——你不可能全部记得
- 跨会话的信息是**隐性连接**：Session 37 的决策会影响 Session 283 的结果
- Council 帮你完成匹配、提取、生成，不需要你记住全部历史

---

## 架构

```
Reasonix 会话文件 (.jsonl)
  → 会话扫描器 → 摘要提取器
  → 议会配置 → 匹配引擎
  → 发言人生成器 → 群聊格式输出
```

---

## CLI 命令

- `council.py scan --recent 20` — 列出最近会话
- `council.py init --sessions "id1,id2"` — 选择议员
- `council.py speak "问题"` — 运行讨论
- `council.py manage --list/--add/--remove` — 管理成员
- `council.py extract --force` — 刷新所有摘要

---

## 效率对比

| 方式 | 效果 |
|------|------|
| 翻 5 个历史会话找答案 | ~15 分钟，可能遗漏 |
| 反复问同一个 AI | 得到相似答案（回声室） |
| **Council 多视角讨论** | **~30 秒，多个角度碰撞** |

---

## 兼容性

支持 Reasonix v0.53 / v1.X (Go 重写) / Codex — 自动检测格式，无需手动配置。

---

## Next Step

讨论结束后想沉淀成知识文章 → [**Conversation Distiller**](https://github.com/CS-Faith/conversation-distiller)

讨论前想先清理知识库重复 → [**knowledge-cleanup**](https://github.com/CS-Faith/knowledge-cleanup)

跨设备便携你的议员和数据 → [**Portakit**](https://github.com/CS-Faith/reasonix-portakit)

---

## License
MIT © 2026 [CS-Faith](https://cs-faith.github.io)

<details>
<summary>English Version</summary>

**Conversation Council** — Chat logs that talk back. Your past AI sessions answer you — in the first person.

You have asked ChatGPT the same question three times across different sessions — and forgotten each answer. Council brings those answers back as a multi-perspective discussion.

### Key Features
- Automatic session scanning and summary extraction
- Relevance matching across your entire conversation history
- First-person responses from historical "council members"
- Group-chat format output

### Compatibility
Reasonix v0.53 / v1.X (Go) / Codex — automatic format detection.
</details>