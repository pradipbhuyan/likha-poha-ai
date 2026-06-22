import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

/**
 * Raw markdown loader — allows import.meta.glob("*.md", { as: "raw" })
 * to work with Vite 8 / Rolldown. Without this plugin, Rolldown tries
 * to parse .md files as JavaScript and fails on YAML frontmatter.
 */
function rawMarkdownPlugin() {
  return {
    name: "raw-markdown",
    // Transform .md files into JS modules that export the raw string.
    // This satisfies both direct ?raw imports and glob { as: "raw" } calls.
    transform(code, id) {
      if (id.endsWith(".md")) {
        return {
          code: `export default ${JSON.stringify(code)}`,
          map: null,
        };
      }
    },
  };
}

export default defineConfig({
  plugins: [react(), rawMarkdownPlugin()],

  test: {
    globals: true,
    environment: "jsdom",
    setupFiles: "./src/tests/setup.js",
    exclude: [
      "node_modules/**",
      "dist/**",
      "e2e/**",
    ],
  },
});
