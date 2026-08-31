<script>
  import { onMount } from 'svelte';
  import { api } from '$lib/api.js';
  import { t } from '$lib/i18n';
  import { session } from '$lib/stores.js';
  import Spinner from '$lib/components/Spinner.svelte';

  let loading = $state(true);
  let error = $state('');
  let saving = $state('');
  let permissions = $state([]);
  /** @type {Record<string, Record<string, boolean>>} */
  let matrix = $state({ dept_default: {}, branch_default: {} });

  const PROFILES = [
    { name: 'dept_default', key: 'admin.deptDefault' },
    { name: 'branch_default', key: 'admin.branchDefault' }
  ];

  onMount(async () => {
    if (!$session?.is_super_admin) {
      error = 'forbidden';
      loading = false;
      return;
    }
    try {
      const [perms, dept, branch] = await Promise.all([
        api('/permissions'),
        api('/permission-profiles/dept_default'),
        api('/permission-profiles/branch_default')
      ]);
      permissions = perms;
      matrix = { dept_default: dept, branch_default: branch };
    } catch (e) {
      error = e.detail ?? 'error';
    } finally {
      loading = false;
    }
  });

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

<svelte:head><title>{$t('admin.heading')} · Nobojatra</title></svelte:head>

<h1>{$t('admin.heading')}</h1>

{#if loading}
  <Spinner block />
{:else if error === 'forbidden'}
  <p class="err">403</p>
{:else if error}
  <p class="err" role="alert">{$t('common.error', { detail: error })}</p>
{:else}
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

  <section class="soon">
    <h2 class="label">{$t('admin.categories')} · {$t('admin.areas')}</h2>
    <p class="hint">Managed through the API today; a panel here is the next slice.</p>
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
  .soon {
    opacity: 0.75;
  }
  .err {
    color: var(--danger);
  }
</style>
