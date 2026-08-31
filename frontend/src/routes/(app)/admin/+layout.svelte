<script>
  import { page } from '$app/stores';
  import { t } from '$lib/i18n';
  import { session } from '$lib/stores.js';

  let { children } = $props();

  const tabs = [
    { href: '/admin', key: 'admin.nav.permissions' },
    { href: '/admin/categories', key: 'admin.nav.categories' },
    { href: '/admin/areas', key: 'admin.nav.areas' },
    { href: '/admin/org-units', key: 'admin.nav.orgUnits' }
  ];
  const on = (href) => (href === '/admin' ? $page.url.pathname === '/admin' : $page.url.pathname.startsWith(href));
</script>

{#if !$session?.is_super_admin}
  <p class="err">403 — {$t('admin.heading')}</p>
{:else}
  <h1>{$t('admin.heading')}</h1>
  <nav class="tabs">
    {#each tabs as { href, key } (href)}
      <a {href} class:on={on(href)} aria-current={on(href) ? 'page' : undefined}>{$t(key)}</a>
    {/each}
  </nav>
  {@render children()}
{/if}

<style>
  .tabs {
    display: flex;
    gap: 0.25rem;
    border-bottom: 2px solid var(--rule);
    margin: 0 0 1.75rem;
  }
  .tabs a {
    padding: 0.5em 0.9em;
    color: var(--ink-muted);
    text-decoration: none;
    font-weight: 700;
    letter-spacing: 0.02em;
    border-bottom: 2px solid transparent;
    margin-bottom: -2px;
  }
  .tabs a:hover {
    color: var(--ink);
  }
  .tabs a.on {
    color: var(--thread-strong);
    border-color: var(--seal);
  }
  .err {
    color: var(--danger);
  }
</style>
