# Frontend Redesign Spec — NOBOJATRA UI

**Status:** Draft v2 (corrected against actual repo — v1 was written from a screenshot and overstated the problem)
**Scope:** 3 confirmed CSS/markup bugs. No dependency changes, no framework migration.

---

## 1. Verified Findings

v1 of this spec claimed the UI had no real design system and needed a framework migration (shadcn-svelte/Tailwind). That was wrong — checked against the actual repo:

**Already correct, no action needed:**
- `--radius: 3px` is a single token, applied consistently across `.paper-card`, `.btn`, `.field input/textarea/select`
- `--step--1` through `--step-3` type scale exists and is applied consistently (h1/h2/labels/meta)
- Carlito/Tiro Bangla `@font-face` declared and applied via `--font-latin`/`--font-bangla` + `:lang(bn)` rule in app.css
- Stamp/unit tag (`Stamp.svelte`) is already a styled bordered pill, not bare text

**Confirmed real bugs (3):**

| # | Issue | Location | Fix |
|---|---|---|---|
| 1 | Two competing greens — header `--board: #14352a` vs. button `--thread: #1f6f5c` | Global tokens | Pick one as `--primary`; either retire `--thread` or use it only as a distinct secondary/hover accent, deliberately, not by accident |
| 2 | Native `<input type="date">` left unstyled — default browser chrome | `+page.svelte:92-93` | Custom-style native date input chrome (`::-webkit-calendar-picker-indicator` etc.) or swap in a lightweight Svelte date-picker component matching `.field` styling |
| 3 | Category tag (`.cat`) is bare colored text; happens to share `--seal` red with the unit Stamp pill, making them collide visually | `+page.svelte:183` | Give `.cat` its own pill/background treatment (reuse the `.paper-card`/`.field` radius token) so it reads as a distinct tag type, not a copy of the Stamp component's color |

## 2. Non-Findings — No Action

- Border-radius: not inconsistent, leave as-is
- Type scale: not missing, leave as-is
- Fonts: already wired per §10 of spec.md, leave as-is
- No case for introducing Tailwind, shadcn-svelte, or any new styling dependency — the existing hand-rolled token system is deliberate and working; these are isolated bugs, not systemic gaps

## 3. Out of Scope

- Any framework/dependency change
- Auth/session handling (unrelated to this doc)
- Illustration/empty-state work — separate v2+ discussion if still wanted, not tied to these 3 bugs

## 4. Deliverable

Direct CSS/markup patches for the 3 items above, scoped to existing files (`app.css`, `+page.svelte`, `Stamp.svelte` reference only). No new `components.json`, no new build tooling.
