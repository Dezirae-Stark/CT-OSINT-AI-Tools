"""
GhostExodus OSINT Platform — Windows Launcher
Entry point for PyInstaller bundle.

Handles:
  - Setting up sys.path so all bundled modules resolve correctly
  - Locating the correct base directory whether frozen or running from source
  - Changing working directory so relative paths in the app (./data, ./static) work
  - Launching uvicorn programmatically in-process
  - Showing a system-tray / console message with the URL
  - Graceful shutdown on CTRL+C or window close
"""

import sys
import os
import logging
import signal
import threading
import webbrowser
import time

# ─── Determine base directory ─────────────────────────────────────────────────
# When frozen by PyInstaller, sys.frozen is True and sys._MEIPASS points to
# the temp extraction directory for the bundle.
# When running from source, __file__ gives us the project root.

if getattr(sys, "frozen", False):
    # Running as PyInstaller bundle
    BUNDLE_DIR = sys._MEIPASS          # extracted bundle (read-only)
    BASE_DIR   = os.path.dirname(sys.executable)  # next to the .exe (writable)
else:
    BUNDLE_DIR = os.path.dirname(os.path.abspath(__file__))
    BASE_DIR   = BUNDLE_DIR

# The backend package lives inside BUNDLE_DIR/backend
BACKEND_DIR = os.path.join(BUNDLE_DIR, "backend")
if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)
if BUNDLE_DIR not in sys.path:
    sys.path.insert(0, BUNDLE_DIR)

# Change CWD to BASE_DIR so relative paths (./data, ./static, .env) resolve
os.chdir(BASE_DIR)

# ─── Environment / .env loading ───────────────────────────────────────────────
env_path = os.path.join(BASE_DIR, ".env")
if os.path.exists(env_path):
    from dotenv import load_dotenv
    load_dotenv(env_path)
else:
    # First run — copy .env.example to .env and prompt user to edit
    example = os.path.join(BUNDLE_DIR, ".env.example")
    if os.path.exists(example):
        import shutil
        shutil.copy(example, env_path)
        print("[GhostExodus] .env created from template.")
        print("              Edit .env with your Telegram API credentials before using the collector.")

# ─── Ensure data directories exist ───────────────────────────────────────────
for sub in [
    "data/chromadb",
    "data/sqlite",
    "data/evidence",
    "data/evidence/media",
    "data/reports",
]:
    os.makedirs(os.path.join(BASE_DIR, sub), exist_ok=True)

# ─── Logging ──────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(os.path.join(BASE_DIR, "data", "ghostexodus.log"), encoding="utf-8"),
    ],
)
logger = logging.getLogger("ghostexodus.launcher")

HOST = "127.0.0.1"
PORT = 8000
URL  = f"http://{HOST}:{PORT}"


def open_browser():
    """Wait for the server to start, then open the browser."""
    for _ in range(20):
        time.sleep(0.5)
        try:
            import urllib.request
            urllib.request.urlopen(f"{URL}/api/setup/status", timeout=1)
            webbrowser.open(URL)
            logger.info(f"Browser opened at {URL}")
            return
        except Exception:
            pass
    logger.warning("Could not confirm server startup for browser open")


def main():
    logger.info("=" * 60)
    logger.info("  GhostExodus OSINT Platform")
    logger.info(f"  Starting at {URL}")
    logger.info("=" * 60)

    # Open browser after server starts (in a background thread)
    t = threading.Thread(target=open_browser, daemon=True)
    t.start()

    try:
        import uvicorn
        uvicorn.run(
            "main:app",
            host=HOST,
            port=PORT,
            log_level="info",
            # Don't use reload — not compatible with frozen bundles
            reload=False,
            # Use only 1 worker — ChromaDB / SQLite are not multi-process safe
            workers=1,
        )
    except KeyboardInterrupt:
        logger.info("Shutdown requested (CTRL+C)")
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        input("Press ENTER to exit...")
        sys.exit(1)


if __name__ == "__main__":
    main()
