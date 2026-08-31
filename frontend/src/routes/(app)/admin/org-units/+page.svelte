<script>
  import { onMount } from 'svelte';
  import { api } from '$lib/api.js';
  import { t } from '$lib/i18n';
  import { unitLabel } from '$lib/format.js';
  import Spinner from '$lib/components/Spinner.svelte';

  let loading = $state(true);
  let error = $state('');
  let areas = $state([]);
  let units = $state([]);

  // single create
  let cType = $state('dept');
  let cName = $state('');
  let cCode = $state('');
  let cArea = $state('');
  let cPassword = $state('');
  let creating = $state(false);
  let createErr = $state('');

  // csv import
  let iType = $state('dept');
  let iArea = $state('');
  let iFile = $state(null);
  let importing = $state(false);
  let importOk = $state('');
  let rowErrors = $state([]);
  let importErr = $state('');

  // inline profile edit (Super Admin only page)
  let editId = $state(null);
  let eName = $state('');
  let eCode = $state('');
  let eArea = $state('');
  let savingEdit = $state(false);
  let editErr = $state('');

  onMount(load);

  async function load() {
    loading = true;
    try {
      [areas, units] = await Promise.all([api('/areas'), api('/org-units')]);
      if (areas.length && !cArea) cArea = areas[0].id;
      if (areas.length && !iArea) iArea = areas[0].id;
      error = '';
    } catch (e) {
      error = e.detail ?? 'error';
    } finally {
      loading = false;
    }
  }

  function sortUnits(list) {
    return [...list].sort((a, b) => a.unit_type.localeCompare(b.unit_type) || a.name.localeCompare(b.name));
  }

  function startEdit(u) {
    editId = u.id;
    eName = u.name;
    eCode = u.code;
    eArea = u.area_id;
    editErr = '';
  }

  async function removeUnit(u) {
    if (!confirm($t('admin.units.deleteConfirm', { name: u.name }))) return;
    error = '';
    try {
      await api(`/org-units/${u.id}`, { method: 'DELETE' });
      units = units.filter((x) => x.id !== u.id);
    } catch (e) {
      error = e.detail ?? 'error';
    }
  }

  async function saveEdit() {
    if (savingEdit) return;
    const cur = units.find((x) => x.id === editId);
    const patch = {};
    if (eName.trim() !== cur.name) patch.name = eName.trim();
    if (eCode.trim() !== cur.code) patch.code = eCode.trim();
    if (eArea !== cur.area_id) patch.area_id = eArea;
    if (!Object.keys(patch).length) {
      editId = null;
      return;
    }
    savingEdit = true;
    editErr = '';
    try {
      const updated = await api(`/org-units/${editId}`, { method: 'PATCH', body: patch });
      units = sortUnits(units.map((x) => (x.id === updated.id ? updated : x)));
      editId = null;
    } catch (e) {
      editErr = e.detail ?? 'error';
    } finally {
      savingEdit = false;
    }
  }

  async function createOne() {
    if (creating) return;
    creating = true;
    createErr = '';
    try {
      const u = await api('/org-units', {
        method: 'POST',
        body: { unit_type: cType, name: cName.trim(), code: cCode.trim(), area_id: cArea, password: cPassword }
      });
      units = sortUnits([...units, u]);
      cName = cCode = cPassword = '';
    } catch (e) {
      createErr = e.detail ?? 'error';
    } finally {
      creating = false;
    }
  }

  async function runImport() {
    if (!iFile || importing) return;
    importing = true;
    importOk = '';
    importErr = '';
    rowErrors = [];
    try {
      const fd = new FormData();
      fd.append('unit_type', iType);
      fd.append('area_id', iArea);
      fd.append('file', iFile);
      const res = await api('/org-units/import', { method: 'POST', body: fd });
      importOk = $t('admin.units.import.ok', { n: res.created });
      await load();
    } catch (e) {
      const rows = e.data?.detail?.errors;
      if (Array.isArray(rows)) rowErrors = rows;
      else importErr = e.detail ?? 'error';
    } finally {
      importing = false;
    }
  }

  const areaName = $derived((id) => areas.find((a) => a.id === id)?.name ?? '—');
</script>

<svelte:head><title>{$t('admin.nav.orgUnits')} · Nobojatra</title></svelte:head>

{#if loading}
  <Spinner block />
{:else if error}
  <p class="err" role="alert">{$t('common.error', { detail: error })}</p>
{:else if areas.length === 0}
  <p class="muted">{$t('admin.units.needArea')} <a href="/admin/areas">{$t('admin.nav.areas')}</a></p>
{:else}
  <details class="disc">
    <summary class="label">{$t('admin.units.createOne')}</summary>
    <form class="grid" onsubmit={(e) => (e.preventDefault(), createOne())}>
      <label>{$t('admin.units.type')}
        <select bind:value={cType}>
          <option value="dept">{$t('admin.units.dept')}</option>
          <option value="branch">{$t('admin.units.branch')}</option>
        </select>
      </label>
      <label>{$t('admin.units.area')}
        <select bind:value={cArea}>
          {#each areas as a (a.id)}<option value={a.id}>{a.name}</option>{/each}
        </select>
      </label>
      <label>{$t('admin.units.name')}<input bind:value={cName} required /></label>
      <label>{$t('admin.units.code')}<input bind:value={cCode} required autocapitalize="none" spellcheck="false" /></label>
      <label>{$t('admin.units.password')}<input type="text" bind:value={cPassword} required /></label>
      <div class="act">
        <button class="btn" disabled={creating || !cName.trim() || !cCode.trim() || !cPassword}>
          {creating ? $t('admin.units.creating') : $t('admin.units.create')}
        </button>
        {#if createErr}<span class="err">{createErr}</span>{/if}
      </div>
    </form>
    <p class="hint">{$t('admin.units.codeHint')}</p>
  </details>

  <details class="disc">
    <summary class="label">{$t('admin.units.importCsv')}</summary>
    <form class="grid" onsubmit={(e) => (e.preventDefault(), runImport())}>
      <label>{$t('admin.units.type')}
        <select bind:value={iType}>
          <option value="dept">{$t('admin.units.dept')}</option>
          <option value="branch">{$t('admin.units.branch')}</option>
        </select>
      </label>
      <label>{$t('admin.units.area')}
        <select bind:value={iArea}>
          {#each areas as a (a.id)}<option value={a.id}>{a.name}</option>{/each}
        </select>
      </label>
      <label class="wide">{$t('admin.units.file')}
        <input type="file" accept=".csv,text/csv" onchange={(e) => (iFile = e.currentTarget.files[0] ?? null)} />
      </label>
      <div class="act">
        <button class="btn" disabled={importing || !iFile}>
          {importing ? $t('admin.units.import.running') : $t('admin.units.import.run')}
        </button>
        {#if importOk}<span class="ok">{importOk}</span>{/if}
        {#if importErr}<span class="err">{importErr}</span>{/if}
      </div>
    </form>
    <p class="hint">{$t('admin.units.import.hint', { cols: iType === 'branch' ? 'branch_name, branch_code, branch_password' : 'dept_name, dept_code, dept_password' })}</p>

    {#if rowErrors.length}
      <div class="rowerrs">
        <p class="label">{$t('admin.units.import.rejected')}</p>
        <ul>
          {#each rowErrors as r (r.row)}
            <li><b>{$t('admin.units.import.row', { n: r.row })}</b> — {r.errors.join('; ')}</li>
          {/each}
        </ul>
      </div>
    {/if}
  </details>

  <section>
    <h2 class="label">{$t('admin.units.existing')}</h2>
    {#if units.length === 0}
      <p class="muted">{$t('common.none')}</p>
    {:else}
      <table>
        <thead><tr><th>{$t('admin.units.type')}</th><th>{$t('admin.units.code')}</th><th>{$t('admin.units.name')}</th><th>{$t('admin.units.area')}</th><th>{$t('admin.units.actions')}</th></tr></thead>
        <tbody>
          {#each units as u (u.id)}
            {#if editId === u.id}
              <tr>
                <td>{u.unit_type === 'dept' ? $t('admin.units.dept') : $t('admin.units.branch')}</td>
                <td><input class="ei" bind:value={eCode} aria-label={$t('admin.units.code')} /></td>
                <td><input class="ei" bind:value={eName} aria-label={$t('admin.units.name')} /></td>
                <td>
                  <select class="ei" bind:value={eArea} aria-label={$t('admin.units.area')}>
                    {#each areas as a (a.id)}<option value={a.id}>{a.name}</option>{/each}
                  </select>
                </td>
                <td class="acts">
                  <button class="lnk" onclick={saveEdit} disabled={savingEdit}>
                    {savingEdit ? $t('admin.units.creating') : $t('common.save')}
                  </button>
                  <button class="lnk" onclick={() => (editId = null)} disabled={savingEdit}>{$t('common.cancel')}</button>
                </td>
              </tr>
              {#if editErr}<tr><td colspan="5" class="err">{editErr}</td></tr>{/if}
            {:else}
              <tr>
                <td>{u.unit_type === 'dept' ? $t('admin.units.dept') : $t('admin.units.branch')}</td>
                <td class="code">{u.code}</td>
                <td>{u.name}</td>
                <td>{areaName(u.area_id)}</td>
                <td class="acts">
                  <button class="lnk" onclick={() => startEdit(u)}>{$t('common.edit')}</button>
                  <button class="lnk danger" onclick={() => removeUnit(u)}>{$t('common.delete')}</button>
                </td>
              </tr>
            {/if}
          {/each}
        </tbody>
      </table>
    {/if}
  </section>
{/if}

<style>
  section {
    margin-bottom: 2.5rem;
  }
  .disc {
    margin-bottom: 1rem;
    border: 1px solid var(--rule);
    border-radius: var(--radius);
    background: var(--paper-raised);
  }
  .disc summary {
    cursor: pointer;
    padding: 0.8rem 1rem;
    user-select: none;
  }
  .disc[open] summary {
    border-bottom: 1px solid var(--rule);
  }
  .disc > :not(summary) {
    margin-left: 1rem;
    margin-right: 1rem;
  }
  .disc > :first-of-type {
    margin-top: 1rem;
  }
  .disc > :last-child {
    margin-bottom: 1rem;
  }
  .grid {
    display: grid;
    grid-template-columns: repeat(2, minmax(0, 1fr));
    gap: 0.9rem 1rem;
    max-width: 40rem;
    margin-top: 0.75rem;
  }
  .grid label {
    display: grid;
    gap: 0.3rem;
    font-size: var(--step--1);
    color: var(--ink-muted);
  }
  .grid .wide,
  .grid .act {
    grid-column: 1 / -1;
  }
  .grid input,
  .grid select {
    padding: 0.5em 0.65em;
    background: var(--paper);
    border: 1px solid var(--rule);
    border-radius: var(--radius);
    color: var(--ink);
  }
  .act {
    display: flex;
    align-items: center;
    gap: 1rem;
    margin-top: 0.25rem;
  }
  .hint {
    color: var(--ink-muted);
    font-size: var(--step--1);
    max-width: var(--measure);
  }
  .ok {
    color: var(--thread-strong);
    font-weight: 700;
  }
  .err {
    color: var(--danger);
  }
  .rowerrs {
    border: 1px solid var(--danger);
    border-radius: var(--radius);
    padding: 0.75rem 1rem;
    margin-top: 1rem;
    max-width: 40rem;
  }
  .rowerrs ul {
    margin: 0.4rem 0 0;
    padding-left: 1.1rem;
    font-size: var(--step--1);
  }
  table {
    width: 100%;
    border-collapse: collapse;
    max-width: 44rem;
  }
  th {
    text-align: left;
    font-size: var(--step--1);
    letter-spacing: 0.05em;
    text-transform: uppercase;
    color: var(--ink-muted);
    border-bottom: 2px solid var(--rule);
    padding: 0.45rem 0.55rem;
  }
  td {
    padding: 0.5rem 0.55rem;
    border-bottom: 1px solid var(--rule);
  }
  .code {
    font-weight: 700;
    letter-spacing: 0.04em;
    color: var(--seal);
  }
  .muted {
    color: var(--ink-muted);
  }
  .ei {
    width: 100%;
    padding: 0.35em 0.5em;
    background: var(--paper);
    border: 1px solid var(--rule);
    border-radius: var(--radius);
    color: var(--ink);
    font: inherit;
  }
  .acts {
    white-space: nowrap;
  }
  .lnk {
    background: none;
    border: 0;
    color: var(--thread);
    cursor: pointer;
    font-size: var(--step--1);
    padding: 0 0.3rem;
  }
  .lnk:hover {
    color: var(--thread-strong);
  }
  .lnk.danger {
    color: var(--seal);
  }
  .lnk[disabled] {
    opacity: 0.5;
    cursor: default;
  }
  @media (max-width: 560px) {
    .grid {
      grid-template-columns: 1fr;
    }
  }
</style>
