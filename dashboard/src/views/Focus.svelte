<script>
  import { focus, toggleFocus, resetFocus, setDuration } from '../lib/focus.svelte.js';
  import { remaining } from '../lib/focus.js';
  let now = $state(Date.now());
  let left = $derived(remaining(focus.session, now));
  let seconds = $derived(Math.ceil(left / 1000));
  let done = $derived(left === 0);
  let display = $derived(String(Math.floor(seconds / 60)).padStart(2, '0') + ':' + String(seconds % 60).padStart(2, '0'));
  // Only the active Focus view ticks. Hidden tabs use no per-second rendering.
  $effect(() => {
    if (!focus.session.running) return;
    const id = setInterval(() => { now = Date.now(); }, 1000);
    return () => clearInterval(id);
  });
  const tick = () => { now = Date.now(); };
</script>

<div class="wrap">
  <section class="sheet timer">
    <div class="seg" role="group" aria-label="Timer mode">
      <button aria-pressed={focus.session.phase === 'focus'} class:on={focus.session.phase === 'focus'} onclick={() => { resetFocus('focus'); tick(); }}>Focus</button>
      <button aria-pressed={focus.session.phase === 'break'} class:on={focus.session.phase === 'break'} onclick={() => { resetFocus('break'); tick(); }}>Break</button>
    </div>
    <h1>{focus.session.phase === 'focus' ? 'Time to focus' : 'Take a breath'}</h1>
    <div class="num countdown" role="timer" aria-label="Time remaining">{display}</div>
    <p role="status">{done ? (focus.session.phase === 'focus' ? 'Session complete. Ready for a break?' : 'Break complete. Ready to focus?') : focus.session.running ? 'One thing at a time.' : 'Ready when you are.'}</p>
    <div class="actions">
      {#if done}
        <button class="primary" onclick={() => { resetFocus(focus.session.phase === 'focus' ? 'break' : 'focus'); tick(); }}>Next session</button>
      {:else}
        <button class="primary" onclick={() => { toggleFocus(); tick(); }}>{focus.session.running ? 'Pause' : 'Start'}</button>
      {/if}
      <button onclick={() => { resetFocus(); tick(); }}>Reset</button>
    </div>
  </section>
  <section class="sheet options">
    <h2>Your rhythm</h2>
    <p>Choose a focus session and a short break. Each session starts when you’re ready.</p>
    {#each [['focus', 'Focus minutes'], ['break', 'Break minutes']] as [phase, label]}
      <label>{label}<input type="number" min="1" max="120" step="1" value={focus.durations[phase]} disabled={focus.session.running} onchange={(e) => { setDuration(phase, e.currentTarget.value); e.currentTarget.value = String(focus.durations[phase]); tick(); }} /></label>
    {/each}
    <p class="hint">The timer keeps its place when you switch views or reload. The clock screen stays off while your timer is running.</p>
  </section>
</div>

<style>
  .wrap { height: 100%; padding: 10px 28px 28px; display: grid; grid-template-columns: 2fr 1fr; gap: 20px; }
  .timer { display: flex; flex-direction: column; align-items: center; justify-content: center; }
  h1 { font-size: 28px; margin: 28px 0 0; font-weight: 600; }
  .countdown { font-size: 132px; font-weight: 500; letter-spacing: -.04em; line-height: 1.2; }
  p { color: var(--secondary); font-size: 20px; }
  .actions, .seg { display: flex; gap: 12px; }
  button { padding: 0 28px; border-radius: 14px; background: var(--track); font-size: 20px; font-weight: 600; }
  button:active { opacity: .6; }
  .primary { background: var(--blue); color: #fff; min-width: 160px; text-align: center; }
  .seg { gap: 0; border-radius: 15px; padding: 3px; background: var(--track); }
  .seg button.on { background: var(--thumb); }
  h2 { font-size: 26px; margin: 0; }
  .options { align-self: center; }
  label { display: flex; align-items: center; justify-content: space-between; gap: 12px; font-size: 20px; margin: 24px 0; }
  input { width: 90px; min-height: 48px; border: 1px solid var(--sep); border-radius: 10px; background: var(--ground); color: var(--label); font: inherit; text-align: center; }
  .hint { font-size: 17px; }
</style>
