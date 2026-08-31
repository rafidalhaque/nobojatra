<script>
  import { onMount } from 'svelte';
  import { t, lang } from '$lib/i18n';
  import { session } from '$lib/stores.js';
  import { persistPreference, applyTheme, osTheme } from '$lib/theme.js';

  /** @type {{ compact?: boolean }} */
  let { compact = false } = $props();

  let busy = $state(false);
  let theme = $state('light');
  onMount(() => {
    theme = document.documentElement.dataset.theme ?? osTheme();
  });

  async function toggleLang() {
    const next = $lang === 'bn' ? 'en' : 'bn';
    lang.set(next);
    if ($session) {
      try {
        await persistPreference({ lang_pref: next });
      } catch {
        /* preference is cosmetic; ignore a failed write */
      }
    }
  }

  async function toggleTheme() {
    const next = theme === 'dark' ? 'light' : 'dark';
    theme = next;
    applyTheme(next);
    if ($session) {
      busy = true;
      try {
        await persistPreference({ theme_pref: next });
        session.update((m) => (m ? { ...m, theme_pref: next } : m));
      } finally {
        busy = false;
      }
    }
  }
</script>

<header class="mast" class:compact>
  <a class="wordmark" href={$session ? '/' : '/login'}>
    <span class="bn" lang="bn">নবযাত্রা</span>
    <span class="en">Nobojatra</span>
    {#if !compact}<span class="sub">· {$t('brand.tagline')}</span>{/if}
  </a>

  <div class="controls">
    <button class="chip" onclick={toggleLang}>{$t('lang.toggle')}</button>
    <button
      class="chip"
      onclick={toggleTheme}
      disabled={busy}
      aria-label={theme === 'dark' ? $t('theme.toLight') : $t('theme.toDark')}
    >
      {theme === 'dark' ? '☾' : '☀'}
    </button>
  </div>
</header>

<style>
  .mast {
    display: flex;
    align-items: baseline;
    justify-content: space-between;
    gap: 1rem;
    padding: 14px 20px;
    background: var(--board);
    color: var(--board-text);
    border-bottom: 3px double rgba(243, 242, 234, 0.35);
  }
  .compact {
    padding: 10px 16px;
    border-bottom-width: 2px;
  }
  .wordmark {
    display: inline-flex;
    align-items: baseline;
    gap: 0.5ch;
    color: inherit;
    text-decoration: none;
  }
  .bn {
    font-family: var(--font-bangla);
    font-size: 1.15rem;
    line-height: 1;
  }
  .en {
    font-weight: 700;
    letter-spacing: 0.05em;
    font-size: 0.95rem;
    text-transform: uppercase;
  }
  .sub {
    opacity: 0.65;
    font-size: 0.85rem;
  }
  .controls {
    display: inline-flex;
    gap: 6px;
    flex: none;
  }
  .chip {
    background: transparent;
    color: inherit;
    border: 1px solid rgba(243, 242, 234, 0.4);
    border-radius: var(--radius);
    padding: 3px 10px;
    font-size: var(--step--1);
    letter-spacing: 0.03em;
    cursor: pointer;
  }
  .chip:hover {
    background: rgba(243, 242, 234, 0.12);
  }
</style>
