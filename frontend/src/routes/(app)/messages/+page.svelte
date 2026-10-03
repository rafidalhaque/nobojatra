<script>
  import { onMount } from 'svelte';
  import { page } from '$app/stores';
  import { api } from '$lib/api.js';
  import { t, lang } from '$lib/i18n';
  import { session } from '$lib/stores.js';
  import { fmtDate, unitLabel } from '$lib/format.js';
  import Spinner from '$lib/components/Spinner.svelte';

  let loading = $state(true);
  let error = $state('');
  let units = $state(new Map());
  let conversations = $state([]);
  let openWith = $state('');
  let thread = $state([]);
  let threadLoading = $state(false);
  let draft = $state('');
  let sending = $state(false);
  let files = $state([]);
  let dragOver = $state(false);

  const apiBase = import.meta.env.VITE_API_BASE ?? '/api';
  const INLINE_IMG = ['image/png', 'image/jpeg', 'image/gif', 'image/webp'];
  const isImage = (a) => INLINE_IMG.includes((a.content_type ?? '').toLowerCase());
  const fileKey = (f) => `${f.name}:${f.size}:${f.lastModified}`;

  function addFiles(list) {
    const seen = new Set(files.map(fileKey));
    const next = [...(list ?? [])].filter((f) => !seen.has(fileKey(f)));
    if (next.length) files = [...files, ...next];
  }
  function removeFile(i) {
    files = files.filter((_, n) => n !== i);
  }

  const isSuper = $derived(Boolean($session?.is_super_admin));
  // Branch/dept accounts act as their own unit; a Super Admin picks a dept to act as.
  let actingUnit = $state($session?.org_unit_id ?? '');
  const canMessage = $derived(Boolean(actingUnit));
  // non-super account with no unit: nothing to show
  const noUnitNotice = $derived(!isSuper && !$session?.org_unit_id);
  const myUnit = $derived(units.get(actingUnit));
  const depts = $derived([...units.values()].filter((u) => u.unit_type === 'dept'));
  const otherUnits = $derived([...units.values()].filter((u) => u.id !== actingUnit));

  // Super Admin sends the acting dept along on every call; a unit account doesn't.
  const asQuery = () => (isSuper && actingUnit ? { as: actingUnit } : {});

  onMount(async () => {
    if (noUnitNotice) {
      loading = false;
      return;
    }
    try {
      const us = await api('/org-units');
      units = new Map(us.map((u) => [u.id, u]));
      if (actingUnit) conversations = await api('/messages/conversations', { query: asQuery() });
      const to = $page.url.searchParams.get('to');
      if (to && to !== actingUnit) await open(to);
    } catch (e) {
      error = e.detail ?? 'error';
    } finally {
      loading = false;
    }
  });

  async function chooseUnit() {
    openWith = '';
    thread = [];
    conversations = [];
    error = '';
    if (!actingUnit) return;
    try {
      conversations = await api('/messages/conversations', { query: asQuery() });
    } catch (e) {
      error = e.detail ?? 'error';
    }
  }

  async function open(unitId) {
    openWith = unitId;
    threadLoading = true;
    try {
      thread = await api('/messages', { query: { with: unitId, ...asQuery() } });
      for (const m of thread) {
        if (m.recipient_org_unit_id === actingUnit && !m.read_at) {
          api(`/messages/${m.id}/read`, { method: 'POST', query: asQuery() }).catch(() => {});
        }
      }
    } catch (e) {
      error = e.detail ?? 'error';
    } finally {
      threadLoading = false;
    }
  }

  async function send() {
    if ((!draft.trim() && !files.length) || !openWith || sending) return;
    sending = true;
    try {
      const fd = new FormData();
      fd.append('recipient_org_unit_id', openWith);
      fd.append('body', draft);
      if (isSuper) fd.append('sender_org_unit_id', actingUnit);
      for (const f of files) fd.append('files', f);
      const m = await api('/messages', { method: 'POST', body: fd });
      thread = [...thread, m];
      draft = '';
      files = [];
    } catch (e) {
      error = e.detail ?? 'error';
    } finally {
      sending = false;
    }
  }
</script>

<svelte:head><title>{$t('messages.heading')} · Nobojatra</title></svelte:head>

<h1>{$t('messages.heading')}</h1>
{#if myUnit && !isSuper}<p class="asunit label">{$t('messages.fromUnit', { unit: unitLabel(myUnit) })}</p>{/if}

{#if noUnitNotice}
  <p class="muted center">{$t('messages.noUnit')}</p>
{:else if loading}
  <Spinner block />
{:else}
  {#if isSuper}
    <label class="actas">
      {$t('messages.messageAs')}
      <select bind:value={actingUnit} onchange={chooseUnit}>
        <option value="" disabled>—</option>
        {#each depts as u (u.id)}<option value={u.id}>{unitLabel(u)}</option>{/each}
      </select>
    </label>
  {/if}

  {#if error}
    <p class="err" role="alert">{$t('common.error', { detail: error })}</p>
  {/if}

  {#if !canMessage}
    <p class="muted center">{$t('messages.pickDept')}</p>
  {:else}
  <div class="split">
    <aside>
      <label class="newconv">
        {$t('messages.to')}
        <select bind:value={openWith} onchange={() => open(openWith)}>
          <option value="" disabled>—</option>
          {#each otherUnits as u (u.id)}<option value={u.id}>{unitLabel(u)}</option>{/each}
        </select>
      </label>

      <ul class="convs">
        {#each conversations as c (c.org_unit_id)}
          <li>
            <button class:on={openWith === c.org_unit_id} onclick={() => open(c.org_unit_id)}>
              <span class="cu">{unitLabel(units.get(c.org_unit_id)) || c.org_unit_id.slice(0, 8)}</span>
              <span class="cx">{c.last_body}</span>
              {#if c.unread}<span class="badge">{c.unread}</span>{/if}
            </button>
          </li>
        {:else}
          <li class="muted">{$t('messages.empty')}</li>
        {/each}
      </ul>
    </aside>

    <section class="pane">
      {#if !openWith}
        <p class="muted center">{$t('messages.empty')}</p>
      {:else}
        {@const peer = units.get(openWith)}
        <header class="phead">
          <span class="avatar">{unitLabel(peer).slice(0, 2).toUpperCase()}</span>
          <div>
            <strong>{unitLabel(peer)}</strong>
            <small>{peer?.unit_type ?? ''}</small>
          </div>
        </header>
      {/if}
      {#if !openWith}
        <!-- header branch above covers the empty state -->
      {:else if threadLoading}
        <Spinner block />
      {:else}
        <ol class="bubbles" lang={$lang}>
          {#if !thread.length}<li class="hint">{$t('messages.write')}</li>{/if}
          {#each thread as m (m.id)}
            <li class:mine={m.sender_org_unit_id === actingUnit}>
              {#if m.body}<p>{m.body}</p>{/if}
              {#if m.attachments?.length}
                <ul class="atts">
                  {#each m.attachments as a (a.id)}
                    <li>
                      {#if isImage(a)}
                        <a href={`${apiBase}/messages/attachments/${a.id}`} target="_blank" rel="noopener">
                          <img src={`${apiBase}/messages/attachments/${a.id}`} alt={a.original_filename} loading="lazy" />
                        </a>
                      {:else}
                        <a href={`${apiBase}/messages/attachments/${a.id}`} target="_blank" rel="noopener">{a.original_filename}</a>
                      {/if}
                    </li>
                  {/each}
                </ul>
              {/if}
              <time>{fmtDate(m.created_at, true)}</time>
            </li>
          {/each}
        </ol>
        <form
          class="compose"
          class:over={dragOver}
          onsubmit={(e) => (e.preventDefault(), send())}
          ondragover={(e) => (e.preventDefault(), (dragOver = true))}
          ondragleave={() => (dragOver = false)}
          ondrop={(e) => (e.preventDefault(), (dragOver = false), addFiles(e.dataTransfer?.files))}
        >
          {#if files.length}
            <ul class="pending">
              {#each files as f, i (fileKey(f))}
                <li>
                  <span class="fn">{f.name}</span>
                  <button type="button" class="rm" onclick={() => removeFile(i)} aria-label={$t('messages.remove')}>×</button>
                </li>
              {/each}
            </ul>
          {/if}
          <div class="composerow">
            <label class="clip" title={$t('messages.attach')} aria-label={$t('messages.attach')}>
              <svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="m21 12-9 9a6 6 0 0 1-8.5-8.5l9-9a4 4 0 0 1 5.7 5.7l-9 9a2 2 0 0 1-2.8-2.8l8.5-8.5" /></svg>
              <input
                type="file"
                multiple
                onchange={(e) => {
                  addFiles(e.currentTarget.files);
                  e.currentTarget.value = '';
                }}
              />
            </label>
            <textarea
              rows="1"
              bind:value={draft}
              placeholder={$t('messages.write')}
              lang={$lang}
              onkeydown={(e) => e.key === 'Enter' && !e.shiftKey && (e.preventDefault(), send())}
            ></textarea>
            <button class="sendbtn" aria-label={$t('messages.send')} disabled={sending || (!draft.trim() && !files.length)}>
              <svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="m22 2-7 20-4-9-9-4z" /><path d="M22 2 11 13" /></svg>
            </button>
          </div>
        </form>
      {/if}
    </section>
  </div>
  {/if}
{/if}

<style>
  .asunit {
    color: var(--seal);
    margin-top: -0.5rem;
  }
  .actas {
    display: inline-flex;
    align-items: center;
    gap: 0.5rem;
    margin-bottom: 1rem;
    font-size: var(--step--1);
    color: var(--ink-muted);
  }
  .actas select {
    padding: 0.4em 0.6em;
    border: 1px solid var(--rule);
    border-radius: var(--radius);
    background-color: var(--paper);
  }
  .split {
    display: grid;
    grid-template-columns: 16rem minmax(0, 1fr);
    gap: 1.25rem;
    align-items: start;
  }
  aside {
    border: 1px solid var(--rule);
    border-radius: var(--radius);
    padding: 0.75rem;
    background: var(--paper-raised);
  }
  .newconv {
    display: grid;
    gap: 0.3rem;
    font-size: var(--step--1);
    color: var(--ink-muted);
    margin-bottom: 0.75rem;
  }
  .newconv select {
    padding: 0.4em;
    border: 1px solid var(--rule);
    border-radius: var(--radius);
    background-color: var(--paper);
  }
  .convs {
    list-style: none;
    margin: 0;
    padding: 0;
    display: grid;
    gap: 2px;
  }
  .convs button {
    width: 100%;
    text-align: left;
    background: none;
    border: 1px solid transparent;
    border-radius: var(--radius);
    padding: 0.5rem;
    cursor: pointer;
    display: grid;
    gap: 1px;
  }
  .convs button:hover {
    background: color-mix(in srgb, var(--thread) 8%, transparent);
  }
  .convs button.on {
    border-color: var(--rule);
    background: var(--paper);
  }
  .cu {
    font-weight: 700;
    letter-spacing: 0.03em;
    font-size: var(--step--1);
  }
  .cx {
    color: var(--ink-muted);
    font-size: var(--step--1);
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }
  .badge {
    justify-self: start;
    background: var(--seal);
    color: #fff;
    border-radius: 999px;
    font-size: 0.7rem;
    padding: 0 0.45em;
  }
  .pane {
    border: 1px solid var(--rule);
    border-radius: var(--radius);
    min-height: 32rem;
    overflow: hidden;
    display: flex;
    flex-direction: column;
    background: var(--paper-raised);
  }
  .bubbles {
    list-style: none;
    margin: 0;
    padding: 1rem;
    display: grid;
    align-content: start;
    gap: 0.6rem;
    flex: 1;
    overflow-y: auto;
  }
  .bubbles li {
    max-width: 80%;
    padding: 0.5rem 0.75rem;
    border: 1px solid var(--rule);
    border-radius: var(--radius);
    background: var(--paper);
  }
  .bubbles li.mine {
    justify-self: end;
    border-color: var(--thread);
    background: color-mix(in srgb, var(--thread) 10%, transparent);
  }
  .bubbles p {
    margin: 0 0 0.2rem;
  }
  .bubbles time {
    font-size: 0.7rem;
    color: var(--ink-muted);
    letter-spacing: 0.03em;
  }
  .atts {
    list-style: none;
    margin: 0.35rem 0 0;
    padding: 0;
    display: grid;
    gap: 0.35rem;
  }
  .atts img {
    max-width: 12rem;
    border-radius: var(--radius);
    display: block;
  }
  .compose {
    display: flex;
    flex-direction: column;
    gap: 0.4rem;
    padding: 0.75rem;
    border-top: 1px solid var(--rule);
  }
  .compose.over {
    background: color-mix(in srgb, var(--thread) 6%, transparent);
  }
  .composerow {
    display: flex;
    gap: 0.5rem;
    align-items: flex-end;
  }
  .clip {
    display: inline-flex;
    align-items: center;
    padding: 0 0.6em;
    height: 2.3em;
    border: 1px solid var(--rule);
    border-radius: var(--radius);
    background: var(--paper);
    cursor: pointer;
    font-size: var(--step--1);
    color: var(--ink-muted);
    white-space: nowrap;
  }
  .clip input {
    display: none;
  }
  .compose textarea {
    flex: 1;
    resize: none;
    font-family: var(--font-latin);
    height: 2.6rem;
    padding: 0.6em 0.8em;
    border: 1px solid var(--rule);
    border-radius: var(--radius);
    background: var(--paper);
    color: var(--ink);
  }
  .compose textarea:focus {
    outline: none;
    border-color: var(--thread);
  }
  .clip,
  .sendbtn {
    width: 2.6rem;
    height: 2.6rem;
    padding: 0;
    justify-content: center;
    flex: none;
  }
  .sendbtn {
    display: inline-flex;
    align-items: center;
    border: 1px solid var(--rule);
    border-radius: var(--radius);
    background: var(--paper);
    color: var(--ink);
    cursor: pointer;
  }
  .sendbtn:hover:not(:disabled) {
    border-color: var(--thread);
    color: var(--thread);
  }
  .sendbtn:disabled {
    opacity: 0.5;
    cursor: default;
  }
  .composerow {
    align-items: center;
  }
  .phead {
    display: flex;
    align-items: center;
    gap: 0.75rem;
    padding: 0.9rem 1.1rem;
    border-bottom: 1px solid var(--rule);
  }
  .phead div {
    display: grid;
  }
  .phead small {
    color: var(--ink-muted);
    font-size: var(--step--1);
  }
  .avatar {
    display: grid;
    place-items: center;
    width: 2.1rem;
    height: 2.1rem;
    border-radius: 50%;
    border: 1px solid var(--thread);
    background: color-mix(in srgb, var(--thread) 15%, transparent);
    color: var(--thread);
    font-size: 0.7rem;
    font-weight: 700;
  }
  .bubbles li.hint {
    justify-self: center;
    border: 0;
    background: none;
    color: var(--ink-muted);
  }
  .pending {
    list-style: none;
    margin: 0;
    padding: 0;
    display: grid;
    gap: 2px;
  }
  .pending li {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    padding: 0.3rem 0.55rem;
    border: 1px solid var(--rule);
    border-radius: var(--radius);
    background: var(--paper);
    font-size: var(--step--1);
  }
  .pending .fn {
    flex: 1;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }
  .pending .rm {
    border: 0;
    background: none;
    cursor: pointer;
    color: var(--ink-muted);
    font-size: 1.15rem;
    line-height: 1;
    padding: 0 0.25rem;
  }
  .pending .rm:hover {
    color: var(--danger);
  }
  .muted {
    color: var(--ink-muted);
  }
  .center {
    text-align: center;
    padding: 3rem 1rem;
  }
  .err {
    color: var(--danger);
  }
  @media (max-width: 720px) {
    .split {
      grid-template-columns: 1fr;
    }
  }
</style>
