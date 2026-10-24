# CryptoTrace — Cryptocurrency Fraud Investigation Dashboard

A full-stack educational investigation dashboard with a React + TypeScript + Tailwind frontend and Python FastAPI backend. It ships with fictional demo data only.

## Features
- Public landing page and dashboard shell
- Register/login/logout with bcrypt password hashing and server-side bearer sessions
- Role-aware API permissions (Administrator, Investigator, Analyst, Auditor)
- Transaction search and filters, wallet profiles, transaction graph data
- Deterministic explainable suspicious-activity rules
- Alerts, investigation cases, case notes, CSV export with spreadsheet formula safety
- Mentor lessons and per-user progress
- SQLite local mode, PostgreSQL deployment configuration
- API docs at `/docs`, tests, seed script, `.env.example`

> **Safety and scope:** alerts are investigative leads, not proof of wrongdoing. All seeded data is fictional and labeled DEMO DATA. This starter project is not independently security-audited and should not be used for real investigations or sensitive production data without review.

## Requirements
- Python 3.11+
- Node.js 20+
- npm

## Run locally

### 1. Backend
```bash
cd backend
python -m venv .venv
# Windows PowerShell:
.venv\Scripts\Activate.ps1
# macOS/Linux:
source .venv/bin/activate
pip install -r requirements.txt
copy .env.example .env  # Windows; on macOS/Linux use: cp .env.example .env
python seed.py
uvicorn app.main:app --reload
```
API docs: http://127.0.0.1:8000/docs

Demo account (created by `seed.py`):
- Email: `admin@cryptotrace.local`
- Password: `ChangeMe123!`
Change this password immediately for any non-demo use. The seed account is for local demo only.

### 2. Frontend
Open another terminal:
```bash
cd frontend
npm install
npm run dev
```
Open the URL printed by Vite (normally http://localhost:5173).

## Tests
From `backend/` with the virtual environment active:
```bash
pytest -q
```

## Database configuration
SQLite is used by default at `backend/cryptotrace.db`. For PostgreSQL set `DATABASE_URL` in `.env`, for example:
`postgresql+psycopg://cryptotrace:password@localhost:5432/cryptotrace`

For production, configure a strong `SECRET_KEY`, HTTPS, secure cookies / token transport, strict CORS, TLS database connections, backups, migrations, monitoring, email provider, and independent security review. This starter uses revocable opaque bearer sessions; production deployments should consider secure HttpOnly cookie sessions with CSRF protections based on the deployment architecture.

## Push to GitHub
Create an empty repository on GitHub, then from this project folder:
```bash
git init
git add .
git commit -m "Build CryptoTrace full-stack dashboard"
git branch -M main
git remote add origin https://github.com/YOUR_USERNAME/YOUR_REPOSITORY.git
git push -u origin main
```
Never commit `.env`, database files, API keys, or real user data.

## Project layout
```text
cryptotrace/
  backend/
    app/main.py
    app/database.py
    app/models.py
    app/security.py
    seed.py
    tests/test_api.py
  frontend/
    src/App.tsx
    src/main.tsx
    src/index.css
  docs/
    architecture.md
    threat-model.md
    security-checklist.md
  .env.example
```
