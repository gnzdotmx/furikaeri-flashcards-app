# Developer guide

For **normal use** (default settings), see [README.md](README.md). This guide is for **custom installs** (different ports, paths, study settings) and **contributors** (tech stack, APIs, testing).

---

## Run the app

**Prerequisites:** Docker and Docker Compose. From the **project root** (where `compose.yml` and `Makefile` are):

```bash
make run
```

- **App:** http://localhost:8000  
- **Health:** http://localhost:8000/health  

Stop: `make stop`.

### Environment variables

Copy `.env.example` to `.env` and edit. Common overrides:

| Variable | Purpose |
|----------|---------|
| `APP_ENV` | Environment name (e.g. `production`) |
| `SQLITE_PATH` | Path to SQLite database file |
| `CORS_ALLOW_ORIGINS` | Allowed origins for CORS (comma-separated) |
| `JWT_SECRET` | Secret for JWT (required; at least 32 characters in production) |
| `STUDY_CONFIG_PATH` | Path to optional `study_config.yaml` (scheduler/session/import limits) |

See `.env.example` for the full list.

- **Production:** Session cookie is `HttpOnly`, `SameSite=Lax`, and `Secure` when `APP_ENV=production`. Serve over **HTTPS** (e.g. reverse proxy with TLS).
- **CORS:** Same-origin deployment needs no CORS config. For a separate frontend origin, set `CORS_ALLOW_ORIGINS` to explicit origins (e.g. `https://app.example.com`). Do **not** use `*` in production.
- **Data (Docker):** Volume `flashcards_data` is mounted at `/data`. SQLite default: `/data/flashcards.sqlite`. Audio cache: `/data/audio_cache/`. When overriding `SQLITE_PATH`, use a path the container can read/write.

---

## Tech stack

| Layer | Stack |
|-------|--------|
| **Backend** | Python 3.12+, FastAPI, Uvicorn, SQLite (WAL), Pydantic |
| **Auth** | JWT (HS256), Argon2 password hashing, server-side sessions (`auth_sessions` table) |
| **Frontend** | React 18, TypeScript, Vite 5, Vitest |
| **Scheduler** | FSRS-style spaced repetition (stability/difficulty, learning steps) |
| **TTS** | espeak-ng (cached audio for reading/listening cards) |
| **Config** | Env vars (`.env.example`); optional YAML (`study_config.yaml`) |

Backend deps: `flashcards/app/api/pyproject.toml`. Frontend deps: `flashcards/app/web/package.json`. One Dockerfile builds the API and serves the built web app when `SERVE_WEB=true`.

---

## Project structure

```
flashcards/app/
├── api/                    # Backend (FastAPI)
│   ├── app/
│   │   ├── auth/           # JWT, password hashing, dependencies
│   │   ├── db.py           # SQLite connection, migrations, transaction helper
│   │   ├── logging_config.py
│   │   ├── main.py         # FastAPI app, middleware, static files, health/version
│   │   ├── migrations/    # SQL migrations (0001_init.sql, …)
│   │   ├── middleware/    # Auth session, rate limit, security headers
│   │   ├── personalization/ # Bandit, user prefs, FSRS params
│   │   ├── repositories/  # Data access (users, decks, cards, notes, sessions, …)
│   │   ├── routes/        # API route modules (auth, sessions, cards, imports, metrics, tts, admin)
│   │   ├── scheduler/     # FSRS-style scheduler, clock, strategy
│   │   ├── settings.py
│   │   ├── study_config.py # Study/scheduler/session/limits/import config (defaults + YAML)
│   │   ├── tts/           # TTS strategy, espeak, cache, kana
│   │   ├── exports/       # CSV export
│   │   ├── imports/       # CSV import (grammar/kanji/vocab), adapters
│   │   ├── cards/         # Card factory, types
│   │   └── version.py
│   ├── scripts/           # reset_data.py, audit
│   ├── conftest.py        # Pytest: JWT_SECRET for tests
│   ├── pyproject.toml
│   └── AUTH.md            # Auth/sessions documentation
└── web/                   # Frontend (React, Vite)
    ├── src/
    │   ├── api.ts         # API client, auth token
    │   ├── App.tsx        # Tabs, routing, error boundary
    │   ├── context/       # AuthContext, AppContext, StudyContext
    │   ├── tabs/          # Study, Decks, Import, Search, Metrics, Leeches, Account
    │   ├── views/         # LandingView (login/register)
    │   └── components/    # StudyCard, ErrorBoundary, ErrorFallback
    ├── package.json       # Exact versions; package-lock.json is source of truth
    └── vite.config.ts
```

### Frontend dependencies (web)

- `package.json` uses **exact versions** (no `^` or `~`). **`package-lock.json`** is the source of truth; use **`npm ci`** in CI and Docker (Dockerfile already does).
- To upgrade: change the version in `package.json`, run `npm install`, commit both files.
- To inspect versions: from `flashcards/app/web/` run `npm run versions` (or `npm ls`).

### Study by label

- Cards can have **label tags** (e.g. `label:foo`) in `tags_json`. Grammar, Kanji, and Vocabulary CSV imports support an optional **`labels`** column (values split on `;` or `,`, then normalized). Kanji and Grammar cards get the same `label:*` tags when `labels` is present.
- **Study by label:** In the Study tab, pick a deck, optionally a label, then “Start label session”. Backend: `nextCard` accepts `?label=label:...`; labels at `GET /api/decks/{deck_id}/labels`. Frontend: `StudyContext` keeps `studyLabel` and `activeLabelFilter`.

### CSV import and deck export formats

Imports are implemented in `app/imports/adapters.py` (`GrammarCsvAdapter`, `KanjiCsvAdapter`, `VocabularyCsvAdapter`). Rows are validated with per-cell length limits from `study_config` (`import.max_cell_chars_default`, default 20_000). UTF-8 (with BOM allowed); use `csv` quoting for cells that contain commas or newlines.

**Optional columns (all types that support them):**

| Column | Purpose |
|--------|--------|
| `labels` | Short tags; split on `;` or `,`; stored in note `fields_json` and emitted as `label:*` card tags. |
| `notes` | Longer free text; stored in note `fields_json`; copied into card `back_template` as `notes` when non-empty; shown in the UI as “Deck note”. Normalized with NFKC; internal newlines preserved (unlike `norm_text` on other fields). Only read if a `notes` header exists. When exporting a deck, this `notes` cell may also include your per-card **My note** text (from `card_study_notes`) merged for the authenticated account. |

**Recommended header order** (matches **deck export** in `app/exports/deck_export.py` for round-trip):

- **Grammar:** `japanese_expression`, `english_meaning`, `grammar_structure`, `labels`, `notes`, `example_1` … `example_5` (more `example_*` columns are still collected as examples).
- **Kanji:** `rank`, `kanji`, `onyomi`, `kunyomi`, `meaning`, `labels`, `notes`, `example_1` …
- **Vocabulary:** `rank`, `word`, `reading_kana`, `reading_romaji`, `part_of_speech`, `labels`, `notes`, `meaning`, `example_1` …

**Vocabulary column order:** `meaning` may appear before or after `labels`/`notes` in the file; `DictReader` matches by name. Repo JLPT vocab CSVs under `data/jlpt/` use `…, part_of_speech, meaning, labels, notes, example_1, …`.

**Export:** `export_deck_csv` writes one row per content note using the same field names; cells are passed through `sanitize_csv_cell` in `app/exports/csv_export.py` to reduce spreadsheet formula injection when opened in Excel/Sheets.
For authenticated exports, deck CSV `notes` is composed of the deck note plus distinct per-card **My note** bodies for cards that share the same note (merged into a single CSV cell). Re-import stores that merged text back into the deck CSV `notes` field (shown as **Deck note**), not as separate per-card `card_study_notes` rows.

### Sync / merge behavior
When syncing/importing with **Merge examples into existing**, examples are merged/deduped while deck `notes` are preserved unless the incoming CSV row has a non-empty `notes` cell.

---

## Auth and API

See **`flashcards/app/api/AUTH.md`** for full details. Summary:

- **Required env:** `JWT_SECRET` (at least 32 characters). Optional: `JWT_ALGORITHM` (default `HS256`).
- **Endpoints:** `POST /api/auth/register`, `POST /api/auth/login`, `POST /api/auth/logout`, `GET /api/auth/me`. All other `/api/*` routes require a valid Bearer token and matching row in `auth_sessions`.
- **Middleware:** Auth session (outer) → rate limit → security headers. Public paths: `/health`, `/api/health`, `/api/version`, `/api/auth/register`, `/api/auth/login`.
- **Frontend:** Token in `sessionStorage`; sent as `Authorization: Bearer`; optional HttpOnly cookie `furikaeri_session` for same-origin.
- **Validation:** Path/query/body IDs are length-limited (e.g. 80 chars). Enums allowlisted. CSV upload size capped (default 50 MiB).

---

## Scheduler and study config

- **Scheduler:** FSRS-style in `app/scheduler/` (`fsrs.py`, `strategy.py`, `clock.py`). Cards have stability, difficulty, learning step; new cards go through learning steps then intervals. Target retention and learning steps come from study config.
- **Study config:** `app/study_config.py` loads defaults and optional YAML. Path: env `STUDY_CONFIG_PATH` or `{DATA_DIR}/study_config.yaml` or `./study_config.yaml`. See `study_config.yaml.example` for keys (SchedulerConfig, SessionConfig, LimitsConfig, ImportConfig). Values are validated and clamped; invalid or missing keys fall back to defaults.
- **Custom study config:** Copy `flashcards/app/api/study_config.yaml.example` to `study_config.yaml` in your data directory (e.g. `/data` in Docker) or set `STUDY_CONFIG_PATH`; restart the app after changes.

---

## API routes (prefix `/api`)

| Router | Purpose |
|--------|---------|
| **auth** | register, login, logout, me |
| **sessions** | start session, submit rating, end session, session state |
| **cards** | decks list, deck detail, cards list, notes, leeches, suspend/unsuspend, export CSV, delete deck |
| **imports** | import CSV (grammar/kanji/vocab), merge/skip options |
| **metrics** | retention proxy, streak, daily goal, rating distribution, time per card |
| **tts** | generate/cache audio for text |
| **admin** | debug/health-style endpoints if needed |

Routes use repositories for DB access; auth dependency injects current user. See `app/routes/__init__.py` for inclusion.

---

## Database

- **SQLite** with WAL; path from env `SQLITE_PATH` (default `{DATA_DIR}/flashcards.sqlite`). Migrations in `app/migrations/` applied on startup; version in `schema_migrations`.
- **Key tables:** `users`, `auth_sessions`, `decks`, `notes`, `cards`, `review_state`, `study_sessions`, `session_seen`, `events`, `bandit_state`, `user_prefs`, `user_fsrs_params`. Foreign keys enabled; scripts (e.g. `reset_data.py`) respect delete order.

---

## Testing and lint

- **Run:** From project root, `make run`. App at http://localhost:8000.
- **Tests (recommended):** From the **project root**, `make test` — runs API pytest and web Vitest **in Docker** (same as CI).
- **Lint:** API: Ruff (`make lint`). Web: ESLint, Prettier (`npm run lint`, `npm run fmt` in `flashcards/app/web/` or via `make lint` / `make fmt`).

---

## Useful commands

From the **project root** unless noted.

| Command | Description |
|--------|-------------|
| `make run` | Build (if needed), start containers. App at http://localhost:8000 |
| `make stop` | Stop containers |
| `make test` | Run API tests (pytest) and web tests (Vitest) **in containers** (CI-style) |
| `make lint` | Lint API (Ruff) and web (ESLint) |
| `make fmt` | Format API (Ruff) and web (Prettier) |
| `make audit` | Run API and web security audits (e.g. pip-audit, npm audit) |
| `make reset-data` | Reset all deck/user data. Prompts for `yes` to confirm |
| `make logs` | Follow container logs (tail 200 lines) |
| `docker compose build --no-cache` | Rebuild API image from scratch (after Dockerfile or dependency changes) |

For reproducible web installs in CI/Docker, use **`npm ci`** (see `flashcards/app/web/package.json` and lockfile).

---

## Reset data

To clear all decks, cards, and review state:

1. **Reset script (recommended):** From project root, `make reset-data` (prompts for `yes`).
2. **Remove volume:** `make stop`, then `docker compose down -v`, then `make run`.

---

## Deploy / sync to server

From project root, sync repo to a server (excluding `./data` and `.gitignore`):

```bash
rsync -avz --exclude-from=.gitignore --exclude=data ./ user@YOUR_SERVER:/path/to/pj-furikaeri-flashcards-app/
```

Replace `user@YOUR_SERVER` and the target path. The trailing `/` after `./` copies the **contents** of the current directory into the target path.

**Never commit `.env` or real secrets.** In production, serve over **HTTPS** so the session cookie’s `Secure` flag takes effect.
