import { cp, mkdir, rename } from 'node:fs/promises';

// Only generated files enter the directory exposed by FastAPI.
const output = new URL('../../app/static/', import.meta.url);
const dist = new URL('../dist/', import.meta.url);
await mkdir(output, { recursive: true });
await cp(new URL('assets/', dist), new URL('assets/', output), { recursive: true });
await cp(new URL('index.html', dist), new URL('index.html.next', output));
await rename(new URL('index.html.next', output), new URL('index.html', output));
console.log('Frontend published to app/static (backend routes unchanged).');
