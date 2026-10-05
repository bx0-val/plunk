import { readFile, writeFile } from 'node:fs/promises';
import { marked } from 'marked';
const markdown = await readFile('docs/setup.md', 'utf8');
const content = marked.parse(markdown)
  .replaceAll('<pre>', '<pre tabindex="0">')
  .replaceAll('<table>', '<div class="table-scroll" tabindex="0"><table>')
  .replaceAll('</table>', '</table></div>');
await writeFile('public/setup.html', `<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Set up Plunk with Tailscale</title><link rel="icon" href="/brand/icon.svg"><link rel="stylesheet" href="/setup.css"></head>
<body><nav><a class="logo" href="/">plunk<span>.</span></a><a href="/app">Open the app ↗</a></nav><main>${content}</main></body></html>\n`);
console.log('Built setup.html from docs/setup.md');
