import { api } from './api.js';

/** @param {'light'|'dark'} theme */
export function applyTheme(theme) {
  if (typeof document !== 'undefined') document.documentElement.dataset.theme = theme;
}

/** OS preference — the only source before login (spec 12.2). */
export function osTheme() {
  return typeof matchMedia !== 'undefined' && matchMedia('(prefers-color-scheme: dark)').matches
    ? 'dark'
    : 'light';
}

/** Persist per-profile in the DB (not a cookie / localStorage), then apply. */
export async function persistPreference(patch) {
  const me = await api('/me/preferences', { method: 'PATCH', body: patch });
  if (patch.theme_pref) applyTheme(patch.theme_pref);
  return me;
}
