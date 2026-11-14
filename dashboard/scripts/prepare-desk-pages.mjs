import { cp, mkdir, readFile, writeFile } from 'node:fs/promises';
import { fileURLToPath, pathToFileURL } from 'node:url';
import { tmpdir } from 'node:os';
import { join, resolve } from 'node:path';

const root = new URL('../', import.meta.url);
const source = new URL('dist-desk/client/', root);
const output = new URL('dist-desk-pages/', root);
await readFile(new URL('index.html', source)); // require a completed desk build
await mkdir(output, { recursive: true });
await cp(source, output, { recursive: true });
await cp(new URL('hosting/pages-relay.js', root), new URL('_worker.js', output));
await writeFile(new URL('_routes.json', output), JSON.stringify({
  version: 1, include: ['/api/*'], exclude: [],
}, null, 2) + '\n');
const headers = await readFile(new URL('_headers', source), 'utf8').catch(() => '');
await writeFile(new URL('_headers', output), headers + `
/*
  Referrer-Policy: no-referrer
  X-Content-Type-Options: nosniff
/
  Cache-Control: no-store
/index.html
  Cache-Control: no-store
`);
console.log('Prepared local-only Pages artifact: ' + fileURLToPath(output));

// Pages discovers wrangler.jsonc in its working directory. Stage the named Pages
// config separately so the original dashboard's wrangler.jsonc is never selected.
// Use a temporary directory outside the Vite project's ancestor tree: otherwise
// Wrangler discovers Vite's .wrangler/deploy redirect and rejects the Pages config.
const staging = pathToFileURL(resolve(process.env.PAGES_DEPLOY_DIR || join(tmpdir(), 'pf1007l-pages-deploy')) + '/');
await mkdir(staging, { recursive: true });
const config = await readFile(new URL('wrangler.desk-pages.jsonc', root), 'utf8');
await writeFile(new URL('wrangler.jsonc', staging), config.replace(
  '"./dist-desk-pages"', JSON.stringify(fileURLToPath(output)),
));
console.log('Prepared isolated Pages CLI config: ' + fileURLToPath(staging));
