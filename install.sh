#!/usr/bin/env bash
# conversation-council install script (macOS / Linux)
set -e

SKILL_NAME="conversation-council"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

# 检测目标目录
if [ -n "$REASONIX_HOME" ]; then
    TARGET="$REASONIX_HOME/skills/$SKILL_NAME"
elif [ -d "$HOME/.reasonix" ]; then
    TARGET="$HOME/.reasonix/skills/$SKILL_NAME"
else
    echo "未找到 Reasonix 数据目录。请设置 REASONIX_HOME 环境变量后重试。"
    exit 1
fi

echo "安装 $SKILL_NAME → $TARGET"

mkdir -p "$TARGET"
cp "$SCRIPT_DIR/council.py" "$TARGET/"
cp "$SCRIPT_DIR/SKILL.md" "$TARGET/"
cp "$SCRIPT_DIR/council_config.example.json" "$TARGET/"
cp "$SCRIPT_DIR/README.md" "$TARGET/"
cp "$SCRIPT_DIR/README.zh.md" "$TARGET/"
cp "$SCRIPT_DIR/LICENSE" "$TARGET/"

# 首次安装时创建空白配置
if [ ! -f "$TARGET/council_config.json" ]; then
    cp "$SCRIPT_DIR/council_config.example.json" "$TARGET/council_config.json"
fi

echo ""
echo "✅ conversation-council v$(cat "$SCRIPT_DIR/VERSION") 安装完成"
echo ""
echo "使用前请确保："
echo "  1. Python 3.10+ 已安装"
echo "  2. 环境变量 DEEPSEEK_API_KEY 已设置"
echo ""
echo "在 Reasonix 中输入 /skill conversation-council 即可启动。"
