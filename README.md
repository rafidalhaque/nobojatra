# Nobojatra — Internal Notice Board & Inter-Branch Portal

Auth-gated portal replacing the org's WordPress site. Notice board + org-unit-to-org-unit
messaging. No public surface, no self-registration. See `docs/spec.md`, `docs/prompt.md`.

## Stack

FastAPI + PostgreSQL (two-tier user model + RLS) + S3 (SSE) + ntfy + SvelteKit (CSR/static).
Backend deps via **uv**. Everything dockerized (`docker compose up`).

## Layout

```
app/                FastAPI application
  routers/          one module per resource group
  models.py         SQLAlchemy 2.0 models
  permissions.py    granular permission engine + seed catalog
  deps.py           auth, RLS session scoping, permission guards
  cli.py            create-super-admin (CLI-only, no UI path)
alembic/            migrations (run as schema-owner user only)
scripts/            export_openapi.py -> docs/spec.yml (CI artifact)
docker/             postgres-init.sh (provisions RLS-constrained app role)
tests/              DB-free self-checks
frontend/           SvelteKit app  (next phase)
```

## Run — Docker

```bash
cp .env.example .env          # then set JWT_SECRET and passwords
docker compose up --build     # postgres, minio, ntfy, migrate (one-shot), api, web
docker compose run --rm api uv run python -m app.cli create-super-admin --username root
```

- App: http://localhost  (nginx serves the static build, proxies `/api` to the API)
- API direct: http://localhost:8000 — `/docs` Swagger, `/health` liveness
- MinIO console: http://localhost:9001

## Run — frontend alone

```bash
cd frontend
cp .env.example .env
npm install
npm run dev        # http://localhost:5173 , proxies /api -> localhost:8000
npm run build      # -> frontend/build (static; login.html is prerendered)
```

## Run — local backend

```bash
uv sync
uv run alembic upgrade head            # uses DATABASE_URL_OWNER
uv run uvicorn app.main:app --reload   # uses DATABASE_URL (app user)
uv run python -m app.cli create-super-admin --username root
```

## Checks

```bash
uv run ruff check app scripts alembic
PYTHONPATH=. uv run python tests/test_basic.py
uv run python scripts/export_openapi.py   # regenerate docs/spec.yml
```

## Security model (enforced, not optional)

- **Two Postgres roles.** `nobojatra_owner` owns the schema + runs migrations.
  `nobojatra_app` is the only runtime role, has DML but no DDL, and is subject to RLS.
- **RLS** on `posts`, `messages`, `notifications`, scoped by
  `app.current_org_unit` / `app.is_super_admin` session vars set per request in `deps.py`.
- **Zero pre-auth visibility** — every route except `/auth/login` + `/health` requires a
  valid token. Media is streamed through an auth-gated proxy; no public S3 URLs.
- **`Cache-Control: no-store`** on every API response (middleware).
- **JWT** in an httpOnly + Secure + SameSite=Strict cookie. Expiry from `JWT_EXPIRY_SECONDS`.
- **Super Admin** bypasses the permission engine entirely.

## Frontend

SvelteKit, `adapter-static`, no SSR server. `/login` is prerendered to a real static
`login.html` (branded, paints before the app bundle). Everything under `(app)/` is pure
CSR behind the SPA fallback — zero pre-auth content in the build. Auth is the httpOnly
cookie; the client stores nothing. Theme + language come from `/auth/me` after login,
OS `prefers-color-scheme` before. i18n en/bn via `src/lib/i18n`. Fonts self-hosted —
drop the `.woff2` files in `frontend/static/fonts/` (see the README there).

Identity: official-bulletin — Tiro Bangla + Carlito, bottle-green board, bone paper,
a red-oxide **issuing stamp** on every notice/message (attribution is always the org
unit, never a person).

## What's built vs. pending

Done: backend (auth, areas, org-units + CSV import, categories, posts with
search/filter/media, messaging, notifications + ntfy fan-out, live permission matrix,
RLS migrations, compose). Frontend (login shell, app shell + nav, feed + filters, post
view with Markdown, post editor, messaging, notifications page, permission-matrix admin,
i18n, theming, nginx).

Pending: real font files, Bangla copy review, admin panels for categories/areas/per-unit
permission overrides, CI step for `docs/spec.yml`, TLS termination, tests for the
frontend and for backend RLS/permission paths against a live DB.
