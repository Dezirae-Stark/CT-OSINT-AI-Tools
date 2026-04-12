# GhostExodus OSINT Platform

Counter-extremism intelligence monitoring suite for UK law enforcement support.
Monitors Telegram channels, performs automated entity correlation, generates structured
intelligence reports, and maintains a legally defensible evidence archive.

**Runtime:** Windows 11 · Alienware Aurora 16 · RTX 5060 8GB · 16GB RAM
**Fully local — no cloud dependencies. All data stays on device.**

---

## Technology Stack

| Layer | Technology |
|-------|-----------|
| Backend API | FastAPI (Python 3.11+, async) |
| Telegram collector | Telethon (MTProto API) |
| Vector DB | ChromaDB (local, persistent) |
| Relational DB | SQLite via SQLModel |
| LLM inference | Ollama (llama3.1:8b) |
| Embeddings | Ollama (nomic-embed-text) |
| RAG framework | LlamaIndex |
| Authentication | JWT + bcrypt |
| Task scheduling | APScheduler |
| Frontend | React 18 + Vite + Tailwind CSS v3 |
| Charting | Recharts |
| Graph viz | React Flow |
| PDF reports | WeasyPrint |
| Evidence hashing | SHA-256 + SQLite audit log |

---

## Prerequisites

Before running setup, install:

1. **Python 3.11+** — [python.org](https://www.python.org/downloads/)
2. **Node.js 18+** — [nodejs.org](https://nodejs.org/)
3. **Ollama** — [ollama.com](https://ollama.com/) — run `ollama serve` before starting

---

## Quick Start (Windows)

### 1. Clone the repository

```batch
git clone https://github.com/Dezirae-Stark/CT-OSINT-AI-Tools.git ghostexodus
cd ghostexodus
```

### 2. Get Telegram API credentials

1. Go to [my.telegram.org/apps](https://my.telegram.org/apps)
2. Sign in with your Telegram account
3. Create a new application
4. Note your **API ID** and **API Hash**

### 3. Run the setup script

```batch
setup_windows.bat
```

This will:
- Install Python dependencies
- Pull Ollama models (`llama3.1:8b` and `nomic-embed-text`)
- Build and deploy the React frontend
- Create the `data/` directory structure
- Create `.env` from the template

### 4. Configure `.env`

Open `.env` and fill in:

```env
TELEGRAM_API_ID=12345678
TELEGRAM_API_HASH=abcdef1234567890abcdef1234567890
TELEGRAM_PHONE=+447700000000
JWT_SECRET=your-strong-random-secret-here
```

Generate a JWT secret:
```batch
python -c "import secrets; print(secrets.token_hex(32))"
```

### 5. Start the platform

```batch
cd backend
uvicorn main:app --host 127.0.0.1 --port 8000
```

### 6. First run

1. Open [http://localhost:8000](http://localhost:8000)
2. The first-run wizard will prompt you to create an admin account
3. **Telegram authentication**: On first startup with Telegram configured, the terminal
   will prompt for your phone verification code. Enter it to authorise the session.
   The session file is saved to `data/telegram.session` for subsequent runs.

---

## Development Mode

Run frontend with hot reload:

```batch
# Terminal 1 — Backend
cd backend
uvicorn main:app --host 127.0.0.1 --port 8000 --reload

# Terminal 2 — Frontend
cd frontend
npm run dev
```

Set `ENV=development` in `.env` to enable CORS for the dev server.

---

## User Roles

| Role | Permissions |
|------|------------|
| ADMIN | Full access — user management, channel management, all operations |
| ANALYST | Search, search & export, report generation, alert rule management |
| VIEWER | Read-only — view feed, search, timeline, entity map |

---

## Key Features

### Live Monitoring
- Telethon MTProto connection to monitored Telegram channels
- Real-time message ingestion with keyword matching
- WebSocket live feed to dashboard

### Threat Classification
- 6-category keyword engine (Operational Planning, Recruitment, Financing, Propaganda, UK-Specific, Incitement)
- Asynchronous LLM classification for medium+ severity messages
- User-defined alert rules with regex support

### Semantic Search
- ChromaDB vector store with nomic-embed-text embeddings
- LlamaIndex RAG pipeline for intelligence queries
- Keyword, entity, and semantic search modes

### Evidence Management
- SHA-256 hash at capture time on raw JSON payload
- Timestamped evidence archive (`data/evidence/YYYY-MM-DD/`)
- Case bundle export: ZIP with manifest, custody trail, verification script
- Integrity verification: re-hash and compare to stored hash

### Intelligence Reports
- INTELREPORT PDF via WeasyPrint + Jinja2
- LLM-generated executive summary, TTP assessment, UK relevance assessment
- Evidence reference list with hashes
- Formal classification header: `SENSITIVE — LAW ENFORCEMENT USE ONLY`

### Entity Correlation
- Regex + LLM hybrid entity extraction
- Co-occurrence graph for React Flow visualisation
- Stylometry: writing style fingerprinting and author comparison

---

## API Documentation

Interactive API docs available at [http://localhost:8000/api/docs](http://localhost:8000/api/docs)

---

## Important Security Notes

1. **The `.env` file contains sensitive credentials** — never commit it to version control
2. **The Telegram session file** (`data/telegram.session`) contains authentication tokens — never commit
3. **Evidence directory** contains raw intelligence data — handle according to your organisation's data handling policies
4. **All API actions** by authenticated users are logged to the audit trail
5. SHA-256 hashes are computed on raw content at capture time before any processing

---

## Running as a Windows Service (Optional)

Use NSSM (Non-Sucking Service Manager) to run as a background Windows service:

```batch
nssm install GhostExodus "C:\path\to\python.exe" "C:\path\to\ghostexodus\backend\main_service.py"
nssm set GhostExodus AppDirectory "C:\path\to\ghostexodus\backend"
nssm start GhostExodus
```

---

## Classification

```
SENSITIVE — LAW ENFORCEMENT USE ONLY
Built for local deployment. No cloud dependencies. All data stays on device.
```

---

*GhostExodus OSINT Platform — Counter-Extremism Intelligence Suite*
