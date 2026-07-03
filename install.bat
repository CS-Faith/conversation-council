@echo off
REM conversation-council install script (Windows)
setlocal enabledelayedexpansion

set SKILL_NAME=conversation-council
set SCRIPT_DIR=%~dp0

REM 检测目标目录
if defined REASONIX_HOME (
    set TARGET=%REASONIX_HOME%\skills\%SKILL_NAME%
) else if exist "%APPDATA%\reasonix" (
    set TARGET=%APPDATA%\reasonix\skills\%SKILL_NAME%
) else if exist "%USERPROFILE%\.reasonix" (
    set TARGET=%USERPROFILE%\.reasonix\skills\%SKILL_NAME%
) else (
    echo 未找到 Reasonix 数据目录。请设置 REASONIX_HOME 环境变量后重试。
    exit /b 1
)

echo 安装 %SKILL_NAME% -^> %TARGET%

if not exist "%TARGET%" mkdir "%TARGET%"
copy /Y "%SCRIPT_DIR%council.py" "%TARGET%\" >nul
copy /Y "%SCRIPT_DIR%SKILL.md" "%TARGET%\" >nul
copy /Y "%SCRIPT_DIR%council_config.example.json" "%TARGET%\" >nul
copy /Y "%SCRIPT_DIR%README.md" "%TARGET%\" >nul
copy /Y "%SCRIPT_DIR%README.zh.md" "%TARGET%\" >nul
copy /Y "%SCRIPT_DIR%LICENSE" "%TARGET%\" >nul

REM 首次安装时创建空白配置
if not exist "%TARGET%\council_config.json" (
    copy /Y "%SCRIPT_DIR%council_config.example.json" "%TARGET%\council_config.json" >nul
)

echo.
echo ^^✅ conversation-council 安装完成
echo.
echo 使用前请确保：
echo   1. Python 3.10+ 已安装
echo   2. 环境变量 DEEPSEEK_API_KEY 已设置
echo.
echo 在 Reasonix 中输入 /skill conversation-council 即可启动。
