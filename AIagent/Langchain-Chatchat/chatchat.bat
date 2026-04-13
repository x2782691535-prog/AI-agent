@echo off
REM Chatchat 启动脚本 - 修复版
REM 使用方法: chatchat start -a

if "%1"=="start" if "%2"=="-a" (
    echo 正在启动 Langchain-Chatchat...
    D:\anaconda3\envs\enev\python.exe final_start.py
) else (
    echo 使用方法: chatchat start -a
    echo 或者直接运行: D:\anaconda3\envs\enev\python.exe final_start.py
)
