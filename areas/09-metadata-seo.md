# 9. Metadata & SEO

**Versions:** Void 1.6.2 · Next.js 16.4 (App Router) · React Router 8 (framework mode) · TanStack Start 1.169 (React) · Nuxt 5.0 pre-release (4.x is stable) · SvelteKit 3.1 · SolidStart 2.0 · Astro 7.4

**Note:** Void's head behavior was re-checked in `pages/head.ts` (server merge), `pages/head-client.ts` (client-navigation updates) and `pages/protocol.ts`.

**Paths:** Void file paths are in the `voidzero-dev/void` repo. Short paths such as `pages/scan.ts` are under `packages/void/src/`; paths that start with a package name, such as `react/src/…`, are under `packages/`.

## At a glance

- **Void's head API is server-defined and layered.** Precedence is page `head()` > middleware `headDefaults` > config `head`. Merging is deterministic, and head is always rendered into the initial `<head>`, even with React streaming. Bots therefore never miss tags, and Void needs no bot sniffing or per-route streaming opt-outs (Nuxt).
- **Biggest structural gap: no layout-level head.** Every other framework lets a layout or parent route contribute head tags that merge down the tree (table stakes).
- **Second gap: no component-level head in React, Vue and Solid.** Svelte's `<svelte:head>` happens to work but is undocumented. React Router, Nuxt, SvelteKit, SolidStart and Astro all allow head tags from any component.
- **Tag coverage is narrow.** `meta` emits only `name`, `property`, `content` and `charset`, so there is no `http-equiv`, `media` (for example `theme-color` per color scheme) or `itemprop`. There is no `style`, `noscript` or `base`, and no body-position scripts. Scripts, `htmlAttrs` and `bodyAttrs` are not updated on client navigation.
- **Title templating is minimal.** There is one config-level `titleTemplate` string (`%s`). Pages cannot opt out, layouts cannot add their own template, and there is no function form (Next.js and Nuxt have these).
- **Nothing for SEO files or images.** There is no sitemap, robots, manifest, icon or OG-image generation. Only Next.js has the full set. Sitemap generation is common (Next.js, TanStack, Astro), and OG images are Next.js-only.
- **No canonical, hreflang or JSON-LD helpers and no absolute-URL base.** Canonical links and JSON-LD are written by hand. JSON-LD via `script.innerHTML` is emitted **unescaped**.
- **Strengths:** a request-aware middleware head layer (unique); the same API across 4 UI libraries; Markdown frontmatter turns into `title`/`description` automatically; and `c.originalUrl()` gives canonical URLs under rewrites.

## Gap list for this area

| Gap in Void | Who has it (mechanism, briefly) | Prevalence | Notes for design (constraints, dependencies, adapter impact) |
|---|---|---|---|
| Layouts cannot contribute head | Next.js (layout `metadata`), React Router (`meta`/`links` per route; React elements), TanStack (`head` on every route), Nuxt (`useHead` in layouts), SvelteKit/SolidStart/Astro (head in layout components) | Table stakes (7) | Depends on layout companions/loaders (area 3; layouts have no `.server.ts` today). The merge order would become config → middleware → layouts (outer→inner) → page. Decide replace vs merge for nested objects; Next.js's shallow replace is a known footgun. |
| Missing tags/attributes: `meta` `http-equiv`/`media`/`itemprop`/arbitrary attrs; `style`, `noscript`, `base`; body-position scripts | Nuxt (all + `tagPosition`), TanStack (`styles`, body `scripts()`), React Router/SvelteKit/SolidStart/Astro (raw elements); Next.js only via `viewport` and components | Table stakes (6) | Widen `HeadDescriptor.meta` to arbitrary attrs. The dedupe key must include `media` (theme-color). Add `style`/`noscript`/`base`; `script` needs `position`. The client diff (`head-client.ts`) only handles `meta`/`link` today. |
| Component-level head API (React/Vue/Solid) | React Router (React 19 elements), Nuxt (`useHead` anywhere), SvelteKit (`<svelte:head>`), SolidStart (`@solidjs/meta`), Astro (HTML in components) | Common (5) | Adapter-specific. Svelte already works (document it). React: let React render into `<head>`, or collect hoistables. Vue: Unhead or a `useHead` shim. Solid: `@solidjs/meta` + `MetaProvider` + SSR tag collection. Must merge with the server `head()` layers. |
| Async `head()` | Next.js (`generateMetadata` + `parent`), TanStack (`head` may return a Promise), Astro (top-level await); Nuxt reactive | Common (3–4) | Small change in `protocol.ts` (await `headFn`). A loader workaround exists today. |
| `htmlAttrs`/`bodyAttrs`/`script` not re-applied on client navigation; title kept when the next page has none | Nuxt (reactive), React Router and TanStack (React-rendered document; inferred) | Common (3) | Extend `applyClientHead`. Scripts need idempotence/once semantics (cf. TanStack `ScriptOnce`, Next.js `beforeInteractive` once per document). |
| Sitemap generation | Next.js (`sitemap.ts`, `generateSitemaps`), TanStack (build-time from prerender crawl), Astro (`@astrojs/sitemap`) | Common (3) | Void knows page routes, `routing.prerender`/ISR lists and `@void/md/pages`. Needs an absolute site URL config and dynamic-route enumeration. |
| Title template per layout, opt-out, function form | Next.js (`{ default, template, absolute }` per segment), Nuxt (function `titleTemplate`, `templateParams`) | Differentiator (2) | Pairs with layout head. Also let middleware set the template. |
| Canonical/hreflang helpers and an absolute URL base | Next.js (`alternates` + `metadataBase`), Astro (`site` + sitemap `i18n`) | Differentiator (2) | `c.originalUrl()` already exists. Config-level link concatenation must allow page override (dedupe by `rel` + `hreflang`). |
| Default charset/viewport + viewport/theme-color API | Next.js (`viewport`/`generateViewport`), Nuxt (`app.head` defaults) | Differentiator (2) | Cheap: emit defaults in the adapter shells (React/Vue/Svelte/Solid + islands templates). |
| Typed SEO keys (OG/Twitter) | Next.js (`Metadata` type), Nuxt (`useSeoMeta`, 100+ keys) | Differentiator (2) | Could be a typed `seo: {…}` field on `HeadDescriptor` that expands to `meta`. |
| robots.txt generation | Next.js (`robots.ts`) | Differentiator (1) | Trivial as a route today; a convention would add typed rules and per-env defaults (e.g. noindex on previews). |
| Web manifest generation | Next.js (`manifest.ts`) | Differentiator (1) | — |
| Icon conventions / generated icons | Next.js (`icon`, `apple-icon`, code-generated) | Differentiator (1) | Depends on image generation. |
| OG image generation | Next.js (`opengraph-image`, `ImageResponse`); Astro recipe only | Differentiator (1) | Workers runtime: Satori + resvg-wasm size limits. Build-time prerendering in Node is simpler. |
| Safe JSON-LD helper | React Router (`'script:ld+json'`) | Differentiator (1) | At minimum, escape `</script` in `script.innerHTML` (security hardening independent of the helper). |

## Where Void is ahead

- **A request-aware middleware head layer** (`c.set('headDefaults', …)`) that merges structurally between config and page. No other framework has a structured middleware head layer; Nuxt and SvelteKit only offer string-level HTML hooks.
- **Head is always complete in the initial `<head>`, even with React streaming and deferred props.** There is no crawler-visibility trade-off. Next.js needs `htmlLimitedBots`, Nuxt's experimental streaming drops post-`await` tags for non-matching bots, and SolidStart needs `deferStream`.
- **One head API across React, Vue, Svelte and Solid.** The competitors are single-library, or (Astro) leave islands out of head.
- **Markdown pages produce `<title>` and `meta description` from frontmatter** with `titleTemplate` applied and no server file. Among the others, only Astro's Markdown layouts get frontmatter, and they render it by hand.
- **The client head diff preserves unchanged tags** (signature match) instead of re-creating them, and escapes attributes and title.
- **`c.originalUrl()`** gives correct canonical URLs under internal rewrites (only TanStack's `location.publicHref` is comparable).

## Where head can be declared, and when it runs

| Framework | Page | Layout / parent route | Any component | Global config | Request level (middleware) | Sync / async; where it runs |
|---|---|---|---|---|---|---|
| **Void** | `export const head = defineHead<Props>((c, props) => HeadDescriptor \| undefined)` in `.server.ts`. Markdown: frontmatter `title`/`description` produce tags with no server file. | **No.** Layouts have no companion file. | **No** for React, Vue and Solid. **Svelte:** `<svelte:head>` output is injected on SSR (undocumented; packages/svelte/src/plugin-pages.ts). React renders into `<div id="app">` (packages/react/src/runtime/pages-server.ts), so React 19's `<title>`/`<meta>` hoisting cannot reach `<head>` on SSR. | `head` in `void.config.ts`: `title`, `titleTemplate`, `meta`, `link`, `script`, `htmlAttrs`, `bodyAttrs` | `c.set('headDefaults', HeadDescriptor)`. This is **one slot**: a later middleware's `c.set` replaces an earlier one's instead of merging. | **Synchronous** (`headFn(c, props)` is not awaited, packages/void/src/pages/protocol.ts:469). Server-only, after the loader. Re-evaluated on the server for every client navigation, because the page JSON carries the resolved head. |
| Next.js | `metadata` / `generateMetadata({ params, searchParams }, parent)` | Yes (`layout`), evaluated root → page | No (Server Component `layout`/`page` files only) | Root layout + metadata file conventions | No | **Async**. `parent` is a promise of the resolved parent metadata. `redirect()`/`notFound()` are allowed. |
| React Router | `meta` export **or** React 19 `<title>`/`<meta>`/`<link>` in the route component (recommended) | Yes (each route) | **Yes** (React 19 elements, anywhere) | Root route | No | `meta(args)` is sync over `loaderData`/`matches`; runs on server and client. |
| TanStack Start | Route `head(ctx)`; separate route `scripts()` for body scripts | Yes (every route, including root/layout routes) | No (`ScriptOnce` only) | Root route | No | **Sync or async** (`Promise` return type). Runs after loaders; ctx `{ matches, match, params, loaderData }`. |
| Nuxt | `useHead`, `useSeoMeta`, `useHeadSafe`, `<Title>`/`<Meta>`/… | Yes | **Yes** (any `setup`, `app.vue`, plugins) | `app.head` (static, not reactive) | Nitro `render:html` hook (string-level rewrite) | Reactive (refs, getters or a function input); entries are disposed with the component. |
| SvelteKit | `<svelte:head>` | Yes | **Yes** | `app.html` template | `handle` → `transformPageChunk` (string-level) | Template-driven from `load` data |
| SolidStart | `@solidjs/meta` `<Title>`, `<Meta>`, `<Link>`, `<Style>` under `<MetaProvider>` | Yes | **Yes** | `entry-server.tsx` document | — | Components (with Suspense) |
| Astro | Raw `<head>` HTML in pages and layouts (props / named slots) | Yes | **Yes** | Layouts | Middleware can rewrite the HTML | Top-level `await` in frontmatter |

**Behavioral differences that matter:**
- Void is the only framework where a **layout cannot contribute head**. A docs section layout that wants `<meta name="robots">` or a section title suffix must use middleware (one slot, not path-scoped) or repeat it in every page.
- Void's middleware layer is unique: request-aware defaults (per tenant, per locale, a pre-paint theme script) merge structurally under page values. Nuxt and SvelteKit only offer string-level HTML rewriting at request level.
- `head()` cannot `await`. Anything async has to move into the loader. Next.js, TanStack and Astro allow async head code directly.

**Void gap:** missing at layout level and at component level (React, Vue and Solid adapters). Partial on async (sync only, but it receives resolved loader props) and on middleware composition (single slot).

## Merge, dedupe and title templates

| Framework | Title | `meta` dedupe | `link` / `script` | Title template | html/body attrs |
|---|---|---|---|---|---|
| **Void** | Page > middleware > config (`pageHead?.title ?? middlewareHead?.title ?? configHead?.title`) | Key = `charset` \| `property:<p>` \| `name:<n>`. A later layer replaces the entry but keeps its first position. An entry with neither `name` nor `property` falls under `name:` and collapses with others like it. | **Concatenated** config → middleware → page, with **no dedupe and no removal**: a page cannot drop or replace a config `link` (e.g. `canonical`). | **Config only**: `titleTemplate` string with `%s` (only the first `%s` is replaced: `String.replace`). It also wraps config and middleware fallback titles. No page opt-out (`absolute`), no layout templates, no function form, and middleware cannot set it (`HeadDescriptor` has no `titleTemplate`). | Shallow merge; page wins |
| Next.js | Deepest segment wins | Field-level shallow merge root → page. A later segment **replaces whole nested objects** (`openGraph`, `robots`), so shared fragments are spread by hand. | n/a (not in metadata) | `title: { default, template, absolute }`. A template applies to **child segments** only and has no effect in `page`; `absolute` bypasses it. | Root layout JSX |
| React Router | `meta`: the **deepest route's array replaces everything** (compose via `matches`). React 19 elements: no framework merge. | Same (replace) | `links` aggregated across all matched routes | None (compose via `matches`) | Root `Layout` JSX |
| TanStack Start | Last (deepest) wins | Same `name`/`property`: deepest wins | Load/unload with route activity | "Composable" per docs but not documented | Root / `shellComponent` JSX |
| Nuxt (Unhead) | Last active entry | Unhead dedupe by tag identity; `key` option | Dedupe by `key`; `tagPosition` (`head`, `bodyClose`, …); Capo.js sorting always on in Nuxt 5 | `titleTemplate` string **or function** (the function form can't go in `nuxt.config`); `templateParams` (`%siteName`, `%separator`) | `htmlAttrs` / `bodyAttrs` (reactive) |
| SvelteKit | Whatever renders | **No merge or dedupe** | All rendered | None | `%lang%` + `transformPageChunk` |
| SolidStart | Route-level overrides higher-level | A route `Meta` overrides the same tag higher up | — | Wrap `<Title>` in your own component | `entry-server.tsx` JSX |
| Astro | Manual | None | Manual | Manual | Layout HTML |

**Behavioral differences that matter:** Void's link concatenation means site-wide `link`s (canonical, alternate, preload) cannot be overridden per page. With Next.js's field-level replace, TanStack's unloading or Unhead's keyed dedupe, a page *can* override them.

**Void gap:** partial. Missing: link/script dedupe or override keys (Nuxt `key`); per-layout title templates and an opt-out (`absolute`, Next.js); a function template and template params (Nuxt); middleware-settable `titleTemplate`.

## Supported tags and attributes

| Framework | `meta` attributes | Other head tags | Tag position | Typed SEO keys / safety |
|---|---|---|---|---|
| **Void** | **Only `name`, `property`, `content`, `charset`** are serialized (packages/void/src/pages/head.ts `renderHeadToString`). No `http-equiv`, `media`, `itemprop` or `id`. | `title`, `link` (any attrs), `script` (`src`, `innerHTML`, any attrs). **No `style`, `noscript` or `base`.** | All in `<head>`; no body-end option | Generic `HeadDescriptor` (no OG/Twitter keys). Attributes and title are HTML-escaped; `script.innerHTML` is emitted **raw**. |
| Next.js | Typed `Metadata` fields: `openGraph`, `twitter`, `robots`, `icons`, `manifest`, `verification`, `appleWebApp`, `alternates`, `appLinks`, `archives`, `assets`, `bookmarks`, `pagination`, `category`, `facebook`, `pinterest`, `other` | **No `http-equiv`, `<base>`, `<noscript>`, `<style>` or `<script>`** in metadata; use components or `ReactDOM.preload` etc. | Head | Fully typed object |
| React Router | Descriptors: `{ title }`, `{ name/property, content }`, `{ charSet }`, `{ 'script:ld+json': obj }`, `{ tagName: 'link', … }`. React elements: anything. | `links` descriptors (`rel`, `href`, `as`, …) | Head | `Route.MetaArgs` typed |
| TanStack Start | `meta` objects (`title`, `charSet`, `name`/`property`) | `links`, head `scripts`, inline `styles` (with `media`), plus body `scripts()`; `ScriptOnce` | Head + body (`<Scripts/>`) | CSP `ssr.nonce` applied to rendered `<style>` |
| Nuxt | Any | `title`, `base`, `link`, `meta`, `style`, `script`, `noscript`, `htmlAttrs`, `bodyAttrs` | `tagPosition: 'bodyClose'` etc. | `useSeoMeta`: 100+ flat **typed** keys (`ogImage`, `twitterCard`, …), XSS-safe. `useHeadSafe` attribute whitelist (drops `innerHTML` and `http-equiv`). |
| SvelteKit / SolidStart / Astro | Any (raw elements; Solid via `<Meta>`) | Any | Wherever rendered | — |

**Void gap:** partial. Missing: `meta` `http-equiv`, `media`, `itemprop` and arbitrary attributes (all six component- or element-based frameworks allow them; Next.js covers `theme-color` media via `viewport`); `style`, `noscript` and `base` tags; body-position scripts; typed OG/Twitter keys (Next.js, Nuxt); escaping of inline script content.

## Client-navigation updates

| Framework | What is updated on client navigation |
|---|---|
| **Void** | `meta` and `link` are diffed against `[data-void-head]` elements by attribute signature (unchanged tags are kept, stale ones removed). `title` is set **only if the new head has one**; otherwise the previous `document.title` **stays** (packages/void/src/pages/head-client.ts). `script`, `htmlAttrs` and `bodyAttrs` are **SSR-only**: a script declared by page B does not run on an A→B client navigation, and `<html lang>` does not change. |
| Next.js | Metadata re-resolved per navigation |
| React Router | `<Meta>`/`<Links>` re-render for the new matches. React renders the whole document (root `Layout`), so `<html>` attributes can update (inferred). |
| TanStack Start | Tags load and unload as routes become active or inactive. The document is rendered by React (inferred for attributes). |
| Nuxt | Reactive. Entries are disposed with their component; `htmlAttrs`/`bodyAttrs` are reactive. |
| SvelteKit | `<svelte:head>` content mounts and unmounts with its component |
| SolidStart | Route tags removed or updated on route change |
| Astro | With `<ClientRouter/>`: head is diffed (stylesheets and scripts kept, the rest replaced, `transition:persist` honored) and the title is announced. Without it: MPA navigation. |

**Void gap:** partial. Missing: client-side re-application of `htmlAttrs`, `bodyAttrs` and `script` (Nuxt reactive; React Router and TanStack through a React-rendered document); title reset when the destination has no title.

## Metadata from loaded data and streaming metadata

| Framework | Data access | Streaming behavior | Bot handling |
|---|---|---|---|
| **Void** | `head(c, props)` gets the **resolved** loader props. `defer()`ed props are still placeholders at that point, so they can't be used. | Head is resolved **before** the shell streams (React) or renders (Vue/Svelte/Solid), so it is always in the initial `<head>`. | Not needed: tags are always blocking and complete. |
| Next.js | `generateMetadata`; `fetch` memoized with the page | **Streaming metadata** (15.2): the UI is sent first and tags are appended to `<body>` when resolved. [Cache Components] Uncached data in metadata is an error unless it is cached or explicitly dynamic. | HTML-limited bots (UA list; `htmlLimitedBots` regex) get blocking `<head>` metadata. |
| React Router | `meta({ loaderData, matches })` | Resolved before render | — |
| TanStack Start | `head` runs after loaders and receives `loaderData`. `head().links` feed dynamic Early Hints (experimental). | Runs after loaders; how it interacts with streaming is not documented | — |
| Nuxt | `useHead`/`useSeoMeta` with computed values from `useFetch` | **Experimental `ssrStreaming`**: tags registered after an `await` are sent as client patch scripts. | Crawlers outside `botRegex` miss streamed tags; `routeRules` `streaming: false` per route. |
| SvelteKit | Return SEO fields from `load`, render `<svelte:head>` from `page.data` | — | — |
| SolidStart | `<Title>{data().name}</Title>` in Suspense | Streams | `deferStream: true` on the query keeps it crawler-visible |
| Astro | Frontmatter runs before the template (top-level `await`) | — | — |

**Void gap:** none for SEO correctness. Void's blocking head is the safe default. Missing at option level: metadata that depends on deferred or streamed data, which Next.js has as a deliberate trade-off.

## Sitemap, robots, web manifest, icons

| Framework | Sitemap | robots.txt | Web manifest | Icons / favicons |
|---|---|---|---|---|
| **Void** | Manual: a route handler in `routes/` or a file in `public/`. `@void/md/pages` (`[{ path, title, frontmatter, headings }]`) can feed a Markdown sitemap. | `public/robots.txt` or a route | `public/` | `public/` + `head.link` |
| Next.js | `sitemap.(xml\|ts)` returning `MetadataRoute.Sitemap` (`url`, `lastModified`, `changeFrequency`, `priority`, `alternates.languages`, `images`, `videos`); nested per segment; `generateSitemaps()` → `/…/sitemap/[id].xml` (in v16 the `id` arrives as a Promise) | `robots.(txt\|ts)`: `rules` per user-agent, `sitemap`, `host`, `other` (16.3) | `manifest.(json\|webmanifest\|ts)` (`MetadataRoute.Manifest`) | `favicon.ico` (root), `icon.*`, `apple-icon.*`, numbered variants, **code-generated icons**; `sizes`/`type` inferred and tags auto-emitted |
| React Router | Resource route (`sitemap[.]xml.tsx`) | Resource route | — | `links` export |
| TanStack Start | **Built-in at build time** when prerender crawling is on: `sitemap: { enabled, host }` (only crawlable/prerendered pages). Dynamic: server route `sitemap[.]xml.ts`. | Server route or `public/` (also `llms.txt` guide) | Static file only | Static file only |
| Nuxt | Not in core: server route + `prerender.routes`. The roadmap's "SEO & PWA" milestone is not shipped. Community modules: `@nuxtjs/robots` (named in docs); `@nuxtjs/sitemap` / Nuxt SEO (from memory, unverified). | Same | Not found | Static |
| SvelteKit | `+server.js` endpoint (prerenderable) | `static/` | — | — |
| SolidStart | `public/` | `public/` | `public/` | `public/` |
| Astro | **`@astrojs/sitemap`** official integration (requires `site`): `filter`, `customPages`, `customSitemaps`, `entryLimit`, `changefreq`/`lastmod`/`priority`, `serialize`, `chunks`, `i18n` hreflang, `xslURL`, `filenameBase`, `namespaces`. **Cannot list dynamic SSR routes.** | `public/` or `robots.txt.ts` endpoint | `public/` | `public/` |

**Void gap:** missing. Void has no generator for any of the four. A Void sitemap is easier to build than Astro's or TanStack's, because Void knows its page routes, ISR/prerender lists and Markdown index. Dynamic routes would still need a `getStaticPaths`-like enumeration (`routing.prerender` entries).

## Open Graph / Twitter image generation

| Framework | Mechanism |
|---|---|
| **Void** | None. OG `meta` tags only, via `head()`. |
| Next.js | `opengraph-image` / `twitter-image` file conventions: static (`.jpg/.png/.gif`; OG ≤ 8 MB, Twitter ≤ 5 MB, otherwise the build fails; `.alt.txt`) or code returning an `ImageResponse`. Code images receive `params`, export `alt`, `size` and `contentType`, and are prerendered unless they use request APIs; `generateImageMetadata` produces several. `ImageResponse` (`next/og`, Satori + Resvg, PNG): `width` 1200, `height` 630, `emoji` set, `fonts[]` (ttf/otf/woff), `debug`, `status`, `headers`. Flexbox/CSS subset only; **500 KB bundle limit**. Meta tags are auto-wired. |
| Astro | Not built in. Documented recipe: an endpoint using Satori + Sharp, loading self-hosted fonts via `experimental_getFontFileURL()`; Cloudinary `getCldOgImageUrl()`. |
| Nuxt | Not in core (community `nuxt-og-image`; from memory, unverified) |
| React Router, TanStack Start, SvelteKit, SolidStart | None (a resource or server route could return an image) |

**Void gap:** missing. Only Next.js ships this. Design constraint: Void's default runtime is Cloudflare Workers, where Satori + resvg-wasm fits only within Worker size limits (Next.js caps `ImageResponse` bundles at 500 KB for a similar reason). Prerendering at build time in Node avoids that.

## Canonical, alternates (hreflang), JSON-LD

| Framework | Canonical | hreflang / alternates | Absolute URL base | JSON-LD |
|---|---|---|---|---|
| **Void** | Manual `link: [{ rel: 'canonical', href }]`; `c.originalUrl()` gives the pre-rewrite URL (docs/guide/edge/rewrites.md) | Manual `link`s | None (no `site`/`metadataBase`) | `script: [{ type: 'application/ld+json', innerHTML: JSON.stringify(data) }]` works, but `innerHTML` is **not escaped**, so a `</script>` inside the data breaks out (packages/void/src/pages/head.ts). Because links are concatenated, a page cannot override a config-level canonical. |
| Next.js | `alternates.canonical` | `alternates.languages`, `media`, `types` | `metadataBase` (relative URL fields without it are a **build error**) | No API; render a native `<script>` and sanitize `<` (guide) |
| React Router | `{ tagName: 'link', rel: 'canonical', href }` in `meta` | Manual | — | **`{ 'script:ld+json': object }`** (stringified automatically) |
| TanStack Start | `links: [{ rel: 'canonical' }]`; `location.publicHref` under rewrites | Manual | — | Head `scripts` with `type: 'application/ld+json'` + `children`; GEO guide (schema.org types) |
| Nuxt | Manual `useHead` link | Manual | — | `useHead` script |
| SvelteKit | Manual; `trailingSlash` redirects avoid duplicate URLs | Manual | — | Manual |
| SolidStart | `<Link rel="canonical">` (from memory, unverified) | Manual | — | Manual |
| Astro | `new URL(Astro.url.pathname, Astro.site)` | `@astrojs/sitemap` `i18n` option emits hreflang | `site` config | `set:html={JSON.stringify(…)}` |

Extra: Next.js automatically marks 404s `noindex`.

**Void gap:** partial. Missing: canonical/alternates helpers resolved against a configured site URL (Next.js, Astro); a safe JSON-LD helper (React Router); auto `noindex` on 404.

## Viewport, theme-color, charset defaults

| Framework | Defaults emitted | Viewport / theme API |
|---|---|---|
| **Void** | **Nothing**: no `<meta charset>` and no viewport unless added in config `head.meta` (the docs example does this). Pages mode has no user-owned HTML document; the adapters generate the shell. | Plain `meta`. **`theme-color` per color scheme cannot be expressed**: there is no `media` attribute, and two `name="theme-color"` entries collapse into one under dedupe. |
| Next.js | `<meta charset>` and `<meta viewport>` always | `viewport` / `generateViewport`: `themeColor` (with media variants), `colorScheme`, `width`, `initialScale`, `maximumScale`, `userScalable` |
| Nuxt | `app.head` defaults `charset: utf-8` and `viewport: width=device-width, initial-scale=1` (via `charset`/`viewport` shortcuts) | Any `meta` with `media` |
| React Router, TanStack Start, SvelteKit, SolidStart, Astro | In the user-owned document (root `Layout`, root/shell route, `app.html`, `entry-server.tsx`, layout) | Raw `meta` |

**Void gap:** partial. Missing: built-in defaults (Next.js, Nuxt), a viewport/theme-color API with media variants, and the `media` attribute generally.
