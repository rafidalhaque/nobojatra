# AI Build Prompt — Internal Notice Board & Inter-Branch Portal

Use this prompt to brief an AI coding assistant (e.g. Claude Code) to scaffold or build this project. Paste it as-is, or trim to whichever phase you're working on.

---

You are building an internal, authentication-gated web portal for an organization to replace their current WordPress site. It functions as a notice board and lightweight inter-branch/inter-department communication tool. This is **not** a public-facing product — every screen requires a successful login, and there is no self-registration anywhere in the system.

## Tech stack (fixed — do not substitute without asking)
- **Backend:** FastAPI (Python), package/dependency management via **uv** — not pip/poetry/pipenv. `pyproject.toml` + `uv.lock` are the source of truth; run/install via `uv run` / `uv sync`. The backend Dockerfile should build using `uv` (official `uv` base image or bootstrap install), not `pip install -r requirements.txt`.
- **Database:** PostgreSQL — use a two-tier user model: a schema-owner user for Alembic migrations only, and a separate RLS-constrained application user for all runtime queries. Never let the runtime app user run migrations or own the schema.
- **Object storage:** S3-compatible storage, server-side encryption (SSE) enabled on the bucket.
- **Frontend:** SvelteKit, running in **static/CSR mode only** — do not use SvelteKit's SSR server or any server-rendering of authenticated content. The build should be deployable as static assets.
- **Notifications delivery:** self-hosted **ntfy** instance — used only as the push/delivery transport. The DB `notifications` table (see below) is the source of truth, not ntfy.
- **Mobile app:** none in v1 (Kotlin/Android planned for v2 — do not scaffold it now).
- **Version control:** Git, from the first commit. Never commit secrets — use `.env` files (git-ignored) or a secret manager, matching the pattern used on the org's other projects.
- **Deployment:** everything dockerized, brought up via `docker-compose` (API, DB, frontend build/serve step, and any worker/nginx services needed).
- **API docs:** an OpenAPI `spec.yml` must be a build/CI-generated artifact from the FastAPI app's own schema generation — not hand-written. Treat "docs drift from code" as a bug class to design against, not something to fix manually later.

## Roles & identity model
- Three effective role tiers: **Super Admin** (CLI-created only, no UI path — ever), **Admin** (tied to a Department), **Non-Admin** (tied to a Branch).
- Members belong to exactly one Branch or one Department and inherit that unit's Admin/Non-Admin status.
- There is no self-registration for members, branches, or departments. All account and org-unit creation flows are Super-Admin-driven (member creation may be delegated to Admins later — confirm before building).
- Individual members must never appear in any public/shared list or profile view. Only branch/department identities are ever exposed to other users.

## Core domain objects

**Area**
- Created by **Super Admin** — this is the source of truth for the `area` dropdown used on branch/dept profiles, not a hardcoded static list.
- A branch/dept must reference an existing area; areas must exist before branches/depts can be created under them.

**Branch/Department profile**
- Fields: `name` (free text), `code` (free text), `area` (dropdown/FK to Area, not free text).
- Creatable only by Super Admin, either individually or via **CSV bulk import**:
  - Super Admin selects an existing area from a dropdown first, then uploads a CSV to create branches (columns: `branch_name, branch_code, branch_password`) or depts (equivalent columns) under that area.
  - **The CSV must never be persisted after processing** — no filesystem write, no object storage, no logs retaining it, no surviving temp file. Stream/process in-memory and discard immediately after the rows are created.
  - Passwords from the CSV must be hashed on ingestion, never stored or logged in plaintext.
  - **Import is all-or-nothing (transactional):** validate the whole CSV first; if any row fails, create nothing from that upload and return a clear per-row error report so Super Admin can fix and re-upload.
- Full list + full profile of every branch/dept is visible to any logged-in user (but never a list of the individual members inside them).

**Post**
- Fields, kept deliberately minimal: `title`, `body` (Markdown), `media[]` (optional, multiple, any filetype), `created_at`, `updated_at`.
- `created_at` is an **optional, user-fillable field on the create/edit form.** If left blank, the backend fills it with the actual row-creation timestamp. If the user provides a value, use that instead (e.g. backdating a notice to when it took effect) — there is a single `created_at` column either way, not a separate manual-date field.
- **Status:** `draft` or `published`. Drafts are visible/editable only by the owning org unit and Super Admin, and must never appear in the public feed/listing. Publishing a draft doesn't require `created_at` to be set — same fallback applies.
- Exactly one `category` per post; a post may have multiple media attachments.
- Editable at any time by an authorized user — both text fields and media can be replaced after publishing.
- `created_at` and `updated_at` must be tracked and displayed separately in the UI — never show a merged/ambiguous timestamp.

**Category**
- Managed from an admin panel UI (not CLI).

**Media**
- **No file size limit, no per-post attachment count limit, and no filetype validation/whitelisting** — any file, any size, any count is accepted as uploaded, client- or server-side. Do not add validation the spec doesn't call for.
- Stored in S3 with SSE enabled.

**Message**
- Sent branch↔branch, branch↔dept, or dept↔dept.
- Always attributed to the sending org unit, **never** to the individual member who sent it, even though the member is authenticated as themselves.
- Standard encryption-at-rest / in-transit security — **do not implement end-to-end encryption for messaging or anything else**; this was evaluated and explicitly rejected for this project (server-side readability is required for search/moderation/notification-preview, and the org already uses Telegram for anything needing stronger secrecy).

**Search & Filtering (Posts)**
- Full-text search over post `title` and `body`.
- Filters, combinable with search and each other: `category`, `created_at` time range, and `posted_by` (the authoring org unit).
- Scoped to posts the requesting user can actually see — drafts never appear in results for anyone but the owning org unit / Super Admin.

**Notification**
- Backed by a dedicated `notifications` DB table — fields at minimum: `id`, recipient org unit (branch/dept, consistent with the org-unit-attribution pattern used for messages), `type`, a title/body or reference to the source object (post/message/etc.), `status` (`read` / `unread`), `created_at`, `read_at` (nullable).
- **v1 trigger: new (published) post creation only.** Drafts do not trigger notifications. Other triggers may be added later but aren't required now.
- Delivery/push happens via the org's self-hosted **ntfy** instance; the DB table is what the frontend Notifications page actually reads, and is authoritative for read/unread state and history.
- Frontend: a **dedicated, separate Notifications page** (not just a dropdown/toast) — list view with read/unread status, and a way to mark items read.
- Confirm full trigger list (new post, new message, category updates, etc.) before finalizing.

## Security requirements (hard requirements, not preferences)
1. **Zero pre-auth visibility.** No API route or frontend view may return or render any content (posts, media, profiles, categories, messages) without a valid, successful authentication check. Fail closed.
2. **No local caching, anywhere, of content/data.** No `localStorage`, `sessionStorage`, or `IndexedDB` use for API data. No service-worker caching of API responses. Set `Cache-Control: no-store` (or equivalent) on all API responses that carry user/org content. Static JS/CSS/font bundle caching is fine (it's code, not data).
3. **JWT auth**, default expiry **1 hour**, must be overridable via an environment variable (`.env`) — do not hardcode.
4. **Encryption at rest:** rely on Postgres disk/volume-level encryption (and `pgcrypto` for any specifically sensitive columns) and S3 SSE. TLS in transit is mandatory everywhere, including internal service calls where feasible.
5. **DB access separation:** enforce the two-tier Postgres user pattern described above; consider Row-Level Security (RLS) policies scoped by branch/dept for the runtime application user.
6. **Granular permissions:** design an explicit permission system (not just three hardcoded role checks) so that specific actions (create post, edit post, manage categories, send message, manage branch/dept profiles, etc.) can be independently governed per role. Super Admin configures **two separate default permission profiles** — one for Depts (Admin role), one for Branches (Non-Admin role) — applied as the baseline for newly created org units. **This entire matrix (both defaults, and per-unit overrides) must be manageable from the Admin panel UI** — Super Admin toggles individual action permissions per role/unit directly in the app, no CLI/config/DB edit required, and changes apply without a deploy. **Per-branch/per-dept overrides on top of the defaults are supported in v1** — build the schema so an individual org unit's permissions can diverge from its default profile.
7. **Super Admin override:** Super Admin can edit anything in the portal unconditionally — it sits outside the granular permission system entirely, not just as "highest permission level" within it.

## Frontend requirements
- Framework: SvelteKit, CSR/static mode, no server-rendering of authenticated views.
- **Static, pre-rendered login shell** is a hard requirement: the login screen must be servable as static HTML instantly, without waiting on JS to boot, so users on slow connections see something branded immediately instead of a blank screen.
- Keep the initial bundle small and code-split — the login screen should not require pulling in the full application (feed, media viewer, messaging) first.
- **Two languages: English and Bangla**, user-switchable (i18n layer needed for all UI strings).
- **Bangla font: Tiro Bangla, self-hosted** (do not fetch from Google Fonts CDN at runtime).
- **English font:** a clean humanist sans in the Calibri family (e.g. Carlito, a metric-compatible open-source Calibri alternative) — self-hosted too. **No monospace-style fonts anywhere in the UI**, including for things like post metadata or codes.
- Use `font-display: swap` on all fonts so text always renders (in a fallback font first) rather than staying blank while the font loads.
- Every asynchronous wait state needs an explicit, localized (Bengali-capable) loading indicator — never a silent gap. This audience includes non-technical users on unreliable networks; silent waits cause confusion and repeated clicking, which must be designed against.
- Support Markdown rendering for post bodies on the frontend.
- **Light and dark theme, both required, user-toggleable.** Preference is **per-profile, persisted server-side in the DB** (not a cookie, not `localStorage`) — fetch it from the API after login and apply it; write back on toggle. Before login (e.g. the static login shell, which has no profile to read), fall back to OS `prefers-color-scheme`. Applies to every page including the login shell.

## Explicitly out of scope for this build (do not implement unless asked)
- Any public or anonymous-access route.
- Self-registration flows of any kind.
- End-to-end encryption.
- Android/Kotlin app.
- Individual member directories or public member profiles.

## Before you start building
These items still need confirmation, but each has a suggested default below — proceed with the default unless told otherwise, don't block on asking:

1. **Permission matrix.** Suggested initial seed: Depts and Branches both get create/edit/delete on their own posts, draft/publish, send messages, and view any org-unit profile. Only Depts get category management by default (keeps taxonomy from fragmenting across many branches). Neither role can edit branch/dept profiles or manage areas — those stay Super-Admin-only. This is just the seed — the full matrix must be editable from the Admin panel per §6 above, not hardcoded.
2. **ntfy topic naming.** Suggested default: one topic per org unit, named from its internal UUID (not its human-readable `code`), with ntfy access-control/auth enabled — do not name topics after the public branch/dept `code`, since plain ntfy topics are unauthenticated-by-default and a guessable name would let anyone subscribe.
3. **Static asset caching.** Suggested default: normal HTTP caching is fine for content-hashed JS/CSS/font build output (it's code, not content). Keep `Cache-Control: no-store` only on API responses carrying posts/profiles/messages/notifications/media. This satisfies the "no local cache" policy's actual intent (protect content) without disabling browser asset caching.

Work incrementally: propose the DB schema and API route list first, confirm before scaffolding the frontend, and flag anywhere the "no local cache" requirement conflicts with a normal framework default so it can be resolved deliberately rather than silently.