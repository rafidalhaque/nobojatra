# Internal Notice Board & Inter-Branch Social Portal — Specification

**Status:** Draft v1
**Replaces:** WordPress-based internal system
**Audience:** Internal organization use only (branches + departments), not public-facing

---

## 1. Purpose

A private, authentication-gated web portal that serves as a notice board and lightweight social/communication layer between an organization's **branches** and **departments**. Branches and departments post content, communicate with each other, and browse each other's public profiles — all as organizational units, not as individuals.

---

## 2. Roles & Identity

| Role | Description |
|---|---|
| **Super Admin** | Highest privilege. Created only via CLI — no UI/registration path exists for this role. Creates branch/dept profiles and (likely) initial admin accounts. |
| **Admin** | Associated with a **Department**. |
| **Non-Admin** | Associated with a **Branch**. |
| **Member** | Belongs to a Department (→ inherits Admin role) or a Branch (→ inherits Non-Admin role). No self-registration; accounts are provisioned by Super Admin (see §7). |

Notes:
- There is no public sign-up flow anywhere in the system.
- Individual members are never independently identifiable in public-facing lists (see §5).

---

## 3. Content — Posts

- **Fields (intentionally minimal):**
  - Title
  - Body (Markdown supported)
  - Media (optional, **multiple** files per post, any filetype)
  - **Creation date/time: an optional, user-fillable field.** If left blank, it auto-fills with the row's actual creation timestamp (`created_at`). If the user provides a value, that value is used instead (e.g. for backdating a notice to when it actually took effect). Either way it's stored as `created_at` — there's no separate "manual date" column.
- **Category:** exactly **one** category per post (single-select).
- **Status:** a post can be saved as **Draft** or **Published**.
  - Drafts are only visible/editable by their owning org unit (and Super Admin) — never shown in the public feed/listing.
  - A draft can be edited freely and published at any time; publishing does not require the creation-date field to be filled (falls back to the current timestamp at publish/creation time if still blank).
- **Editing:**
  - Posts are editable at any time after publishing (title, body).
  - Media can be replaced at any time after publishing.
  - A separate `updated_at` (modification time) is tracked and displayed distinctly from `created_at` in the UI — never conflated.
- **Search & Filtering:**
  - **Full-text search** across a post's **title (heading) and body**.
  - **Filters** (combinable with search and each other):
    - **Category** (single or multi-select).
    - **Time range** (filter by `created_at` — e.g. date-from/date-to).
    - **Posted by** — the org unit (branch/dept) that authored the post.
  - Applies to published posts visible to the requesting user; drafts are excluded from search/filter results for anyone other than the owning org unit / Super Admin.

## 4. Categories

- Managed via the Admin panel (not CLI, not self-service by regular members).

## 5. Media

- Any filetype supported — **no server-side or client-side filetype validation/whitelisting; any file is accepted as uploaded.**
- **No file size limit.**
- **No limit on the number of media attachments per post.**
- Uploaded directly within the post-creation/edit flow.
- Stored in S3 (with server-side encryption — see §11).
- A post can hold multiple media attachments.

## 6. Messaging

- Branches and Departments can message any other Branch or Department (branch↔branch, branch↔dept, dept↔dept).
- Messages are attributed to the **organizational unit** (branch/dept), never to the individual member who authored/sent them.
- **Security model:** standard baseline (encryption at rest + TLS in transit + granular permission-based access control). **End-to-end encryption was evaluated and explicitly rejected** — see §11.1 for rationale.
- Server can read message content, enabling: notification previews, search, and admin moderation/audit if needed later.

## 7. Branch / Department Profiles

- **Fields:** `name` (free text), `code` (free text), `area` (dropdown, controlled vocabulary).
- **Creation:** Super Admin only. No self-registration for branches/depts.
- **Visibility:** Full list and full profile of every branch/dept is visible to **any logged-in user**.

### 7.1 Areas
- Areas are **created by Super Admin** — this is the source of truth for the `area` dropdown, not a static hardcoded list.
- A branch or department must be assigned to an existing area, so an area must exist before branches/depts can be created under it.

### 7.2 Bulk Import (Areas → Branches / Depts)
- **Branch import flow:** Super Admin first **selects an existing area** from a dropdown, then uploads a **CSV** to create branches under that area. CSV columns: `branch_name, branch_code, branch_password`.
- **Department import:** same pattern — select area first, then upload a CSV of depts (equivalent columns, e.g. `dept_name, dept_code, dept_password`).
- **CSV handling — hard requirement:** the uploaded CSV is used only transiently to process/create rows. **It must never be persisted anywhere after processing** — not on the server filesystem, not in object storage, not in logs, not in any temp-file location that survives past the request. Process in-memory/stream, then discard immediately.
- Passwords supplied via CSV must be hashed immediately on ingestion — never stored or logged in plaintext, same standard as any other credential in the system.
- Import should validate rows (duplicate codes, malformed rows, etc.). **Import is all-or-nothing (transactional):** if any row in the CSV fails validation, no rows from that upload are created — Super Admin gets a clear error report and re-uploads a corrected file.

- **Everything requires successful authentication.** No content (posts, media, profiles, categories, messages) is visible pre-login. Zero public/anonymous surface.
- Branch/Dept profiles and the full branch/dept directory: visible to all logged-in users.
- **Individual member profiles and member lists are never exposed** — members act and appear only through their branch/dept identity.
- Granular, permission-based access control governs actions (create/edit/delete posts, manage categories, send messages, etc.).
- **Super Admin can edit anything in the portal**, unconditionally — not subject to the granular permission system that governs Admin/Non-Admin roles; it's a full-override tier for corrections, moderation, and support.

### 8.1 Default Granular Permissions
- Super Admin defines the **default permission set for Depts (Admin role) and Branches (Non-Admin role) separately** — two independently configurable default permission profiles, not one shared default applied to both.
- **Managed from the Admin panel UI** — Super Admin can view and edit the full permission matrix for Depts and Branches directly in the app (toggle individual actions on/off per role), not via CLI, config file, or a code/DB-only change. Changes take effect for the relevant role without a deploy.
- These act as the baseline for newly created depts/branches. **Per-unit overrides are supported** — Super Admin (or a permitted role) can override the default permission set for an individual branch or department on top of the two global defaults, also from the Admin panel.

## 9. Notifications

- **Delivery:** self-hosted **ntfy** instance (already run by the org) — used as the push/delivery channel.
- **Persistence:** a dedicated `notifications` table in the DB, independent of ntfy — every notification is a row with a **status** of `read` / `unread`.
- **Frontend:** a **separate, dedicated Notifications page** (not just a dropdown/toast) where a user can browse their notification history and see/change read status.
- **Trigger (v1, confirmed):** a notification is generated on **new post creation** (published posts — drafts do not trigger notifications; see §15). Additional triggers (new message, etc.) may be added later but are not required for v1.

## 10. Localization

- **Two frontend languages: English and Bangla** (user-switchable).
- **Bangla font:** Tiro Bangla (Google Fonts family), self-hosted.
- **English font:** a clean humanist sans-serif in the Calibri family style (e.g. Carlito, a metric-compatible open-source alternative to Calibri) — **explicitly no monospace-style fonts** anywhere in the UI.
- Fonts self-hosted (not loaded from Google/third-party CDNs at runtime) to avoid extra slow external round-trips on weak connections.
- `font-display: swap` on all fonts — text must render immediately in a fallback font and swap in once the target font loads, never leaving blank text.

## 11. Security

### 11.1 Encryption Baseline (applies to posts, profiles, categories, media, messages)
- **In transit:** TLS everywhere — non-negotiable.
- **At rest:**
  - PostgreSQL: disk-level / cloud-provider encrypted volumes, and/or `pgcrypto` for specific sensitive columns.
  - S3: server-side encryption (SSE, AES-256 or KMS-managed).
- **E2EE was evaluated for messaging and explicitly rejected.** Rationale:
  - Time-sensitive/highly sensitive real-time communication already happens via the org's existing Telegram usage (separate system).
  - This portal's messaging is secondary/lower-stakes, so server-side readability (moderation, search, notification previews) outweighs E2EE's added complexity (key ownership per org-unit identity, key rotation on offboarding, new-device provisioning).
  - E2EE was also assessed as fundamentally unsuited to posts/profiles/categories, since those are broadcast content (all logged-in users can read them) rather than point-to-point secrets — applying E2EE there would break search, moderation, and rendering with no real confidentiality benefit.

### 11.2 Auth & Session
- No content viewable without a successful login — enforced end-to-end (API + frontend).
- JWT expiry: **1 hour default**, configurable via `.env`.
- **No local caching of any kind, at any point:**
  - No persisted app data in `localStorage` / `sessionStorage` / `IndexedDB`.
  - No service-worker caching of API responses.
  - `Cache-Control: no-store` (or equivalent) on API responses carrying content/data.
  - Static JS/CSS/font assets may still use normal HTTP caching (code, not content/data) — confirm scope with stakeholders if this needs tightening further.

### 11.3 Database Access Separation
- Two-tier Postgres user model recommended (proven pattern from a related internal project):
  - A schema-owner user for migrations only.
  - An RLS-constrained application user for runtime queries — enforces branch/dept-scoped row access at the DB layer, not just the API layer.

## 12. Frontend Architecture (Final Decision)

- **Not** using Next.js / SSR. Rationale: the "nothing visible pre-auth, zero local cache" requirement is simpler to guarantee and audit with a client-rendered app than by disabling Next.js's default caching machinery (ISR, Data Cache, Router Cache, etc.) piece by piece.
- **Chosen framework: SvelteKit, in static/CSR mode** (not using its SSR server) — selected over a plain Vite+React SPA for:
  - Smaller runtime → faster parse/hydrate on low-end devices.
  - Better performance on slow/BD-typical mobile networks.
  - Built-in prerendering support for the static login shell (below).

### 12.1 Firm UX/Performance Requirements
These exist specifically to prevent panic/confusion for non-technical users on slow Bangladeshi mobile networks:
- **Static, pre-rendered login shell** — served instantly (no live rendering server needed), so users see a branded, familiar screen immediately instead of a blank tab, even before the JS bundle finishes loading.
- **Small, code-split initial bundle** — the login screen must not require downloading the full application (post feed, media viewer, messaging UI, etc.) first.
- **Explicit Bengali-language loading states** at every wait point (e.g. "সাইন ইন হচ্ছে...") — silent gaps are what cause user panic/re-clicking, not the wait itself.

### 12.2 Theming
- **Both a light ("white") and a dark ("night") theme**, user-toggleable.
- **Preference is per-profile (per-login-account) and persisted server-side in the DB** — not a cookie, not `localStorage`, not in-memory-only. On login, the frontend fetches the saved preference from the API and applies it; changing the toggle writes back to the DB. This keeps it consistent with the "no local cache" policy (nothing about theme relies on client-side persistence) while still surviving across devices/sessions for the same user.
- Defaults to OS-level preference (`prefers-color-scheme`) only for a not-yet-logged-in view (e.g. the static login shell, which has no profile to read a preference from) — once logged in, the stored DB preference takes over.
- Applies consistently across both languages (English/Bangla) and all pages, including the static pre-rendered login shell (using the OS-preference default there).

## 13. Technology Stack

| Layer | Choice |
|---|---|
| Database | PostgreSQL |
| Object storage | S3 (SSE enabled) |
| Backend | FastAPI |
| Backend package management | **uv** |
| Frontend | SvelteKit (CSR/static mode) |
| Notifications delivery | Self-hosted **ntfy** |
| Mobile (Android) | Kotlin — **deferred to v2** |
| Version control | **Git** |
| Deployment | **Docker**, orchestrated via **docker-compose** |
| API documentation | **OpenAPI `spec.yml`**, auto-generated from the FastAPI codebase (not hand-maintained) |

### 13.1 Notifications Table (DB)
Minimum shape:
- `id`, `recipient_org_unit` (branch/dept — consistent with the "attributed to org unit, not individual" pattern used elsewhere), `type`, `title`/`body` or a reference to the source object (post/message/etc.), `status` (`read` / `unread`), `created_at`, `read_at` (nullable).
- ntfy is used purely as the **push delivery mechanism**; the DB table remains the source of truth for history and read/unread state, and is what the dedicated Notifications page reads from.

### 13.2 Development & Deployment Practices
- **Version control:** all code tracked in Git from day one (this matches the pattern already used on related internal projects — secrets never committed, `.env`/1Password-style secret management expected).
- **Containerization:** the full stack (API, worker if any, frontend build/serve, Postgres, and any supporting services) is dockerized and brought up via `docker-compose`. Mirrors the working pattern already in use for the org's other services (`api`, `worker`, `admin`, `postgres`, `redis`, `nginx` style composition).
- **API docs:** OpenAPI `spec.yml` is a required deliverable, generated automatically from the FastAPI app (FastAPI generates this natively via its OpenAPI schema) rather than hand-written/maintained separately — must be kept in sync by construction, not by discipline.
- **Backend package management:** **uv** for dependency management, virtual envs, and running the app (`uv sync`, `uv run`, etc.) — not pip/poetry/pipenv. `pyproject.toml` + `uv.lock` are the source of truth for backend dependencies. The backend Dockerfile should use a `uv`-based build (e.g. the official `uv` Docker image or `pip install uv` bootstrap) rather than a plain `pip install -r requirements.txt` flow.

## 14. Explicitly Out of Scope (v1)

- Public/anonymous access of any kind.
- Self-service registration for members, branches, or departments.
- Individual member discovery/profile browsing.
- End-to-end encryption (messaging or otherwise) — revisit only if requirements change.
- Android app — v2.

## 15. Open Items — Suggested Defaults (Pending Confirmation)

The items below are the ones still genuinely open. Each has a suggested default so implementation isn't blocked — confirm or override before/while building.

**Permission matrix contents (Dept default vs. Branch default)**
Suggested starting point, adjustable later without a schema change (since permissions are already modeled as data, not hardcoded):
| Action | Dept (Admin) default | Branch (Non-Admin) default |
|---|---|---|
| Create/edit/delete own posts | ✅ | ✅ |
| Save/publish drafts | ✅ | ✅ |
| Create/manage categories | ✅ | ❌ (view/select only) |
| Send messages to any branch/dept | ✅ | ✅ |
| View any branch/dept profile | ✅ | ✅ |
| Edit own branch/dept profile | ❌ (Super Admin only, per §7) | ❌ (Super Admin only, per §7) |
| Manage areas | ❌ (Super Admin only) | ❌ (Super Admin only) |
Rationale: keeps categories curated (avoids duplicate/messy taxonomy from many branches creating overlapping categories) while giving both roles equal footing on the core notice-board/messaging actions, matching the "branches and depts are functionally symmetric except category curation" pattern implied so far. **This is just the initial seed value** — the whole matrix is editable by Super Admin from the Admin panel at any time (see §8.1), so it isn't a fixed/hardcoded default.

**ntfy topic structure per org unit**
Suggested: one ntfy topic per org unit, named from its internal (non-guessable) ID rather than its human-readable `code` — e.g. `portal-{env}-{org_unit_uuid}` — with ntfy's access-control/auth mode enabled so topics aren't publicly subscribable by guessing the name. (Plain ntfy topics are just unauthenticated strings by default; using the branch/dept `code` directly as the topic name would let anyone who knows a branch's code listen in.) The backend subscribes/publishes server-side; end users never see the raw topic name.

**Static asset caching under the "no local cache" policy**
Suggested: keep normal HTTP caching for build-output static assets only — JS/CSS bundles and self-hosted font files, all served with content-hashed filenames (e.g. `app.a1b2c3.js`) so a cache is always correct or a cache-miss, never stale. Everything that carries user/org content (API responses: posts, profiles, messages, notifications, media) keeps `Cache-Control: no-store`. This matches the original intent of the "no local cache" rule (protecting content, not code) without fighting the browser's normal asset caching.