@echo off
setlocal enabledelayedexpansion
title LiveTranslateTool - Setup

cd /d "%~dp0"

echo ==============================================================================
echo                 LiveTranslateTool - Automated Setup
echo ==============================================================================
echo.

:: 1. Check Python
python --version >nul 2>&1
if %ERRORLEVEL% neq 0 (
    echo [!] Python was not detected on your system.
    set /p INSTALL_PY="Would you like to install Python 3.11 automatically via winget? (Y/N): "
    if /i "!INSTALL_PY!"=="Y" (
        echo Installing Python 3.11...
        winget install Python.Python.3.11 --accept-source-agreements --accept-package-agreements
        echo Python installed. Please restart this setup script to continue.
        pause
        exit /b 0
    ) else (
        echo Please install Python 3.10+ manually from https://python.org and rerun this script.
        pause
        exit /b 1
    )
)

:: 2. Create Virtual Environment
if not exist "venv\Scripts\python.exe" (
    echo [*] Creating Python virtual environment in .\venv...
    python -m venv venv
    if %ERRORLEVEL% neq 0 (
        echo [!] Failed to create virtual environment.
        pause
        exit /b 1
    )
)

:: 3. Install Requirements
echo [*] Installing / updating required dependencies...
venv\Scripts\python.exe -m pip install --upgrade pip
venv\Scripts\python.exe -m pip install -r requirements.txt
if %ERRORLEVEL% neq 0 (
    echo [!] Warning: Some dependencies may not have installed cleanly.
)

:: 4. Check Ollama
echo.
echo ==============================================================================
echo                 Local AI Translation Setup (Optional)
echo ==============================================================================
set "OLLAMA_EXE="
where ollama >nul 2>&1
if %ERRORLEVEL% equ 0 (
    set "OLLAMA_EXE=ollama"
) else if exist "%LOCALAPPDATA%\Programs\Ollama\ollama.exe" (
    set "OLLAMA_EXE=%LOCALAPPDATA%\Programs\Ollama\ollama.exe"
)

if not defined OLLAMA_EXE (
    echo Ollama enables local neural translation with Mistral-NeMo 12B.
    echo If you skip this, the app will use the built-in Oblivion Dictionary and fast offline translator.
    set /p INSTALL_OLLAMA="Would you like to install Ollama now? (Y/N): "
    if /i "!INSTALL_OLLAMA!"=="Y" (
        echo Installing Ollama...
        winget install Ollama.Ollama --accept-source-agreements --accept-package-agreements
        if exist "%LOCALAPPDATA%\Programs\Ollama\ollama.exe" (
            set "OLLAMA_EXE=%LOCALAPPDATA%\Programs\Ollama\ollama.exe"
        )
    )
)

:: 5. Check Mistral-NeMo Model
if defined OLLAMA_EXE (
    echo.
    echo Checking Mistral-NeMo 12B model...
    set /p PULL_MODEL="Would you like to download mistral-nemo:12b-instruct-2407-q5_K_M (~8.5 GB)? (Y/N): "
    if /i "!PULL_MODEL!"=="Y" (
        echo Downloading and preparing Mistral-NeMo 12B...
        "%OLLAMA_EXE%" run mistral-nemo:12b-instruct-2407-q5_K_M "/bye"
    ) else (
        echo [i] Model download skipped. The app will use the built-in Oblivion Dictionary + Fast Translator.
    )
)

echo.
echo ==============================================================================
echo                 Setup Complete!
echo ==============================================================================
echo You can now launch the app anytime by double-clicking 'Launch.bat'.
echo.
pause
