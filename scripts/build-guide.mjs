import { readFile, writeFile, readdir } from "node:fs/promises";
import { marked } from "marked";
for (const file of (await readdir("docs")).filter((name) =>
  name.endsWith(".md"),
)) {
  const markdown = (await readFile(`docs/${file}`, "utf8")).replace(
    /^\uFEFF/,
    "",
  );
  const title = markdown
    .split("\n")[0]
    .replace(/^#+\s*/, "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;");
  const content = marked
    .parse(markdown)
    .replace(/href="([a-z-]+)\.md(#[^"]*)?"/g, 'href="$1.html$2"')
    .replaceAll('src="../public/', 'src="/')
    .replaceAll('href="../public/', 'href="/')
    .replaceAll("<pre>", '<pre tabindex="0">')
    .replaceAll("<table>", '<div class="table-scroll" tabindex="0"><table>')
    .replaceAll("</table>", "</table></div>");
  await writeFile(
    `public/${file.replace(".md", ".html")}`,
    `<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><meta name="theme-color" content="#0e1014"><title>${title} · Plunk</title><link rel="icon" href="/brand/icon.svg"><link rel="stylesheet" href="/setup.css"></head>
<body><nav><a class="logo" href="/">plunk<span>.</span></a><a href="/app">Open the app ↗</a></nav><main>${content}</main></body></html>\n`,
  );
}
console.log("Built hosted guides from docs/");
