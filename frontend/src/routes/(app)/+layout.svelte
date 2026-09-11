<script>
  import { onMount } from 'svelte';
  import { page } from '$app/stores';
  import { goto } from '$app/navigation';
  import { api } from '$lib/api.js';
  import { session } from '$lib/stores.js';
  import { applyTheme, osTheme, persistPreference } from '$lib/theme.js';
  import { lang, t } from '$lib/i18n';
  import Masthead from '$lib/components/Masthead.svelte';
  import Spinner from '$lib/components/Spinner.svelte';

  let { children } = $props();
  let ready = $state(false);

  // own org-unit's display info for the user card — fetched once, same data
  // the /profile page already shows (see profile/+page.svelte)
  let unit = $state(null);
  let areaName = $state('');

  let collapsed = $state(false);
  let menuOpen = $state(false);
  let theme = $state('light');
  let busy = $state(false);

  onMount(async () => {
    try {
      collapsed = localStorage.getItem('sidebar-collapsed') === '1';
    } catch {
      /* private window etc — default to expanded */
    }
    theme = document.documentElement.dataset.theme ?? osTheme();

    try {
      const me = await api('/auth/me');
      session.set(me);
      applyTheme(me.theme_pref);
      lang.set(me.lang_pref);
      theme = me.theme_pref;
      ready = true;
    } catch {
      await goto('/login', { replaceState: true });
      return;
    }

    if ($session?.org_unit_id) {
      try {
        unit = await api('/me/profile');
        const areas = await api('/areas').catch(() => []);
        areaName = areas.find((a) => a.id === unit.area_id)?.name ?? '';
      } catch {
        /* user card falls back to the username */
      }
    }
  });

  function toggleCollapse() {
    collapsed = !collapsed;
    try {
      localStorage.setItem('sidebar-collapsed', collapsed ? '1' : '0');
    } catch {
      /* per-viewer convenience only */
    }
  }

  function toggleMenu() {
    menuOpen = !menuOpen;
  }

  function closeMenu() {
    menuOpen = false;
  }

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
    { href: '/', key: 'nav.feed', icon: 'feed' },
    ...($session?.org_unit_id || $session?.is_super_admin
      ? [{ href: '/messages', key: 'nav.messages', icon: 'messages' }]
      : []),
    { href: '/notifications', key: 'nav.notifications', icon: 'notifications' },
    { href: '/directory', key: 'nav.directory', icon: 'directory' },
    { href: '/profile', key: 'nav.profile', icon: 'profile' },
    ...($session?.is_super_admin ? [{ href: '/admin', key: 'nav.admin', icon: 'admin' }] : [])
  ]);

  const displayName = $derived(
    $session?.org_unit_id ? (unit?.name ?? '') : ($session?.username ?? '')
  );
  const subText = $derived(
    $session?.org_unit_id
      ? unit
        ? `${unit.code}${areaName ? ' · ' + areaName : ''}`
        : ''
      : $t('nav.superAdmin')
  );
  const avatarInitial = $derived((displayName || '?').trim().charAt(0).toUpperCase() || '?');

  function active(href) {
    const p = $page.url.pathname;
    return href === '/' ? p === '/' : p.startsWith(href);
  }

  // thin-line 24x24 icons, stroke-based — matches the sidebar redesign mock
  const ICONS = {
    feed: '<rect x="3" y="4" width="18" height="4" rx="1"/><line x1="3" y1="11" x2="21" y2="11"/><line x1="3" y1="16" x2="21" y2="16"/><line x1="3" y1="20" x2="14" y2="20"/>',
    messages: '<path d="M4 4h16v13H7l-3 3z"/>',
    notifications:
      '<path d="M12 3l1.6 3.2L17 7l-2.5 2.5.6 3.5L12 11.5 8.9 13l.6-3.5L7 7l3.4-.8z"/>',
    directory: '<path d="M4 6h16M4 6a2 2 0 012-2h5l2 2h5a2 2 0 012 2v9a2 2 0 01-2 2H6a2 2 0 01-2-2z"/>',
    profile: '<circle cx="12" cy="8" r="3.4"/><path d="M5 20c0-3.5 3.1-6 7-6s7 2.5 7 6"/>',
    admin:
      '<circle cx="12" cy="12" r="3"/><path d="M19.4 13a1.7 1.7 0 00.34 1.87l.06.06a2 2 0 11-2.83 2.83l-.06-.06a1.7 1.7 0 00-1.87-.34 1.7 1.7 0 00-1 1.55V19a2 2 0 01-4 0v-.09a1.7 1.7 0 00-1-1.55 1.7 1.7 0 00-1.87.34l-.06.06a2 2 0 11-2.83-2.83l.06-.06a1.7 1.7 0 00.34-1.87 1.7 1.7 0 00-1.55-1H4a2 2 0 010-4h.09a1.7 1.7 0 001.55-1 1.7 1.7 0 00-.34-1.87l-.06-.06a2 2 0 112.83-2.83l.06.06a1.7 1.7 0 001.87.34H10a1.7 1.7 0 001-1.55V4a2 2 0 014 0v.09a1.7 1.7 0 001 1.55 1.7 1.7 0 001.87-.34l.06-.06a2 2 0 112.83 2.83l-.06.06a1.7 1.7 0 00-.34 1.87V10a1.7 1.7 0 001.55 1H20a2 2 0 010 4h-.09a1.7 1.7 0 00-1.55 1z"/>',
    password: '<rect x="4" y="10" width="16" height="10" rx="2"/><path d="M8 10V7a4 4 0 018 0v3"/>',
    signout: '<path d="M9 21H5a2 2 0 01-2-2V5a2 2 0 012-2h4"/><path d="M16 17l5-5-5-5"/><line x1="21" y1="12" x2="9" y2="12"/>',
    panel: '<rect x="3" y="4" width="18" height="16" rx="2"/><line x1="10" y1="4" x2="10" y2="20"/>',
    chevron: '<polyline points="6 9 12 15 18 9"/>'
  };
</script>

<svelte:window onclick={(e) => { if (menuOpen && !e.target.closest('.user-wrap')) closeMenu(); }} />

<div class="mobile-mast">
  <Masthead compact />
</div>

{#if !ready}
  <Spinner block />
{:else}
  <div class="shell">
    <aside class="sidebar" class:collapsed>
      <div class="brand">
        <a class="brand-mark" href="/" aria-label={$t('brand.name')}>
          <span class="brand-badge" aria-hidden="true">ন</span>
          {#if !collapsed}
            <span class="brand-text">
              <span class="bn" lang="bn">নবযাত্রা</span>
              <span class="en">NOBOJATRA</span>
            </span>
          {/if}
        </a>
        <button
          class="collapse-btn"
          onclick={toggleCollapse}
          aria-label={$t(collapsed ? 'sidebar.expand' : 'sidebar.collapse')}
        >
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"
            >{@html ICONS.panel}</svg
          >
        </button>
      </div>

      <nav aria-label="sections">
        {#each nav as item (item.href)}
          <a
            href={item.href}
            class="nav-item"
            class:active={active(item.href)}
            aria-current={active(item.href) ? 'page' : undefined}
            title={collapsed ? $t(item.key) : undefined}
          >
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"
              >{@html ICONS[item.icon]}</svg
            >
            {#if !collapsed}<span>{$t(item.key)}</span>{/if}
          </a>
        {/each}
      </nav>

      <div class="nav-spacer"></div>

      <div class="controls-row">
        <button class="chip" onclick={toggleLang}>{collapsed ? $t('lang.toggle').charAt(0) : $t('lang.toggle')}</button>
        <button
          class="chip"
          onclick={toggleTheme}
          disabled={busy}
          aria-label={$t(theme === 'dark' ? 'theme.toLight' : 'theme.toDark')}
        >
          {theme === 'dark' ? '☾' : '☀'}
        </button>
      </div>

      <div class="user-wrap">
        <div class="dropup" class:show={menuOpen} role="menu">
          <a class="dropup-item" role="menuitem" href="/profile" onclick={closeMenu}>
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"
              >{@html ICONS.profile}</svg
            >
            {$t('nav.profile')}
          </a>
          <a class="dropup-item" role="menuitem" href="/profile#password" onclick={closeMenu}>
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"
              >{@html ICONS.password}</svg
            >
            {$t('password.change')}
          </a>
          <div class="dropup-divider" role="separator"></div>
          <button class="dropup-item danger" role="menuitem" onclick={signOut}>
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"
              >{@html ICONS.signout}</svg
            >
            {$t('nav.signout')}
          </button>
        </div>

        <button
          class="user-card"
          class:open={menuOpen}
          aria-haspopup="menu"
          aria-expanded={menuOpen}
          onclick={toggleMenu}
        >
          <span class="avatar" aria-hidden="true">{avatarInitial}</span>
          {#if !collapsed}
            <span class="user-meta">
              <span class="name" lang={$lang}>{displayName}</span>
              <span class="sub">{subText}</span>
            </span>
            <svg class="chev" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"
              >{@html ICONS.chevron}</svg
            >
          {/if}
        </button>
      </div>
    </aside>

    <main lang={$lang}>
      {@render children()}
    </main>

    <nav class="mobile-bar" aria-label="sections">
      {#each nav as item (item.href)}
        <a href={item.href} class:on={active(item.href)} aria-current={active(item.href) ? 'page' : undefined}>
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"
            >{@html ICONS[item.icon]}</svg
          >
          <span class="l">{$t(item.key)}</span>
        </a>
      {/each}
      <button class="signout" onclick={signOut}>
        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"
          >{@html ICONS.signout}</svg
        >
        <span class="l">{$t('nav.signout')}</span>
      </button>
    </nav>
  </div>
{/if}

<style>
  .mobile-mast {
    display: none;
  }

  .shell {
    display: flex;
    min-height: 100dvh;
  }

  /* ---------- desktop sidebar ---------- */
  .sidebar {
    width: 264px;
    flex-shrink: 0;
    background: var(--paper-raised);
    border-right: 1px solid var(--rule);
    display: flex;
    flex-direction: column;
    padding: 20px 16px;
    position: sticky;
    top: 0;
    align-self: start;
    height: 100dvh;
  }
  .sidebar.collapsed {
    width: 76px;
    align-items: center;
  }

  .brand {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 4px 4px 22px;
    width: 100%;
  }
  .sidebar.collapsed .brand {
    flex-direction: column;
    gap: 10px;
    padding: 4px 0 18px;
  }
  .brand-mark {
    display: flex;
    align-items: center;
    gap: 10px;
    color: inherit;
    text-decoration: none;
    min-width: 0;
  }
  .brand-badge {
    width: 34px;
    height: 34px;
    flex-shrink: 0;
    background: var(--board);
    color: var(--board-text);
    border-radius: 9px;
    display: flex;
    align-items: center;
    justify-content: center;
    font-weight: 700;
    font-size: 16px;
    font-family: var(--font-bangla);
  }
  .brand-text {
    line-height: 1.05;
    min-width: 0;
    overflow: hidden;
  }
  .brand-text .bn {
    display: block;
    font-family: var(--font-bangla);
    font-weight: 700;
    font-size: 16px;
    color: var(--board);
  }
  .brand-text .en {
    font-weight: 600;
    font-size: 10px;
    letter-spacing: 0.06em;
    color: var(--ink-muted);
  }
  .collapse-btn {
    width: 26px;
    height: 26px;
    flex-shrink: 0;
    border-radius: 7px;
    border: 1px solid var(--rule);
    display: flex;
    align-items: center;
    justify-content: center;
    color: var(--ink-muted);
    cursor: pointer;
    background: var(--paper-raised);
  }
  .collapse-btn:hover {
    background: var(--paper);
  }

  nav[aria-label='sections'] {
    display: flex;
    flex-direction: column;
    gap: 2px;
    width: 100%;
  }
  .nav-item {
    display: flex;
    align-items: center;
    gap: 12px;
    padding: 10px 12px;
    border-radius: 11px;
    color: var(--ink-muted);
    font-size: var(--step--1);
    font-weight: 500;
    text-decoration: none;
    transition: background 0.15s ease, color 0.15s ease;
  }
  .sidebar.collapsed .nav-item {
    justify-content: center;
    padding: 10px;
  }
  .nav-item svg {
    flex-shrink: 0;
  }
  .nav-item:hover {
    background: var(--paper);
    color: var(--ink);
  }
  .nav-item.active {
    background: var(--nav-active-bg);
    color: var(--board);
    font-weight: 600;
  }

  .nav-spacer {
    flex: 1;
  }

  .controls-row {
    display: flex;
    gap: 6px;
    width: 100%;
    margin-bottom: 8px;
  }
  .sidebar.collapsed .controls-row {
    flex-direction: column;
  }
  .controls-row .chip {
    flex: 1;
    background: transparent;
    color: var(--ink-muted);
    border: 1px solid var(--rule);
    border-radius: var(--radius);
    padding: 5px 8px;
    font-size: var(--step--1);
    letter-spacing: 0.02em;
    cursor: pointer;
  }
  .controls-row .chip:hover {
    background: var(--paper);
  }

  /* ---------- user card + dropup ---------- */
  .user-wrap {
    position: relative;
    width: 100%;
  }
  .user-card {
    display: flex;
    align-items: center;
    gap: 10px;
    width: 100%;
    padding: 8px;
    border-radius: 12px;
    border: 1px solid transparent;
    background: none;
    cursor: pointer;
    color: inherit;
    text-align: left;
  }
  .sidebar.collapsed .user-card {
    justify-content: center;
    padding: 8px 0;
  }
  .user-card:hover {
    background: var(--paper);
  }
  .avatar {
    width: 36px;
    height: 36px;
    flex-shrink: 0;
    border-radius: 10px;
    background: linear-gradient(135deg, var(--thread-strong), var(--board));
    color: #fff;
    display: flex;
    align-items: center;
    justify-content: center;
    font-weight: 600;
    font-size: 14px;
  }
  .user-meta {
    flex: 1;
    min-width: 0;
  }
  .user-meta .name {
    display: block;
    font-size: 13.5px;
    font-weight: 600;
    color: var(--ink);
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
  }
  .user-meta .sub {
    display: block;
    font-size: 11.5px;
    color: var(--ink-muted);
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
  }
  .chev {
    color: var(--ink-muted);
    flex-shrink: 0;
    transition: transform 0.15s ease;
  }
  .user-card.open .chev {
    transform: rotate(180deg);
  }

  .dropup {
    position: absolute;
    bottom: calc(100% + 8px);
    left: 0;
    right: 0;
    background: var(--paper-raised);
    border: 1px solid var(--rule);
    border-radius: 14px;
    box-shadow: var(--shadow);
    padding: 8px;
    display: none;
    flex-direction: column;
    gap: 2px;
    z-index: 10;
  }
  .dropup.show {
    display: flex;
  }
  .dropup-item {
    display: flex;
    align-items: center;
    gap: 10px;
    padding: 9px 10px;
    border-radius: 9px;
    font-size: 13.5px;
    color: var(--ink);
    cursor: pointer;
    text-decoration: none;
    border: none;
    background: none;
    width: 100%;
    text-align: left;
  }
  .dropup-item:hover {
    background: var(--paper);
  }
  .dropup-item.danger {
    color: var(--danger);
  }
  .dropup-item.danger:hover {
    background: color-mix(in srgb, var(--danger) 10%, transparent);
  }
  .dropup-divider {
    height: 1px;
    background: var(--rule);
    margin: 5px 2px;
  }

  main {
    flex: 1;
    min-width: 0;
    padding: 1.75rem clamp(1rem, 4vw, 2.5rem) 4rem;
    max-width: 62rem;
  }

  /* ---------- mobile: fall back to the existing bottom-bar nav pattern ---------- */
  .mobile-bar {
    display: none;
  }

  @media (max-width: 767px) {
    .mobile-mast {
      display: block;
    }
    .sidebar {
      display: none;
    }
    .shell {
      display: block;
    }
    main {
      padding-bottom: 5.5rem;
    }
    .mobile-bar {
      display: flex;
      position: fixed;
      inset: auto 0 0 0;
      border-top: 1px solid var(--rule);
      background: var(--paper);
      padding: 4px;
      z-index: 20;
      overflow-x: auto;
      gap: 2px;
    }
    .mobile-bar a,
    .mobile-bar .signout {
      display: flex;
      flex-direction: column;
      align-items: center;
      gap: 2px;
      padding: 0.4em 0.5em;
      border-radius: var(--radius);
      color: var(--ink);
      text-decoration: none;
      font-size: 0.7rem;
      font-weight: 600;
      border: none;
      background: none;
      cursor: pointer;
      flex: 1 0 auto;
    }
    .mobile-bar a svg {
      color: var(--seal);
    }
    .mobile-bar a.on {
      color: var(--thread-strong);
      background: var(--paper-raised);
    }
    .mobile-bar a.on svg {
      color: var(--thread-strong);
    }
    .mobile-bar .l {
      white-space: nowrap;
    }
    .mobile-bar .signout {
      color: var(--ink-muted);
    }
  }
</style>
