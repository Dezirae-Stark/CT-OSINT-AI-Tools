# GhostExodus OSINT Platform

**Counter-extremism intelligence monitoring suite for UK law enforcement support.**

Monitors Telegram channels in real time, classifies threats with local AI, correlates entities across communications, generates INTELREPORT PDFs, and maintains a legally defensible SHA-256 evidence archive with full chain-of-custody logging — entirely on-device, no cloud, no subscriptions.

---

## TL;DR

| What | Detail |
|------|--------|
| **Platform** | Windows 11 native (no Docker, no WSL) |
| **Install** | Run `build_installer.bat` → generates `GhostExodus_Setup_v1.0.0.exe` |
| **Start** | Launch `GhostExodus.exe` → browser opens at `http://localhost:8000` |
| **First run** | Create admin account in the browser wizard |
| **Telegram auth** | Enter phone verification code once in the terminal window |
| **Data** | All data stored in `%AppData%\GhostExodus\` — never leaves the machine |
| **Default login** | Username and password set during first-run wizard |
| **Roles** | ADMIN / ANALYST / VIEWER (RBAC enforced on every API endpoint) |
| **LLM** | `ghostexodus-analyst` — custom model built on `llama3.1:8b` via Ollama (must be running before start) |
| **Embeddings** | `nomic-embed-text` via Ollama |
| **Model setup** | Run `setup_models.bat` once after installing Ollama — pulls base model + builds custom analyst model (~4.7 GB) |

---

## Table of Contents

1. [Features](#features)
2. [System Requirements](#system-requirements)
3. [Installation — Installer Package (Recommended)](#installation--installer-package-recommended)
4. [Installation — From Source](#installation--from-source)
5. [Configuration (.env)](#configuration-env)
6. [First Run](#first-run)
7. [User Interface](#user-interface)
8. [User Roles & Permissions](#user-roles--permissions)
9. [Telegram Channel Monitoring](#telegram-channel-monitoring)
10. [Threat Classification Engine](#threat-classification-engine)
11. [Semantic Search & RAG](#semantic-search--rag)
12. [Entity Correlation & Graph](#entity-correlation--graph)
13. [Evidence Management](#evidence-management)
14. [Intelligence Reports](#intelligence-reports)
15. [Alert Rules](#alert-rules)
16. [API Reference](#api-reference)
17. [Building the Windows Installer](#building-the-windows-installer)
18. [Architecture](#architecture)
19. [Security Notes](#security-notes)
20. [Technology Stack](#technology-stack)

---

## Features

### Core Capabilities

- **Real-time Telegram monitoring** — Telethon MTProto connection subscribes to live message events from monitored channels; new messages appear on the dashboard within seconds
- **Keyword threat engine** — 6 built-in threat categories (Operational Planning, Recruitment, Financing, Propaganda, UK-Specific, Incitement) with regex and exact-match custom rules
- **Local LLM classification** — `ghostexodus-analyst` (custom model built on `llama3.1:8b`) classifies medium/high severity messages for threat category, TTP identification, UK relevance, and urgency; specialised OSINT system prompt and few-shot examples baked into the model
- **Semantic search** — `nomic-embed-text` embeddings stored in ChromaDB; search by meaning, keyword, or entity with cosine similarity scoring
- **RAG intelligence queries** — LlamaIndex retrieval-augmented generation pipeline answers analytical questions over the message corpus
- **Entity extraction & correlation** — regex + LLM hybrid extracts Telegram handles, phone numbers, email addresses, onion links, crypto addresses, domain names; builds co-occurrence graph
- **Stylometry** — writing style fingerprinting (TTR, trigrams, sentence cadence, emoji ratio) with cosine similarity author comparison
- **SHA-256 evidence archive** — every ingested message hashed at capture time; filesystem archive at `data/evidence/YYYY-MM-DD/`; per-item integrity verification
- **Case bundle export** — ZIP with JSON evidence files, manifest with hashes, human-readable chain-of-custody log, and a standalone Python verification script
- **INTELREPORT PDF** — 9-section formal intelligence report (Executive Summary → Actors → TTPs → Network → Temporal Analysis → UK Relevance → Evidence Reference) generated via WeasyPrint + Jinja2; falls back to HTML if WeasyPrint unavailable
- **Role-based access control** — ADMIN / ANALYST / VIEWER enforced on every API endpoint
- **Full audit trail** — every user action (login, report generation, severity override, evidence export, user creation, etc.) written to an immutable audit log table
- **Alert rules** — KEYWORD / ENTITY / FREQUENCY trigger types with ARCHIVE / NOTIFY / BOTH actions; email (SMTP) and push (ntfy.sh) notifications
- **APScheduler jobs** — evidence integrity scan every 6 hours, entity co-occurrence linking every 30 minutes, frequency cache cleanup every 15 minutes
- **Live WebSocket feed** — dashboard receives real-time message events without polling; auto-reconnects with exponential backoff

---

## System Requirements

### Minimum Hardware

| Component | Requirement |
|-----------|------------|
| OS | Windows 10 (build 17763) or Windows 11 (64-bit only) |
| RAM | 16 GB (8 GB for Ollama LLM + 8 GB OS/app) |
| GPU | NVIDIA GPU with 8 GB+ VRAM recommended (Ollama uses GPU by default) |
| Storage | 20 GB free (models + data) |
| CPU | 8-core recommended |

### Software Prerequisites

These must be installed **before** running GhostExodus:

1. **Ollama** — [https://ollama.com](https://ollama.com)
   - After installing Ollama, run the model setup script included with GhostExodus:
     ```batch
     setup_models.bat
     ```
     This pulls `llama3.1:8b` (~4.7 GB) and builds the `ghostexodus-analyst` custom model.
     To pull only the embedding model manually:
     ```batch
     ollama pull nomic-embed-text
     ```
   - Ollama must be **running** (`ollama serve`) before launching GhostExodus

2. **Telegram API credentials** — see [Telegram Channel Monitoring](#telegram-channel-monitoring)

### For building from source only

- **Python 3.11+** — [python.org](https://www.python.org/downloads/)
- **Node.js 18+** — [nodejs.org](https://nodejs.org/)
- **Inno Setup 6** (optional, for installer) — [jrsoftware.org/isinfo.php](https://jrsoftware.org/isinfo.php)

---

## Installation — Installer Package (Recommended)

> **Download the pre-built installer from the [Releases](https://github.com/Dezirae-Stark/CT-OSINT-AI-Tools/releases) page.**

1. Install **Ollama** from [https://ollama.com](https://ollama.com) if not already present
2. Run `GhostExodus_Setup_v1.0.0.exe` as Administrator
3. Follow the installation wizard
4. On the final screen, optionally tick **"Download and configure AI analyst model"** — this runs `setup_models.bat` to pull `llama3.1:8b` and build `ghostexodus-analyst` (~4.7 GB, requires internet)
5. Tick **"Launch GhostExodus"** to start immediately

> If you skip step 4, run **Start Menu → GhostExodus → Setup AI Model** at any time to build the model.

The installer:
- Deploys to `C:\Program Files\GhostExodus\`
- Creates writable data directories in `%AppData%\GhostExodus\`
- Copies `.env.example` to `%AppData%\GhostExodus\.env` for first-run configuration
- Installs `ghostexodus.Modelfile` and `setup_models.bat` alongside the application
- Adds an optional startup registry entry (opt-in during install)
- Warns if Ollama is not detected with instructions for the model setup script

After installation, **edit `%AppData%\GhostExodus\.env`** before launching (see [Configuration](#configuration-env)).

---

## Installation — From Source

```batch
:: 1. Clone
git clone https://github.com/Dezirae-Stark/CT-OSINT-AI-Tools.git ghostexodus
cd ghostexodus

:: 2. Create Python venv
python -m venv venv
call venv\Scripts\activate

:: 3. Install dependencies
pip install -r requirements.txt

:: 4. Build frontend
cd frontend
npm install
npm run build
cd ..

:: 5. Copy frontend to backend static
xcopy /E /Y /I frontend\dist backend\static

:: 6. Create .env
copy .env.example .env
:: Edit .env with your credentials

:: 7. Set up Ollama models (pulls llama3.1:8b + builds ghostexodus-analyst)
setup_models.bat
:: Or manually:
::   ollama pull llama3.1:8b && ollama create ghostexodus-analyst -f ghostexodus.Modelfile
ollama pull nomic-embed-text

:: 8. Start (from project root)
cd backend
uvicorn main:app --host 127.0.0.1 --port 8000
```

---

## Configuration (.env)

The `.env` file lives next to `GhostExodus.exe` (installed: `%AppData%\GhostExodus\.env`; source: project root).

### Required settings

```env
# Telegram API — obtain from https://my.telegram.org/apps
TELEGRAM_API_ID=12345678
TELEGRAM_API_HASH=abcdef1234567890abcdef1234567890abcdef12
TELEGRAM_PHONE=+447700000000

# Security — generate with: python -c "import secrets; print(secrets.token_hex(32))"
JWT_SECRET=your-64-character-hex-secret-here-do-not-use-default
```

### Optional settings

```env
# Environment (development enables CORS for Vite dev server)
ENV=production

# Ollama (defaults work if Ollama is running on localhost)
OLLAMA_BASE_URL=http://localhost:11434
# Custom analyst model — built by setup_models.bat
# Falls back gracefully if you set this to llama3.1:8b directly
LLM_MODEL=ghostexodus-analyst
EMBED_MODEL=nomic-embed-text

# JWT expiry in hours
JWT_EXPIRY_HOURS=24

# Email alerts (leave blank to disable)
SMTP_HOST=smtp.example.com
SMTP_PORT=587
SMTP_USER=alerts@example.com
SMTP_PASSWORD=your-smtp-password
SMTP_FROM=alerts@example.com
ALERT_EMAIL_TO=analyst@example.com

# Push notifications via ntfy.sh (leave blank to disable)
NTFY_URL=https://ntfy.sh/your-topic-here
```

### Generate a JWT secret

```batch
python -c "import secrets; print(secrets.token_hex(32))"
```

---

## First Run

1. **Ensure Ollama is running**: `ollama serve` (or it runs as a Windows service after installation)
2. **Launch GhostExodus**: double-click the desktop icon, or run `GhostExodus.exe`
3. A console window opens — leave it running, it is the server process
4. Your browser automatically opens at `http://localhost:8000`
5. The **setup wizard** detects no users exist and prompts you to create the first admin account

### Telegram Authentication

On first launch with Telegram credentials configured, the **console window** will display:

```
Please enter the code you received on Telegram:
```

Enter the 5-digit code sent to your Telegram account. The session is saved to `data/telegram.session` — subsequent launches will not ask again unless the session expires.

> If you do not have Telegram credentials yet, you can skip this step. The platform runs fully without Telegram connected — you can add credentials and restart later.

---

## User Interface

GhostExodus uses a dark terminal-aesthetic UI with IBM Plex Mono typography and blue accent colour scheme.

### Dashboard

Real-time overview with:
- 4 stat cards: Messages Today · Active Alerts · Channels Monitored · High/Critical Flags
- **Live feed** (left, 60%): scrolling message cards with severity badges, keyword highlights, and inline LLM classification labels
- **Severity donut** (right top): distribution of NONE/LOW/MEDIUM/HIGH/CRITICAL
- **Top channels bar chart** (right mid): most active channels in the last 24 hours
- **Recent LLM classifications** (right bottom): threat categories from the AI classifier

New messages arrive via WebSocket and slide into the top of the feed without page reload.

### Search

Three search modes selectable by tab:
- **Semantic** — meaning-based search using vector embeddings
- **Keyword** — exact/regex text search
- **Entity** — search by Telegram handle, phone, email, crypto address etc.

RAG mode: ask natural-language intelligence questions and receive an AI-synthesised answer with cited source messages.

### Entity Map

Force-directed graph (React Flow) of extracted entities:
- Nodes coloured by type (handle/phone/email/crypto/onion/domain)
- Edge thickness = co-occurrence count
- Click a node to open detail panel: entity type, first/last seen, co-occurring entities, recent messages, stylometry features

### Timeline

Multi-series area chart of message volume over time by channel. Severity breakdown stacked chart. Frequency heatmap. Peak activity hour detection with likely timezone offset.

### Alert Rules

Create and manage rules that fire on:
- **KEYWORD** — regex or exact match in message text
- **ENTITY** — entity value string match
- **FREQUENCY** — N messages from a channel in M minutes (format: `N:M`)

Actions: **ARCHIVE** (auto-flag message), **NOTIFY** (email + push), **BOTH**.

Test any rule against the last 100 messages before activating.

### Reports

Generate formal intelligence reports for a date range and optional channel/severity filter. Reports are generated asynchronously — status shows PENDING → COMPLETE. Download as PDF (or HTML fallback if WeasyPrint is unavailable).

Report sections:
1. Case Reference & Classification Header
2. Executive Summary (LLM-generated)
3. Actors Identified (table with entity details)
4. Key Communications (top flagged messages)
5. TTPs Assessment (AI-generated)
6. Network Relationships (AI-generated)
7. Temporal Analysis (AI-generated)
8. UK Relevance Assessment (AI-generated)
9. Evidence Reference List (with SHA-256 hashes)
10. Analyst Notes & Recommended Actions

### Evidence

Evidence archive browser with:
- Per-item SHA-256 hash display (click to copy full hash)
- **Verify** button — re-hashes the file and checks against stored hash (VERIFIED/TAMPERED)
- Multi-select and **Export Case Bundle** — downloads ZIP with evidence JSON files, manifest, chain-of-custody log, and a standalone `verification_script.py`

### Settings

Tabbed settings panel:
- **Channels** — add/remove monitored Telegram channels; trigger history backfill
- **Users** — create accounts, assign roles, reset passwords, deactivate users (ADMIN only)
- **System** — Ollama status, ChromaDB collection stats, SQLite file size, active monitor count

---

## User Roles & Permissions

| Action | VIEWER | ANALYST | ADMIN |
|--------|--------|---------|-------|
| View dashboard, feed, timeline, entity map | Yes | Yes | Yes |
| Keyword/semantic/entity search | Yes | Yes | Yes |
| Override message severity | No | Yes | Yes |
| Create/edit alert rules | No | Yes | Yes |
| Generate reports | No | Yes | Yes |
| Export evidence bundles | No | Yes | Yes |
| Add/remove Telegram channels | No | Yes | Yes |
| Manage users | No | No | Yes |
| View audit log | No | No | Yes |
| View system status | No | No | Yes |

---

## Telegram Channel Monitoring

### Getting API Credentials

1. Log in at [https://my.telegram.org/apps](https://my.telegram.org/apps) with the phone number you want to use for monitoring
2. Create a new application (name/description can be anything)
3. Copy **API ID** (integer) and **API Hash** (32-character hex string)
4. Enter these in `.env` along with the phone number in E.164 format (`+447700000000`)

> Use a dedicated monitoring account, not your personal Telegram account.

### Adding Channels

1. Go to **Settings → Channels**
2. Enter the channel username (e.g. `@channelname`) or Telegram channel ID
3. Click **Add Channel**
4. Optionally click **Backfill** to ingest the last 500 historical messages

GhostExodus subscribes to live message events via Telethon's event handler API. The session persists across restarts. FloodWait errors are handled with exponential backoff automatically.

### What is collected per message

- Message text, sender ID/username, timestamp
- Forward chain information
- Media type (PHOTO/DOCUMENT/WEBPAGE/OTHER)
- View and forward counts
- SHA-256 of the complete raw JSON payload
- Keyword match results (category, keyword, pattern type, severity contribution)
- LLM classification (async, for MEDIUM+ severity messages)

---

## Threat Classification Engine

### Built-in Keyword Categories

| Category | Severity Weight | Example Patterns |
|----------|----------------|-----------------|
| OPERATIONAL_PLANNING | 3 | attack, target, operation, surveillance, reconnaissance, weapons acquisition |
| INCITEMENT | 3 | kill, murder, execute, behead, martyr, jihad |
| RECRUITMENT | 2 | join, recruit, pledge, bay'ah, brothers wanted |
| FINANCING | 2 | donate, funding, zakat, hawala, crypto for the cause |
| UK_SPECIFIC | 2 | London, Birmingham, Manchester, Home Office, MI5, PREVENT |
| PROPAGANDA | 1 | nasheed, infidel, crusader, taghut, takfir |

Plus regex patterns for: `@telegram_handles`, `t.me/` invite links, onion addresses, UK phone numbers, encrypted contact references, crypto wallet addresses.

### Severity Calculation

| Match Score | Severity |
|-------------|----------|
| 0 | NONE |
| 1–2 | LOW |
| 3–5 | MEDIUM |
| 6+ | HIGH |

LLM can override to CRITICAL if `severity == "CRITICAL"` in the classification response, or escalate to HIGH if `requires_immediate_action == true`.

### LLM Classification Output

Each classified message receives a JSON object with:
- `threat_category` (OPERATIONAL_PLANNING / RECRUITMENT / etc.)
- `severity` (NONE/LOW/MEDIUM/HIGH/CRITICAL)
- `ttps` (array of MITRE ATT&CK-style tactic strings)
- `target_indicators` (potential targets mentioned)
- `uk_relevance` (boolean)
- `requires_immediate_action` (boolean)
- `reasoning` (analyst-readable explanation)

### Custom Analyst Model — ghostexodus-analyst

GhostExodus uses a custom Ollama model (`ghostexodus-analyst`) rather than a raw base model. It is built from `ghostexodus.Modelfile` and configured specifically for OSINT threat analysis work:

| Parameter | Value | Effect |
|-----------|-------|--------|
| `temperature` | 0.1 | Deterministic, analytical — minimal hallucination |
| `num_ctx` | 4096 | Full context window for long message threads |
| `top_k` | 20 | Reduces random token selection |
| `repeat_penalty` | 1.1 | Suppresses repetitive phrasing in long outputs |

**Baked-in capabilities (few-shot trained):**
- Threat classification → returns valid JSON without prompting for format
- Entity extraction → returns valid JSON array without formatting instructions
- Stylometric comparison → structured similarity scoring
- OSINT analytical prose in formal intelligence report style

**To rebuild the model** after modifying `ghostexodus.Modelfile`:
```batch
ollama create ghostexodus-analyst -f ghostexodus.Modelfile
```

**To use a different base model**, edit the first line of `ghostexodus.Modelfile`:
```
FROM mistral:7b
```
Then rebuild with the command above.

---

## Semantic Search & RAG

### Semantic Search

All messages are embedded using `nomic-embed-text` (768-dimensional vectors) and stored in ChromaDB with cosine similarity metric. Semantic search returns messages ranked by meaning proximity.

### RAG Intelligence Queries

LlamaIndex constructs a retrieval-augmented generation pipeline:
1. Embeds the query
2. Retrieves the top-K most semantically similar messages from ChromaDB
3. Passes retrieved context + query to `ghostexodus-analyst`
4. Returns synthesised answer with source citations

Useful for queries like: *"What logistics planning is occurring in [city]?"* or *"Are there references to a specific individual across channels?"*

---

## Entity Correlation & Graph

### Extracted Entity Types

| Type | Examples |
|------|---------|
| TELEGRAM_HANDLE | `@username`, `t.me/username` |
| PHONE | UK landline/mobile, international E.164 |
| EMAIL | Any email address |
| CRYPTO | Bitcoin/Ethereum/Monero addresses |
| ONION | `.onion` addresses |
| DOMAIN | Referenced web domains |
| ALIAS | LLM-inferred aliases and nicknames |

### Co-occurrence Correlation

Entities that appear together in messages are linked. Pairs with 2+ co-occurrences receive a `linked_entities` edge in the graph with the co-occurrence count as weight. The entity map uses React Flow to render this as a force-directed graph.

### Stylometry

Writing style features extracted per author (Telegram sender):
- Average sentence length
- Type-token ratio (vocabulary richness)
- Top 10 trigrams
- Punctuation ratio, emoji ratio, capitalisation ratio
- Detected language (via langdetect)

`compare_authors(messages_a, messages_b)` computes cosine similarity over the feature vectors and returns a similarity score (0.75+ = high similarity / likely same author).

---

## Evidence Management

### Capture

Every ingested message is archived as:
```
data/evidence/YYYY-MM-DD/{channel_id}_{message_id}.json
```

The JSON file contains the complete raw payload serialised at capture time. The SHA-256 hash of this JSON is stored in the `evidence_manifest` database table alongside:
- `captured_at_utc` — timestamp of capture
- `file_path` — relative path to the JSON file
- `verification_status` — NULL (unchecked), VERIFIED, or TAMPERED

### Integrity Verification

Click **Verify** on any evidence item, or the scheduler runs `verify_integrity_batch()` every 6 hours. The verification re-reads the file, recomputes SHA-256, and compares to the stored hash. Any mismatch is flagged as TAMPERED and written to the audit log.

### Case Bundle Export

Select evidence items and click **Export Case Bundle**. The downloaded ZIP contains:
```
case_bundle_{timestamp}.zip
├── messages/
│   ├── {channel_id}_{message_id}.json
│   └── ...
├── manifest.json          # All hashes + timestamps
├── chain_of_custody.txt   # Human-readable audit trail
└── verification_script.py # Standalone Python verifier (no GhostExodus required)
```

The verification script can be provided to prosecutors or forensic examiners — it requires only Python's standard library.

---

## Intelligence Reports

Reports are generated as PDF (WeasyPrint) with HTML fallback. Generation runs as a background task; the UI polls for completion.

### Case Reference Format

```
GX-YYYYMM-{4-digit-sequence}
Example: GX-202601-0001
```

### Report Sections

1. **Classification header** — `SENSITIVE — LAW ENFORCEMENT USE ONLY`
2. **Report metadata** — case reference, date range, generated by, channels covered
3. **Executive Summary** — LLM-generated 200-word intelligence summary
4. **Actors Identified** — table of extracted entities with occurrence counts
5. **Key Communications** — top 10 messages by severity with text excerpts
6. **TTP Assessment** — LLM analysis of tactics, techniques, and procedures
7. **Network Relationships** — LLM analysis of inter-actor connections
8. **Temporal Analysis** — LLM analysis of operational tempo and timing patterns
9. **UK Relevance Assessment** — LLM assessment of UK-specific threat indicators
10. **Evidence Reference List** — all archived messages in scope with SHA-256 hashes
11. **Analyst Notes & Recommended Actions** — LLM-generated, manual review required disclaimer

---

## Alert Rules

### Rule Types

| Type | Trigger Value Format | Example |
|------|---------------------|---------|
| KEYWORD | Regex pattern or exact string | `bomb.{0,20}london` |
| ENTITY | Entity value substring | `@suspicious_handle` |
| FREQUENCY | `N:M` (N messages in M minutes) | `50:60` = 50 msgs in 60 min |

### Actions

| Action | Effect |
|--------|--------|
| ARCHIVE | Sets `is_archived=True` on the triggering message |
| NOTIFY | Sends email (SMTP) and/or push notification (ntfy.sh) |
| BOTH | Archive + Notify |

### Notifications

- **Email**: configure `SMTP_*` and `ALERT_EMAIL_TO` in `.env`; supports TLS (port 465) and STARTTLS (port 587)
- **Push**: configure `NTFY_URL` with your ntfy.sh topic; notifications appear on mobile/desktop ntfy apps

---

## API Reference

Interactive Swagger UI: `http://localhost:8000/api/docs`
ReDoc: `http://localhost:8000/api/redoc`

### Key Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/feed` | Paginated message feed with severity/channel filters |
| GET | `/api/messages/{id}` | Full message detail with linked entities |
| PATCH | `/api/messages/{id}/severity` | Override severity (ANALYST+) |
| WS | `/api/feed/live` | WebSocket live message stream |
| POST | `/api/search` | Semantic/keyword/entity/RAG search |
| GET | `/api/entities/graph` | React Flow graph data |
| GET | `/api/entities/{id}` | Entity detail with stylometry and recent messages |
| GET | `/api/timeline` | Time-series message volume data |
| GET | `/api/timeline/hourly` | Hourly distribution + peak detection |
| GET | `/api/alerts/rules` | List alert rules |
| POST | `/api/alerts/rules` | Create alert rule (ANALYST+) |
| POST | `/api/alerts/rules/{id}/test` | Test rule against recent messages |
| POST | `/api/reports/generate` | Trigger async report generation (ANALYST+) |
| GET | `/api/reports/{id}/download` | Download report PDF/HTML |
| GET | `/api/evidence` | Evidence manifest list |
| GET | `/api/evidence/{id}/verify` | Run integrity check |
| POST | `/api/evidence/export-bundle` | Export case bundle ZIP |
| GET | `/api/channels` | Monitored channels list |
| POST | `/api/channels` | Add channel (ANALYST+) |
| GET | `/api/admin/users` | User list (ADMIN only) |
| POST | `/api/admin/users` | Create user (ADMIN only) |
| GET | `/api/admin/audit-log` | Full audit trail (ADMIN only) |
| GET | `/api/admin/system/status` | System health status |

---

## Building the Windows Installer

### Prerequisites

- Windows machine with Python 3.11+, Node.js 18+
- [Inno Setup 6](https://jrsoftware.org/isinfo.php) (optional — builds raw bundle without it)
- UPX for compression (optional)

### Build

```batch
build_installer.bat
```

The script runs these steps:
1. Checks Python and Node.js are installed
2. Builds the React frontend (`npm install && npm run build`)
3. Creates an isolated Python venv for the build
4. Installs `requirements.txt` + `pyinstaller==6.11.1` into the build venv
5. Cleans previous `build/` and `dist/` directories
6. Runs `pyinstaller ghostexodus.spec` — produces `dist/GhostExodus/GhostExodus.exe`
7. Copies `ghostexodus.Modelfile` and `installer/setup_models.bat` into `dist/GhostExodus/`
8. Runs Inno Setup compiler to produce `installer/output/GhostExodus_Setup_v1.0.0.exe`

The resulting installer includes the `ghostexodus.Modelfile` and `setup_models.bat` — users run the model setup script once after installation to pull the base model and build `ghostexodus-analyst`.

If Inno Setup is not found, the script exits gracefully with instructions and leaves the raw `dist/GhostExodus/` bundle ready to run directly.

### Customising the installer

Edit `installer/ghostexodus.iss` to change:
- `AppVersion` — version number
- `DefaultDirName` — installation path
- Compression level (`Compression=lzma2/ultra64`)
- Whether to include startup registry entry by default

---

## Architecture

```
GhostExodus.exe (PyInstaller --onedir)
│
├── launcher.py              Entry point — sets up paths, loads .env,
│                            starts uvicorn in-process, opens browser
│
└── backend/
    ├── main.py              FastAPI app — lifespan starts monitors + scheduler
    │                        Serves React SPA from /backend/static/
    │
    ├── config.py            Pydantic Settings — all config from .env
    ├── database.py          9 SQLModel tables + write_audit_log() helper
    │
    ├── auth/                JWT auth, bcrypt, RBAC dependencies
    ├── collector/           Telethon connection, channel monitoring,
    │                        keyword engine, APScheduler jobs
    ├── intelligence/        Ollama LLM client (semaphore-serialised),
    │                        ChromaDB vector store, LlamaIndex RAG,
    │                        entity extractor, stylometry
    ├── evidence/            SHA-256 archiver, case bundle export,
    │                        chain-of-custody log
    ├── reports/             WeasyPrint PDF generator, Jinja2 templates
    ├── alerts/              Rules engine, email/push notifier
    └── routers/             FastAPI routers for all API endpoints
```

### Data Flow — Message Ingestion

```
Telegram channel
      │ (Telethon event)
      ▼
_process_message()
      ├── SHA-256 hash raw JSON
      ├── Deduplicate (channel_id + telegram_message_id)
      ├── keyword_engine.match_keywords() → severity
      ├── archive_message() → data/evidence/YYYY-MM-DD/
      ├── asyncio.create_task(_embed_message_async())  → ChromaDB
      ├── asyncio.create_task(_classify_async())       → Ollama LLM [MEDIUM+]
      └── asyncio.create_task(_evaluate_alerts())      → alert rules
            │
            └── broadcast() → WebSocket clients → Dashboard live feed
```

### Ollama Concurrency

All Ollama calls are serialised through a single `asyncio.Semaphore(1)` to prevent VRAM exhaustion on an 8 GB card. Classification, embedding, and RAG queries queue behind each other. Embedding runs at a lower effective priority (fire-and-forget) and will not block message ingestion.

---

## Security Notes

1. **`.env` file** — contains Telegram credentials and JWT secret. Never commit to version control. The `.gitignore` excludes it.
2. **Telegram session file** (`data/telegram.session`) — contains authenticated session tokens. Handle as a credential.
3. **Evidence directory** — contains raw intelligence data. Handle according to your organisation's data handling policies and legal obligations.
4. **JWT secret** — use a strong 32-byte random secret. The default placeholder will be rejected in a future version.
5. **All user actions** are logged to the audit trail. The audit log table is append-only by design.
6. **SHA-256 hashes** are computed on raw serialised JSON at capture time, before any processing or transformation. This ensures admissibility of the hash as representing the original captured content.
7. **Network binding** — the server binds to `127.0.0.1:8000` only. It is not exposed to the network unless you deliberately change the host setting.
8. **Role enforcement** — roles are enforced on the API server, not just in the UI. A VIEWER token will receive 403 on any ANALYST+ endpoint regardless of UI state.

---

## Technology Stack

| Layer | Technology | Version |
|-------|-----------|---------|
| Backend API | FastAPI | 0.111+ |
| ASGI server | Uvicorn | 0.30+ |
| Telegram client | Telethon | 1.36+ |
| Vector DB | ChromaDB | 0.5+ |
| Relational DB | SQLite via SQLModel | 0.0.19+ |
| ORM | SQLAlchemy (async) | 2.0+ |
| LLM inference | Ollama | ghostexodus-analyst (llama3.1:8b base) |
| Embeddings | Ollama | nomic-embed-text |
| RAG framework | LlamaIndex | 0.10+ |
| Authentication | python-jose (JWT) | 3.3+ |
| Password hashing | bcrypt | 4.0+ |
| Task scheduling | APScheduler | 3.10+ |
| HTTP client | httpx + aiohttp | — |
| PDF generation | WeasyPrint | 62+ |
| Template engine | Jinja2 | 3.1+ |
| Frontend | React 18 + Vite 5 + Tailwind CSS v3 | — |
| Charting | Recharts | 2.x |
| Graph visualisation | React Flow | 11.x |
| State management | Zustand | 4.x |
| HTTP client (frontend) | Axios | 1.x |
| Fonts | IBM Plex Mono, JetBrains Mono, Inter | (Google Fonts) |
| Build system (Windows) | PyInstaller 6.11 + Inno Setup 6 | — |
| Evidence hashing | SHA-256 (Python hashlib) | — |

---

## Classification

```
SENSITIVE — LAW ENFORCEMENT USE ONLY
Built for local deployment. No cloud dependencies. All data stays on device.
This platform is intended for use by authorised personnel only.
Misuse may constitute a criminal offence under the Computer Misuse Act 1990.
```

---

*GhostExodus OSINT Platform v1.0.0 — CT-OSINT Intelligence*
*Built for counter-extremism intelligence operations in support of UK law enforcement.*
