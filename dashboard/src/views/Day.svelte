<script>
  import EventRow from '../components/EventRow.svelte';
  import { clock, calendarEvents, calendarCovers } from '../lib/state.svelte.js';
  import { addDays, eventsOn } from '../lib/format.js';
  let { offset = 0 } = $props();
  let day = $derived(addDays(clock.now,offset));
  let events = $derived(eventsOn(calendarEvents(),day));
</script>
<section class="sheet day">
  <h2>{day.toLocaleDateString([], { weekday:'long',month:'long',day:'numeric' })}</h2>
  {#if !calendarCovers(day)}<p>Calendar data is unavailable for this date.</p>{/if}
  <div class="events">
    {#each events as e (e.uid+e.start)}<EventRow event={e} now={clock.now} />
    {:else}{#if calendarCovers(day)}<p>No events</p>{/if}{/each}
  </div>
</section>
<style>
  .day { flex:1; min-height:0; display:flex; flex-direction:column; padding:20px 24px; }
  h2 { margin:0 0 12px; font-size:24px; }
  .events { min-height:0; overflow-y:auto; }
  p { font-size:19px; color:var(--secondary); }
</style>
