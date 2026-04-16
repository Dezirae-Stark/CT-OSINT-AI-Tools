@echo off
setlocal EnableDelayedExpansion
title GhostExodus — AI Model Setup

echo.
echo  ============================================================
echo    GHOSTEXODUS — AI Model Setup
echo  ============================================================
echo.
echo  This script will:
echo    1. Download the base model llama3.1:8b  (~4.7 GB)
echo    2. Build the GhostExodus analyst model  (~30 seconds)
echo.
echo  Requirements:
echo    - Ollama installed  (https://ollama.com)
echo    - Internet connection for model download
echo    - ~6 GB free disk space
echo.

:: ─── Check Ollama is installed ─────────────────────────────────────────────
where ollama >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Ollama not found on PATH.
    echo.
    echo         Please install Ollama from: https://ollama.com
    echo         Then re-run this script.
    echo.
    pause
    exit /b 1
)
echo [OK] Ollama found.

:: ─── Start Ollama serve if not already running ─────────────────────────────
echo [..] Checking Ollama service...
curl -s --max-time 3 http://localhost:11434/api/tags >nul 2>&1
if errorlevel 1 (
    echo [..] Starting Ollama service in background...
    start /B "" ollama serve
    :: Wait for it to become ready
    set /A _wait=0
    :wait_loop
    timeout /t 2 /nobreak >nul
    curl -s --max-time 2 http://localhost:11434/api/tags >nul 2>&1
    if not errorlevel 1 goto :ollama_ready
    set /A _wait+=1
    if !_wait! LSS 15 goto :wait_loop
    echo [ERROR] Ollama service did not start within 30 seconds.
    pause
    exit /b 1
)
:ollama_ready
echo [OK] Ollama service is running.

:: ─── Check if ghostexodus-analyst already exists ───────────────────────────
echo [..] Checking for existing ghostexodus-analyst model...
ollama list | findstr /I "ghostexodus-analyst" >nul 2>&1
if not errorlevel 1 (
    echo [OK] ghostexodus-analyst model already installed.
    echo.
    set /P _REBUILD="Rebuild the model from updated Modelfile? (y/N): "
    if /I "!_REBUILD!" NEQ "y" goto :done
    echo [..] Removing existing model for rebuild...
    ollama rm ghostexodus-analyst >nul 2>&1
)

:: ─── Step 1: Pull base model ───────────────────────────────────────────────
echo.
echo [1/2] Downloading base model llama3.1:8b...
echo       Size: approximately 4.7 GB
echo       Time: 10-40 minutes depending on connection speed
echo.
ollama pull llama3.1:8b
if errorlevel 1 (
    echo.
    echo [ERROR] Failed to pull llama3.1:8b.
    echo         Check your internet connection and try again.
    pause
    exit /b 1
)
echo.
echo [OK] Base model downloaded.

:: ─── Step 2: Create custom GhostExodus analyst model ──────────────────────
echo.
echo [2/2] Building ghostexodus-analyst model...
echo       Applying OSINT analyst system prompt and parameters...
echo.

:: Modelfile lives next to this script in the app install dir
set "MODELFILE=%~dp0ghostexodus.Modelfile"

if not exist "%MODELFILE%" (
    echo [ERROR] ghostexodus.Modelfile not found at:
    echo         %MODELFILE%
    echo.
    echo         Ensure GhostExodus is fully installed before running this script.
    pause
    exit /b 1
)

ollama create ghostexodus-analyst -f "%MODELFILE%"
if errorlevel 1 (
    echo.
    echo [ERROR] Failed to create ghostexodus-analyst model.
    echo         See output above for details.
    pause
    exit /b 1
)

:done
echo.
echo  ============================================================
echo    MODEL SETUP COMPLETE
echo  ============================================================
echo.
echo    Model:  ghostexodus-analyst
echo    Base:   llama3.1:8b
echo    Params: temp=0.1  ctx=4096  top_k=20
echo.
echo    GhostExodus AI engine is ready.
echo    Start GhostExodus and the model will load automatically.
echo.
pause
exit /b 0
