# 12. Markdown & content

**Versions:** Void 1.5.0 · Next.js 16.4 (App Router) · React Router 8 (framework mode) · TanStack Start 1.169 (React) · Nuxt 5.0 pre-release (4.x is stable) · SvelteKit 3.1 · SolidStart 2.0 · Astro 7.4

**Note:** Every claim that Void lacks something was checked by searching `packages/` and `docs/`; the search terms are listed in each section.

**Paths:** Void file paths are in the `voidzero-dev/void` repo. Short paths such as `pages/scan.ts` are under `packages/void/src/`; paths that start with a package name, such as `react/src/…`, are under `packages/`.

## At a glance

- **Markdown is a Void strength.** Markdown pages work in all 4 adapters, with Shiki dual-theme highlighting, containers, a TOC, a `@void/md/pages` index and auto-prerendering. The gap is MDX-style server-rendered components (Markdown components must be hydrated islands) and the lack of a plugin hook.

## Gap list for this area

| Gap in Void | Who has it (mechanism, briefly) | Prevalence | Notes for design (constraints, dependencies, adapter impact) |
|---|---|---|---|
| Server-rendered components in Markdown (MDX/MDC-style) | Next.js (MDX), Astro (MDX), SolidStart (`.mdx` routes), SvelteKit (mdsvex add-on), Nuxt (MDC via `@nuxt/content`); React Router RSC only (unstable) | Common (5) | Void's islands pipeline already server-renders static components in `.island.*` pages. Allowing non-island imports in `.md` `<script>` to render statically would cover most of this without MDX. Real MDX would be JSX-based and React/Solid-flavoured, so the 4-adapter impact is uneven. |
| Markdown plugin hook | Next.js (remark/rehype), Astro (`unified()` processor) | Differentiator (2) | Expose markdown-it `use()` in `voidMarkdown()` options. |
| Schema-validated content collections | Astro (content + live collections, Zod), Nuxt (`@nuxt/content` collections) | Differentiator (2) | `@void/md/pages` is a starting point (path, title, frontmatter, headings). |

## Where Void is ahead

- **Built-in Markdown pages in 4 UI libraries:** Shiki dual-theme highlighting, line/diff/focus notation, line numbers, containers, GitHub alerts, footnotes, `[[toc]]`, heading anchors, code-copy, frontmatter → head, named layouts, islands, companion loaders, auto-prerender, a `@void/md/pages` index and a ready theme. Only Astro is comparable, and only for its own `.astro` + islands model.

## Markdown / MDX as pages

| Framework | Format and engine | Files become pages? | Components inside Markdown | Frontmatter | Layouts | Syntax highlighting | Plugin hook | Content index / collections |
|---|---|---|---|---|---|---|---|---|
| **Void** | `.md` only (**no MDX**) via `@void/md` (markdown-exit / markdown-it) + `voidMarkdown()`, all 4 adapters | **Yes**: `pages/**/*.md` are island pages (zero JS except islands, the client `<script>` and code-copy). Companion `.server.ts` allowed; auto-prerendered when static. | **Only island imports** in the leading `<script>` block (`with { island: 'load' \| 'visible' \| 'idle' \| 'media:…' }`), used as uppercase tags, so **every component hydrates**. Non-island imports become client code, not server-rendered components (packages/md/src/extract-script.ts). | YAML. `title`/`description` → head; `layout` selects a named `_layouts/` layout (`!name` = exclusive); `useFrontmatter()` in layouts and islands | Inherited chain + named layouts | Shiki dual theme (`shiki.themes { light, dark }` is the only option; default github-light/dark), languages on demand, `{1,3-5}` line highlights, `// [!code ++\|--\|focus\|error\|warning]`, `:line-numbers` | **None.** Fixed plugin set: GFM, `:::` containers, GitHub alerts, emoji, footnotes, `{.class #id}`, anchors, `[[toc]]`, `.md` link rewriting. | `@void/md/pages` → `[{ path, title, frontmatter, headings }]` (sorted, HMR). No schemas, Markdown only. Theme CSS `theme.css` / `theme-content.css`. |
| Next.js | MDX (`@next/mdx`); `.md` via `extension` | Yes (`pageExtensions`) | **MDX JSX**: server components; `mdx-components.tsx` with `useMDXComponents` **required**; global/local/layout mapping | **Not supported by default** (remark-frontmatter) | Via components; `metadata` exports work | Via plugins | remark/rehype (Turbopack: string names + serializable options); `mdxRs` experimental; remote MDX | — |
| React Router | MDX documented **only for RSC mode (unstable)** (`@mdx-js/rollup` ≥ 3.1.1) | RSC only | MDX | — | — | — | — | — |
| TanStack Start | Not a page format. `@tanstack/markdown` renders at runtime (no MDX; escapes raw HTML) | No | No | Via Content Collections | — | TanStack Highlight | — | Content Collections (third-party) |
| Nuxt | Official module `@nuxt/content` (`.md/.yml/.csv/.json`) | **No.** A catch-all page renders `queryCollection(…).path(route.path)` | **MDC** syntax (Vue components) via `<ContentRenderer>` | Yes | Page/layout of the catch-all | (module) | (module) | Collections with a MongoDB-like query API; auto navigation |
| SvelteKit | mdsvex add-on (`npx sv add mdsvex`) | Yes, via `extensions` (e.g. `.svx`, `.svelte.md`) | Svelte components | (mdsvex) | (mdsvex) | (mdsvex) | — | — |
| SolidStart | `.mdx` in `src/routes` treated as a page (compiler plugin unspecified; `extensions`) | Yes | MDX | — | — | — | — | SolidBase recommended for docs sites |
| Astro | `.md` (core) + `.mdx` (`@astrojs/mdx`); v7 default processor Sätteri | Yes | MDX `components` mapping, exported variables, `optimize` | Yes; `layout` key | `layout` frontmatter; `MarkdownLayoutProps` | `syntaxHighlight`: `'shiki'` (default github-dark), `'prism'`, `false`; `excludeLangs` | `markdown.processor: unified()` for remark/rehype/recma | **Content collections** (`glob()`/`file()`/custom loaders, Zod schemas, `reference()`) + live collections |

**Behavioral differences that matter:**
- Void Markdown is the most "batteries included" on the rendering side (VitePress-grade features with zero config) and the only one that works the same for 4 UI libraries. Astro is the closest.
- Void cannot server-render a component inside Markdown. In Next.js, Astro and SolidStart (MDX), SvelteKit (mdsvex) and Nuxt (MDC), a non-interactive component (a callout, a chart rendered to HTML) ships zero JS. In Void it must be a hydrated island.
- There is no way to add a markdown-it plugin (math, mermaid, custom directives). Next.js and Astro allow remark/rehype plugins.

**Void gap:** partial. Missing: MDX or server-rendered (non-hydrated) components in Markdown, a plugin hook, and schema-validated content collections (Astro; Nuxt via module).
