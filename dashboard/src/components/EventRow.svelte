<script>
  import { calVars, timeRange, isPast, isNow, dayName } from '../lib/format.js';
  import { completeItem, reminders } from '../lib/state.svelte.js';
  let { event, now, showDay = false } = $props();
  let live = $derived(isNow(event, now));
</script>

<div class="ev" class:past={isPast(event, now)} style={calVars(event)}>
  {#if event.kind === 'reminder'}
    <button class="task-ring" disabled={!event.task.canComplete || reminders.stale} onclick={() => completeItem('todo', event.task)} aria-label={'Complete ' + event.title}>○</button>
  {:else}<span class="dot"></span>{/if}
  <div class="body">
    <div class="title">{event.title}</div>
    <div class="meta">
      {#if showDay}{dayName(event, now) + ' · '}{/if}{#if event.kind === 'reminder'}Due{event.allDay ? '' : ' ' + new Date(event.start).toLocaleTimeString([], {hour:'numeric',minute:'2-digit'})} · PF1007L Test{:else if event.allDay}All day{:else if live}<b>Now</b> · until {timeRange(event).split(' – ')[1]}{:else}{timeRange(event)}{/if}{event.location && !showDay ? ' · ' + event.location : ''}
    </div>
  </div>
</div>

<style>
  .task-ring { flex: none; min-width: 38px; min-height: 44px; color: var(--cal1); font-size: 32px; }
  .task-ring:disabled { opacity: .4; }
  .ev { display: flex; gap: 14px; padding: 10px 0; }
  .past .title { color: var(--secondary); }
  .dot { flex: none; width: 10px; height: 10px; border-radius: 50%; background: var(--c); margin-top: 9px; }
  .body { min-width: 0; }
  .title { font-size: 22px; font-weight: 600; letter-spacing: -.01em; overflow-wrap: anywhere; }
  .meta { font-size: 17px; color: var(--secondary); margin-top: 3px; overflow-wrap: anywhere; }
  .meta b { color: var(--label); font-weight: 700; }
</style>
