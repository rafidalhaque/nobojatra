import { writable } from 'svelte/store';

/**
 * Current account: null = signed out, undefined = not checked yet.
 * @typedef {{ id: string, username: string, is_super_admin: boolean,
 *   org_unit_id: string | null, theme_pref: 'light'|'dark', lang_pref: 'en'|'bn' }} Me
 * @type {import('svelte/store').Writable<Me | null | undefined>}
 */
export const session = writable(undefined);
