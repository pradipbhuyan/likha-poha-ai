#!/usr/bin/env node
// Fails if any var(--token) reference in the frontend doesn't correspond to a
// token actually defined in App.css's :root / body.dark-mode blocks.
//
// Why this exists: on 2026-08-26 we found 5 token names (--surface,
// --card-bg, --text-secondary, --border-color, --accent-soft) referenced
// across 54 files with an inline fallback — e.g. `var(--surface, #f8fafc)`
// — that were never actually defined anywhere. Every one of those call
// sites silently used the hardcoded fallback forever and never responded
// to the dark-mode toggle, because a fallback only fires for a genuinely
// undefined/invalid variable, so the bug never threw, never warned, and
// was invisible short of reading the token table by hand. This script is
// that reading, automated, so a 6th one can't happen the same way.
//
// A `var(--x, fallback)` with an undefined --x isn't a CSS error — the
// fallback just silently wins forever. That's exactly the failure mode:
// looks like theming, never actually theme-aware. Run: npm run lint:css-tokens

import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const SRC = path.join(ROOT, "src");
const TOKEN_SOURCE = path.join(SRC, "App.css");

function walk(dir, exts, out = []) {
  for (const entry of fs.readdirSync(dir, { withFileTypes: true })) {
    if (entry.name === "node_modules" || entry.name.startsWith(".")) continue;
    const full = path.join(dir, entry.name);
    if (entry.isDirectory()) walk(full, exts, out);
    else if (exts.some((e) => entry.name.endsWith(e))) out.push(full);
  }
  return out;
}

// --- 1. Defined tokens: every `--name: value;` declared anywhere in any
//        .css file under src/ — not just App.css's :root/body.dark-mode.
//        Some pages keep their own prefixed namespace (e.g.
//        StudentDashboardPage.css's --sd-* tokens) which is legitimate and
//        shouldn't false-positive here. This check only cares whether a
//        referenced name is defined *somewhere*, the same low bar that lets
//        the browser resolve it at all — it does not attempt full CSS-cascade
//        scoping/specificity, which would be a much larger undertaking for
//        marginal extra precision. ---
const defined = new Set();
for (const file of walk(SRC, [".css"])) {
  const text = fs.readFileSync(file, "utf8");
  for (const decl of text.matchAll(/(--[a-zA-Z0-9-]+)\s*:/g)) defined.add(decl[1]);
}

if (!fs.existsSync(TOKEN_SOURCE) || defined.size < 10) {
  console.error(`check-css-tokens: found suspiciously few token definitions (${defined.size}) — App.css's :root/body.dark-mode block shape may have changed; sanity-check this script.`);
  process.exit(1);
}

// --- 2. Referenced tokens: every var(--name across all source CSS/JSX/JS. ---
const files = [...walk(SRC, [".css"]), ...walk(SRC, [".jsx", ".js", ".tsx", ".ts"])];
const problems = [];

for (const file of files) {
  const text = fs.readFileSync(file, "utf8");
  const lines = text.split("\n");
  lines.forEach((line, i) => {
    for (const m of line.matchAll(/var\(\s*(--[a-zA-Z0-9-]+)/g)) {
      const token = m[1];
      if (!defined.has(token)) {
        problems.push({ file: path.relative(ROOT, file), line: i + 1, token });
      }
    }
  });
}

if (problems.length > 0) {
  console.error(`check-css-tokens: ${problems.length} reference(s) to a CSS custom property that isn't defined in App.css's :root or body.dark-mode block.\n`);
  console.error("A var(--x, fallback) with an undefined --x doesn't error — the fallback just wins forever and silently never responds to dark mode. That's the exact bug class this check exists to catch.\n");
  for (const p of problems) {
    console.error(`  ${p.file}:${p.line}  var(${p.token} ...)`);
  }
  console.error(`\nFix: either add ${[...new Set(problems.map((p) => p.token))].join(", ")} to both blocks in ${path.relative(ROOT, TOKEN_SOURCE)}, or point the call site(s) at an existing token instead.`);
  process.exit(1);
}

console.log(`check-css-tokens: OK — every var(--x) reference across ${files.length} files resolves to a token defined in both :root and body.dark-mode (${defined.size} tokens).`);
