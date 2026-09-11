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
  let units = $state(new Map());
  let comments = $state([]);
  let commentBody = $state('');
  let commentSending = $state(false);
  let commentError = $state('');

  onMount(async () => {
    try {
      post = await api(`/posts/${id}`);
      const [cats, u, allUnits, cs] = await Promise.all([
        api('/categories'),
        api(`/org-units/${post.org_unit_id}`).catch(() => null),
        api('/org-units').catch(() => []),
        api(`/posts/${id}/comments`).catch(() => [])
      ]);
      unit = u;
      units = new Map(allUnits.map((x) => [x.id, x]));
      categoryName = cats.find((c) => c.id === post.category_id)?.name ?? '';
      comments = cs;
    } catch (e) {
      error = e.status === 404 ? $t('post.notFound') : (e.detail ?? 'error');
    } finally {
      loading = false;
    }
  });

  const canComment = $derived(!!$session?.org_unit_id);

  async function sendComment() {
    if (commentSending || !commentBody.trim()) return;
    commentSending = true;
    commentError = '';
    try {
      const c = await api(`/posts/${id}/comments`, { method: 'POST', body: { body: commentBody.trim() } });
      comments = [...comments, c];
      commentBody = '';
    } catch (e) {
      commentError = e.detail ?? 'error';
    } finally {
      commentSending = false;
    }
  }

  async function deleteComment(c) {
    if (!confirm($t('comments.deleteConfirm'))) return;
    try {
      await api(`/comments/${c.id}`, { method: 'DELETE' });
      comments = comments.filter((x) => x.id !== c.id);
    } catch (e) {
      commentError = e.detail ?? 'error';
    }
  }

  const canDeleteComment = (c) =>
    !!$session && ($session.is_super_admin || $session.org_unit_id === c.org_unit_id);

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

    <section class="comments">
      <h2 class="label">{$t('comments.heading')}</h2>
      {#if comments.length === 0}
        <p class="empty">{$t('comments.empty')}</p>
      {:else}
        <ul class="thread">
          {#each comments as c (c.id)}
            <li>
              <div class="c-head">
                <Stamp unit={units.get(c.org_unit_id)} unitId={c.org_unit_id} date={fmtDate(c.created_at)} />
                {#if canDeleteComment(c)}
                  <button type="button" class="rm" onclick={() => deleteComment(c)} aria-label={$t('editor.remove')}>×</button>
                {/if}
              </div>
              <p lang={$lang}>{c.body}</p>
            </li>
          {/each}
        </ul>
      {/if}

      {#if commentError}<p class="err" role="alert">{commentError}</p>{/if}

      {#if canComment}
        <form class="compose" onsubmit={(e) => (e.preventDefault(), sendComment())}>
          <textarea
            bind:value={commentBody}
            placeholder={$t('comments.placeholder')}
            aria-label={$t('comments.placeholder')}
            lang={$lang}
          ></textarea>
          <button class="btn" disabled={commentSending || !commentBody.trim()}>
            {commentSending ? $t('comments.sending') : $t('comments.send')}
          </button>
        </form>
      {:else}
        <p class="empty">{$t('comments.needsUnit')}</p>
      {/if}
    </section>
  </article>
{/if}

<style>
  .back {
    font-size: var(--step--1);
    letter-spacing: 0.03em;
  }
  .cat {
    display: inline-flex;
    padding: 0.15em 0.6em;
    border-radius: 999px;
    background: color-mix(in srgb, var(--thread) 15%, transparent);
    color: var(--thread-strong);
  }
  .draft {
    margin-left: 0.75rem;
    border: 1px solid var(--rule);
    padding: 0 0.4em;
    border-radius: 999px;
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
  .comments {
    margin-top: 2.5rem;
    border-top: 1px solid var(--rule);
    padding-top: 1rem;
  }
  .empty {
    color: var(--ink-muted);
    font-size: var(--step--1);
  }
  .thread {
    list-style: none;
    margin: 0 0 1.25rem;
    padding: 0;
    display: grid;
    gap: 0.75rem;
  }
  .thread li {
    padding: 0.75rem 0.9rem;
    border: 1px solid var(--rule);
    border-radius: var(--radius);
    background: var(--paper);
  }
  .thread p {
    margin: 0.5rem 0 0;
  }
  .c-head {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 0.5rem;
  }
  .rm {
    border: 0;
    background: none;
    cursor: pointer;
    color: var(--ink-muted);
    font-size: 1.15rem;
    line-height: 1;
  }
  .rm:hover {
    color: var(--danger);
  }
  .compose {
    display: flex;
    gap: 0.6rem;
    align-items: flex-start;
  }
  .compose textarea {
    flex: 1;
    min-height: 3.5rem;
    padding: 0.6em 0.75em;
    background: var(--paper);
    color: var(--ink);
    border: 1px solid var(--rule);
    border-radius: var(--radius);
    resize: vertical;
  }
  .compose textarea:focus {
    border-color: var(--thread);
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
