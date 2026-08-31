<script>
  import { onMount } from 'svelte';
  import { api } from '$lib/api.js';
  import { t } from '$lib/i18n';
  import Spinner from '$lib/components/Spinner.svelte';

  let loading = $state(true);
  let error = $state('');
  let categories = $state([]);
  let name = $state('');
  let adding = $state(false);
  let editingId = $state('');
  let editName = $state('');

  onMount(load);

  async function load() {
    loading = true;
    try {
      categories = await api('/categories');
      error = '';
    } catch (e) {
      error = e.detail ?? 'error';
    } finally {
      loading = false;
    }
  }

  async function add() {
    if (!name.trim() || adding) return;
    adding = true;
    error = '';
    try {
      const c = await api('/categories', { method: 'POST', body: { name: name.trim() } });
      categories = [...categories, c].sort((a, b) => a.name.localeCompare(b.name));
      name = '';
    } catch (e) {
      error = e.status === 409 ? $t('admin.cats.dup') : (e.detail ?? 'error');
    } finally {
      adding = false;
    }
  }

  function startEdit(c) {
    editingId = c.id;
    editName = c.name;
  }

  async function saveEdit() {
    if (!editName.trim()) return;
    try {
      const c = await api(`/categories/${editingId}`, { method: 'PATCH', body: { name: editName.trim() } });
      categories = categories.map((x) => (x.id === c.id ? c : x)).sort((a, b) => a.name.localeCompare(b.name));
      editingId = '';
    } catch (e) {
      error = e.status === 409 ? $t('admin.cats.dup') : (e.detail ?? 'error');
    }
  }

  async function remove(c) {
    if (!confirm($t('admin.cats.deleteConfirm', { name: c.name }))) return;
    error = '';
    try {
      await api(`/categories/${c.id}`, { method: 'DELETE' });
      categories = categories.filter((x) => x.id !== c.id);
    } catch (e) {
      error = e.status === 409 ? $t('admin.cats.inUse') : (e.detail ?? 'error');
    }
  }
</script>

<svelte:head><title>{$t('admin.nav.categories')} · Nobojatra</title></svelte:head>

<p class="hint">{$t('admin.cats.hint')}</p>

<form class="add" onsubmit={(e) => (e.preventDefault(), add())}>
  <input bind:value={name} placeholder={$t('admin.cats.name')} aria-label={$t('admin.cats.name')} />
  <button class="btn" disabled={adding || !name.trim()}>
    {adding ? $t('admin.areas.adding') : $t('common.add')}
  </button>
</form>

{#if error}<p class="err" role="alert">{$t('common.error', { detail: error })}</p>{/if}

{#if loading}
  <Spinner block />
{:else if categories.length === 0}
  <p class="muted">{$t('admin.cats.empty')}</p>
{:else}
  <ul class="list">
    {#each categories as c (c.id)}
      <li>
        {#if editingId === c.id}
          <input bind:value={editName} onkeydown={(e) => e.key === 'Enter' && saveEdit()} />
          <button class="btn btn--ghost sm" onclick={saveEdit}>{$t('common.save')}</button>
          <button class="del" onclick={() => (editingId = '')}>{$t('common.cancel')}</button>
        {:else}
          <span>{c.name}</span>
          <button class="del" onclick={() => startEdit(c)}>{$t('common.edit')}</button>
          <button class="del" onclick={() => remove(c)}>{$t('common.delete')}</button>
        {/if}
      </li>
    {/each}
  </ul>
{/if}

<style>
  .hint {
    color: var(--ink-muted);
    font-size: var(--step--1);
    max-width: var(--measure);
  }
  .add {
    display: flex;
    gap: 0.5rem;
    margin: 1rem 0 1.5rem;
  }
  .add input {
    flex: 1 1 18rem;
    padding: 0.55em 0.7em;
    background: var(--paper);
    border: 1px solid var(--rule);
    border-radius: var(--radius);
    color: var(--ink);
  }
  .list {
    list-style: none;
    margin: 0;
    padding: 0;
    border-top: 1px solid var(--rule);
    max-width: 34rem;
  }
  .list li {
    display: flex;
    gap: 0.75rem;
    justify-content: space-between;
    align-items: center;
    padding: 0.7rem 0.4rem;
    border-bottom: 1px solid var(--rule);
  }
  .list li span {
    margin-right: auto;
  }
  .list li input {
    flex: 1;
    margin-right: auto;
    padding: 0.4em 0.6em;
    background: var(--paper);
    border: 1px solid var(--rule);
    border-radius: var(--radius);
    color: var(--ink);
  }
  .sm {
    padding: 0.3em 0.7em;
  }
  .del {
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
