<script>
  import { onMount } from 'svelte';
  import { page } from '$app/stores';
  import { api } from '$lib/api.js';
  import { t, lang } from '$lib/i18n';
  import { session } from '$lib/stores.js';
  import { fmtDate, unitLabel } from '$lib/format.js';
  import Spinner from '$lib/components/Spinner.svelte';

  const id = $page.params.id;

  let loading = $state(true);
  let error = $state('');
  let forbidden = $state(false);
  let unit = $state(null);
  let areaName = $state('');
  let posts = $state([]);
  let categories = $state(new Map());

  onMount(async () => {
    try {
      unit = await api(`/org-units/${id}/profile`);
      const [areas, cats, ps] = await Promise.all([
        api('/areas').catch(() => []),
        api('/categories').catch(() => []),
        api('/posts', { query: { posted_by: id, size: 50 } }).catch(() => ({ items: [] }))
      ]);
      areaName = areas.find((a) => a.id === unit.area_id)?.name ?? '';
      categories = new Map(cats.map((c) => [c.id, c.name]));
      posts = ps.items;
    } catch (e) {
      if (e.status === 403) forbidden = true;
      else error = e.status === 404 ? $t('profile.notFound') : (e.detail ?? 'error');
    } finally {
      loading = false;
    }
  });

  const canMessage = $derived(!!$session && unit && $session.org_unit_id !== unit.id);
</script>

<svelte:head><title>{unit ? unitLabel(unit) : $t('profile.backToDirectory')} · Nobojatra</title></svelte:head>

<p><a href="/directory" class="back">← {$t('profile.backToDirectory')}</a></p>

{#if loading}
  <Spinner block />
{:else if forbidden}
  <p class="err" role="alert">{$t('profile.noPermission')}</p>
{:else if error}
  <p class="err" role="alert">{error}</p>
{:else}
  <header class="head">
    <div>
      <h1 lang={$lang}>{unit.name}</h1>
      <p class="sub">
        <span class="label">{$t('profile.code')}</span> {unit.code}
        <span class="sep">·</span>
        <span class="label">{$t('profile.area')}</span> {areaName || '—'}
      </p>
    </div>
    {#if canMessage}
      <a class="btn" href={`/messages?to=${unit.id}`}>{$t('profile.message')}</a>
    {/if}
  </header>

  <section>
    <h2 class="label">{$t('profile.posts')}</h2>
    {#if posts.length === 0}
      <p class="empty">{$t('profile.noPosts')}</p>
    {:else}
      <ul class="posts">
        {#each posts as p (p.id)}
          <li class="paper-card">
            <a href={`/posts/${p.id}`}>
              <span class="cat label">{categories.get(p.category_id) ?? ''}</span>
              <h3 lang={$lang}>{p.title}</h3>
              <p class="date">{$t('post.postedOn', { date: fmtDate(p.created_at) })}</p>
            </a>
          </li>
        {/each}
      </ul>
    {/if}
  </section>
{/if}

<style>
  .back {
    font-size: var(--step--1);
    letter-spacing: 0.03em;
  }
  .head {
    display: flex;
    align-items: flex-start;
    justify-content: space-between;
    gap: 1rem;
    padding-bottom: 1rem;
    margin-bottom: 1.5rem;
    border-bottom: 1px solid var(--rule);
  }
  h1 {
    margin: 0.4rem 0 0.5rem;
  }
  .sub {
    margin: 0;
    color: var(--ink-muted);
    font-size: var(--step--1);
  }
  .sep {
    margin: 0 0.4em;
  }
  .empty {
    color: var(--ink-muted);
    font-size: var(--step--1);
  }
  .posts {
    list-style: none;
    margin: 0;
    padding: 0;
    display: grid;
    gap: 0.75rem;
  }
  .posts li {
    padding: 0.9rem 1rem;
  }
  .posts a {
    display: block;
    color: inherit;
    text-decoration: none;
  }
  .cat {
    display: inline-flex;
    padding: 0.1em 0.55em;
    border-radius: 999px;
    background: color-mix(in srgb, var(--thread) 15%, transparent);
    color: var(--thread-strong);
  }
  .posts h3 {
    font-size: var(--step-1);
    margin: 0.35rem 0 0.25rem;
  }
  .posts a:hover h3 {
    color: var(--thread-strong);
  }
  .date {
    margin: 0;
    color: var(--ink-muted);
    font-size: var(--step--1);
  }
  .err {
    color: var(--danger);
  }
</style>
