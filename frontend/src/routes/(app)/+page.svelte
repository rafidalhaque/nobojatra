<script>
  import { onMount } from 'svelte';
  import { api } from '$lib/api.js';
  import { t, lang } from '$lib/i18n';
  import { session } from '$lib/stores.js';
  import { fmtDate, unitLabel } from '$lib/format.js';
  import Spinner from '$lib/components/Spinner.svelte';
  import Stamp from '$lib/components/Stamp.svelte';

  let loading = $state(true);
  let error = $state('');
  let posts = $state([]);
  let categories = $state([]);
  let units = $state(new Map());

  // filters
  let q = $state('');
  let category = $state('');
  let postedBy = $state('');
  let dateFrom = $state('');
  let dateTo = $state('');
  let searching = $state(false);
  let timer;

  onMount(async () => {
    try {
      const [cats, us] = await Promise.all([api('/categories'), api('/org-units')]);
      categories = cats;
      units = new Map(us.map((u) => [u.id, u]));
      await run();
    } catch (e) {
      error = e.detail ?? 'error';
    } finally {
      loading = false;
    }
  });

  async function run() {
    searching = true;
    try {
      const res = await api('/posts', {
        query: {
          q,
          category,
          posted_by: postedBy,
          date_from: dateFrom ? new Date(dateFrom).toISOString() : '',
          date_to: dateTo ? new Date(dateTo).toISOString() : '',
          size: 50
        }
      });
      posts = res.items;
      error = '';
    } catch (e) {
      error = e.detail ?? 'error';
    } finally {
      searching = false;
    }
  }

  function debounced() {
    clearTimeout(timer);
    timer = setTimeout(run, 250);
  }

  const catName = $derived((id) => categories.find((c) => c.id === id)?.name ?? '');
</script>

<svelte:head><title>{$t('feed.heading')} · Nobojatra</title></svelte:head>

<header class="head">
  <h1>{$t('feed.heading')}</h1>
  <a class="btn" href="/posts/new">{$t('feed.new')}</a>
</header>

<div class="filters paper-card">
  <input
    class="search"
    type="search"
    placeholder={$t('feed.searchPlaceholder')}
    bind:value={q}
    oninput={debounced}
    aria-label={$t('common.search')}
  />
  <select bind:value={category} onchange={run} aria-label={$t('feed.filterCategory')}>
    <option value="">— {$t('feed.filterCategory')} —</option>
    {#each categories as c (c.id)}<option value={c.id}>{c.name}</option>{/each}
  </select>
  <select bind:value={postedBy} onchange={run} aria-label={$t('feed.filterPostedBy')}>
    <option value="">— {$t('feed.filterPostedBy')} —</option>
    {#each [...units.values()] as u (u.id)}<option value={u.id}>{unitLabel(u)}</option>{/each}
  </select>
  <label class="d">{$t('feed.filterFrom')}<input type="date" bind:value={dateFrom} onchange={run} /></label>
  <label class="d">{$t('feed.filterTo')}<input type="date" bind:value={dateTo} onchange={run} /></label>
  {#if searching}<Spinner />{/if}
</div>

{#if loading}
  <Spinner block />
{:else if error}
  <p class="err" role="alert">{$t('common.error', { detail: error })} <button class="btn btn--ghost" onclick={run}>{$t('common.retry')}</button></p>
{:else if posts.length === 0}
  <p class="empty" lang={$lang}>{$t('feed.empty')}</p>
{:else}
  <ul class="board">
    {#each posts as p (p.id)}
      <li class="notice paper-card">
        <a class="body" href={`/posts/${p.id}`}>
          <span class="cat label">{catName(p.category_id)}</span>
          {#if p.status === 'draft'}<span class="draft label">{$t('feed.draftBadge')}</span>{/if}
          <h2 lang={$lang}>{p.title}</h2>
          <p class="dates">
            <span>{$t('post.postedOn', { date: fmtDate(p.created_at) })}</span>
            {#if p.updated_at && p.updated_at !== p.created_at}
              <span>· {$t('post.updatedOn', { date: fmtDate(p.updated_at) })}</span>
            {/if}
          </p>
        </a>
        <div class="mark">
          <Stamp unit={units.get(p.org_unit_id)} unitId={p.org_unit_id} date={fmtDate(p.created_at)} />
        </div>
      </li>
    {/each}
  </ul>
{/if}

<style>
  .head {
    display: flex;
    align-items: baseline;
    justify-content: space-between;
    gap: 1rem;
    margin-bottom: 1rem;
  }
  .head h1 {
    margin: 0;
  }
  .filters {
    display: flex;
    flex-wrap: wrap;
    gap: 0.6rem;
    align-items: center;
    padding: 0.75rem;
    margin-bottom: 1.5rem;
  }
  .filters input,
  .filters select {
    padding: 0.45em 0.6em;
    background: var(--paper);
    border: 1px solid var(--rule);
    border-radius: var(--radius);
  }
  .search {
    flex: 1 1 14rem;
  }
  .d {
    display: inline-flex;
    align-items: center;
    gap: 0.4em;
    font-size: var(--step--1);
    color: var(--ink-muted);
  }
  .board {
    list-style: none;
    margin: 0;
    padding: 0;
    display: grid;
    gap: 1rem;
  }
  .notice {
    display: grid;
    grid-template-columns: minmax(0, 1fr) auto;
    align-items: end;
    gap: 1rem;
    padding: 1.1rem 1.2rem;
  }
  .body {
    display: block;
    color: inherit;
    text-decoration: none;
    min-width: 0;
  }
  .cat {
    color: var(--seal);
  }
  .draft {
    margin-left: 0.75rem;
    color: var(--ink-muted);
    border: 1px solid var(--rule);
    padding: 0 0.4em;
    border-radius: 2px;
  }
  .notice h2 {
    font-size: var(--step-1);
    margin: 0.35rem 0 0.4rem;
  }
  .body:hover h2 {
    color: var(--thread-strong);
  }
  .dates {
    margin: 0;
    color: var(--ink-muted);
    font-size: var(--step--1);
    letter-spacing: 0.02em;
    display: flex;
    gap: 0.4em;
    flex-wrap: wrap;
  }
  .mark {
    align-self: end;
  }
  .empty {
    color: var(--ink-muted);
    max-width: var(--measure);
  }
  .err {
    color: var(--danger);
  }
  @media (max-width: 560px) {
    .notice {
      grid-template-columns: 1fr;
    }
    .mark {
      justify-self: start;
    }
  }
</style>
