import { derived, get, writable } from 'svelte/store';
import en from './en.json';
import bn from './bn.json';

const DICTS = { en, bn };

/** Active UI language. Pre-login: seeded from the browser, not persisted (spec:
 *  no local caching). Post-login: set from the profile's lang_pref. */
export const lang = writable('en');

export function initLangFromBrowser() {
  if (typeof navigator === 'undefined') return;
  lang.set(navigator.language?.toLowerCase().startsWith('bn') ? 'bn' : 'en');
}

/** $t('key', { name: 'x' }) — falls back to English, then the key itself. */
export const t = derived(lang, ($lang) => (key, params) => {
  let s = DICTS[$lang]?.[key] ?? DICTS.en[key] ?? key;
  if (params) for (const k of Object.keys(params)) s = s.replaceAll(`{${k}}`, params[k]);
  return s;
});

export function tr(key, params) {
  return get(t)(key, params);
}
