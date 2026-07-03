# Changelog

## [2.0.0] — 2026-07-03

### Added
- **Reasonix v1.X (Go 重写版) 支持** — 自动检测会话存储格式
- 自动检测 sessions 目录：`REASONIX_HOME` → `%APPDATA%/reasonix` → `~/.reasonix` → v0.53 相对路径
- 双格式元数据支持：v0.53 `.meta.json` + v1.X `.meta` (BranchMeta sidecar)
- 双扩展名 JSONL 扫描：`.jsonl` + `.events.jsonl`
- `install.sh` / `install.bat` 一键安装脚本
- `VERSION` 文件
- `CHANGELOG.md`
- `.gitignore`（cache/ council_config.json __pycache__/）
- `council_config.example.json` 空白配置模板
- SKILL.md 新增版本兼容性说明表格

### Changed
- `scan_sessions()` 不再硬编码 `desktop-*.meta.json` glob 模式
- 日期提取从固定偏移 `[8:16]` 改为正则匹配 8 位连续数字
- `read_session_messages()` 支持完整路径和 session ID 两种参数
- `extract_summary()` 缓存验证改用 `_find_jsonl_for_session()`
- `init_council()` / `add_member()` 的 `session_file` 使用检测到的扩展名
- README.zh.md 兼容性章节重写为双版本说明
- 最低 Python 版本要求：3.10+

### Fixed
- 1.X 会话文件名不含 `desktop-` 前缀时无法扫描的问题
- 1.X 元数据字段 `Preview` 映射到 `summary_hint`

## [1.0.0] — 2026-07-02

### Added
- 初始版本：Reasonix v0.53 支持
- 会话扫描、摘要提取、议员匹配、代言生成
- DeepSeek API 集成
- 缓存机制
- CLI: scan / init / extract / match / speak / manage
