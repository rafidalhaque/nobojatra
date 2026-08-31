<script>
  import { onMount } from 'svelte';
  import { goto } from '$app/navigation';
  import { api, ApiError } from '$lib/api.js';
  import { session } from '$lib/stores.js';
  import { applyTheme } from '$lib/theme.js';
  import { lang, t } from '$lib/i18n';
  import Masthead from '$lib/components/Masthead.svelte';

  let username = $state('');
  let password = $state('');
  let submitting = $state(false);
  let error = $state('');
  let checking = $state(true);

  onMount(async () => {
    // already signed in? skip the form.
    try {
      const me = await api('/auth/me');
      session.set(me);
      applyTheme(me.theme_pref);
      lang.set(me.lang_pref);
      await goto('/', { replaceState: true });
      return;
    } catch {
      /* not signed in — show the form */
    }
    checking = false;
  });

  async function submit(e) {
    e.preventDefault();
    if (submitting) return;
    submitting = true;
    error = '';
    try {
      const me = await api('/auth/login', { method: 'POST', body: { username, password } });
      session.set(me);
      applyTheme(me.theme_pref);
      lang.set(me.lang_pref);
      await goto('/', { replaceState: true });
    } catch (err) {
      error = err instanceof ApiError && err.status === 401 ? $t('login.failed') : $t('common.error', { detail: '' });
      submitting = false;
    }
  }
</script>

<svelte:head><title>{$t('login.heading')} · Nobojatra</title></svelte:head>

<Masthead />

<main class="wrap">
  <div class="sheet paper-card">
    <p class="kicker label">গোপনীয় · Confidential</p>
    <h1>{$t('login.heading')}</h1>
    <p class="tagline">{$t('login.tagline')}</p>

    {#if checking}
      <p class="tagline">{$t('common.loading')}</p>
    {:else}
      <form onsubmit={submit} novalidate>
        <div class="field">
          <label for="u">{$t('login.username')}</label>
          <input id="u" name="username" autocomplete="username" bind:value={username} required autocapitalize="none" spellcheck="false" />
        </div>
        <div class="field">
          <label for="p">{$t('login.password')}</label>
          <input id="p" name="password" type="password" autocomplete="current-password" bind:value={password} required />
        </div>

        {#if error}<p class="err" role="alert">{error}</p>{/if}

        <button class="btn wide" type="submit" disabled={submitting}>
          {submitting ? $t('login.submitting') : $t('login.submit')}
        </button>
      </form>
    {/if}
  </div>

  <p class="foot" lang={$lang}>{$t('login.footer')}</p>
</main>

<style>
  .wrap {
    min-height: calc(100dvh - 52px);
    display: grid;
    place-content: center;
    gap: 1.25rem;
    padding: 2rem 1.25rem 3rem;
  }
  .sheet {
    width: min(92vw, 27rem);
    padding: 2.25rem 2rem 2rem;
    position: relative;
  }
  /* a torn top edge — the sheet is pinned to the board */
  .sheet::before {
    content: '';
    position: absolute;
    inset: 0 0 auto 0;
    height: 4px;
    background: var(--seal);
    border-radius: var(--radius) var(--radius) 0 0;
  }
  .kicker {
    margin: 0 0 0.75rem;
  }
  h1 {
    font-size: var(--step-2);
    margin: 0 0 0.35rem;
  }
  .tagline {
    color: var(--ink-muted);
    margin: 0 0 1.5rem;
  }
  form {
    margin: 0;
  }
  label {
    font-size: var(--step--1);
    font-weight: 700;
    letter-spacing: 0.04em;
  }
  .wide {
    width: 100%;
    margin-top: 0.25rem;
    padding-block: 0.75em;
  }
  .err {
    color: var(--danger);
    font-size: var(--step--1);
    margin: 0 0 0.75rem;
  }
  .foot {
    max-width: 27rem;
    text-align: center;
    color: var(--ink-muted);
    font-size: var(--step--1);
    margin: 0;
  }
  /* subtle field entrance — one gesture, respects reduced-motion via app.css */
  .field {
    animation: rise 320ms ease both;
  }
  .field:nth-of-type(2) {
    animation-delay: 45ms;
  }
  @keyframes rise {
    from {
      opacity: 0;
      transform: translateY(6px);
    }
  }
</style>
