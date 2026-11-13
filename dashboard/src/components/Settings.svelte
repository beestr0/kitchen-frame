<script>
  import { onMount } from 'svelte';
  import Icon from './Icon.svelte';
  import { ui, calendar, photos, setSetting, announceTarget, refreshFeeds } from '../lib/state.svelte.js';
  import { ha, haConfigured } from '../lib/ha.svelte.js';
  // Speaker offered for reading agent messages aloud: the chosen one, else the fallback (first speaker).
  let announceSpeaker = $derived(ha.players.find((p) => p.entity_id === ui.announceOn) || announceTarget() || ha.players[0]);
  import { api } from '../lib/api.js';
  import { time } from '../lib/format.js';

  const THEMES = [['auto', 'Automatic'], ['light', 'Light'], ['dark', 'Dark']];
  const IDLE = [[2, '2 min'], [5, '5 min'], [15, '15 min'], [0, 'Never']];
  // Slideshow clock colours: white plus the iOS system colours that read well over photos.
  const CLOCK = [['#ffffff', 'White'], ['#ffd60a', 'Yellow'], ['#ff9f0a', 'Orange'], ['#ff375f', 'Pink'], ['#bf5af2', 'Purple'], ['#64d2ff', 'Blue'], ['#30d158', 'Green']];
  const close = () => (ui.settingsOpen = false);
  let reloading = $state(false);
  let refreshing = $state(false);
  let dialog;
  onMount(() => { dialog.showModal(); return () => dialog.close(); });
  async function refresh() { refreshing = true; await refreshFeeds(); refreshing = false; }

  // Brightness goes through the kiosk app (window.FrameKiosk); not available in a normal browser.
  const kiosk = typeof window !== 'undefined' ? window.FrameKiosk : null;
  const saved = kiosk ? kiosk.getBrightness() : -1;
  let brightness = $state(saved < 0 ? 100 : Math.round(saved * 100));
  const setBrightness = () => kiosk && kiosk.setBrightness(brightness / 100);
  // Pull the calendar fresh from its feeds, then restart the page.
  async function reload() {
    reloading = true;
    try { await api('/api/calendar?refresh'); } catch {}
    location.reload();
  }
</script>

<!-- Tap outside the sheet to close; the sheet itself swallows the tap. -->
<dialog bind:this={dialog} class="panel sheet" aria-label="Settings" oncancel={close}>
    <header>
      <h2>Settings</h2>
      <button class="done" onclick={close}>Done</button>
    </header>

    <div class="row">
      <span>Appearance</span>
      <div class="seg">
        {#each THEMES as [v, label] (v)}
          <button class:on={ui.themePref === v} aria-pressed={ui.themePref === v} onclick={() => setSetting('themePref', v)}>{label}</button>
        {/each}
      </div>
    </div>
    <p class="hint">Automatic follows local sunrise and sunset from weather; uses 7 AM–7 PM until configured.</p>

    <div class="row">
      <span>Clock color<small>Clock screen text, day and night</small></span>
      <div class="swatches">
        {#each CLOCK as [c, name] (c)}
          <button class="swatch" class:on={ui.clockColor === c} style="--c:{c}" aria-label={name} onclick={() => setSetting('clockColor', c)}></button>
        {/each}
      </div>
    </div>

    <div class="row">
      <span>Clock screen after</span>
      <div class="seg">
        {#each IDLE as [v, label] (v)}
          <button class:on={ui.idleMinutes === v} onclick={() => setSetting('idleMinutes', v)}>{label}</button>
        {/each}
      </div>
    </div>

    <div class="row">
      <span>Photos at night</span>
      <div class="seg">
        <button class:on={ui.nightPhotos} onclick={() => setSetting('nightPhotos', true)}>Dimmed</button>
        <button class:on={!ui.nightPhotos} onclick={() => setSetting('nightPhotos', false)}>Off</button>
      </div>
    </div>

    {#if kiosk}
      <div class="row">
        <span>Brightness</span>
        <div class="bright">
          <Icon name="sun" size={18} />
          <input type="range" min="5" max="100" step="5" bind:value={brightness} oninput={setBrightness} aria-label="Brightness" style="--pct:{((brightness - 5) / 95) * 100}%" />
          <Icon name="sun" size={26} />
        </div>
      </div>
    {/if}

    {#if haConfigured() && announceSpeaker}
      <div class="row">
        <span>Read messages aloud<small>Through Home Assistant, not 10 PM–7 AM</small></span>
        <div class="seg">
          <button class:on={ui.announceOn === announceSpeaker.entity_id} onclick={() => setSetting('announceOn', announceSpeaker.entity_id)}>{announceSpeaker.label}</button>
          <button class:on={ui.announceOn === 'off'} onclick={() => setSetting('announceOn', 'off')}>Off</button>
        </div>
      </div>
    {/if}

    <div class="row">
      <span>Demo mode<small>Sample calendar, lists and no photos, for showing people</small></span>
      <div class="seg">
        <button class:on={ui.demo} onclick={() => setSetting('demo', true)}>On</button>
        <button class:on={!ui.demo} onclick={() => setSetting('demo', false)}>Off</button>
      </div>
    </div>

    <div class="row">
      <label for="refresh-interval">Calendar and task refresh<small>Weather refreshes every 15 minutes</small></label>
      <select id="refresh-interval" value={ui.refreshMinutes} onchange={(e) => setSetting('refreshMinutes', Number(e.currentTarget.value))}>
        <option value={1}>Every minute</option><option value={5}>Every 5 minutes</option><option value={15}>Every 15 minutes</option>
      </select>
    </div>
    <div class="row">
      <span>Refresh data<small>Retains saved data if offline</small></span>
      <button class="reload" disabled={refreshing} onclick={refresh}>{refreshing ? 'Refreshing…' : 'Refresh now'}</button>
    </div>
    <div class="row last">
      <span>{ui.demo ? 'Showing demo data' : (calendar.data ? 'Calendar updated ' + time(new Date(calendar.data.updated)) : 'Calendar not loaded') + ' · ' + photos.items.length + ' photos'}</span>
      <button class="reload" disabled={reloading} onclick={reload}><Icon name="reload" size={20} />{reloading ? 'Reloading…' : 'Reload'}</button>
    </div>
</dialog>

<style>
  dialog::backdrop { background: rgba(0, 0, 0, .45); }
  .panel { width: 740px; max-width: calc(100vw - 48px); max-height: calc(100vh - 48px); margin: auto; padding: 22px 28px 10px; border: 0; color: var(--label); overflow-y: auto; }
  select { font: inherit; color: var(--label); background: var(--track); border: 0; border-radius: 11px; min-height: 48px; padding: 0 12px; }
  header { display: flex; align-items: center; justify-content: space-between; margin-bottom: 6px; }
  h2 { margin: 0; font-size: 26px; font-weight: 700; letter-spacing: -.01em; }
  .done { font-size: 20px; font-weight: 600; color: var(--blue-text); padding: 8px 0 8px 16px; }
  .row { display: flex; align-items: center; justify-content: space-between; gap: 20px; min-height: 64px; padding: 8px 0; border-top: 1px solid var(--sep); font-size: 20px; }
  .row.last { color: var(--secondary); font-size: 17px; }
  .hint { margin: -6px 0 8px; font-size: 15px; color: var(--secondary); }
  .seg { display: flex; padding: 3px; border-radius: 11px; background: var(--track); }
  .seg button { min-width: 84px; height: 48px; padding: 0 14px; border-radius: 9px; font-size: 17px; font-weight: 500; text-align: center; }
  .seg button.on { background: var(--thumb); font-weight: 600; }
  .seg button:not(.on):active { opacity: .5; }
  .row small { display: block; font-size: 15px; color: var(--secondary); margin-top: 2px; }
  .swatches { display: flex; gap: 6px; }
  .swatch { width: 48px; height: 48px; border-radius: 50%; background: var(--c); border: 1px solid var(--sep); }
  /* Selected: a ring just outside the swatch. */
  .swatch.on { outline: 2px solid var(--label); outline-offset: 3px; }
  .swatch:active { opacity: .7; }
  .bright { display: flex; align-items: center; gap: 12px; color: var(--secondary); }
  /* Native range input, restyled flat: grey track, white round thumb. */
  input[type='range'] { -webkit-appearance: none; appearance: none; width: 300px; height: 6px; border-radius: 3px; outline: none;
    background: linear-gradient(90deg, var(--blue) var(--pct), var(--tertiary) var(--pct)); }
  input[type='range']::-webkit-slider-thumb { -webkit-appearance: none; width: 30px; height: 30px; border-radius: 50%; background: #fff; border: 1px solid var(--sep); }
  .reload { display: flex; align-items: center; gap: 8px; height: 44px; padding: 0 16px; border-radius: 11px; background: var(--track); color: var(--label); font-size: 17px; font-weight: 600; }
  .reload:active, .reload:disabled { opacity: .6; }
</style>
