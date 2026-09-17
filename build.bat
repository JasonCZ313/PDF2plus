@echo off
chcp 65001 >nul
echo ========================================
echo  PDF2plus 一键打包
echo  产出: dist\package\PDF2plus.exe
echo ========================================
echo.

python -m pip show pyinstaller >nul 2>&1
if %errorlevel% neq 0 (
    echo [INFO] 正在安装 PyInstaller...
    python -m pip install pyinstaller -i https://pypi.tuna.tsinghua.edu.cn/simple
)

python "%~dp0run_build.py"
if %errorlevel% neq 0 (
    echo [ERROR] 打包失败
    pause
    exit /b 1
)

echo.
echo 本地运行入口:
echo   dist\package\PDF2plus.exe
echo.
echo 可选网盘分发:
echo   dist\app_payload.zip
echo.
pause
