import { get } from 'svelte/store';
import { marked } from 'marked';
import DOMPurify from 'dompurify';
import { lang } from './i18n';

marked.setOptions({ gfm: true, breaks: true });

/** Render post body Markdown to sanitized HTML. CSR-only, so DOMPurify has a DOM. */
export function renderMarkdown(src) {
  return DOMPurify.sanitize(marked.parse(src ?? '', { async: false }));
}

/** Locale-aware date. Bangla UI -> Bangla digits/months. */
export function fmtDate(iso, withTime = false) {
  if (!iso) return '';
  const locale = get(lang) === 'bn' ? 'bn-BD' : 'en-GB';
  const opts = withTime
    ? { dateStyle: 'medium', timeStyle: 'short' }
    : { dateStyle: 'medium' };
  try {
    return new Intl.DateTimeFormat(locale, opts).format(new Date(iso));
  } catch {
    return iso;
  }
}

export function unitLabel(unit) {
  if (!unit) return '';
  return unit.code || unit.name || '';
}
