<script>
  import { onMount } from 'svelte';
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

  const myUnit = $derived(units.get($session?.org_unit_id));
  const hasUnit = $derived(Boolean($session?.org_unit_id));

  onMount(async () => {
    if (!hasUnit) {
      loading = false;
      return;
    }
    try {
      const [us, convs] = await Promise.all([api('/org-units'), api('/messages/conversations')]);
      units = new Map(us.map((u) => [u.id, u]));
      conversations = convs;
    } catch (e) {
      error = e.detail ?? 'error';
    } finally {
      loading = false;
    }
  });

  async function open(unitId) {
    openWith = unitId;
    threadLoading = true;
    try {
      thread = await api('/messages', { query: { with: unitId } });
      for (const m of thread) {
        if (m.recipient_org_unit_id === $session.org_unit_id && !m.read_at) {
          api(`/messages/${m.id}/read`, { method: 'POST' }).catch(() => {});
        }
      }
    } catch (e) {
      error = e.detail ?? 'error';
    } finally {
      threadLoading = false;
    }
  }

  async function send() {
    if (!draft.trim() || !openWith || sending) return;
    sending = true;
    try {
      const m = await api('/messages', {
        method: 'POST',
        body: { recipient_org_unit_id: openWith, body: draft }
      });
      thread = [...thread, m];
      draft = '';
    } catch (e) {
      error = e.detail ?? 'error';
    } finally {
      sending = false;
    }
  }

  const otherUnits = $derived([...units.values()].filter((u) => u.id !== $session?.org_unit_id));
</script>

<svelte:head><title>{$t('messages.heading')} · Nobojatra</title></svelte:head>

<h1>{$t('messages.heading')}</h1>
{#if myUnit}<p class="asunit label">{$t('messages.fromUnit', { unit: unitLabel(myUnit) })}</p>{/if}

{#if !hasUnit}
  <p class="muted center">{$t('messages.noUnit')}</p>
{:else if loading}
  <Spinner block />
{:else if error}
  <p class="err" role="alert">{$t('common.error', { detail: error })}</p>
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
      {:else if threadLoading}
        <Spinner block />
      {:else}
        <ol class="bubbles" lang={$lang}>
          {#each thread as m (m.id)}
            <li class:mine={m.sender_org_unit_id === $session.org_unit_id}>
              <p>{m.body}</p>
              <time>{fmtDate(m.created_at, true)}</time>
            </li>
          {/each}
        </ol>
        <form class="compose" onsubmit={(e) => (e.preventDefault(), send())}>
          <textarea rows="2" bind:value={draft} placeholder={$t('messages.write')} lang={$lang}></textarea>
          <button class="btn" disabled={sending || !draft.trim()}>
            {sending ? $t('messages.sending') : $t('messages.send')}
          </button>
        </form>
      {/if}
    </section>
  </div>
{/if}

<style>
  .asunit {
    color: var(--seal);
    margin-top: -0.5rem;
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
    background: var(--paper);
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
    min-height: 24rem;
    display: flex;
    flex-direction: column;
    background: var(--paper-raised);
  }
  .bubbles {
    list-style: none;
    margin: 0;
    padding: 1rem;
    display: grid;
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
  .compose {
    display: flex;
    gap: 0.5rem;
    padding: 0.75rem;
    border-top: 1px solid var(--rule);
  }
  .compose textarea {
    flex: 1;
    resize: none;
    font-family: var(--font-latin);
    padding: 0.5em;
    border: 1px solid var(--rule);
    border-radius: var(--radius);
    background: var(--paper);
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
