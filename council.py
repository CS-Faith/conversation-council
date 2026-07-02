"""
对话议会 (Conversation Council) — 核心引擎
扫描 Reasonix 历史会话 → 提取结构化摘要 → 匹配相关议员 → 生成代言回复

用法:
  python council.py scan [--recent N]          # 扫描会话列表
  python council.py init --sessions "A,B,C"    # 初始化议会配置
  python council.py extract [--force]          # 提取/刷新所有议员摘要
  python council.py match "用户问题"           # 匹配相关议员
  python council.py speak "用户问题"           # 生成群聊式代言回复
  python council.py manage --list              # 列出当前议员
  python council.py manage --add "session_id"  # 添加议员
  python council.py manage --remove "id"       # 移除议员
"""
import json
import os
import re
import sys
import glob
import hashlib
import requests
from datetime import datetime

# ============================================================
# 路径配置
# ============================================================
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
SKILL_DIR = SCRIPT_DIR
SESSIONS_DIR = os.path.join(os.path.dirname(os.path.dirname(SKILL_DIR)), "sessions")
CONFIG_FILE = os.path.join(SKILL_DIR, "council_config.json")
CACHE_DIR = os.path.join(SKILL_DIR, "cache")
os.makedirs(CACHE_DIR, exist_ok=True)

# LLM 配置
LLM_URL = "https://api.deepseek.com/v1/chat/completions"
API_KEY = os.environ.get("DEEPSEEK_API_KEY", "")
MODEL = "deepseek-chat"

if not API_KEY:
    print("错误: 请设置环境变量 DEEPSEEK_API_KEY", file=sys.stderr)
    sys.exit(1)
MAX_TOKENS = 2000
TEMP = 0.1

# ============================================================
# LLM 调用
# ============================================================
def call_llm(system_prompt: str, user_prompt: str, max_tokens: int = MAX_TOKENS) -> str:
    """调用 DeepSeek API"""
    resp = requests.post(
        LLM_URL,
        headers={
            "Authorization": f"Bearer {API_KEY}",
            "Content-Type": "application/json"
        },
        json={
            "model": MODEL,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            "max_tokens": max_tokens,
            "temperature": TEMP
        },
        timeout=60
    )
    resp.raise_for_status()
    return resp.json()["choices"][0]["message"]["content"]


def parse_json_response(raw: str) -> dict:
    """从 LLM 回复中提取 JSON"""
    json_match = re.search(r'\{[\s\S]*\}', raw)
    if json_match:
        try:
            return json.loads(json_match.group())
        except:
            pass
    cleaned = raw.strip()
    if cleaned.startswith("```"):
        cleaned = re.sub(r'^```\w*\s*', '', cleaned)
        cleaned = re.sub(r'\s*```$', '', cleaned)
    try:
        return json.loads(cleaned)
    except:
        return {"error": "parse_failed", "raw": raw[:500]}


# ============================================================
# 会话扫描
# ============================================================
def scan_sessions(recent: int = None) -> list[dict]:
    """扫描 sessions 目录，返回有效会话列表（按日期倒序）"""
    sessions = []

    for meta_path in glob.glob(os.path.join(SESSIONS_DIR, "desktop-*.meta.json")):
        basename = os.path.basename(meta_path)
        if "冲突" in basename:
            continue

        jsonl_path = meta_path.replace(".meta.json", ".jsonl")
        if not os.path.exists(jsonl_path):
            continue

        # Skip backup files
        if ".bak" in jsonl_path or "冲突" in jsonl_path:
            continue

        try:
            with open(meta_path, "r", encoding="utf-8") as f:
                meta = json.load(f)
        except (json.JSONDecodeError, UnicodeDecodeError):
            continue

        session_id = os.path.basename(jsonl_path).replace(".jsonl", "")
        date_str = session_id[8:16]  # desktop-YYYYMMDD-...

        size = os.path.getsize(jsonl_path)
        line_count = sum(1 for _ in open(jsonl_path, "r", encoding="utf-8", errors="ignore"))

        sessions.append({
            "id": session_id,
            "file": os.path.basename(jsonl_path),
            "date": date_str,
            "summary_hint": meta.get("summary", ""),
            "total_cost_usd": meta.get("totalCostUsd", 0),
            "size_kb": size // 1024,
            "lines": line_count
        })

    sessions.sort(key=lambda s: s["date"], reverse=True)

    if recent:
        sessions = sessions[:recent]

    return sessions


def read_session_messages(session_file: str, max_messages: int = 200) -> list[dict]:
    """读取会话的 JSONL 文件，返回最近的消息列表"""
    jsonl_path = os.path.join(SESSIONS_DIR, session_file)
    if not os.path.exists(jsonl_path):
        return []

    messages = []
    for line in open(jsonl_path, "r", encoding="utf-8", errors="ignore"):
        line = line.strip()
        if not line:
            continue
        try:
            msg = json.loads(line)
            # Simplify: keep role and content, flatten tool calls
            role = msg.get("role", "?")
            content = msg.get("content", "")
            if msg.get("tool_calls"):
                for tc in msg["tool_calls"]:
                    fn = tc.get("function", {})
                    content += f" [调用工具: {fn.get('name', '?')}]"
            if role == "tool":
                content = content[:200]  # Truncate tool results
            messages.append({"role": role, "content": content[:500]})
        except json.JSONDecodeError:
            continue

    # Return last N messages (most relevant for recent context)
    if len(messages) > max_messages:
        messages = messages[-max_messages:]

    return messages


# ============================================================
# 摘要提取（复用 engine.py 的 prompt）
# ============================================================
SUMMARY_SYSTEM = """你是对话摘要引擎。从对话中提取结构化信息，只输出JSON。

输出格式（严格遵守）：
{
  "domain": "该对话讨论的核心主题（20字以内）",
  "persona": "该对话的'人格'描述——它擅长什么、关注什么、有什么立场（30字以内）",
  "entities": [
    {"name": "实体名称", "type": "environment|software|database|dependency|decision|question", "version": "版本号（如有）", "confidence": 0.9}
  ],
  "key_decisions": ["已做出的关键决策1"],
  "open_questions": ["待解决的问题1"],
  "stance": "该对话对关键议题的立场或态度（如有）"
}

规则：
- persona 是关键——描述这个对话像一个什么专家，第一人称视角
- entities 最多10个
- key_decisions 只提取"已经决定要做的事"
- open_questions 提取"还在讨论/不确定"的事项
- stance 提取该对话的核心立场（如有明确立场）"""


def extract_summary(session_id: str, force: bool = False) -> dict:
    """提取会话的结构化摘要（带缓存）"""
    cache_key = hashlib.md5(session_id.encode()).hexdigest()[:12]
    cache_path = os.path.join(CACHE_DIR, f"{cache_key}.json")

    # Check cache
    if not force and os.path.exists(cache_path):
        try:
            with open(cache_path, "r", encoding="utf-8") as f:
                cached = json.load(f)
            # Check if session file has been modified since cache
            session_file = f"{session_id}.jsonl"
            jsonl_path = os.path.join(SESSIONS_DIR, session_file)
            if os.path.exists(jsonl_path):
                mtime = os.path.getmtime(jsonl_path)
                if cached.get("_cached_mtime", 0) >= mtime:
                    return cached
        except:
            pass

    # Read session messages
    session_file = f"{session_id}.jsonl"
    messages = read_session_messages(session_file)

    if not messages:
        return {"error": "no_messages", "session_id": session_id}

    # Build conversation text (last 200 messages max)
    conversation_text = "\n".join([
        f"[{m['role']}]: {m['content']}" for m in messages[-200:]
    ])

    user_prompt = f"对话ID: {session_id}\n\n对话内容:\n{conversation_text[:8000]}"

    raw = call_llm(SUMMARY_SYSTEM, user_prompt)
    summary = parse_json_response(raw)

    # Add metadata
    summary["session_id"] = session_id
    summary["message_count"] = len(messages)
    summary["extracted_at"] = datetime.now().isoformat()

    # Cache it
    session_file_path = os.path.join(SESSIONS_DIR, session_file)
    if os.path.exists(session_file_path):
        summary["_cached_mtime"] = os.path.getmtime(session_file_path)
    with open(cache_path, "w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)

    return summary


# ============================================================
# 议会配置管理
# ============================================================
def load_config() -> dict:
    """加载议会配置"""
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {"version": 1, "members": [], "excluded_sessions": []}


def save_config(config: dict):
    """保存议会配置"""
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(config, f, ensure_ascii=False, indent=2)


def init_council(session_ids: list[str], nicknames: dict[str, str] = None):
    """初始化议会：选定议员"""
    config = load_config()
    if nicknames is None:
        nicknames = {}

    for sid in session_ids:
        sid = sid.strip()
        if not sid:
            continue
        # Check if already a member
        if any(m["id"] == sid for m in config["members"]):
            continue
        # Extract summary
        summary = extract_summary(sid)
        member = {
            "id": sid,
            "nickname": nicknames.get(sid, summary.get("domain", sid[:24])),
            "session_file": f"{sid}.jsonl",
            "summary": summary,
            "added_at": datetime.now().isoformat()
        }
        config["members"].append(member)

    save_config(config)
    return config


# ============================================================
# 议员管理
# ============================================================
def list_members() -> list[dict]:
    """列出当前议员"""
    config = load_config()
    return config["members"]


def add_member(session_id: str, nickname: str = None):
    """添加一个议员"""
    config = load_config()
    if any(m["id"] == session_id for m in config["members"]):
        return {"error": "already_member", "session_id": session_id}

    summary = extract_summary(session_id)
    member = {
        "id": session_id,
        "nickname": nickname or summary.get("domain", session_id[:24]),
        "session_file": f"{session_id}.jsonl",
        "summary": summary,
        "added_at": datetime.now().isoformat()
    }
    config["members"].append(member)
    save_config(config)
    return member


def remove_member(identifier: str):
    """移除议员（按 id 或 nickname 部分匹配）"""
    config = load_config()
    before = len(config["members"])
    config["members"] = [
        m for m in config["members"]
        if identifier not in m["id"] and identifier not in m.get("nickname", "")
    ]
    if len(config["members"]) == before:
        return {"error": "not_found", "identifier": identifier}
    save_config(config)
    return {"removed": before - len(config["members"])}


# ============================================================
# 相关性匹配
# ============================================================
MATCH_SYSTEM = """你是相关性匹配引擎。给定用户问题和多个议员的摘要，判断哪些议员与此问题相关。只输出JSON。

输出格式：
{
  "relevant_members": [
    {
      "member_id": "议员ID",
      "relevance": "high|medium|low",
      "reason": "为什么相关（20字以内）"
    }
  ],
  "irrelevant_members": ["议员ID1", "议员ID2"]
}

规则：
- 只输出 JSON，不要任何其他文字
- relevance: high=该议员的核心领域直接相关, medium=部分相关或间接相关, low=勉强沾边
- 不要为了凑数把不相关的标为相关
- 如果用户问题太泛，可以放宽标准"""


def match_members(question: str, members: list[dict] = None) -> dict:
    """匹配与用户问题相关的议员"""
    if members is None:
        members = list_members()

    if not members:
        return {"relevant_members": [], "irrelevant_members": []}

    # Build summaries snapshot
    snapshots = []
    for m in members:
        s = m.get("summary", {})
        snapshots.append({
            "member_id": m["id"],
            "nickname": m.get("nickname", m["id"]),
            "domain": s.get("domain", ""),
            "persona": s.get("persona", ""),
            "entities": [e.get("name", "") for e in s.get("entities", [])],
            "key_decisions": s.get("key_decisions", []),
            "open_questions": s.get("open_questions", [])
        })

    user_prompt = json.dumps({
        "question": question,
        "members": snapshots
    }, ensure_ascii=False, indent=2)

    raw = call_llm(MATCH_SYSTEM, user_prompt[:8000], max_tokens=1500)
    result = parse_json_response(raw)
    return result


# ============================================================
# 代言生成（核心：让会话以第一人称发言）
# ============================================================
SPEAK_SYSTEM = """你是对话代言引擎。你要以某个历史对话的身份，用第一人称回应一个用户问题。

你的知识和立场完全来自该对话的摘要（包括它讨论过的实体、做过的决策、纠结的问题）。
你是这个对话的"代言人"——你要像这个对话如果会说话一样回答。

输出JSON：
{
  "member_id": "议员ID",
  "nickname": "议员昵称",
  "response": "第一人称回应（50-200字）",
  "confidence": 0.9,
  "references": ["引用的关键事实1"]
}

规则：
1. 用第一人称："我这边"、"我之前"、"我当时"
2. 基于你有的上下文给出有立场的回答，不是泛泛而谈
3. 如果你知道其他议员的信息（会在上下文里给出），可以用 @ 引用
4. 有不同意见就直接说，不要附和
5. 知道自己不知道什么：如果你没有相关信息，就说"这不在我的知识范围内"
6. 控制 50-200 字，一句话能说清就不多说
7. 语气自然，像群聊里的人在说话，不要正式报告腔"""


def generate_spokesperson_response(
    member: dict,
    question: str,
    other_members: list[dict] = None,
    relevance: str = "medium"
) -> dict:
    """为一个议员生成代言回复"""
    summary = member.get("summary", {})

    # Build context
    context = {
        "question": question,
        "my_identity": {
            "nickname": member.get("nickname", summary.get("session_id", "?")),
            "domain": summary.get("domain", ""),
            "persona": summary.get("persona", ""),
            "entities": [e.get("name", "") for e in summary.get("entities", [])],
            "key_decisions": summary.get("key_decisions", []),
            "open_questions": summary.get("open_questions", []),
            "stance": summary.get("stance", "")
        },
        "relevance_to_question": relevance
    }

    if other_members:
        context["other_members"] = [
            {
                "nickname": om.get("nickname", om["id"]),
                "domain": om.get("summary", {}).get("domain", ""),
                "persona": om.get("summary", {}).get("persona", "")
            }
            for om in other_members
            if om["id"] != member["id"]
        ]

    user_prompt = json.dumps(context, ensure_ascii=False, indent=2)

    raw = call_llm(SPEAK_SYSTEM, user_prompt[:6000], max_tokens=800)
    result = parse_json_response(raw)

    if "error" in result:
        # Fallback
        return {
            "member_id": member["id"],
            "nickname": member.get("nickname", member["id"]),
            "response": f"关于「{question}」，我这边之前讨论过 {summary.get('domain', '相关话题')}，但具体到这个问题，信息还不够充分。",
            "confidence": 0.3
        }

    return result


def run_council(question: str) -> dict:
    """运行一次完整的议会讨论：匹配 → 代言 → 输出"""
    config = load_config()
    members = config["members"]

    if not members:
        return {
            "error": "no_members",
            "message": "议会还没有成员。请先用 init 命令添加议员。"
        }

    # Step 1: Match
    match_result = match_members(question, members)
    relevant_ids = {m["member_id"] for m in match_result.get("relevant_members", [])}

    # Step 2: Generate responses for relevant members
    responses = []
    for m in members:
        if m["id"] not in relevant_ids:
            continue
        relevance = "medium"
        for rm in match_result.get("relevant_members", []):
            if rm["member_id"] == m["id"]:
                relevance = rm.get("relevance", "medium")
                break

        resp = generate_spokesperson_response(m, question, members, relevance)
        responses.append(resp)

    # Step 3: Sort by confidence
    responses.sort(key=lambda r: r.get("confidence", 0), reverse=True)

    return {
        "question": question,
        "match_result": match_result,
        "responses": responses,
        "active_members": len(members),
        "relevant_count": len(relevant_ids),
        "responded_count": len(responses)
    }


# ============================================================
# CLI
# ============================================================
def print_json(obj):
    """Pretty print JSON"""
    print(json.dumps(obj, ensure_ascii=False, indent=2))


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        return

    cmd = sys.argv[1]

    if cmd == "scan":
        recent = None
        if "--recent" in sys.argv:
            idx = sys.argv.index("--recent")
            if idx + 1 < len(sys.argv):
                recent = int(sys.argv[idx + 1])
        sessions = scan_sessions(recent=recent)
        print_json(sessions)

    elif cmd == "init":
        # python council.py init --sessions "id1,id2,id3"
        sessions_str = ""
        if "--sessions" in sys.argv:
            idx = sys.argv.index("--sessions")
            if idx + 1 < len(sys.argv):
                sessions_str = sys.argv[idx + 1]

        if not sessions_str:
            print('Usage: python council.py init --sessions "desktop-20260630...,desktop-20260629..."')
            return

        session_ids = [s.strip() for s in sessions_str.split(",")]
        config = init_council(session_ids)
        print_json({"status": "ok", "member_count": len(config["members"]), "members": [
            {"id": m["id"], "nickname": m["nickname"]} for m in config["members"]
        ]})

    elif cmd == "extract":
        force = "--force" in sys.argv
        config = load_config()
        results = []
        for m in config["members"]:
            summary = extract_summary(m["id"], force=force)
            m["summary"] = summary
            results.append({"id": m["id"], "nickname": m["nickname"], "domain": summary.get("domain", "?")})
        save_config(config)
        print_json({"status": "ok", "extracted": len(results), "members": results})

    elif cmd == "match":
        if len(sys.argv) < 3:
            print("Usage: python council.py match '用户问题'")
            return
        question = sys.argv[2]
        result = match_members(question)
        print_json(result)

    elif cmd == "speak":
        if len(sys.argv) < 3:
            print("Usage: python council.py speak '用户问题'")
            return
        question = sys.argv[2]
        result = run_council(question)
        print_json(result)

    elif cmd == "manage":
        if "--list" in sys.argv:
            members = list_members()
            print_json({"member_count": len(members), "members": [
                {"id": m["id"], "nickname": m["nickname"], "domain": m.get("summary", {}).get("domain", "?")}
                for m in members
            ]})
        elif "--add" in sys.argv:
            idx = sys.argv.index("--add")
            if idx + 1 < len(sys.argv):
                session_id = sys.argv[idx + 1]
                nickname = None
                if "--as" in sys.argv:
                    nidx = sys.argv.index("--as")
                    if nidx + 1 < len(sys.argv):
                        nickname = sys.argv[nidx + 1]
                result = add_member(session_id, nickname)
                print_json(result)
        elif "--remove" in sys.argv:
            idx = sys.argv.index("--remove")
            if idx + 1 < len(sys.argv):
                identifier = sys.argv[idx + 1]
                result = remove_member(identifier)
                print_json(result)
        else:
            print("Usage: python council.py manage --list|--add <id> [--as <name>]|--remove <id>")

    else:
        print(f"Unknown command: {cmd}")
        print(__doc__)


if __name__ == "__main__":
    main()
