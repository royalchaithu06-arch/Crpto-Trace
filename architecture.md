# Architecture

```mermaid
flowchart LR
  Browser[React + TypeScript + Tailwind] -->|JSON over HTTP| API[FastAPI REST API]
  API --> Auth[Password hashing + revocable sessions]
  API --> Rules[Deterministic detection rules]
  API --> DB[(SQLite local / PostgreSQL deployment)]
  API --> Audit[Audit events]
  API --> Export[CSV report generator]
```

- Frontend is a Vite single-page app.
- Backend validates inputs with Pydantic and enforces role checks in dependencies.
- SQLAlchemy models support SQLite local demo and PostgreSQL deployment.
- Demo records are fictional and clearly identified as DEMO DATA.
