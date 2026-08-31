<script>
  import { onMount } from 'svelte';
  import { goto } from '$app/navigation';
  import { api } from '$lib/api.js';
  import { session } from '$lib/stores.js';
  import { t, lang } from '$lib/i18n';
  import { unitLabel } from '$lib/format.js';
  import Spinner from '$lib/components/Spinner.svelte';

  /** @type {{ postId?: string }} */
  let { postId } = $props();
  const editing = $derived(!!postId);
  // Super Admin has no org unit, so on a NEW post they must name one to post as.
  const needsUnitPick = $derived(!editing && !!$session?.is_super_admin && !$session?.org_unit_id);

  let loading = $state(true);
  let saving = $state('');
  let error = $state('');
  let categories = $state([]);
  let units = $state([]);

  let title = $state('');
  let body = $state('');
  let categoryId = $state('');
  let orgUnitId = $state('');
  let noticeDate = $state(''); // datetime-local; blank -> backend uses now()
  let files = $state([]);
  let existingMedia = $state([]); // already-uploaded attachments (edit mode)
  let dragOver = $state(false);
  let status = $state('draft');

  const fileKey = (f) => `${f.name}:${f.size}:${f.lastModified}`;

  function addFiles(list) {
    const seen = new Set(files.map(fileKey));
    const next = [...(list ?? [])].filter((f) => !seen.has(fileKey(f)));
    if (next.length) files = [...files, ...next];
  }
  function removeFile(i) {
    files = files.filter((_, n) => n !== i);
  }
  async function removeExisting(m) {
    if (!confirm($t('editor.removeConfirm', { name: m.original_filename }))) return;
    try {
      await api(`/posts/${postId}/media/${m.id}`, { method: 'DELETE' });
      existingMedia = existingMedia.filter((x) => x.id !== m.id);
    } catch (e) {
      error = e.detail ?? 'error';
    }
  }

  onMount(async () => {
    try {
      const reqs = [api('/categories')];
      if (needsUnitPick) reqs.push(api('/org-units'));
      const [cats, us] = await Promise.all(reqs);
      categories = cats;
      if (us) units = us;
      if (editing) {
        const p = await api(`/posts/${postId}`);
        title = p.title;
        body = p.body;
        categoryId = p.category_id;
        status = p.status;
        noticeDate = toLocalInput(p.created_at);
        existingMedia = p.media ?? [];
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
    if (needsUnitPick && !orgUnitId) {
      error = $t('editor.pickUnitFirst');
      return;
    }
    saving = publish ? 'publish' : 'draft';
    error = '';
    const payload = {
      title,
      body,
      category_id: categoryId,
      created_at: noticeDate ? new Date(noticeDate).toISOString() : null,
      ...(needsUnitPick ? { org_unit_id: orgUnitId } : {})
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
    <div class="main">
      <div class="field">
        <label for="t">{$t('editor.title')}</label>
        <input id="t" bind:value={title} required lang={$lang} />
      </div>

      <div class="field grow">
        <label for="b">{$t('editor.body')}</label>
        <textarea id="b" bind:value={body} lang={$lang}></textarea>
      </div>
    </div>

    <aside class="side">
      {#if needsUnitPick}
        <div class="field">
          <label for="ou">{$t('editor.postAs')}</label>
          <select id="ou" bind:value={orgUnitId} required>
            <option value="" disabled>—</option>
            {#each units as u (u.id)}<option value={u.id}>{unitLabel(u)}</option>{/each}
          </select>
        </div>
      {/if}

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

      <div class="field">
        <span class="lbl">{$t('editor.media')}</span>
        {#if existingMedia.length}
          <ul class="files">
            {#each existingMedia as m (m.id)}
              <li>
                <span class="fn">{m.original_filename}</span>
                <button type="button" class="rm" onclick={() => removeExisting(m)} aria-label={$t('editor.remove')}>×</button>
              </li>
            {/each}
          </ul>
        {/if}
        <label
          class="drop"
          class:over={dragOver}
          ondragover={(e) => (e.preventDefault(), (dragOver = true))}
          ondragleave={() => (dragOver = false)}
          ondrop={(e) => (e.preventDefault(), (dragOver = false), addFiles(e.dataTransfer?.files))}
        >
          <input
            type="file"
            multiple
            onchange={(e) => {
              addFiles(e.currentTarget.files);
              e.currentTarget.value = ''; // allow re-picking the same file
            }}
          />
          <span>{$t('editor.dropHint')}</span>
        </label>
        {#if files.length}
          <ul class="files">
            {#each files as f, i (fileKey(f))}
              <li>
                <span class="fn">{f.name}</span>
                <button type="button" class="rm" onclick={() => removeFile(i)} aria-label={$t('editor.remove')}>×</button>
              </li>
            {/each}
          </ul>
        {/if}
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
    </aside>
  </form>
{/if}

<style>
  .editor {
    display: grid;
    grid-template-columns: minmax(0, 1fr) 19rem;
    gap: 2.5rem;
    align-items: start;
  }
  .main {
    display: flex;
    flex-direction: column;
    gap: 1rem;
    min-height: 70vh;
  }
  .main .grow {
    flex: 1;
  }
  textarea {
    flex: 1;
    min-height: 60vh;
    resize: vertical;
    font-family: var(--font-latin);
    line-height: 1.6;
  }
  .side {
    position: sticky;
    top: 1.5rem;
    display: flex;
    flex-direction: column;
    gap: 1.1rem;
    border-left: 1px solid var(--rule);
    padding-left: 1.75rem;
  }
  .side .field {
    margin-bottom: 0;
  }
  small {
    color: var(--ink-muted);
    font-size: var(--step--1);
  }
  .lbl {
    display: block;
    margin-bottom: 0.35em;
  }
  .drop {
    display: block;
    border: 1.5px dashed var(--rule);
    border-radius: var(--radius);
    padding: 1rem;
    text-align: center;
    color: var(--ink-muted);
    font-size: var(--step--1);
    cursor: pointer;
  }
  .drop:hover,
  .drop.over {
    border-color: var(--thread);
    color: var(--thread-strong);
    background: color-mix(in srgb, var(--thread) 6%, transparent);
  }
  .drop input {
    display: none;
  }
  .files {
    list-style: none;
    margin: 0.5rem 0 0;
    padding: 0;
    display: grid;
    gap: 2px;
  }
  .files li {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    padding: 0.35rem 0.55rem;
    border: 1px solid var(--rule);
    border-radius: var(--radius);
    background: var(--paper);
    font-size: var(--step--1);
  }
  .fn {
    flex: 1;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }
  .rm {
    border: 0;
    background: none;
    cursor: pointer;
    color: var(--ink-muted);
    font-size: 1.15rem;
    line-height: 1;
    padding: 0 0.25rem;
  }
  .rm:hover {
    color: var(--danger);
  }
  .actions {
    display: flex;
    flex-direction: column;
    gap: 0.6rem;
    margin-top: 0.5rem;
  }
  .actions .btn {
    width: 100%;
  }
  .err {
    color: var(--danger);
    font-size: var(--step--1);
  }

  @media (max-width: 820px) {
    .editor {
      grid-template-columns: 1fr;
      gap: 1.5rem;
    }
    .side {
      position: static;
      border-left: 0;
      padding-left: 0;
      border-top: 1px solid var(--rule);
      padding-top: 1.25rem;
    }
    textarea {
      min-height: 40vh;
    }
  }
</style>
