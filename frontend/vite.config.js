import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import fs from "fs";

/**
 * Two-part fix for import.meta.glob("*.md", { as: "raw" }) in Vite 8 / Rolldown:
 *
 * PART 1 — rawMarkdownPlugin:
 *   Transform every .md (and .md?raw) file into `export default "content"`.
 *   Prevents Rolldown from trying to parse YAML frontmatter as JavaScript.
 *
 * PART 2 — fixBlogUtilsPlugin:
 *   Vite 8 / Rolldown wraps every eager glob result in a module namespace
 *   object { default: "string" }. The `{ as: "raw" }` flag is supposed to
 *   unwrap .default automatically but Rolldown does not do this correctly.
 *
 *   Fix: At build time, insert a one-line guard at the start of parseFrontmatter
 *   that unwraps the module namespace object if one is received:
 *     if (raw && typeof raw === "object" && "default" in raw) raw = raw.default;
 *   This keeps the original blogUtils.js source intact while ensuring the
 *   production bundle handles both plain strings and namespace objects.
 */

function rawMarkdownPlugin() {
  return {
    name: "raw-markdown",
    enforce: "pre",
    load(id) {
      const cleanId = id.split("?")[0];
      if (cleanId.endsWith(".md")) {
        try {
          const content = fs.readFileSync(cleanId, "utf8");
          return {
            code: `export default ${JSON.stringify(content)}`,
            map: null,
          };
        } catch {
          return null;
        }
      }
    },
  };
}

function fixBlogUtilsPlugin() {
  // The line in parseFrontmatter immediately after the opening brace
  const TARGET = "function parseFrontmatter(raw) {";
  const GUARD =
    '\n  // Unwrap Rolldown module namespace objects ({ default: string })\n' +
    '  if (raw && typeof raw === "object" && "default" in raw) raw = raw.default;';

  return {
    name: "fix-blog-utils",
    enforce: "pre",
    transform(code, id) {
      if (id.endsWith("blogUtils.js") && code.includes(TARGET) && !code.includes("Unwrap Rolldown")) {
        return {
          code: code.replace(TARGET, TARGET + GUARD),
          map: null,
        };
      }
    },
  };
}

export default defineConfig({
  plugins: [react(), rawMarkdownPlugin(), fixBlogUtilsPlugin()],

  test: {
    globals: true,
    environment: "jsdom",
    setupFiles: "./src/tests/setup.js",
    exclude: [
      "node_modules/**",
      "dist/**",
      "e2e/**",
    ],
    // Provide stub env vars so Supabase/API clients initialise without throwing in CI
    env: {
      VITE_SUPABASE_URL:     "https://test-project.supabase.co",
      VITE_SUPABASE_ANON_KEY: "test-anon-key",
      VITE_API_BASE_URL:      "http://localhost:8000",
    },
  },
});
