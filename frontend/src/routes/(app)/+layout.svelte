<script>
  import { onMount } from 'svelte';
  import { page } from '$app/stores';
  import { goto } from '$app/navigation';
  import { api } from '$lib/api.js';
  import { session } from '$lib/stores.js';
  import { applyTheme } from '$lib/theme.js';
  import { lang, t } from '$lib/i18n';
  import Masthead from '$lib/components/Masthead.svelte';
  import Spinner from '$lib/components/Spinner.svelte';

  let { children } = $props();
  let ready = $state(false);

  onMount(async () => {
    try {
      const me = await api('/auth/me');
      session.set(me);
      applyTheme(me.theme_pref); // DB preference now wins over OS
      lang.set(me.lang_pref);
      ready = true;
    } catch {
      await goto('/login', { replaceState: true });
    }
  });

  async function signOut() {
    try {
      await api('/auth/logout', { method: 'POST' });
    } catch {
      /* clearing the cookie is best-effort */
    }
    session.set(null);
    await goto('/login', { replaceState: true });
  }

  const nav = $derived([
    { href: '/', key: 'nav.feed', glyph: '▤' },
    ...($session?.org_unit_id || $session?.is_super_admin
      ? [{ href: '/messages', key: 'nav.messages', glyph: '✉' }]
      : []),
    { href: '/notifications', key: 'nav.notifications', glyph: '❈' },
    { href: '/directory', key: 'nav.directory', glyph: '☰' },
    ...($session?.is_super_admin ? [{ href: '/admin', key: 'nav.admin', glyph: '⚙' }] : [])
  ]);

  function active(href) {
    const p = $page.url.pathname;
    return href === '/' ? p === '/' : p.startsWith(href);
  }
</script>

<Masthead compact />

{#if !ready}
  <Spinner block />
{:else}
  <div class="frame">
    <nav aria-label="sections">
      {#each nav as item (item.href)}
        <a href={item.href} class:on={active(item.href)} aria-current={active(item.href) ? 'page' : undefined}>
          <span class="g" aria-hidden="true">{item.glyph}</span>
          <span class="l">{$t(item.key)}</span>
        </a>
      {/each}
      <button class="signout" onclick={signOut}>
        <span class="g" aria-hidden="true">⏻</span>
        <span class="l">{$t('nav.signout')}</span>
      </button>
    </nav>

    <main lang={$lang}>
      {@render children()}
    </main>
  </div>
{/if}

<style>
  .frame {
    display: grid;
    grid-template-columns: 13.5rem minmax(0, 1fr);
    gap: 0;
    min-height: calc(100dvh - 44px);
  }
  nav {
    border-right: 1px solid var(--rule);
    padding: 1.25rem 0.75rem;
    display: flex;
    flex-direction: column;
    gap: 2px;
    position: sticky;
    top: 0;
    align-self: start;
  }
  nav a,
  .signout {
    display: flex;
    align-items: center;
    gap: 0.7em;
    padding: 0.55em 0.75em;
    border-radius: var(--radius);
    color: var(--ink);
    text-decoration: none;
    font-weight: 600;
    letter-spacing: 0.01em;
    border: 1px solid transparent;
    background: none;
    cursor: pointer;
    text-align: left;
    width: 100%;
  }
  nav a:hover,
  .signout:hover {
    background: color-mix(in srgb, var(--thread) 9%, transparent);
  }
  nav a.on {
    color: var(--thread-strong);
    border-color: var(--rule);
    background: var(--paper-raised);
  }
  .g {
    width: 1.1em;
    text-align: center;
    color: var(--seal);
  }
  .signout {
    margin-top: auto;
    color: var(--ink-muted);
  }
  main {
    padding: 1.75rem clamp(1rem, 4vw, 2.5rem) 4rem;
    max-width: 62rem;
  }

  @media (max-width: 720px) {
    .frame {
      grid-template-columns: 1fr;
    }
    nav {
      position: fixed;
      inset: auto 0 0 0;
      flex-direction: row;
      border-right: 0;
      border-top: 1px solid var(--rule);
      background: var(--paper);
      padding: 4px;
      z-index: 20;
      overflow-x: auto;
    }
    nav a,
    .signout {
      flex-direction: column;
      gap: 2px;
      font-size: 0.7rem;
      padding: 0.4em 0.5em;
      width: auto;
      flex: 1 0 auto;
    }
    nav a .l,
    .signout .l {
      white-space: nowrap;
    }
    .signout {
      margin-top: 0;
    }
    main {
      padding-bottom: 5.5rem;
    }
  }
</style>
