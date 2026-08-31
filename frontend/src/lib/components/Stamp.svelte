<script>
  import { unitLabel } from '$lib/format.js';
  /**
   * The issuing stamp — attribution is always the org unit, never a person
   * (spec 6). Shown on every notice and message.
   * @type {{ unit?: { code?: string, name?: string, unit_type?: string } | null,
   *   unitId?: string, date?: string }}
   */
  let { unit = null, unitId, date } = $props();
</script>

<span class="stamp" title={unit?.name ?? unitId}>
  <b>{unit ? unitLabel(unit) : (unitId ?? '—').slice(0, 8)}</b>
  {#if unit?.unit_type}<span>{unit.unit_type}</span>{/if}
  {#if date}<span>{date}</span>{/if}
</span>
