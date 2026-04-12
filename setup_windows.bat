@echo off
setlocal EnableDelayedExpansion
echo.
echo  ====================================================
echo    GHOSTEXODUS OSINT PLATFORM — Windows Setup
echo  ====================================================
echo.

:: ─── Check Python ────────────────────────────────────────────────────────────
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python not found. Install Python 3.11+ from https://python.org
    pause
    exit /b 1
)
echo [OK] Python found

:: ─── Check Node ──────────────────────────────────────────────────────────────
node --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Node.js not found. Install Node.js 18+ from https://nodejs.org
    pause
    exit /b 1
)
echo [OK] Node.js found

:: ─── Check Ollama ────────────────────────────────────────────────────────────
ollama --version >nul 2>&1
if errorlevel 1 (
    echo [WARNING] Ollama not found in PATH.
    echo           Install from https://ollama.com and ensure it is running.
) else (
    echo [OK] Ollama found
)

:: ─── Create data directories ─────────────────────────────────────────────────
echo.
echo [SETUP] Creating data directories...
if not exist "data\chromadb"       mkdir "data\chromadb"
if not exist "data\sqlite"         mkdir "data\sqlite"
if not exist "data\evidence"       mkdir "data\evidence"
if not exist "data\evidence\media" mkdir "data\evidence\media"
if not exist "data\reports"        mkdir "data\reports"
echo [OK] Data directories created

:: ─── Python dependencies ─────────────────────────────────────────────────────
echo.
echo [SETUP] Installing Python dependencies...
pip install -r requirements.txt
if errorlevel 1 (
    echo [ERROR] pip install failed. Check requirements.txt and your Python environment.
    pause
    exit /b 1
)
echo [OK] Python dependencies installed

:: ─── Pull Ollama models ───────────────────────────────────────────────────────
echo.
echo [SETUP] Pulling Ollama models (this may take several minutes)...
ollama pull llama3.1:8b
if errorlevel 1 (
    echo [WARNING] Failed to pull llama3.1:8b - ensure Ollama is running: ollama serve
)
ollama pull nomic-embed-text
if errorlevel 1 (
    echo [WARNING] Failed to pull nomic-embed-text
)
echo [OK] Ollama models pulled

:: ─── Frontend build ───────────────────────────────────────────────────────────
echo.
echo [SETUP] Installing frontend dependencies...
cd frontend
call npm install
if errorlevel 1 (
    echo [ERROR] npm install failed.
    pause
    exit /b 1
)
echo [OK] npm packages installed

echo [SETUP] Building frontend...
call npm run build
if errorlevel 1 (
    echo [ERROR] Frontend build failed.
    pause
    exit /b 1
)
echo [OK] Frontend built

:: ─── Copy frontend build to backend ──────────────────────────────────────────
cd ..
echo [SETUP] Deploying frontend to backend/static...
if not exist "backend\static" mkdir "backend\static"
xcopy /E /I /Y "frontend\dist\*" "backend\static\"
echo [OK] Frontend deployed

:: ─── Copy env template ────────────────────────────────────────────────────────
if not exist ".env" (
    copy ".env.example" ".env"
    echo [SETUP] .env file created from template — EDIT IT NOW with your Telegram credentials
) else (
    echo [INFO] .env already exists, not overwriting
)

:: ─── Done ─────────────────────────────────────────────────────────────────────
echo.
echo  ====================================================
echo    GHOSTEXODUS Setup Complete
echo  ====================================================
echo.
echo  NEXT STEPS:
echo  1. Edit .env with your Telegram API credentials
echo     (get from https://my.telegram.org/apps)
echo.
echo  2. Start the platform:
echo     cd backend
echo     uvicorn main:app --host 127.0.0.1 --port 8000
echo.
echo  3. Open http://localhost:8000 in your browser
echo     Complete the first-run setup wizard to create
echo     your admin account.
echo.
echo  4. On first run, Telegram will prompt for your
echo     phone verification code in the terminal.
echo.
pause
