@echo off
setlocal EnableDelayedExpansion
title GhostExodus — Build Installer

echo.
echo  ============================================================
echo    GHOSTEXODUS — Windows Installer Build Pipeline
echo  ============================================================
echo.

:: ─── Configuration ────────────────────────────────────────────────────────────
set "PYTHON=python"
set "PIP=pip"
set "NPM=npm"
set "ROOT=%~dp0"
set "VENV=%ROOT%build_venv"
set "DIST=%ROOT%dist\GhostExodus"
set "INNO_COMPILER=C:\Program Files (x86)\Inno Setup 6\ISCC.exe"

cd /d "%ROOT%"

:: ─── Step 1: Check prerequisites ─────────────────────────────────────────────
echo [1/7] Checking prerequisites...

%PYTHON% --version >nul 2>&1
if errorlevel 1 ( echo [ERROR] Python not found. && pause && exit /b 1 )

%NPM% --version >nul 2>&1
if errorlevel 1 ( echo [ERROR] Node.js / npm not found. && pause && exit /b 1 )

echo        Python OK
echo        Node.js OK

:: ─── Step 2: Build frontend ───────────────────────────────────────────────────
echo.
echo [2/7] Building React frontend...
cd frontend
call %NPM% install --silent
if errorlevel 1 ( echo [ERROR] npm install failed. && pause && exit /b 1 )

call %NPM% run build --silent
if errorlevel 1 ( echo [ERROR] Frontend build failed. && pause && exit /b 1 )
cd ..
echo        Frontend built: frontend\dist\

:: ─── Step 3: Create isolated build virtualenv ─────────────────────────────────
echo.
echo [3/7] Setting up build virtual environment...
if exist "%VENV%" rmdir /s /q "%VENV%"
%PYTHON% -m venv "%VENV%"
call "%VENV%\Scripts\activate.bat"
pip install --upgrade pip --quiet
echo        venv created

:: ─── Step 4: Install runtime dependencies ────────────────────────────────────
echo.
echo [4/7] Installing Python dependencies into build venv...
pip install -r requirements.txt --quiet
if errorlevel 1 ( echo [ERROR] pip install failed. && pause && exit /b 1 )

:: Install PyInstaller itself
pip install pyinstaller==6.11.1 --quiet
if errorlevel 1 ( echo [ERROR] Failed to install PyInstaller. && pause && exit /b 1 )

:: UPX for compression (optional — skip silently if not found)
where upx >nul 2>&1 && echo        UPX found - compression enabled || echo        UPX not found - skipping compression

echo        Dependencies installed

:: ─── Step 5: Clean previous build ────────────────────────────────────────────
echo.
echo [5/7] Cleaning previous build artefacts...
if exist "build"         rmdir /s /q "build"
if exist "dist"          rmdir /s /q "dist"
echo        Cleaned

:: ─── Step 6: PyInstaller build ────────────────────────────────────────────────
echo.
echo [6/7] Building with PyInstaller (this will take 3-10 minutes)...

:: Add backend to PYTHONPATH so PyInstaller resolves our modules
set "PYTHONPATH=%ROOT%backend;%ROOT%"

pyinstaller ghostexodus.spec --clean --noconfirm 2>&1
if errorlevel 1 (
    echo [ERROR] PyInstaller build failed. Check output above.
    pause
    exit /b 1
)

:: Verify the exe was created
if not exist "%DIST%\GhostExodus.exe" (
    echo [ERROR] GhostExodus.exe not found in dist\GhostExodus\
    pause
    exit /b 1
)

echo        PyInstaller build complete: %DIST%\

:: ─── Copy additional files into dist ─────────────────────────────────────────
echo.
echo        Copying config files...
copy /Y ".env.example"  "%DIST%\.env.example" >nul
copy /Y "README.md"     "%DIST%\README.md"    >nul

:: ─── Step 7: Inno Setup installer ────────────────────────────────────────────
echo.
echo [7/7] Building Inno Setup installer...

if not exist "%INNO_COMPILER%" (
    echo [WARNING] Inno Setup not found at:
    echo           %INNO_COMPILER%
    echo.
    echo           Download from: https://jrsoftware.org/isinfo.php
    echo           Then rerun:  "%INNO_COMPILER%" installer\ghostexodus.iss
    echo.
    echo [INFO] The raw application bundle is ready at:
    echo        %DIST%\
    echo        You can run it directly without the installer.
    goto :skip_inno
)

mkdir "installer\output" 2>nul
"%INNO_COMPILER%" "installer\ghostexodus.iss"
if errorlevel 1 (
    echo [ERROR] Inno Setup compilation failed.
    pause
    exit /b 1
)

echo.
echo  ============================================================
echo    BUILD COMPLETE
echo  ============================================================
echo.
echo    Installer:  installer\output\GhostExodus_Setup_v1.0.0.exe
echo    Raw bundle: dist\GhostExodus\GhostExodus.exe
echo.
pause
exit /b 0

:skip_inno
echo.
echo  ============================================================
echo    BUILD COMPLETE (no installer — Inno Setup not found)
echo  ============================================================
echo.
echo    Raw bundle: %DIST%\GhostExodus.exe
echo    Run it:     cd "%DIST%" ^&^& GhostExodus.exe
echo.
pause
exit /b 0
