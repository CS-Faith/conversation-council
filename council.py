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
# 路径配置 + 版本自动检测
# ============================================================
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
SKILL_DIR = SCRIPT_DIR
CONFIG_FILE = os.path.join(SKILL_DIR, "council_config.json")
CACHE_DIR = os.path.join(SKILL_DIR, "cache")
os.makedirs(CACHE_DIR, exist_ok=True)


def _get_reasonix_home() -> str:
    """获取 Reasonix 数据根目录（兼容 v0.53 和 1.X）"""
    # 1.X: REASONIX_HOME 环境变量
    rx_home = os.environ.get("REASONIX_HOME", "").strip()
    if rx_home:
        return rx_home
    # 1.X Windows: %APPDATA%/reasonix
    appdata = os.environ.get("APPDATA", "").strip()
    if appdata:
        path = os.path.join(appdata, "reasonix")
        if os.path.isdir(path):
            return path
    # 1.X macOS/Linux: ~/.reasonix
    home = os.path.expanduser("~")
    path = os.path.join(home, ".reasonix")
    if os.path.isdir(path):
        return path
    # v0.53: {script_dir}/../../  (skill dir 在 .reasonix/skills/ 下)
    legacy = os.path.dirname(os.path.dirname(SKILL_DIR))
    if os.path.isdir(os.path.join(legacy, "sessions")):
        return legacy
    return ""


def _detect_sessions_dir() -> str:
    """自动检测 sessions 目录"""
    home = _get_reasonix_home()
    if home:
        path = os.path.join(home, "sessions")
        if os.path.isdir(path):
            return path
    # 最后兜底：v0.53 相对路径
    fallback = os.path.join(os.path.dirname(os.path.dirname(SKILL_DIR)), "sessions")
    return fallback if os.path.isdir(fallback) else ""


# 格式检测结果
_FORMAT = None        # "v053" 或 "v1x"
_META_EXT = None      # ".meta.json" 或 ".meta"
_JSONL_EXTS = None    # [".jsonl"] 或 [".events.jsonl", ".jsonl"]


def _detect_format(sessions_dir: str):
    """检测会话存储格式：v053 用 .meta.json + .jsonl，1.X 用 .meta + .events.jsonl/.jsonl"""
    global _FORMAT, _META_EXT, _JSONL_EXTS
    if _FORMAT is not None:
        return
    # 先看有没有 1.X 的 .meta 文件（无 .json 后缀）
    meta_files = glob.glob(os.path.join(sessions_dir, "*.meta"))
    # 排除 .meta.json（那是 v0.53 的）
    v1x_meta = [f for f in meta_files if not f.endswith(".meta.json")]
    if v1x_meta:
        _FORMAT = "v1x"
        _META_EXT = ".meta"
        _JSONL_EXTS = [".events.jsonl", ".jsonl"]
        return
    # 再看 v0.53 的 .meta.json
    if glob.glob(os.path.join(sessions_dir, "*.meta.json")):
        _FORMAT = "v053"
        _META_EXT = ".meta.json"
        _JSONL_EXTS = [".jsonl"]
        return
    # 都没找到：再试一次宽松匹配（可能目录刚初始化）
    if glob.glob(os.path.join(sessions_dir, "*.jsonl")):
        _FORMAT = "v053"
        _META_EXT = ".meta.json"
        _JSONL_EXTS = [".jsonl"]
        return
    # 默认假设 v0.53
    _FORMAT = "v053"
    _META_EXT = ".meta.json"
    _JSONL_EXTS = [".jsonl"]


# ============================================================
# Codex 检测
# ============================================================
_CODEX_HOME = None
_CODEX_AVAILABLE = False


def _get_codex_home() -> str:
    """获取 Codex 数据根目录（兼容 PortaKit 环境变量劫持）"""
    # 尝试多个可能的用户目录
    candidates = []
    # 1. 真实 Windows 用户目录
    system_drive = os.environ.get("SystemDrive", "C:")
    for username in ["chenshen", os.environ.get("USERNAME", "")]:
        if username:
            candidates.append(os.path.join(system_drive + os.sep, "Users", username, ".codex"))
    # 2. expanduser（可能被 PortaKit 劫持）
    candidates.append(os.path.join(os.path.expanduser("~"), ".codex"))
    # 3. LOCALAPPDATA
    local_appdata = os.environ.get("LOCALAPPDATA", "")
    if local_appdata:
        candidates.append(os.path.join(os.path.dirname(local_appdata), ".codex"))
    # 4. 用 USERNAME 环境变量兜底
    username = os.environ.get("USERNAME", "")
    if username:
        candidates.append(os.path.join(system_drive + os.sep, "Users", username, ".codex"))

    for codex in candidates:
        if os.path.isdir(codex) and os.path.isfile(os.path.join(codex, "session_index.jsonl")):
            return codex
    return ""


def _detect_codex() -> bool:
    """检测 Codex 会话是否可用"""
    global _CODEX_HOME, _CODEX_AVAILABLE
    _CODEX_HOME = _get_codex_home()
    if _CODEX_HOME:
        idx = os.path.join(_CODEX_HOME, "session_index.jsonl")
        _CODEX_AVAILABLE = os.path.isfile(idx)
    return _CODEX_AVAILABLE


# 初始化
SESSIONS_DIR = _detect_sessions_dir()
if SESSIONS_DIR:
    _detect_format(SESSIONS_DIR)
else:
    _FORMAT = "v053"
    _META_EXT = ".meta.json"
    _JSONL_EXTS = [".jsonl"]

# Codex 检测（独立于 Reasonix）
_detect_codex()


def _session_id_from_filename(filename: str) -> str:
    """从文件名提取 session ID（去掉扩展名）。兼容 v0.53 和 1.X 命名。"""
    # v0.53: desktop-YYYYMMDDHHMM-N.jsonl → desktop-YYYYMMDDHHMM-N
    # 1.X:   YYYYMMDD-HHMMSS-model.jsonl → YYYYMMDD-HHMMSS-model
    #        或 desktop-YYYYMMDDHHMM-NNNNNN.events.jsonl
    for ext in _JSONL_EXTS:
        if filename.endswith(ext):
            return filename[:-len(ext)]
    # 兜底：去掉最后一个 . 之后的部分
    if "." in filename:
        return filename.rsplit(".", 1)[0]
    return filename


def _date_from_session_id(session_id: str) -> str:
    """从 session ID 提取日期字符串 YYYYMMDD"""
    # v0.53: desktop-20260630... → 提取 20260630
    # 1.X:   20260630-123456-deepseek-chat → 提取 20260630
    # 通用策略：找第一个 8 位连续数字
    match = re.search(r'(\d{8})', session_id)
    return match.group(1) if match else session_id[:8]


def _find_jsonl_for_session(session_id: str) -> str:
    """根据 session ID 查找对应的 JSONL 文件路径"""
    for ext in _JSONL_EXTS:
        path = os.path.join(SESSIONS_DIR, f"{session_id}{ext}")
        if os.path.isfile(path):
            return path
    return ""


# ============================================================
# Codex 会话扫描
# ============================================================

def _scan_codex_sessions() -> list[dict]:
    """扫描 Codex 会话（session_index.jsonl + sessions/ + archived_sessions/）"""
    if not _CODEX_AVAILABLE:
        return []

    sessions = []
    seen = set()

    # 读索引
    index = {}
    idx_path = os.path.join(_CODEX_HOME, "session_index.jsonl")
    try:
        for line in open(idx_path, "r", encoding="utf-8", errors="ignore"):
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
                index[obj["id"]] = obj
            except json.JSONDecodeError:
                continue
    except OSError:
        pass

    # 扫描活跃会话（sessions/YYYY/MM/DD/）
    sessions_dir = os.path.join(_CODEX_HOME, "sessions")
    if os.path.isdir(sessions_dir):
        for jsonl_path in glob.glob(os.path.join(sessions_dir, "**", "rollout-*.jsonl"), recursive=True):
            basename = os.path.basename(jsonl_path)
            if "_backup" in jsonl_path or "_backup" in basename:
                continue

            # 从文件名提取 UUID（时间戳5段 + UUID 5段 = 至少10段）
            raw = basename.replace("rollout-", "").replace(".jsonl", "")
            parts = raw.split("-")
            uuid = "-".join(parts[5:]) if len(parts) >= 10 else raw

            if uuid in seen:
                continue
            seen.add(uuid)

            idx_entry = index.get(uuid, {})
            thread_name = idx_entry.get("thread_name", "")
            updated_at = idx_entry.get("updated_at", "")

            # 提取日期（从文件名或索引）
            date_str = ""
            if updated_at:
                date_str = updated_at[:10].replace("-", "")
            elif len(parts) >= 3:
                date_str = parts[0] + parts[1] + parts[2][:2]  # YYYY + MM + DD
            else:
                date_str = basename[:8]

            size = os.path.getsize(jsonl_path)
            turns = 0
            try:
                line_count = sum(1 for _ in open(jsonl_path, "r", encoding="utf-8", errors="ignore"))
                # 估算轮数：user_message 出现次数
                for l in open(jsonl_path, "r", encoding="utf-8", errors="ignore"):
                    if '"user_message"' in l:
                        turns += 1
            except (OSError, UnicodeDecodeError):
                line_count = 0

            sessions.append({
                "id": uuid,
                "file": basename,
                "date": date_str,
                "summary_hint": thread_name,
                "total_cost_usd": 0,
                "turns": turns,
                "size_kb": size // 1024,
                "lines": line_count,
                "format": "codex",
                "source": "codex"
            })

    # 扫描归档会话（扁平目录）
    archived_dir = os.path.join(_CODEX_HOME, "archived_sessions")
    if os.path.isdir(archived_dir):
        for jsonl_path in glob.glob(os.path.join(archived_dir, "rollout-*.jsonl")):
            basename = os.path.basename(jsonl_path)
            raw = basename.replace("rollout-", "").replace(".jsonl", "")
            parts = raw.split("-")
            uuid = "-".join(parts[5:]) if len(parts) >= 10 else raw

            if uuid in seen:
                continue
            seen.add(uuid)

            idx_entry = index.get(uuid, {})
            thread_name = idx_entry.get("thread_name", "[Archived] " + basename[:40])

            date_str = ""
            if len(parts) >= 3:
                date_str = parts[0] + parts[1] + parts[2][:2]
            else:
                date_str = basename[:8]

            size = os.path.getsize(jsonl_path)
            line_count = 0
            try:
                line_count = sum(1 for _ in open(jsonl_path, "r", encoding="utf-8", errors="ignore"))
            except OSError:
                pass

            sessions.append({
                "id": uuid,
                "file": "archived/" + basename,
                "date": date_str,
                "summary_hint": thread_name,
                "total_cost_usd": 0,
                "turns": 0,
                "size_kb": size // 1024,
                "lines": line_count,
                "format": "codex",
                "source": "codex",
                "archived": True
            })

    return sessions


def _find_codex_jsonl(session_id: str) -> str:
    """根据 Codex UUID 查找 JSONL 文件路径"""
    if not _CODEX_AVAILABLE:
        return ""
    # 先搜活跃目录
    sessions_dir = os.path.join(_CODEX_HOME, "sessions")
    if os.path.isdir(sessions_dir):
        for jsonl in glob.glob(os.path.join(sessions_dir, "**", "*.jsonl"), recursive=True):
            if session_id in jsonl and "_backup" not in jsonl:
                return jsonl
    # 再搜归档
    archived_dir = os.path.join(_CODEX_HOME, "archived_sessions")
    if os.path.isdir(archived_dir):
        for jsonl in glob.glob(os.path.join(archived_dir, "*.jsonl")):
            if session_id in jsonl:
                return jsonl
    return ""


def _read_codex_messages(session_id: str, max_messages: int = 200) -> list[dict]:
    """读取 Codex 会话 JSONL，解包为标准 {role, content} 格式"""
    jsonl_path = _find_codex_jsonl(session_id)
    if not jsonl_path:
        return []

    messages = []
    for line in open(jsonl_path, "r", encoding="utf-8", errors="ignore"):
        line = line.strip()
        if not line:
            continue
        try:
            obj = json.loads(line)
        except json.JSONDecodeError:
            continue

        # Codex 消息格式：顶层 type + payload
        outer_type = obj.get("type", "")
        payload = obj.get("payload", {})
        inner_type = payload.get("type", "")

        role = None
        content = ""

        if outer_type == "session_meta":
            continue  # 跳过元数据行

        if inner_type == "user_message":
            role = "user"
            # 内容可能在 message.content 或 content 字段
            msg = payload.get("message", {})
            if isinstance(msg, dict):
                content = msg.get("content", "")
            else:
                content = payload.get("content", str(msg))

        elif inner_type == "agent_message":
            role = "assistant"
            content = payload.get("content", payload.get("text", ""))

        elif inner_type == "agent_reasoning":
            role = "assistant"
            content = payload.get("content", payload.get("text", ""))
            # 标注为推理内容
            if content:
                content = f"[思考] {content}"

        elif inner_type in ("function_call", "custom_tool_call", "tool_search_call"):
            role = "assistant"
            fn_name = payload.get("name", payload.get("function_name", "?"))
            content = f"[调用工具: {fn_name}]"

        elif inner_type in ("function_call_output", "custom_tool_call_output", "tool_search_output"):
            role = "tool"
            output = payload.get("output", payload.get("content", ""))
            if isinstance(output, str):
                content = output[:300]
            elif isinstance(output, list):
                content = str(output)[:300]
            else:
                content = str(output)[:300]

        elif inner_type in ("task_started", "task_complete", "token_count",
                            "web_search_call", "web_search_end", "mcp_tool_call_end",
                            "patch_apply_end", "turn_aborted"):
            continue  # 跳过事件/元数据

        elif outer_type in ("event_msg", "turn_context", "response_item"):
            continue  # 跳过框架事件

        else:
            # 未知类型，尝试提取文本
            role = "assistant" if inner_type else "?" 
            content = payload.get("content", payload.get("text", ""))[:300]

        if role and content:
            messages.append({"role": role, "content": content[:500]})

    if len(messages) > max_messages:
        messages = messages[-max_messages:]

    return messages


def _read_meta(session_id: str) -> dict:
    """读取会话元数据（兼容 v0.53 .meta.json 和 1.X .meta）"""
    # 1.X 格式：.meta（BranchMeta JSON）
    if _FORMAT == "v1x":
        meta_path = os.path.join(SESSIONS_DIR, f"{session_id}.meta")
        if os.path.isfile(meta_path):
            try:
                with open(meta_path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except (json.JSONDecodeError, UnicodeDecodeError):
                pass
        # 也尝试 .meta.json（迁移后可能共存）
        meta_path2 = os.path.join(SESSIONS_DIR, f"{session_id}.meta.json")
        if os.path.isfile(meta_path2):
            try:
                with open(meta_path2, "r", encoding="utf-8") as f:
                    return json.load(f)
            except (json.JSONDecodeError, UnicodeDecodeError):
                pass
        return {}

    # v0.53 格式：.meta.json
    meta_path = os.path.join(SESSIONS_DIR, f"{session_id}.meta.json")
    if os.path.isfile(meta_path):
        try:
            with open(meta_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, UnicodeDecodeError):
            pass
    return {}

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
    """扫描所有可用来源的会话（Reasonix + Codex），按日期倒序。"""
    sessions = []
    seen = set()

    # --- Reasonix 会话 ---
    if SESSIONS_DIR:
        for ext in _JSONL_EXTS:
            for jsonl_path in glob.glob(os.path.join(SESSIONS_DIR, f"*{ext}")):
                basename = os.path.basename(jsonl_path)
                if "冲突" in basename or ".bak" in basename:
                    continue

                session_id = _session_id_from_filename(basename)
                if session_id in seen:
                    continue
                seen.add(session_id)

                meta = _read_meta(session_id)
                date_str = _date_from_session_id(session_id)
                size = os.path.getsize(jsonl_path)
                try:
                    line_count = sum(1 for _ in open(jsonl_path, "r", encoding="utf-8", errors="ignore"))
                except (OSError, UnicodeDecodeError):
                    line_count = 0

                summary_hint = ""
                if _FORMAT == "v1x":
                    summary_hint = meta.get("Preview", "")
                else:
                    summary_hint = meta.get("summary", "")

                total_cost_usd = meta.get("totalCostUsd", 0)
                turns = meta.get("Turns", line_count // 2)

                sessions.append({
                    "id": session_id,
                    "file": basename,
                    "date": date_str,
                    "summary_hint": summary_hint,
                    "total_cost_usd": total_cost_usd,
                    "turns": turns,
                    "size_kb": size // 1024,
                    "lines": line_count,
                    "format": _FORMAT,
                    "source": "reasonix"
                })

    # --- Codex 会话 ---
    if _CODEX_AVAILABLE:
        codex_sessions = _scan_codex_sessions()
        for cs in codex_sessions:
            if cs["id"] not in seen:
                seen.add(cs["id"])
                sessions.append(cs)

    sessions.sort(key=lambda s: s["date"], reverse=True)

    if recent:
        sessions = sessions[:recent]

    return sessions


def read_session_messages(session_file: str, max_messages: int = 200) -> list[dict]:
    """读取会话的 JSONL 文件，返回最近的消息列表。
    session_file 可以是文件名、完整路径或 Codex UUID。"""
    # 先尝试 Codex（UUID 格式）
    if _CODEX_AVAILABLE and len(session_file) > 30 and "-" in session_file:
        codex_msgs = _read_codex_messages(session_file, max_messages)
        if codex_msgs:
            return codex_msgs

    # Reasonix 路径查找
    if os.path.isabs(session_file):
        jsonl_path = session_file
    else:
        found = _find_jsonl_for_session(session_file.replace(".jsonl", "").replace(".events.jsonl", ""))
        if found:
            jsonl_path = found
        else:
            jsonl_path = os.path.join(SESSIONS_DIR, session_file) if SESSIONS_DIR else ""

    if not jsonl_path or not os.path.isfile(jsonl_path):
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

    # Find the session file for cache validation
    jsonl_path = _find_jsonl_for_session(session_id)

    # Check cache
    if not force and os.path.exists(cache_path):
        try:
            with open(cache_path, "r", encoding="utf-8") as f:
                cached = json.load(f)
            if jsonl_path and os.path.exists(jsonl_path):
                mtime = os.path.getmtime(jsonl_path)
                if cached.get("_cached_mtime", 0) >= mtime:
                    return cached
        except:
            pass

    # Read session messages
    messages = read_session_messages(session_id)

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
    jsonl_path = _find_jsonl_for_session(session_id)
    if jsonl_path and os.path.exists(jsonl_path):
        summary["_cached_mtime"] = os.path.getmtime(jsonl_path)
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
            "session_file": f"{sid}{_JSONL_EXTS[0]}",
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
        "session_file": f"{session_id}{_JSONL_EXTS[0]}",
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
