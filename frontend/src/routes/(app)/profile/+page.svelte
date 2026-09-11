<script>
  import { onMount } from 'svelte';
  import { api, ApiError } from '$lib/api.js';
  import { session } from '$lib/stores.js';
  import { t, lang } from '$lib/i18n';

  let loading = $state(true);
  let unit = $state(null);
  let areaName = $state('');

  let currentPassword = $state('');
  let newPassword = $state('');
  let confirmPassword = $state('');
  let pwSubmitting = $state(false);
  let pwError = $state('');
  let pwSuccess = $state(false);

  onMount(async () => {
    if ($session?.org_unit_id) {
      try {
        unit = await api('/me/profile');
        const areas = await api('/areas').catch(() => []);
        areaName = areas.find((a) => a.id === unit.area_id)?.name ?? '';
      } catch {
        /* nothing to show */
      }
    }
    loading = false;
  });

  async function changePassword(e) {
    e.preventDefault();
    if (pwSubmitting) return;
    pwError = '';
    pwSuccess = false;
    if (newPassword !== confirmPassword) {
      pwError = $t('password.mismatch');
      return;
    }
    pwSubmitting = true;
    try {
      await api('/me/password', {
        method: 'PATCH',
        body: { current_password: currentPassword, new_password: newPassword }
      });
      pwSuccess = true;
      currentPassword = '';
      newPassword = '';
      confirmPassword = '';
    } catch (err) {
      pwError =
        err instanceof ApiError && err.status === 401
          ? $t('password.incorrect')
          : err instanceof ApiError && err.status === 422
            ? $t('password.tooShort')
            : $t('common.error', { detail: '' });
    } finally {
      pwSubmitting = false;
    }
  }
</script>

<svelte:head><title>{$t('profile.myProfile')} · Nobojatra</title></svelte:head>

<h1>{$t('profile.myProfile')}</h1>

{#if !loading && unit}
  <section class="paper-card info">
    <h2 lang={$lang}>{unit.name}</h2>
    <p class="sub">
      <span class="label">{$t('profile.code')}</span> {unit.code}
      <span class="sep">·</span>
      <span class="label">{$t('profile.area')}</span> {areaName || '—'}
    </p>
  </section>
{/if}

<section class="paper-card pw">
  <h2>{$t('password.change')}</h2>
  <form onsubmit={changePassword} novalidate>
    <div class="field">
      <label for="cur">{$t('password.current')}</label>
      <input id="cur" type="password" autocomplete="current-password" bind:value={currentPassword} required />
    </div>
    <div class="field">
      <label for="new">{$t('password.new')}</label>
      <input id="new" type="password" autocomplete="new-password" minlength="8" bind:value={newPassword} required />
    </div>
    <div class="field">
      <label for="conf">{$t('password.confirm')}</label>
      <input id="conf" type="password" autocomplete="new-password" minlength="8" bind:value={confirmPassword} required />
    </div>

    {#if pwError}<p class="err" role="alert">{pwError}</p>{/if}
    {#if pwSuccess}<p class="ok" role="status">{$t('password.success')}</p>{/if}

    <button class="btn" type="submit" disabled={pwSubmitting}>
      {pwSubmitting ? $t('common.saving') : $t('password.change')}
    </button>
  </form>
</section>

<style>
  h1 {
    margin: 0 0 1.25rem;
  }
  .info,
  .pw {
    padding: 1.25rem 1.5rem;
    margin-bottom: 1.5rem;
    max-width: 28rem;
  }
  .info h2,
  .pw h2 {
    margin: 0 0 0.5rem;
    font-size: var(--step-1);
  }
  .sub {
    margin: 0;
    color: var(--ink-muted);
    font-size: var(--step--1);
  }
  .sep {
    margin: 0 0.4em;
  }
  form {
    margin-top: 0.75rem;
  }
  .field {
    margin-bottom: 0.9rem;
  }
  label {
    display: block;
    font-size: var(--step--1);
    font-weight: 700;
    letter-spacing: 0.04em;
    margin-bottom: 0.3rem;
  }
  .err {
    color: var(--danger);
    font-size: var(--step--1);
  }
  .ok {
    color: var(--seal);
    font-size: var(--step--1);
  }
</style>
