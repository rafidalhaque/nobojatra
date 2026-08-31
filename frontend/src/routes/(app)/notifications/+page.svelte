<script>
  import { onMount } from 'svelte';
  import { api } from '$lib/api.js';
  import { t, lang } from '$lib/i18n';
  import { fmtDate } from '$lib/format.js';
  import Spinner from '$lib/components/Spinner.svelte';

  let loading = $state(true);
  let error = $state('');
  let items = $state([]);

  onMount(load);

  async function load() {
    loading = true;
    try {
      items = await api('/notifications');
      error = '';
    } catch (e) {
      error = e.detail ?? 'error';
    } finally {
      loading = false;
    }
  }

  async function markRead(n) {
    if (n.status === 'read') return;
    try {
      await api(`/notifications/${n.id}/read`, { method: 'POST' });
      items = items.map((x) => (x.id === n.id ? { ...x, status: 'read' } : x));
    } catch { /* keep as unread on failure */ }
  }

  async function markAll() {
    try {
      await api('/notifications/read-all', { method: 'POST' });
      items = items.map((x) => ({ ...x, status: 'read' }));
    } catch (e) {
      error = e.detail ?? 'error';
    }
  }

  const unread = $derived(items.filter((n) => n.status === 'unread').length);
</script>

<svelte:head><title>{$t('notifications.heading')} · Nobojatra</title></svelte:head>

<header class="head">
  <h1>{$t('notifications.heading')}</h1>
  {#if unread}
    <button class="btn btn--ghost" onclick={markAll}>{$t('notifications.markAll')}</button>
  {/if}
</header>

{#if loading}
  <Spinner block />
{:else if error}
  <p class="err" role="alert">{$t('common.error', { detail: error })}</p>
{:else if items.length === 0}
  <p class="muted" lang={$lang}>{$t('notifications.empty')}</p>
{:else}
  <ul class="list">
    {#each items as n (n.id)}
      <li class:unread={n.status === 'unread'}>
        {#if n.source_type === 'post' && n.source_id}
          <a href={`/posts/${n.source_id}`} onclick={() => markRead(n)}>
            <strong lang={$lang}>{n.title}</strong>
          </a>
        {:else}
          <strong lang={$lang}>{n.title}</strong>
        {/if}
        <time>{fmtDate(n.created_at, true)}</time>
        {#if n.status === 'unread'}
          <button class="link" onclick={() => markRead(n)}>{$t('notifications.unread')}</button>
        {/if}
      </li>
    {/each}
  </ul>
{/if}

<style>
  .head {
    display: flex;
    justify-content: space-between;
    align-items: baseline;
    gap: 1rem;
  }
  .list {
    list-style: none;
    margin: 1rem 0 0;
    padding: 0;
    border-top: 1px solid var(--rule);
  }
  .list li {
    display: grid;
    grid-template-columns: 1fr auto auto;
    gap: 0.5rem 1rem;
    align-items: baseline;
    padding: 0.85rem 0.5rem;
    border-bottom: 1px solid var(--rule);
  }
  .list li.unread {
    border-left: 3px solid var(--seal);
    padding-left: 0.75rem;
  }
  time {
    color: var(--ink-muted);
    font-size: var(--step--1);
    letter-spacing: 0.02em;
  }
  .link {
    background: none;
    border: 0;
    color: var(--seal);
    font-size: 0.7rem;
    letter-spacing: 0.08em;
    text-transform: uppercase;
    cursor: pointer;
  }
  .muted {
    color: var(--ink-muted);
  }
  .err {
    color: var(--danger);
  }
</style>
