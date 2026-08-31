<script>
  import { t } from '$lib/i18n';
  /** @type {{ label?: string, block?: boolean }} */
  let { label, block = false } = $props();
</script>

<div class="wait" class:block role="status" aria-live="polite">
  <span class="mark" aria-hidden="true"></span>
  <span>{label ?? $t('common.loading')}</span>
</div>

<style>
  .wait {
    display: inline-flex;
    align-items: center;
    gap: 0.6em;
    color: var(--ink-muted);
    font-size: var(--step--1);
    letter-spacing: 0.04em;
  }
  .block {
    display: flex;
    justify-content: center;
    padding: 3rem 1rem;
  }
  .mark {
    width: 0.9em;
    height: 0.9em;
    border: 2px solid var(--rule);
    border-top-color: var(--thread);
    border-radius: 50%;
    animation: spin 0.8s linear infinite;
  }
  @keyframes spin {
    to {
      transform: rotate(360deg);
    }
  }
  @media (prefers-reduced-motion: reduce) {
    .mark {
      animation: none;
      border-top-color: var(--rule);
      border-right-color: var(--thread);
    }
  }
</style>
