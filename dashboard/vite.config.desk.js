import { defineConfig } from 'vite';
import { svelte } from '@sveltejs/vite-plugin-svelte';
import { cloudflare } from '@cloudflare/vite-plugin';

// Separate output keeps the working USB dashboard's dist/client assets intact.
export default defineConfig({
  plugins: [svelte(), cloudflare({ configPath: './wrangler.desk.jsonc' })],
  build: { outDir: 'dist-desk', target: 'chrome106', cssTarget: 'chrome61' },
  server: { host: '127.0.0.1' },
});
