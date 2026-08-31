<script>
  import { onMount } from 'svelte';
  import { api } from '$lib/api.js';
  import { t } from '$lib/i18n';
  import { unitLabel } from '$lib/format.js';
  import Spinner from '$lib/components/Spinner.svelte';

  let loading = $state(true);
  let error = $state('');
  let saving = $state('');
  let permissions = $state([]);
  /** @type {Record<string, Record<string, boolean>>} */
  let matrix = $state({ dept_default: {}, branch_default: {} });

  // per-unit overrides
  let units = $state([]);
  let ovUnit = $state('');
  let ovMatrix = $state(null); // { unit_type, effective, overrides }
  let ovLoading = $state(false);
  let ovSaving = $state('');

  const PROFILES = [
    { name: 'dept_default', key: 'admin.deptDefault' },
    { name: 'branch_default', key: 'admin.branchDefault' }
  ];

  onMount(async () => {
    try {
      const [perms, dept, branch, us] = await Promise.all([
        api('/permissions'),
        api('/permission-profiles/dept_default'),
        api('/permission-profiles/branch_default'),
        api('/org-units')
      ]);
      permissions = perms;
      matrix = { dept_default: dept, branch_default: branch };
      units = us;
    } catch (e) {
      error = e.detail ?? 'error';
    } finally {
      loading = false;
    }
  });

  async function loadOverrides() {
    ovMatrix = null;
    if (!ovUnit) return;
    ovLoading = true;
    try {
      ovMatrix = await api(`/org-units/${ovUnit}/permissions`);
      error = '';
    } catch (e) {
      error = e.detail ?? 'error';
    } finally {
      ovLoading = false;
    }
  }

  function ovState(key) {
    const o = ovMatrix?.overrides ?? {};
    return key in o ? (o[key] ? 'allow' : 'deny') : 'inherit';
  }

  async function setOverride(key, choice) {
    ovSaving = key;
    try {
      ovMatrix = await api(`/org-units/${ovUnit}/permissions`, {
        method: 'PUT',
        body: { permissions: { [key]: choice === 'inherit' ? null : choice === 'allow' } }
      });
      error = '';
    } catch (e) {
      error = e.detail ?? 'error';
    } finally {
      ovSaving = '';
    }
  }

  async function toggle(profile, key) {
    const next = { ...matrix[profile], [key]: !matrix[profile][key] };
    matrix = { ...matrix, [profile]: next };
    saving = profile + ':' + key;
    try {
      matrix[profile] = await api(`/permission-profiles/${profile}/permissions`, {
        method: 'PUT',
        body: { permissions: next }
      });
    } catch (e) {
      // revert on failure
      matrix = { ...matrix, [profile]: { ...matrix[profile], [key]: !next[key] } };
      error = e.detail ?? 'error';
    } finally {
      saving = '';
    }
  }
</script>

<svelte:head><title>{$t('admin.permissions')} · Nobojatra</title></svelte:head>

{#if loading}
  <Spinner block />
{:else}
  {#if error}
    <p class="err" role="alert">{$t('common.error', { detail: error })}</p>
  {/if}

  <section>
    <h2 class="label">{$t('admin.permissions')}</h2>
    <p class="hint">{$t('admin.permHint')}</p>

    <table>
      <thead>
        <tr>
          <th>Action</th>
          {#each PROFILES as p (p.name)}<th class="ct">{$t(p.key)}</th>{/each}
        </tr>
      </thead>
      <tbody>
        {#each permissions as perm (perm.key)}
          <tr>
            <td><code>{perm.key}</code><small>{perm.description}</small></td>
            {#each PROFILES as p (p.name)}
              <td class="ct">
                <label class="sw">
                  <input
                    type="checkbox"
                    checked={!!matrix[p.name][perm.key]}
                    disabled={saving === p.name + ':' + perm.key}
                    onchange={() => toggle(p.name, perm.key)}
                  />
                  <span class="visually-hidden">{perm.key} — {$t(p.key)}</span>
                </label>
              </td>
            {/each}
          </tr>
        {/each}
      </tbody>
    </table>
  </section>

  <section>
    <h2 class="label">{$t('admin.unitOverrides')}</h2>
    <p class="hint">{$t('admin.unitOverridesHint')}</p>

    <select class="unitsel" bind:value={ovUnit} onchange={loadOverrides}>
      <option value="">{$t('admin.pickUnit')}</option>
      {#each units as u (u.id)}<option value={u.id}>{unitLabel(u)}</option>{/each}
    </select>

    {#if ovLoading}
      <Spinner block />
    {:else if ovMatrix}
      <table>
        <thead>
          <tr><th>Action</th><th class="ct">Override</th><th class="ct">{$t('admin.effective')}</th></tr>
        </thead>
        <tbody>
          {#each permissions as perm (perm.key)}
            <tr>
              <td><code>{perm.key}</code><small>{perm.description}</small></td>
              <td class="ct">
                <select
                  value={ovState(perm.key)}
                  disabled={ovSaving === perm.key}
                  onchange={(e) => setOverride(perm.key, e.currentTarget.value)}
                >
                  <option value="inherit">{$t('admin.inherit')}</option>
                  <option value="allow">{$t('admin.allow')}</option>
                  <option value="deny">{$t('admin.deny')}</option>
                </select>
              </td>
              <td class="ct">{ovMatrix.effective[perm.key] ? '✓' : '—'}</td>
            </tr>
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
  .hint {
    color: var(--ink-muted);
    font-size: var(--step--1);
    max-width: var(--measure);
  }
  table {
    width: 100%;
    border-collapse: collapse;
    margin-top: 1rem;
  }
  th {
    text-align: left;
    font-size: var(--step--1);
    letter-spacing: 0.05em;
    text-transform: uppercase;
    color: var(--ink-muted);
    border-bottom: 2px solid var(--rule);
    padding: 0.5rem 0.6rem;
  }
  .ct {
    text-align: center;
    width: 9rem;
  }
  .unitsel {
    margin-top: 1rem;
    padding: 0.45em 0.6em;
    background: var(--paper);
    border: 1px solid var(--rule);
    border-radius: var(--radius);
    color: var(--ink);
    min-width: 16rem;
  }
  .ct select {
    padding: 0.3em 0.4em;
    background: var(--paper);
    border: 1px solid var(--rule);
    border-radius: var(--radius);
    color: var(--ink);
  }
  td {
    padding: 0.6rem;
    border-bottom: 1px solid var(--rule);
    vertical-align: top;
  }
  td code {
    font-family: var(--font-latin);
    font-weight: 700;
    letter-spacing: 0.03em;
    color: var(--seal);
  }
  td small {
    display: block;
    color: var(--ink-muted);
    font-size: var(--step--1);
  }
  .sw input {
    width: 1.15rem;
    height: 1.15rem;
    accent-color: var(--thread);
  }
  .err {
    color: var(--danger);
  }
</style>
