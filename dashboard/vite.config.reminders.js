import { defineConfig } from 'vite';
import { svelte } from '@sveltejs/vite-plugin-svelte';
// Linux-local, demo-only build. No cloud deployment or provider credentials.
export default defineConfig({
  plugins: [svelte()], base: '/__reminders-demo/',
  define: { 'import.meta.env.VITE_REMINDERS_PILOT': 'true' },
  build: { outDir: 'dist-reminders-demo', target: 'chrome106', cssTarget: 'chrome61' },
});
