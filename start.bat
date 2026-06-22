@echo off
chcp 65001 >nul
setlocal

REM ============================================================
REM  QuantLab 一键启动脚本（Windows）
REM  - 后端：FastAPI (uvicorn)  http://localhost:8000
REM  - 前端：Vite Dev Server    http://localhost:5173
REM  使用：双击运行，或在 PowerShell 中执行  .\start.bat
REM ============================================================

cd /d "%~dp0"

echo.
echo ============================================================
echo  QuantLab 启动中...
echo  项目目录: %CD%
echo ============================================================
echo.

REM ---------- 检查后端依赖 ----------
where uvicorn >nul 2>nul
if errorlevel 1 (
    echo [WARN] 未检测到 uvicorn，将使用 python -m uvicorn 启动后端
    set BACKEND_CMD=python -m uvicorn quantlab.api.app:app --host 0.0.0.0 --port 8000
) else (
    set BACKEND_CMD=uvicorn quantlab.api.app:app --host 0.0.0.0 --port 8000
)

REM ---------- 检查前端依赖 ----------
if not exist "frontend\node_modules" (
    echo [WARN] 未检测到 frontend\node_modules，正在执行 npm install ...
    pushd frontend
    call npm install
    popd
    if errorlevel 1 (
        echo [ERROR] npm install 失败，请手动检查后重试
        pause
        exit /b 1
    )
)

REM ---------- 启动后端（新窗口） ----------
echo [1/2] 启动后端 FastAPI ...
start "QuantLab-Backend" cmd /k "title QuantLab-Backend && %BACKEND_CMD%"

REM ---------- 启动前端（新窗口） ----------
echo [2/2] 启动前端 Vite ...
pushd frontend
start "QuantLab-Frontend" cmd /k "title QuantLab-Frontend && npm run dev"
popd

echo.
echo ============================================================
echo  启动完成！
echo  - 后端地址: http://localhost:8000
echo  - 前端地址: http://localhost:5173
echo  - 停止服务: 直接关闭对应的命令行窗口
echo ============================================================
echo.

endlocal
