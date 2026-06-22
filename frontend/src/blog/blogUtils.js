/**
 * Blog post parser — reads all markdown files from /src/blog/posts/
 * Parses YAML frontmatter and markdown content.
 *
 * HOW TO ADD A NEW POST (no code needed):
 * 1. Create a new .md file in /frontend/src/blog/posts/
 * 2. Add frontmatter at the top (title, slug, date, author, summary, tags)
 * 3. Write the post content in Markdown below the --- separator
 * 4. Commit and push to GitHub — blog updates automatically
 *
 * FRONTMATTER FORMAT:
 * ---
 * title: "Your Post Title"
 * slug: "url-friendly-slug"
 * date: "YYYY-MM-DD"
 * author: "Author Name"
 * summary: "One sentence description shown on blog list."
 * tags: ["Tag1", "Tag2"]
 * ---
 */

// Vite's import.meta.glob loads all .md files at build time
const modules = import.meta.glob("./posts/*.md", { as: "raw", eager: true });

/**
 * Parse YAML frontmatter block at the top of a markdown file.
 * Returns { frontmatter: {}, content: "..." }
 */
function parseFrontmatter(raw) {
  const match = raw.match(/^---\s*\n([\s\S]*?)\n---\s*\n([\s\S]*)$/);
  if (!match) return { frontmatter: {}, content: raw };

  const yamlBlock = match[1];
  const content = match[2].trim();

  const frontmatter = {};
  for (const line of yamlBlock.split("\n")) {
    const colonIdx = line.indexOf(":");
    if (colonIdx < 0) continue;
    const key = line.slice(0, colonIdx).trim();
    let value = line.slice(colonIdx + 1).trim();

    // Remove surrounding quotes
    if ((value.startsWith('"') && value.endsWith('"')) ||
        (value.startsWith("'") && value.endsWith("'"))) {
      value = value.slice(1, -1);
    }

    // Parse arrays like ["Tag1", "Tag2"]
    if (value.startsWith("[") && value.endsWith("]")) {
      try {
        value = JSON.parse(value);
      } catch {
        value = value.slice(1, -1).split(",").map(t =>
          t.trim().replace(/^["']|["']$/g, "")
        );
      }
    }

    frontmatter[key] = value;
  }

  return { frontmatter, content };
}

/**
 * Convert Markdown to HTML (lightweight — handles headers, bold, italic,
 * lists, links, code blocks, horizontal rules).
 * For production you could swap this with `marked` or `remark`.
 */
export function markdownToHtml(md) {
  let html = md;

  // Fenced code blocks
  html = html.replace(/```[\w]*\n([\s\S]*?)```/g, "<pre><code>$1</code></pre>");

  // Headings
  html = html.replace(/^### (.+)$/gm, "<h3>$1</h3>");
  html = html.replace(/^## (.+)$/gm, "<h2>$1</h2>");
  html = html.replace(/^# (.+)$/gm, "<h1>$1</h1>");

  // Bold and italic
  html = html.replace(/\*\*\*(.+?)\*\*\*/g, "<strong><em>$1</em></strong>");
  html = html.replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>");
  html = html.replace(/\*(.+?)\*/g, "<em>$1</em>");

  // Links
  html = html.replace(/\[([^\]]+)\]\(([^)]+)\)/g,
    '<a href="$2" target="_blank" rel="noopener noreferrer">$1</a>');

  // Horizontal rule
  html = html.replace(/^---$/gm, "<hr>");

  // Unordered lists
  html = html.replace(/(^- .+\n?)+/gm, match => {
    const items = match.trim().split("\n")
      .map(l => `<li>${l.replace(/^- /, "")}</li>`)
      .join("");
    return `<ul>${items}</ul>`;
  });

  // Ordered lists
  html = html.replace(/(^\d+\. .+\n?)+/gm, match => {
    const items = match.trim().split("\n")
      .map(l => `<li>${l.replace(/^\d+\. /, "")}</li>`)
      .join("");
    return `<ol>${items}</ol>`;
  });

  // Paragraphs — wrap lines not already wrapped in block tags
  html = html.split("\n\n").map(block => {
    block = block.trim();
    if (!block) return "";
    if (/^<(h[1-6]|ul|ol|pre|hr|blockquote)/.test(block)) return block;
    return `<p>${block.replace(/\n/g, " ")}</p>`;
  }).join("\n");

  return html;
}

/**
 * Load and parse all blog posts.
 * Returns array sorted by date descending (newest first).
 */
export function getAllPosts() {
  const posts = [];

  for (const [path, raw] of Object.entries(modules)) {
    const { frontmatter, content } = parseFrontmatter(raw);
    if (!frontmatter.slug) continue;

    posts.push({
      slug: frontmatter.slug,
      title: frontmatter.title || "Untitled",
      date: frontmatter.date || "",
      author: frontmatter.author || "LikhaPoha AI Team",
      summary: frontmatter.summary || "",
      tags: Array.isArray(frontmatter.tags) ? frontmatter.tags : [],
      content,
      html: markdownToHtml(content),
      _path: path,
    });
  }

  return posts.sort((a, b) => (b.date > a.date ? 1 : -1));
}

/**
 * Get a single post by slug.
 */
export function getPostBySlug(slug) {
  return getAllPosts().find(p => p.slug === slug) || null;
}

/**
 * Format a date string as "22 June 2026"
 */
export function formatDate(dateStr) {
  if (!dateStr) return "";
  try {
    return new Date(dateStr).toLocaleDateString("en-IN", {
      day: "numeric", month: "long", year: "numeric",
    });
  } catch {
    return dateStr;
  }
}
