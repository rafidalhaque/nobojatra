<script>
  import { onMount } from 'svelte';
  import { api } from '$lib/api.js';
  import { t } from '$lib/i18n';
  import { session } from '$lib/stores.js';
  import { unitLabel } from '$lib/format.js';
  import Spinner from '$lib/components/Spinner.svelte';

  let loading = $state(true);
  let error = $state('');
  let units = $state([]);
  let areas = $state(new Map());

  onMount(async () => {
    try {
      const [us, as_] = await Promise.all([api('/org-units'), api('/areas')]);
      units = us;
      areas = new Map(as_.map((a) => [a.id, a.name]));
    } catch (e) {
      error = e.detail ?? 'error';
    } finally {
      loading = false;
    }
  });

  const branches = $derived(units.filter((u) => u.unit_type === 'branch'));
  const depts = $derived(units.filter((u) => u.unit_type === 'dept'));
</script>

<svelte:head><title>{$t('directory.heading')} · Nobojatra</title></svelte:head>

<div class="head">
  <h1>{$t('directory.heading')}</h1>
  {#if $session?.is_super_admin}
    <a class="btn btn--ghost" href="/admin/org-units">{$t('admin.nav.orgUnits')}</a>
  {/if}
</div>

{#if loading}
  <Spinner block />
{:else if error}
  <p class="err" role="alert">{$t('common.error', { detail: error })}</p>
{:else}
  {#each [['directory.depts', depts], ['directory.branches', branches]] as [key, list] (key)}
    <section>
      <h2 class="label">{$t(key)}</h2>
      <table>
        <thead>
          <tr><th>{$t('directory.code')}</th><th>Name</th><th>{$t('directory.area')}</th></tr>
        </thead>
        <tbody>
          {#each list as u (u.id)}
            <tr>
              <td class="code">{u.code}</td>
              <td>{u.name}</td>
              <td>{areas.get(u.area_id) ?? '—'}</td>
            </tr>
          {:else}
            <tr><td colspan="3" class="muted">{$t('common.none')}</td></tr>
          {/each}
        </tbody>
      </table>
    </section>
  {/each}
{/if}

<style>
  .head {
    display: flex;
    align-items: baseline;
    justify-content: space-between;
    gap: 1rem;
    margin-bottom: 1rem;
  }
  .head h1 {
    margin: 0;
  }
  section {
    margin-bottom: 2.5rem;
  }
  table {
    width: 100%;
    border-collapse: collapse;
    font-size: 0.95rem;
  }
  th {
    text-align: left;
    font-size: var(--step--1);
    letter-spacing: 0.06em;
    text-transform: uppercase;
    color: var(--ink-muted);
    border-bottom: 2px solid var(--rule);
    padding: 0.5rem 0.6rem;
  }
  td {
    padding: 0.55rem 0.6rem;
    border-bottom: 1px solid var(--rule);
  }
  .code {
    font-weight: 700;
    letter-spacing: 0.05em;
    color: var(--seal);
  }
  .muted {
    color: var(--ink-muted);
  }
  .err {
    color: var(--danger);
  }
</style>
