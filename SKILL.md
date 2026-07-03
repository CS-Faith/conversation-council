# 对话议会 (Conversation Council)

> 召集 Reasonix 历史会话作为「议员」，在新对话中以群聊形式参与讨论。每个议员以第一人称发言，基于其历史对话中积累的知识和立场。

**兼容版本**: Reasonix v0.53 + v1.X（自动检测会话存储格式）

---

## 触发方式

- `/skill conversation-council` — 启动议会
- 或说「召集议会」「开个群聊会」「让历史对话参与讨论」等

---

## 核心概念

你不是在"查历史记录"。你是在**召集一群专家**——每个专家都是一个历史对话，他们有各自的领域知识、立场、甚至性格。他们会用第一人称（"我这边"、"我之前的经验"）参与讨论。

---

## 协议

### 角色
- **用户**：提出问题的人
- **Reasonix（你）**：议长 / coordinator，负责：
  1. 驱动 council.py 获取议员发言
  2. 以群聊格式呈现结果
  3. 引导讨论、追问、总结
- **议员**：council.py 背后生成的代言回复，非你亲自扮演

### 群聊呈现格式

```
【对话议会·议长】
  开场白：说明召集了多少议员、谁的发言最相关

**【议员昵称 - 领域】**
  第一人称发言内容...

**【另一个议员 - 领域】**
  不同视角的发言，可以有观点碰撞...

【对话议会·议长】
  总结各方观点，追问、建议下一步
```

---

## 工作流程

### Step 1: 首次运行 — 组建议会

用户第一次使用时，需要选定哪些历史会话成为「议员」。

```
python council.py scan --recent 20
```

向用户展示最近 20 个会话，让用户选择。用户可以：
- 按编号选："1,2,4,6"
- 按关键词："所有关于 LLM WIKI 的"
- 按日期："最近一周的全部"
- 自由组合

用户选定后：

```
python council.py init --sessions "id1,id2,id3,..."
```

### Step 2: 日常使用 — 召集讨论

用户在任何新对话中提问后：

```
python council.py speak "用户的问题"
```

拿到 JSON 结果后，按以下规则呈现：

1. **议长开场**：说明召集了多少议员、匹配了几个、最相关的发言者
2. **议员发言**：`**【昵称 - 领域】**` 格式，每个发言一段
3. **议长总结**：提炼共识点、分歧点、建议下一步

### Step 3: 议员管理

```
# 查看当前议员
python council.py manage --list

# 添加新议员（先 scan 找到 session id）
python council.py manage --add "desktop-20260702..." --as "自定义昵称"

# 移除议员
python council.py manage --remove "昵称或id"
```

### Step 4: 刷新摘要

当某个议员对应的历史对话有大量新内容后：

```
python council.py extract --force
```

---

## 发言质量要求

1. **第一人称**："我这边"、"我之前"、"我当时讨论过"
2. **有立场**：不是泛泛而谈，是基于该对话实际讨论过的事实和决策
3. **可以碰撞**：不同议员有不同观点，不要全员附和
4. **知道边界**：如果该议员确实不相关，议长应跳过，不让它强行发言
5. **可以 @ 引用**：一个议员可以引用另一个议员的发言（如果 council.py 返回的上下文里有其他议员信息）

---

## Python 引擎

council.py 路径：`{skill_dir}/council.py`
Python 路径：`{rx_root}/python/python.exe`

完整命令格式：

```
{rx_root}/python/python.exe {skill_dir}/council.py <子命令> [参数]
```

### 子命令速查

| 命令 | 用途 |
|------|------|
| `scan [--recent N]` | 扫描历史会话列表 |
| `init --sessions "id1,id2"` | 初始化议会（选定议员） |
| `extract [--force]` | 刷新所有议员摘要 |
| `speak "问题"` | 运行完整议会讨论 |
| `match "问题"` | 仅匹配相关议员 |
| `manage --list` | 列出当前议员 |
| `manage --add "id" [--as "昵称"]` | 添加议员 |
| `manage --remove "id或昵称"` | 移除议员 |

---

## 成本提示

- 首次组建（10 个议员）：~10,000 tokens（一次性）
- 每次开会讨论：~3,000-5,000 tokens
- 摘要缓存命中后不产生额外提取成本
- DeepSeek 定价约 ¥0.001/1000 tokens，每次开会成本可忽略

---

## 版本兼容

council.py 启动时自动检测 Reasonix 版本和会话存储格式：

| 检测项 | v0.53 | 1.X |
|--------|-------|-----|
| 数据根目录 | `{skill_dir}/../../`（.reasonix） | `%APPDATA%/reasonix/` 或 `$REASONIX_HOME` |
| 会话文件扩展名 | `.jsonl` | `.events.jsonl` 或 `.jsonl` |
| 元数据扩展名 | `.meta.json` | `.meta`（BranchMeta JSON） |
| 摘要来源 | `meta.summary` | `meta.Preview` |
| 日期提取 | 固定偏移 `session_id[8:16]` | 正则匹配 8 位连续数字 |

无需用户手动指定版本——`scan` 命令自动识别目录中的文件格式并采用对应解析策略。

## 失败处理

- council.py 执行失败 → 检查 Python 路径是否正确
- DeepSeek API 超时/报错 → 重试一次，仍失败则告知用户 API 不可用
- 议员数为 0 → 提示用户先运行 scan + init
- JSON 解析失败 → 使用原始文本降级展示
- 会话目录未找到 → 检查 `REASONIX_HOME` 环境变量或 `%APPDATA%/reasonix/sessions/` 是否存在
