# 11. CSS & styling

**Versions:** Void 1.5.0 · Next.js 16.4 (App Router) · React Router 8 (framework mode) · TanStack Start 1.169 (React) · Nuxt 5.0 pre-release (4.x is stable) · SvelteKit 3.1 · SolidStart 2.0 · Astro 7.4

**Markers:** (unverified) not confirmed in docs or source

**Note:** Every claim that Void lacks something was checked by searching `packages/` and `docs/`; the search terms are listed in each section.

**Paths:** Void file paths are in the `voidzero-dev/void` repo. Short paths such as `pages/scan.ts` are under `packages/void/src/`; paths that start with a package name, such as `react/src/…`, are under `packages/`.

## At a glance

- **CSS delivery is solid.** Regular pages link only their own CSS (entry + layout chain + page). Dev SSR inlines CSS as nonce'd `<style>` tags, so there is no FOUC in any of the 4 adapters.
- **Missing:** production critical-CSS inlining (Nuxt, SvelteKit and Astro have it stable), CSS-in-JS SSR hooks, and documentation for Tailwind and preprocessors.
- **Island and Markdown pages share one production stylesheet**, so they don't get per-page CSS the way regular pages do.

## Gap list for this area

| Gap in Void | Who has it (mechanism, briefly) | Prevalence | Notes for design (constraints, dependencies, adapter impact) |
|---|---|---|---|
| Production critical/inlined CSS | Nuxt (`features.inlineStyles`), SvelteKit (`inlineStyleThreshold`), Astro (`build.inlineStylesheets: 'auto'` default); Next.js and TanStack experimental | Common (3 stable) | Small change in `routing-assets.ts` (inline files under a threshold). Interacts with CSP (Void already patches `style-src` in dev) and ISR cache size. |
| CSS-in-JS SSR integration | Next.js (style registry + `useServerInsertedHTML`) | Differentiator (1) | React adapter: streaming via `renderToReadableStream` needs an inserted-HTML hook. Solid: emit `getAssets()` (also needed for `@solidjs/meta` `<Style>`). Vue and Svelte are mostly unaffected. |
| Tailwind / preprocessor docs and scaffolding | All 7 document or scaffold Tailwind (Next.js default template, React Router templates, TanStack guide, Nuxt module, `sv add`, SolidStart template, `astro add`) | Table stakes (7) | Probably works through Vite already (unverified in Void). Mostly docs plus a `void init` option. Check dev CSS inlining of Tailwind output and the island shared stylesheet. |
| Per-page CSS for island/Markdown pages | Astro (per-page + shared chunks for MPA pages) | Differentiator (1) | Today all island pages share one stylesheet (`islandStyleRoots`). |

## Where Void is ahead

- **Dev SSR CSS is inlined with nonce and CSP patching in all 4 adapters**, so there is no dev FOUC. Nuxt documents a dev flash under streaming; Next.js and SvelteKit don't address it.
- **Per-route CSS for regular pages with zero config** (entry + layout chain + page). Next.js keeps global CSS across navigations, and SolidStart v2 lets styles accumulate.
- **CSS modules survive the islands build**, including Vue `<style module>` in island pages (explicitly handled).

## CSS delivery: route splitting, ordering, removal, inlining, dev FOUC

| Framework | Per-route splitting | Order | Removal on client navigation | Production inlining / critical CSS | Dev FOUC |
|---|---|---|---|---|---|
| **Void** | **Regular pages:** CSS collected from the client entry + the page's layout chain + the page's manifest keys, so a page links only its own CSS (`pageCssKeys` in packages/void/src/router/compile.ts; `collectRouteCss` in packages/void/src/runtime/routing-assets.ts). **Island and Markdown pages:** one **shared** production stylesheet for all island pages and their layouts, layouts first (packages/void/src/pages/islands-plugin.ts `islandStyleRoots`). | Dev: root phases, entry → layouts → page. Prod: manifest import-graph order. | No removal logic found in the client runtime (`stylesheet` grep in `packages/void/src/pages` and the adapters). Inferred: route CSS loaded by a client navigation stays. | **None**: only `<link rel="stylesheet">` | **Avoided in all 4 adapters:** dev SSR inlines `.css .scss .sass .less .styl .stylus .pcss .postcss` (and Vue/Svelte style blocks) as `<style data-vite-dev-id nonce>` and patches CSP `style-src` (packages/void/src/pages/dev-css-assets.ts, protocol.ts) |
| Next.js | Chunked per route; `cssChunking` (experimental) | Import order | **Global CSS is not removed** on navigation (React stylesheet integration) | `inlineCss` (experimental) | Not documented |
| React Router | Route-module side-effect imports, or a `links` export (`?url`) → `<Links>` | — | `links` are aggregated over matched routes, so they drop out when the route leaves (inferred) | None | Root `Layout` keeps `<Links>` from remounting |
| TanStack Start | Start manifest links CSS for matched routes via `HeadContent`. Placement scopes it (root, layout, leaf). `import()`/`lazy` CSS is not in SSR links. | Placement | Head links unload with the route | **Experimental** `server.build.inlineCss`: one `<style>` for matched routes, prod SSR only; per-request `handler(req, { inlineCss })`; `url()` rebased; needs a CSP nonce | Styled before hydration (manifest links) |
| Nuxt | Via Vite | — | — | **`features.inlineStyles`** (Vite only; default inlines `.vue` component styles into SSR HTML); `build:manifest` recipe drops links | SFC styles flash in dev under (experimental) streaming |
| SvelteKit | JS and CSS preloaded per route | — | — | **`inlineStyleThreshold`** (default `0`): CSS files under N UTF-16 units are merged into one `<style>` (verified in packages/kit/types/index.d.ts) | Not documented |
| SolidStart | Via Vite. v2 server-renders `lazy()` component CSS. | — | **Not removed** (v2, matching Vite): route styles accumulate. Workarounds: `body:has(main[data-route])` scoping, or `<Link rel="stylesheet">` from `@solidjs/meta`. | None | v2: no FOUC for `lazy()` CSS |
| Astro | Per page + shared chunks | `<link>` < imported CSS < scoped styles; v6+ renders in definition order | ClientRouter keeps stylesheets | **`build.inlineStylesheets`**: `'auto'` (default; under 4 kB inlined), `'always'`, `'never'` | n/a |

**Behavioral differences that matter:**
- Void's dev CSS inlining (with CSP nonce patching) solves dev FOUC structurally, for every adapter. Nuxt still flashes in dev under streaming.
- Void's shared island stylesheet trades per-page precision for one cacheable file. A docs site with many Markdown pages loads every island page's component CSS on each page.

**Void gap:** partial. Missing: production critical/inlined CSS (Nuxt and SvelteKit opt-in, Astro on by default; Next.js and TanStack experimental) and per-page CSS for island/Markdown pages.

## CSS authoring: modules, preprocessors, Tailwind, scoped styles, CSS-in-JS

| Framework | CSS Modules | Preprocessors / PostCSS | Tailwind | Scoped styles | CSS-in-JS |
|---|---|---|---|---|---|
| **Void** | Vite default `*.module.css`. Island builds explicitly keep CSS modules and Vue `<style module>` (packages/void/src/pages/islands-plugin.ts `islandStylesPlugin`). | Vite defaults (the dev-inline regex covers Sass/Less/Stylus/PostCSS). **Not documented** in Void docs. | **Not documented or scaffolded** (grepped `tailwind` in `docs/` and `packages/`: no hits). The Vite plugin is expected to work (unverified). | Adapter-native: Vue SFC `scoped`, Svelte component styles. React and Solid: modules only. | **None.** No SSR style-collection hook: React has no `useServerInsertedHTML` equivalent, and the Solid adapter emits only `generateHydrationScript()`, not `getAssets()` (packages/solid/src/plugin-pages.ts). |
| Next.js | `.module.css` (Turbopack lacks standalone `:local`/`:global`, `@value`, ICSS, `composes` from non-modules) | Sass (`sassOptions`; `functions` unsupported in Turbopack); PostCSS; `useLightningcss` (experimental) | **v4 default** in `create-next-app` | Modules only | Client components: style registry + `useServerInsertedHTML` (styled-components, styled-jsx, MUI, Chakra, Panda, StyleX, vanilla-extract; emotion "working on support") |
| React Router | Via Vite | Via Vite | In default templates | Modules | Vanilla Extract mentioned; no CSS-in-JS docs |
| TanStack Start | `.module.css` (scoped) | "Whatever your bundler supports" | v4 guide (`@tailwindcss/vite`, `@tailwindcss/postcss` for Rsbuild); v3 legacy | Modules | Router how-tos (MUI, Chakra, shadcn) |
| Nuxt | `<style module>` → `$style` | `lang="scss\|sass\|less\|styl\|stylus\|postcss"`; `vite.css.preprocessorOptions`; PostCSS (`postcss.plugins`/`order`). **Nuxt 5 + Vite adds no PostCSS plugins by default.** | `@nuxtjs/tailwindcss` / UnoCSS (community modules) | `<style scoped>`, `v-bind()` in CSS | Third-party (Panda, Pinceau) |
| SvelteKit | Via Vite (not documented) | `vitePreprocess({ style: true })`: PostCSS, SCSS, Less, Stylus, SugarSS; `svelte-preprocess` alternative | `npx sv add tailwind` | **Scoped by default** | Not documented |
| SolidStart | `.module.css/.scss/.sass` | Sass via Vite | `with-tailwindcss` template; `@tailwindcss/vite` | Modules only | `with-solid-styled` template |
| Astro | In framework components (not in `.astro`) | `<style lang>` Sass/Less/Stylus; PostCSS built in; LightningCSS via Vite | v4 via `astro add tailwind` (`@tailwindcss/vite`) | **Scoped by default**: `scopedStyleStrategy` `'attribute'` (default), `'class'`, `'where'`; `is:global`, `:global()`, `define:vars`, `class:list` | Not covered beyond React `experimentalDisableStreaming` |

**Void gap:** partial. Missing: SSR integration for CSS-in-JS (React adapter streaming and Solid `getAssets()`; Next.js only), and documented or scaffolded Tailwind/preprocessor setup, which all 7 others document or scaffold.
