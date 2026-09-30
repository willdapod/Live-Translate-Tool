@echo off
setlocal enabledelayedexpansion
title LiveTranslateTool

:: Change directory to script folder
cd /d "%~dp0"

:: 1. Check if virtual environment exists; if not, run one-time setup
if not exist "venv\Scripts\python.exe" (
    echo ========================================================
    echo  LiveTranslateTool - First Time Setup Detected
    echo ========================================================
    echo Setting up environment and dependencies...
    call setup.bat
    if not exist "venv\Scripts\python.exe" (
        echo [ERROR] Setup could not complete.
        pause
        exit /b 1
    )
)

:: 2. Ensure Ollama background service is running if Ollama is installed
set "OLLAMA_EXE="
where ollama >nul 2>&1
if %ERRORLEVEL% equ 0 (
    set "OLLAMA_EXE=ollama"
) else if exist "%LOCALAPPDATA%\Programs\Ollama\ollama.exe" (
    set "OLLAMA_EXE=%LOCALAPPDATA%\Programs\Ollama\ollama.exe"
) else if exist "%ProgramFiles%\Ollama\ollama.exe" (
    set "OLLAMA_EXE=%ProgramFiles%\Ollama\ollama.exe"
)

if defined OLLAMA_EXE (
    tasklist /fi "imagename eq ollama.exe" 2>NUL | find /i "ollama.exe" >NUL
    if %ERRORLEVEL% neq 0 (
        echo Starting local Ollama background service...
        start "" /b "%OLLAMA_EXE%" serve
        timeout /t 2 /nobreak >nul
    )
)

:: 3. Launch Application cleanly (pythonw launches without keeping console window open)
echo Launching LiveTranslateTool...
start "" "venv\Scripts\pythonw.exe" main.py
exit
