# Changelog

## [2.1.0] — 2026-07-03

### Added
- **Codex 适配** — 自动检测并扫描 Codex 会话历史
  - `session_index.jsonl` 索引读取（含 thread_name 映射）
  - `sessions/YYYY/MM/DD/rollout-*.jsonl` 嵌套目录扫描
  - `archived_sessions/*.jsonl` 扁平目录扫描
  - 22 种 Codex 消息 type 映射到标准 `{role, content}` 格式
  - 新增 `source` 字段（`reasonix` / `codex`）区分会话来源
- 新增函数：`_get_codex_home()` / `_detect_codex()` / `_scan_codex_sessions()` / `_read_codex_messages()` / `_find_codex_jsonl()`

### Changed
- `scan_sessions()` 合并 Reasonix + Codex 双源结果，按日期混排
- `read_session_messages()` 自动识别 Codex UUID 格式并路由到对应解析器
- `_get_codex_home()` 兼容 PortaKit 环境变量劫持（多路径探测）

## [2.0.0] — 2026-07-03

### Added
- **Reasonix v1.X (Go 重写版) 支持** — 自动检测会话存储格式
- 自动检测 sessions 目录：`REASONIX_HOME` → `%APPDATA%/reasonix` → `~/.reasonix` → v0.53 相对路径
- 双格式元数据支持：v0.53 `.meta.json` + v1.X `.meta` (BranchMeta sidecar)
- 双扩展名 JSONL 扫描：`.jsonl` + `.events.jsonl`
- `install.sh` / `install.bat` 一键安装脚本
- `VERSION` / `CHANGELOG.md` / `.gitignore` / `council_config.example.json`

### Changed
- `scan_sessions()` 不再硬编码 `desktop-*.meta.json` glob 模式
- 日期提取从固定偏移改为正则匹配
- `read_session_messages()` / `extract_summary()` / `init_council()` 适配动态扩展名

### Fixed
- 1.X 会话文件名不含 `desktop-` 前缀时无法扫描的问题

## [1.0.0] — 2026-07-02

### Added
- 初始版本：Reasonix v0.53 支持
- 会话扫描、摘要提取、议员匹配、代言生成
- DeepSeek API 集成 + 缓存机制
- CLI: scan / init / extract / match / speak / manage
