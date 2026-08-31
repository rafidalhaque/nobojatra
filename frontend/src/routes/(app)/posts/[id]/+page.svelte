<script>
  import { onMount } from 'svelte';
  import { page } from '$app/stores';
  import { goto } from '$app/navigation';
  import { api } from '$lib/api.js';
  import { t, lang } from '$lib/i18n';
  import { session } from '$lib/stores.js';
  import { fmtDate, renderMarkdown, unitLabel } from '$lib/format.js';
  import Spinner from '$lib/components/Spinner.svelte';
  import Stamp from '$lib/components/Stamp.svelte';

  const id = $page.params.id;
  const apiBase = import.meta.env.VITE_API_BASE ?? '/api';

  let loading = $state(true);
  let error = $state('');
  let post = $state(null);
  let unit = $state(null);
  let categoryName = $state('');

  onMount(async () => {
    try {
      post = await api(`/posts/${id}`);
      const [cats, u] = await Promise.all([
        api('/categories'),
        api(`/org-units/${post.org_unit_id}`).catch(() => null)
      ]);
      unit = u;
      categoryName = cats.find((c) => c.id === post.category_id)?.name ?? '';
    } catch (e) {
      error = e.status === 404 ? $t('post.notFound') : (e.detail ?? 'error');
    } finally {
      loading = false;
    }
  });

  const canEdit = $derived(
    !!post && !!$session && ($session.is_super_admin || $session.org_unit_id === post.org_unit_id)
  );

  let deleting = $state(false);
  async function del() {
    if (deleting || !confirm($t('post.deleteConfirm'))) return;
    deleting = true;
    try {
      await api(`/posts/${post.id}`, { method: 'DELETE' });
      await goto('/');
    } catch (e) {
      error = e.detail ?? 'error';
      deleting = false;
    }
  }
  // mirror the API's inline-render allowlist (svg is served as a download, not rendered)
  const INLINE_IMG = ['image/png', 'image/jpeg', 'image/gif', 'image/webp'];
  const isImage = (m) => INLINE_IMG.includes((m.content_type ?? '').toLowerCase());
</script>

<svelte:head><title>{post?.title ?? $t('feed.heading')} · Nobojatra</title></svelte:head>

<p><a href="/" class="back">← {$t('post.backToFeed')}</a></p>

{#if loading}
  <Spinner block />
{:else if error}
  <p class="err" role="alert">{error}</p>
{:else}
  <article>
    <span class="cat label">{categoryName}</span>
    {#if post.status === 'draft'}<span class="label draft">{$t('feed.draftBadge')}</span>{/if}
    <h1 lang={$lang}>{post.title}</h1>

    <div class="meta">
      <p class="dates">
        <span>{$t('post.postedOn', { date: fmtDate(post.created_at, true) })}</span>
        {#if post.updated_at !== post.created_at}
          <span>{$t('post.updatedOn', { date: fmtDate(post.updated_at, true) })}</span>
        {/if}
      </p>
      <Stamp {unit} unitId={post.org_unit_id} date={fmtDate(post.created_at)} />
    </div>

    {#if canEdit}
      <p class="owner-actions">
        <a class="btn btn--ghost" href={`/posts/${post.id}/edit`}>{$t('editor.editHeading')}</a>
        <button type="button" class="btn del" onclick={del} disabled={deleting}>
          {deleting ? $t('post.deleting') : $t('common.delete')}
        </button>
      </p>
    {/if}

    <!-- markdown is sanitized in renderMarkdown() -->
    <div class="prose" lang={$lang}>{@html renderMarkdown(post.body)}</div>

    {#if post.media?.length}
      <section class="media">
        <h2 class="label">{$t('editor.media')}</h2>
        <ul>
          {#each post.media as m (m.id)}
            <li>
              {#if isImage(m)}
                <img src={`${apiBase}/media/${m.id}`} alt={m.original_filename} loading="lazy" />
              {/if}
              <a href={`${apiBase}/media/${m.id}`} target="_blank" rel="noopener">{m.original_filename}</a>
            </li>
          {/each}
        </ul>
      </section>
    {/if}
  </article>
{/if}

<style>
  .back {
    font-size: var(--step--1);
    letter-spacing: 0.03em;
  }
  .cat {
    color: var(--seal);
  }
  .draft {
    margin-left: 0.75rem;
    border: 1px solid var(--rule);
    padding: 0 0.4em;
    border-radius: 2px;
    color: var(--ink-muted);
  }
  h1 {
    font-size: var(--step-3);
    margin: 0.4rem 0 0.75rem;
  }
  .meta {
    display: flex;
    flex-wrap: wrap;
    gap: 1rem 1.5rem;
    align-items: center;
    justify-content: space-between;
    padding-bottom: 1rem;
    border-bottom: 1px solid var(--rule);
    margin-bottom: 1.5rem;
  }
  .dates {
    margin: 0;
    display: flex;
    flex-direction: column;
    gap: 0.15rem;
    color: var(--ink-muted);
    font-size: var(--step--1);
    letter-spacing: 0.02em;
  }
  .media {
    margin-top: 2.5rem;
    border-top: 1px solid var(--rule);
    padding-top: 1rem;
  }
  .media ul {
    list-style: none;
    padding: 0;
    display: grid;
    gap: 1rem;
  }
  .media img {
    display: block;
    max-width: min(100%, 32rem);
    border: 1px solid var(--rule);
    border-radius: var(--radius);
    margin-bottom: 0.3rem;
  }
  .err {
    color: var(--danger);
  }
  .owner-actions {
    display: flex;
    gap: 0.6rem;
    flex-wrap: wrap;
  }
  .del {
    background: transparent;
    color: var(--danger);
    border-color: var(--rule);
  }
  .del:hover {
    background: color-mix(in srgb, var(--danger) 10%, transparent);
  }
</style>
