<script>
  import { privateCalendar, calendarNotice } from '../lib/state.svelte.js';
  let notice = $derived(calendarNotice());
</script>
{#if privateCalendar.enabled}
  <div class="status" role="status">
    {#if notice}<span>{notice}</span>{/if}
    <div class="legend">
      {#each privateCalendar.calendars || [] as c (c.id)}
        <span><i style={'background:'+c.color}></i>{c.name}{c.stale ? ' · outdated' : ''}</span>
      {/each}
    </div>
  </div>
{/if}
<style>
  .status { flex:none; font-size:14px; color:var(--secondary); margin:4px 0 8px; }
  .legend { display:flex; gap:12px; flex-wrap:wrap; }
  .legend span { display:inline-flex; align-items:center; gap:5px; }
  i { display:inline-block; width:9px; height:9px; border-radius:50%; }
</style>
