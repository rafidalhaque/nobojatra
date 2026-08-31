<script>
  import { onMount } from 'svelte';
  import { goto } from '$app/navigation';
  import { api } from '$lib/api.js';
  import { t, lang } from '$lib/i18n';
  import Spinner from '$lib/components/Spinner.svelte';

  /** @type {{ postId?: string }} */
  let { postId } = $props();
  const editing = $derived(!!postId);

  let loading = $state(editing);
  let saving = $state('');
  let error = $state('');
  let categories = $state([]);

  let title = $state('');
  let body = $state('');
  let categoryId = $state('');
  let noticeDate = $state(''); // datetime-local; blank -> backend uses now()
  let files = $state([]);
  let status = $state('draft');

  onMount(async () => {
    try {
      categories = await api('/categories');
      if (editing) {
        const p = await api(`/posts/${postId}`);
        title = p.title;
        body = p.body;
        categoryId = p.category_id;
        status = p.status;
        noticeDate = toLocalInput(p.created_at);
      } else if (categories.length) {
        categoryId = categories[0].id;
      }
    } catch (e) {
      error = e.detail ?? 'error';
    } finally {
      loading = false;
    }
  });

  function toLocalInput(iso) {
    const d = new Date(iso);
    const p = (n) => String(n).padStart(2, '0');
    return `${d.getFullYear()}-${p(d.getMonth() + 1)}-${p(d.getDate())}T${p(d.getHours())}:${p(d.getMinutes())}`;
  }

  async function save(publish) {
    if (saving) return;
    saving = publish ? 'publish' : 'draft';
    error = '';
    const payload = {
      title,
      body,
      category_id: categoryId,
      created_at: noticeDate ? new Date(noticeDate).toISOString() : null
    };
    try {
      let post;
      if (editing) {
        post = await api(`/posts/${postId}`, { method: 'PATCH', body: payload });
      } else {
        post = await api('/posts', { method: 'POST', body: { ...payload, status: 'draft' } });
      }
      if (files.length) {
        const fd = new FormData();
        for (const f of files) fd.append('files', f);
        await api(`/posts/${post.id}/media`, { method: 'POST', body: fd });
      }
      if (publish && post.status !== 'published') {
        await api(`/posts/${post.id}/publish`, { method: 'POST' });
      }
      await goto(`/posts/${post.id}`);
    } catch (e) {
      error = e.detail ?? 'error';
      saving = '';
    }
  }
</script>

<h1>{editing ? $t('editor.editHeading') : $t('editor.newHeading')}</h1>

{#if loading}
  <Spinner block />
{:else}
  <form onsubmit={(e) => e.preventDefault()} class="editor">
    <div class="field">
      <label for="t">{$t('editor.title')}</label>
      <input id="t" bind:value={title} required lang={$lang} />
    </div>

    <div class="row">
      <div class="field">
        <label for="c">{$t('editor.category')}</label>
        <select id="c" bind:value={categoryId} required>
          {#each categories as c (c.id)}<option value={c.id}>{c.name}</option>{/each}
        </select>
      </div>
      <div class="field">
        <label for="d">{$t('editor.date')}</label>
        <input id="d" type="datetime-local" bind:value={noticeDate} />
        <small>{$t('editor.dateHint')}</small>
      </div>
    </div>

    <div class="field">
      <label for="b">{$t('editor.body')}</label>
      <textarea id="b" rows="14" bind:value={body} lang={$lang}></textarea>
    </div>

    <div class="field">
      <label for="m">{$t('editor.media')}</label>
      <input id="m" type="file" multiple onchange={(e) => (files = [...e.currentTarget.files])} />
    </div>

    {#if error}<p class="err" role="alert">{$t('common.error', { detail: error })}</p>{/if}

    <div class="actions">
      <button class="btn btn--ghost" onclick={() => save(false)} disabled={!!saving}>
        {saving === 'draft' ? $t('common.saving') : $t('editor.saveDraft')}
      </button>
      <button class="btn" onclick={() => save(true)} disabled={!!saving}>
        {saving === 'publish' ? $t('common.saving') : $t('editor.publish')}
      </button>
    </div>
  </form>
{/if}

<style>
  .editor {
    max-width: 44rem;
  }
  .row {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 1rem;
  }
  textarea {
    width: 100%;
    resize: vertical;
    font-family: var(--font-latin);
    line-height: 1.6;
  }
  small {
    color: var(--ink-muted);
    font-size: var(--step--1);
  }
  .actions {
    display: flex;
    gap: 0.75rem;
    margin-top: 1rem;
  }
  .err {
    color: var(--danger);
  }
  @media (max-width: 560px) {
    .row {
      grid-template-columns: 1fr;
    }
  }
</style>
