# -*- mode: python ; coding: utf-8 -*-
"""
GhostExodus OSINT Platform — PyInstaller Spec
Build with: pyinstaller ghostexodus.spec

Output: dist/GhostExodus/GhostExodus.exe  (--onedir bundle)

A --onedir bundle is used instead of --onefile because:
  1. First-launch extraction for --onefile is very slow (>500MB)
  2. SQLite, ChromaDB and data files need a stable, writable directory
  3. --onedir can be wrapped in Inno Setup as a proper installer
"""

import os
import sys
from PyInstaller.utils.hooks import collect_data_files, collect_submodules, collect_dynamic_libs

block_cipher = None

# ─── Collect data files from packages that need them ─────────────────────────

datas = []

# Jinja2 templates
datas += collect_data_files("jinja2")

# Backend templates (our report HTML)
datas += [("backend/reports/templates", "backend/reports/templates")]

# Frontend built assets (React SPA)
datas += [("frontend/dist", "backend/static")]

# .env.example for first-run
datas += [(".env.example", ".")]

# WeasyPrint fonts + data
datas += collect_data_files("weasyprint")
datas += collect_data_files("pyphen")
datas += collect_data_files("fonttools")
datas += collect_data_files("tinycss2")
datas += collect_data_files("tinyhtml5")

# ChromaDB migrations and data
datas += collect_data_files("chromadb")

# LlamaIndex
datas += collect_data_files("llama_index")

# tiktoken encodings
datas += collect_data_files("tiktoken")

# langdetect language profiles
datas += collect_data_files("langdetect")

# NLTK (used by some llama-index components)
datas += collect_data_files("nltk")

# ONNX runtime (used by chromadb embeddings)
datas += collect_data_files("onnxruntime")

# tokenizers
datas += collect_data_files("tokenizers")

# certifi CA bundle
datas += collect_data_files("certifi")


# ─── Hidden imports ────────────────────────────────────────────────────────────
# Packages that use dynamic imports PyInstaller can't detect statically

hiddenimports = [
    # FastAPI / Starlette
    "fastapi",
    "fastapi.middleware.cors",
    "starlette.routing",
    "starlette.middleware",
    "starlette.staticfiles",
    "starlette.responses",
    "starlette.websockets",
    "uvicorn",
    "uvicorn.main",
    "uvicorn.config",
    "uvicorn.lifespan.on",
    "uvicorn.loops.auto",
    "uvicorn.loops.asyncio",
    "uvicorn.loops.uvloop",
    "uvicorn.protocols.http.auto",
    "uvicorn.protocols.http.h11_impl",
    "uvicorn.protocols.http.httptools_impl",
    "uvicorn.protocols.websockets.auto",
    "uvicorn.protocols.websockets.websockets_impl",
    "uvicorn.protocols.websockets.wsproto_impl",
    "websockets",
    "websockets.legacy",
    "websockets.legacy.server",

    # SQLModel / SQLAlchemy
    "sqlmodel",
    "sqlalchemy",
    "sqlalchemy.dialects.sqlite",
    "sqlalchemy.dialects.sqlite.json",
    "sqlalchemy.ext.asyncio",

    # Auth
    "jose",
    "jose.jwt",
    "passlib",
    "passlib.handlers.bcrypt",
    "bcrypt",

    # Config
    "pydantic_settings",
    "dotenv",

    # Telethon
    "telethon",
    "telethon.sessions",
    "telethon.crypto",
    "telethon.crypto.aes",
    "telethon.network",
    "telethon.errors",
    "telethon.tl",
    "telethon.tl.types",
    "telethon.tl.functions",

    # ChromaDB
    "chromadb",
    "chromadb.api",
    "chromadb.api.client",
    "chromadb.api.models",
    "chromadb.config",
    "chromadb.db.impl",
    "chromadb.db.impl.sqlite",
    "chromadb.segment",
    "chromadb.segment.impl",
    "chromadb.segment.impl.metadata",
    "chromadb.segment.impl.vector",
    "chromadb.segment.impl.vector.local_hnsw",
    "chromadb.segment.impl.distributed",
    "chromadb.types",
    "onnxruntime",

    # LlamaIndex
    "llama_index",
    "llama_index.core",
    "llama_index.core.query_engine",
    "llama_index.core.retrievers",
    "llama_index.core.node_parser",
    "llama_index.core.embeddings",
    "llama_index.core.llms",
    "llama_index.llms.ollama",
    "llama_index.embeddings.ollama",
    "llama_index.vector_stores.chroma",

    # Scheduler
    "apscheduler",
    "apscheduler.schedulers.asyncio",
    "apscheduler.triggers.interval",
    "apscheduler.jobstores.memory",
    "apscheduler.executors.asyncio",

    # HTTP
    "httpx",
    "httpcore",
    "aiohttp",
    "aiofiles",
    "aiosmtplib",

    # PDF / Report
    "weasyprint",
    "jinja2",
    "jinja2.ext",
    "jinja2.loaders",
    "pyphen",
    "fonttools",
    "tinycss2",
    "cssselect2",

    # Misc
    "langdetect",
    "langdetect.detector",
    "langdetect.detector_factory",
    "multipart",
    "python_multipart",

    # Our own backend modules
    "config",
    "database",
    "auth.router",
    "auth.models",
    "auth.utils",
    "auth.dependencies",
    "collector.telegram_client",
    "collector.channel_monitor",
    "collector.keyword_engine",
    "collector.scheduler",
    "intelligence.embedder",
    "intelligence.vectorstore",
    "intelligence.rag_query",
    "intelligence.llm_client",
    "intelligence.classifier",
    "intelligence.entity_extractor",
    "intelligence.stylometry",
    "evidence.archiver",
    "evidence.export",
    "evidence.chain_of_custody",
    "reports.generator",
    "alerts.rules_engine",
    "alerts.notifier",
    "routers.feed",
    "routers.search",
    "routers.entities",
    "routers.timeline",
    "routers.alerts",
    "routers.reports",
    "routers.evidence",
    "routers.channels",
    "routers.admin",
]

# Add all submodules for key packages
for pkg in ["telethon", "chromadb", "llama_index", "sqlalchemy", "starlette", "fastapi"]:
    hiddenimports += collect_submodules(pkg)

# ─── Binary libraries ─────────────────────────────────────────────────────────
binaries = []
binaries += collect_dynamic_libs("onnxruntime")

# ─── Analysis ────────────────────────────────────────────────────────────────
a = Analysis(
    ["launcher.py"],
    pathex=[
        ".",
        "backend",
    ],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        # Exclude heavy unused packages
        "tkinter",
        "matplotlib",
        "scipy",
        "pandas",
        "IPython",
        "jupyter",
        "notebook",
        "pytest",
        "sphinx",
        "black",
        "mypy",
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="GhostExodus",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    console=True,         # Keep console open — needed for Telegram auth prompt on first run
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon="installer/icon.ico" if os.path.exists("installer/icon.ico") else None,
    version="installer/version_info.txt" if os.path.exists("installer/version_info.txt") else None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name="GhostExodus",
)
