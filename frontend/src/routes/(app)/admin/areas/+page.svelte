<script>
  import { onMount } from 'svelte';
  import { api } from '$lib/api.js';
  import { t } from '$lib/i18n';
  import Spinner from '$lib/components/Spinner.svelte';

  let loading = $state(true);
  let error = $state('');
  let areas = $state([]);
  let name = $state('');
  let adding = $state(false);
  let bulkText = $state('');
  let bulking = $state(false);
  let bulkMsg = $state('');

  onMount(load);

  async function load() {
    loading = true;
    try {
      areas = await api('/areas');
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
      const a = await api('/areas', { method: 'POST', body: { name: name.trim() } });
      areas = [...areas, a].sort((x, y) => x.name.localeCompare(y.name));
      name = '';
    } catch (e) {
      error = e.detail ?? 'error';
    } finally {
      adding = false;
    }
  }

  async function bulkAdd() {
    if (bulking) return;
    const have = new Set(areas.map((a) => a.name.toLowerCase()));
    const names = [];
    for (const raw of bulkText.split(/\r?\n/)) {
      const n = raw.trim();
      if (n && !have.has(n.toLowerCase())) {
        have.add(n.toLowerCase());
        names.push(n);
      }
    }
    if (!names.length) return;
    bulking = true;
    bulkMsg = '';
    error = '';
    let added = 0;
    const failed = [];
    for (const n of names) {
      try {
        const a = await api('/areas', { method: 'POST', body: { name: n } });
        areas = [...areas, a];
        added++;
      } catch {
        failed.push(n);
      }
    }
    areas = [...areas].sort((x, y) => x.name.localeCompare(y.name));
    bulkMsg = $t('admin.areas.bulkResult', { added, skipped: names.length - added });
    bulkText = failed.join('\n'); // keep the ones that didn't take, for a retry
    bulking = false;
  }

  async function remove(a) {
    if (!confirm($t('admin.areas.deleteConfirm', { name: a.name }))) return;
    error = '';
    try {
      await api(`/areas/${a.id}`, { method: 'DELETE' });
      areas = areas.filter((x) => x.id !== a.id);
    } catch (e) {
      error = e.status === 409 ? $t('admin.areas.inUse') : (e.detail ?? 'error');
    }
  }
</script>

<svelte:head><title>{$t('admin.nav.areas')} · Nobojatra</title></svelte:head>

<p class="hint">{$t('admin.areas.hint')}</p>

<form class="add" onsubmit={(e) => (e.preventDefault(), add())}>
  <input bind:value={name} placeholder={$t('admin.areas.name')} aria-label={$t('admin.areas.name')} />
  <button class="btn" disabled={adding || !name.trim()}>
    {adding ? $t('admin.areas.adding') : $t('common.add')}
  </button>
</form>

<details class="bulk">
  <summary>{$t('admin.areas.bulk')}</summary>
  <textarea bind:value={bulkText} rows="5" aria-label={$t('admin.areas.bulk')}></textarea>
  <button class="btn" onclick={bulkAdd} disabled={bulking || !bulkText.trim()}>
    {bulking ? $t('admin.areas.bulkAdding') : $t('admin.areas.bulkAdd')}
  </button>
  {#if bulkMsg}<p class="ok">{bulkMsg}</p>{/if}
</details>

{#if error}<p class="err" role="alert">{$t('common.error', { detail: error })}</p>{/if}

{#if loading}
  <Spinner block />
{:else if areas.length === 0}
  <p class="muted">{$t('admin.areas.empty')}</p>
{:else}
  <ul class="list">
    {#each areas as a (a.id)}
      <li>
        <span>{a.name}</span>
        <button class="del" onclick={() => remove(a)}>{$t('common.delete')}</button>
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
  }
  .list {
    list-style: none;
    margin: 0;
    padding: 0;
    border-top: 1px solid var(--rule);
    max-width: 32rem;
  }
  .list li {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 0.7rem 0.4rem;
    border-bottom: 1px solid var(--rule);
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
  .bulk {
    max-width: 32rem;
    margin: -0.5rem 0 1.5rem;
  }
  .bulk summary {
    cursor: pointer;
    color: var(--thread);
    font-size: var(--step--1);
  }
  .bulk textarea {
    width: 100%;
    margin: 0.5rem 0;
    padding: 0.55em 0.7em;
    background: var(--paper);
    border: 1px solid var(--rule);
    border-radius: var(--radius);
    font-family: var(--font-latin);
    resize: vertical;
  }
  .ok {
    color: var(--thread-strong);
    font-size: var(--step--1);
  }
</style>
