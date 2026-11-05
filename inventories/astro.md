# Astro — feature inventory
Version documented: **7.4** (latest upgrade guide is `guides/upgrade-to/v7.mdx`, v6→v7; the newest core `<Since>` tags are `7.4.0`: `experimental.parallelPrerender`, `experimental.redirectPage`, the `notFound()` fetch handler, `astro build --timings`, split `image.service` build/runtime; the docs repo's own `package.json` depends on `astro ^7.4.2`) · Docs commit: 2026-11-03 (`c73a3be`)
Context: UI: Astro components (`.astro`, HTML-first, server-only templates that ship zero JS) plus optional "islands" from official React / Preact / Vue / Svelte / Solid / Alpine integrations · bundler: **Vite 8** (dev server and production bundler) with a **Rust-based Astro compiler** (default and only compiler since v7) · server engine: Astro's own Fetch-standard pipeline (`Request` → `Response`). Since v7 you can replace it with `src/fetch.ts`, composed from `astro/fetch` handlers or `astro/hono` (Hono) wrappers · runtimes: static HTML by default (no server needed). On-demand rendering needs an adapter: official adapters are Node (standalone or middleware), Cloudflare Workers (`workerd`, also used in dev), Netlify (Functions plus Edge Functions for middleware) and Vercel (Serverless plus Edge middleware). Deno has an adapter maintained by Deno.

Path convention: every "Source:" path is relative to `src/content/docs/en/` in withastro/docs (repo-root path = `src/content/docs/en/<path>`).

**Notable recent changes (v7.0 to 7.4).** Source: `guides/upgrade-to/v7.mdx` plus `<Since>` tags.
- v7.0:
  - Vite 8.
  - Rust compiler. It is stricter: unclosed tags now error, and invalid HTML is no longer auto-corrected.
  - **Advanced routing** (`src/fetch.ts`, `fetchFile` config, `astro/fetch`, `astro/hono`) graduated to stable.
  - **Route caching** (`cache.provider`, `routeRules`, `Astro.cache`) graduated to stable.
  - **Logger API** (`logger` config, `Astro.logger`) graduated to stable.
  - Queued rendering is now the default.
  - **Sätteri** is the new default Markdown/MDX processor (remark/rehype is opt-in via `unified()`).
  - `compressHTML` defaults to `'jsx'` (JSX whitespace rules).
  - `@astrojs/db` removed.
  - Deprecated `astro:transitions` internals removed.
  - CLI `--background` / `--json` modes added, auto-enabled for AI agents.
- v7.1: `paginate({format})`, CSP `kind` scoping, `experimental.collectionStorage`, `--ignore-lock`.
- v7.2: `session: false`, `experimental.incrementalBuild`, background mode for `astro preview`.
- v7.4: `experimental.parallelPrerender`, `experimental.redirectPage`, `notFound()` handler, `--timings`, separate build and runtime image services.
- Context from v6 (`guides/upgrade-to/v6.mdx`):
  - CSP, Fonts API and live content collections became stable.
  - Node 22 required; Zod 4.
  - The Vite Environment API is used, and Cloudflare dev runs in `workerd`.
  - `<ViewTransitions />` was removed in favour of `<ClientRouter />`; `Astro.glob()` was removed.
  - Images are cropped by default and never upscaled.

**Experimental flags currently documented** (`reference/experimental-flags/`): `chromeDevtoolsWorkspace`, `clientPrerender`, `collectionStorage`, `contentIntellisense`, `incrementalBuild`, `parallelPrerender`, `redirectPage`, `svgOptimizer`. Other APIs marked experimental:
- Container API (`reference/container-reference.mdx`)
- the adapters' CDN cache providers (`guides/caching.mdx`)
- `experimental_getFontFileURL()`
- React `experimentalReactChildren` and `experimentalDisableStreaming`
- Node adapter `experimentalDisableStreaming`

---

## 1. Routing

- **Route definition / file conventions**: **Supported (file-based only, plus programmatic injection by integrations).**
  - Every supported file in `src/pages/` is a route. There is "no separate routing config".
  - Supported page types: `.astro`, `.md`, `.mdx` (requires `@astrojs/mdx`), `.html`, and `.js`/`.ts` (endpoints).
  - Mapping: `src/pages/about.astro` and `src/pages/about/index.astro` both serve `/about`.
  - Files or directories prefixed with `_` are excluded from routing, which allows co-locating components, tests and utils.
  - Integrations add routes with `injectRoute({ pattern, entrypoint, prerender? })`. The pattern uses the same `[param]`/`[...rest]` syntax and the entrypoint is an `.astro` page or a `.js`/`.ts` handler.
  - **Since v7, `src/fetch.ts` (advanced routing) can wrap or replace the whole request pipeline** (see area 6). It is not a route table; file-based routes still do the matching.
  - `src/pages/` is the only directory Astro reserves.
  - Source: `guides/routing.mdx`, `basics/astro-pages.mdx`, `basics/project-structure.mdx`, `reference/integrations-reference.mdx`.
- **Nested layouts**: **Partial (component composition only; no file-convention layouts).**
  - Layouts are ordinary Astro components that render `<slot />`. They are nested by wrapping one component in another, and named slots can be forwarded (`<slot name="head" slot="head" />`).
  - `.md`/`.mdx` pages can name a layout with the `layout` frontmatter key. That layout receives `frontmatter`, `file`, `url`, `headings`, `rawContent()` and `compiledContent()`.
  - There is no `_layout`/`+layout` convention and no persistent layout. Every navigation renders a full HTML document on the server, layouts included.
  - With `<ClientRouter />`, the new `<body>` replaces the old one entirely. Only elements marked `transition:persist` survive.
  - A layout cannot set response headers or redirect: those work only at page level because the HTML is streamed (see area 2).
  - Source: `basics/layouts.mdx`, `basics/astro-components.mdx`, `guides/view-transitions.mdx`.
- **Dynamic segments**: **Supported.**
  - Syntax is `[param]`. Several params can share one segment (`[lang]-[version]`) or sit in separate segments.
  - **Static (prerendered) routes must export `getStaticPaths()`.** It returns `{ params, props? }[]`, and params values must be strings. Since v6, number params are an error (`guides/upgrade-to/v6.mdx`). `undefined` is shown as valid for rest params.
  - `getStaticPaths()` runs once at build time in an **isolated scope**: it can't reference anything from the page's scope except imports.
  - Params from `getStaticPaths()` are not decoded (use `decodeURI()`). `Astro.url.pathname` may be partially decoded since v6.
  - On-demand routes ignore `getStaticPaths()` ("should not be used"). They match any value and cannot receive `props`.
  - `getStaticPaths({ paginate, routePattern })`. `routePattern` has been available since 5.14.
  - Errors: `GetStaticPathsRequired`; `NoMatchingStaticPathFound` (dev request for a path that was not generated); `InvalidGetStaticPathParam`.
  - Source: `guides/routing.mdx`, `reference/routing-reference.mdx`, `reference/errors/*`.
- **Optional segments**: **Partial.**
  - There is no `[[opt]]` syntax.
  - A rest param can match zero segments: in static mode, `[...path]` with `params: { path: undefined }` builds the parent URL; on demand, the param is `undefined` at the root.
  - Source: `guides/routing.mdx`.
- **Catch-all / splat**: **Supported.**
  - Syntax is `[...rest]`. It matches any depth (`a/b/c`) and can be combined with named params (`/[org]/[repo]/tree/[branch]/[...file]`).
  - **On-demand routes may have only one rest param in the file path.**
  - Source: `guides/routing.mdx`.
- **Route priority**: **Supported (deterministic rules).** Rules are applied in this order:
  1. Reserved routes come first: `_astro/`, `_server_islands/` and `_actions/`. The image endpoint (`image.endpoint`, default `/_image`) also exists but is not listed as reserved.
  2. Routes with more path segments beat routes with fewer.
  3. Static routes beat dynamic routes.
  4. Named params beat rest params.
  5. Prerendered dynamic routes beat server dynamic routes.
  6. Endpoints beat pages.
  7. File routes beat config redirects.
  8. Remaining ties are sorted alphabetically using the Node default locale.

  `prerenderConflictBehavior: 'error'|'warn'(default)|'ignore'` controls what happens when two prerendered routes produce the same URL; the highest-priority route wins. Source: `guides/routing.mdx`, `reference/configuration-reference.mdx`, `reference/errors/prerender-route-conflict.mdx`.
- **Route groups / pathless layouts**: **Not found in docs.**
  - There is no `(group)` convention. `_`-prefixed folders are excluded from routing entirely (they don't group routes).
  - Source: `guides/routing.mdx`.
- **Parallel routes / intercepting (modal) routes**: **Not found in docs.**
  - The closest documented features are page partials (`export const partial = true`) for htmx-style fragment loading, and server islands.
  - Source: `basics/astro-pages.mdx`.
- **Typed links / typed route params**: **Not supported for links / Partial for params.**
  - Links are plain `<a href>`. Docs: "There is no framework-specific `<Link>` component".
  - Params are typed only for static routes, by inferring from `getStaticPaths()` (`GetStaticPaths`, `InferGetStaticParamsType`, `InferGetStaticPropsType`).
  - No generated route map was found.
  - Source: `guides/routing.mdx`, `guides/typescript.mdx`.
- **Search params**: **Basic, untyped.**
  - Read them from `Astro.url.searchParams` or `Astro.request.url`.
  - **Prerendered pages never see search params** (`request.url` has none at build time).
  - A server island cannot read the page's query string (its `Astro.url` is the island endpoint). Read the `Referer` header instead.
  - Vercel ISR requests also drop search params.
  - No validation or typing helpers.
  - Source: `reference/api-reference.mdx`, `guides/server-islands.mdx`, `guides/integrations-guide/vercel.mdx`.
- **Programmatic navigation**: **Supported (client, with ClientRouter) / server redirects.**
  - Client: `navigate(href, options)` from `astro:transitions/client`. It is based on the Navigation API signature but implemented on the History API, and it is meant to be used with `<ClientRouter />`. It has no effect during SSR and does **not sanitize** `href`.

    | option | values / default | behavior |
    |---|---|---|
    | `history` | `'auto'`(default) \| `'push'` \| `'replace'` | `auto`: tries `pushState`. If the URL can't be transitioned to, the URL and history stay unchanged. |
    | `formData` | `FormData` | Sends the navigation as a POST with this body, the same path as an intercepted `<form>`. |
    | `info` | any | Passed to the `astro:before-preparation` and `astro:before-swap` events. |
    | `state` | any | Stored on the history entry and read back with `history.getState()`. |
    | `sourceElement` | `Element` | Exposed on the before-preparation and before-swap events. |

  - Server: `Astro.redirect(path, status?)` and `context.redirect()`. Status defaults to 302 on demand; static output uses `<meta http-equiv="refresh">` and ignores the status code. A page must `return` the redirect; a child component cannot redirect because of streaming.
  - Source: `reference/modules/astro-transitions.mdx`, `guides/view-transitions.mdx`, `reference/api-reference.mdx`.
- **Prefetching**: **Supported (opt-in, link-attribute based; fetches whole HTML documents, not data).**
  - Config `prefetch: boolean | { prefetchAll?, defaultStrategy? }`. It adds a prefetch script to every page.
  - Links opt in with `data-astro-prefetch` (bare attribute or a strategy value). Use `data-astro-prefetch="false"` to opt out when `prefetchAll` is on.
  - Works for same-site links only.
  - Implementation: `<link rel="prefetch">` when the browser supports it, otherwise `fetch()`. It relies on HTTP cache headers. Firefox needs explicit `Cache-Control`/`Expires`, or an `ETag`; Safari falls back to `fetch()` and needs cache headers.
  - Data-saver mode or a slow connection downgrades prefetching to `tap`. Quick hovers and scroll-bys don't trigger it.

  | strategy | trigger |
  |---|---|
  | `hover` (default `defaultStrategy`) | Hover or focus. |
  | `tap` | Just before the click. |
  | `viewport` | The link enters the viewport. |
  | `load` | All links after page load. |

  - `prefetchAll` defaults to `false`, **but to `true` on pages using `<ClientRouter />`**.
  - Programmatic: `prefetch(url, { ignoreSlowConnection?: boolean, eagerness?: 'immediate'(default)|'eager'|'moderate'|'conservative' })` from `astro:prefetch`, for client scripts only. `eagerness` applies only with **experimental `clientPrerender`**, which swaps prefetch for Speculation Rules `<script type="speculationrules">` prerendering and falls back where unsupported.
  - Source: `guides/prefetch.mdx`, `reference/configuration-reference.mdx`, `reference/experimental-flags/client-prerender.mdx`.
- **Scroll restoration**: **Partial (ClientRouter only).**
  - During the ClientRouter swap, "scroll position is restored if necessary" on history navigation.
  - `astro:after-swap` fires after the scroll is set, so it can override (e.g. `window.scrollTo(0,0)`).
  - Without the router, browser-native MPA behavior applies.
  - `swapFunctions.saveFocus()` restores focus to persisted elements.
  - Source: `guides/view-transitions.mdx`, `reference/modules/astro-transitions.mdx`.
- **View transitions**: **Supported (two modes).**
  - (a) Browser-native cross-document MPA view transitions. These add no JS (CSS only).
  - (b) `<ClientRouter />` from `astro:transitions`. It intercepts `<a>` clicks, back/forward and `<form>` GET/POST, fetches the next page's full HTML and swaps the DOM inside `document.startViewTransition`. Docs call this "SPA mode".
  - `<ClientRouter />` prop: `fallback: 'animate'(default)|'swap'|'none'`, for browsers without the View Transition API. `animate` simulates the transition, `swap` replaces instantly, `none` does a full page load. The `initial` animation is not simulated.
  - Directives:

    | directive | behavior |
    |---|---|
    | `transition:name="x"` | Pairs old and new elements explicitly. The name must be unique per page. By default pairs are inferred from element type and DOM position. |
    | `transition:animate` | Takes `fade` (default crossfade), `initial` (browser default), `slide` (reverses on back), `none` (on `<html>`, disables the default fade page-wide), `fade({duration})` or `slide({duration})`, or a custom `{forwards:{old,new}, backwards:{old,new}}` object of `{name, delay, duration, easing, fillMode, direction}`. |
    | `transition:persist` (optional name value) | Moves the element or island to the new DOM instead of replacing it, so **island state is kept**. Islands still re-render with the new page's props. CSS animations restart and iframes reload regardless. |
    | `transition:persist-props` | Also keeps the old props (no re-render). |

  - Link and form attributes:
    - `data-astro-reload` on `<a>` or `<form>` forces a full page load.
    - `data-astro-history="auto|push|replace"` on `<a>`.
    - `data-astro-rerun` on inline scripts re-executes them after every swap. Bundled module scripts run once only.
    - Forms submit as `multipart/form-data` by default; set `enctype` to change it. (v6 removed the `handleForms` prop.)
  - Lifecycle events on `document`, in order:
    1. `astro:before-preparation`: `info`, `sourceElement`, `navigationType: 'push'|'replace'|'traverse'`, writable `direction`, `from`, writable `to`, `formData`, overridable `loader()`.
    2. `astro:after-preparation`.
    3. `astro:before-swap`: `newDocument`, `viewTransition`, overridable `swap()`. It can't be cancelled.
    4. `astro:after-swap`: history and scroll are already updated.
    5. `astro:page-load`: also fires on the initial load. It replaces `DOMContentLoaded`.
  - Default swap: `deselectScripts`, `swapRootAttributes`, `swapHeadElements` (keeps stylesheets and scripts that also exist on the new page, plus persisted head elements), `saveFocus`, `swapBodyElement`. These are exposed as `swapFunctions` (4.15+) for custom swaps.
  - Helpers: `supportsViewTransitions`, `transitionEnabledOnThisPage()`.
  - Built in: a route announcer (`aria-live=assertive`; reads `<title>`, else the first `<h1>`, else the pathname) and a `prefers-reduced-motion` media query that disables all animations.
  - **Not compatible with `security.csp`.**
  - Source: `guides/view-transitions.mdx`, `reference/modules/astro-transitions.mdx`, `reference/configuration-reference.mdx`.
- **Route-level code splitting**: **Supported (automatic; island- and page-based).**
  - Each hydrated island's JS is loaded per its directive. A framework runtime is sent once per page.
  - Processed `<script>`s are bundled, deduplicated and sometimes inlined per page.
  - CSS is split into per-page chunks plus shared chunks. Chunks under 4 kB are inlined by default (`build.inlineStylesheets`, Vite `assetsInlineLimit`).
  - Each server island is split into its own route.
  - Source: `guides/framework-components.mdx`, `guides/client-side-scripts.mdx`, `guides/styling.mdx`, `guides/server-islands.mdx`.
- **Base path**: **Supported.**
  - `base` config, also settable with the CLI `--base`. Dev serves under the base too.
  - `import.meta.env.BASE_URL` and the `config.base` seen by integrations are normalized by `trailingSlash`: `'always'` adds a slash, `'never'` strips one.
  - **You must prefix `base` manually** in links and `public/` asset URLs. There is no link helper.
  - `paginate()` URLs include the base.
  - Source: `reference/configuration-reference.mdx`, `reference/routing-reference.mdx`.
- **Notable extras**:
  - **Rewrites**:
    - `Astro.rewrite(string|URL|Request)` and `context.rewrite()` render another route without changing the URL.
    - A rewrite triggers a **new full render phase that re-runs middleware**. In middleware, `next('/path')` instead rewrites in place without re-running middleware.
    - Rewriting to an unknown route gives a 404; a render error gives the overlay in dev and a 500 in prod.
    - Restrictions: `Astro.rewrite('/404')` is allowed only on on-demand pages (`InvalidRewrite404`). An on-demand route can't be rewritten to a prerendered route in `server` output (`ForbiddenRewrite`). You can't rewrite after the request body has been read; clone it first (`RewriteWithBodyUsed`).
    - `Astro.originPathname` (5.0) gives the pre-rewrite path.
  - **Built-in pagination**:
    - `paginate(data, { pageSize=10, params, props, format(url) })`. `format` arrived in 7.1.
    - The `page` prop has `data`, `start`, `end`, `size`, `total`, `currentPage`, `lastPage` and `url.{current, prev, next, first, last}`.
    - `[page].astro` produces `/1`, `/2`…; `[...page].astro` produces `/`, `/2`….
    - Nested pagination works by returning multiple `paginate()` results.
  - **`trailingSlash: 'ignore'(default)|'always'|'never'`** applies to dev and on-demand routes. Prod redirects use 301 for GET and 308 otherwise; dev shows a warning page. Prerendered pages follow the host's rules. Endpoints with a file extension never take a trailing slash. `build.format` (`directory`(default)|`file`|`preserve`) changes output files and `Astro.url`.
  - **Page partials**: `export const partial = true` outputs HTML with no doctype or head (scoped styles and scripts stripped), meant for htmx/Unpoly. Not available for `.md`.
  - `Astro.routePattern` (e.g. `/en/blog/[slug]`).
  - `RouteData` and the `astro:routes:resolved` hook for integrations.
  - i18n routing exists (out of scope).
  - Source: `guides/routing.mdx`, `reference/api-reference.mdx`, `reference/routing-reference.mdx`, `basics/astro-pages.mdx`, `reference/configuration-reference.mdx`.

## 2. Rendering modes

- **SSR (on-demand rendering)**: **Supported, requires an adapter.**
  - Default `output: 'static'` prerenders everything.
  - Per page, `export const prerender = false` opts into on-demand rendering. `output: 'server'` flips the default, and `export const prerender = true` opts back out. The docs note that `'server'` "does not bring any additional functionality".
  - On-demand pages get cookies, `Astro.request` with full headers/body/search params, `clientAddress`, sessions, `Astro.response` status and headers, can return `Response` objects directly, and get `Astro.cache`.
  - Source: `guides/on-demand-rendering.mdx`, `reference/routing-reference.mdx`.
- **Streaming SSR**: **Supported (HTML streaming, in-order; no Suspense/out-of-order).**
  - On-demand pages stream "each component to the browser as it renders them".
  - A top-level `await` in page frontmatter blocks the whole document. Moving awaits into child components lets the shell flush first.
  - **Sibling async components fetch in parallel and stream in document order.**
  - Consequence: anything that changes response headers (status, headers, cookies, redirects) must run in the **page**, not in components or layouts (`ResponseSentError`).
  - Opt-outs:
    - `createApp({ streaming: false })` (adapter API)
    - `@astrojs/node` `experimentalDisableStreaming`
    - `@astrojs/react` `experimentalDisableStreaming` (for CSS-in-JS)
  - The Solid integration wraps components in Suspense and uses `renderToStringAsync`, so `createResource` data is in the initial HTML.
  - **Deferred holes** come from server islands (below), not from in-stream placeholders.
  - Source: `guides/on-demand-rendering.mdx`, `recipes/streaming-improve-page-performance.mdx`, `reference/modules/astro-app.mdx`, `guides/integrations-guide/node.mdx`, `guides/integrations-guide/react.mdx`, `guides/integrations-guide/solid-js.mdx`.
- **Static pre-rendering incl. dynamic params**: **Supported (default).**
  - `getStaticPaths()` with `params`/`props`, plus `paginate()`. Endpoints can be prerendered to files (e.g. `data.json.ts` → `/data.json`).
  - `build.concurrency` (default 1, stable but "breaking changes possible" in minor releases).
  - **Experimental**:
    - `parallelPrerender` (`true | { workers }`) renders with worker threads. Module-level state is not shared, props must be serializable, and it is ignored by Cloudflare's custom prerenderer.
    - `incrementalBuild` reuses previous output when a `cacheKey` returned from `getStaticPaths()` matches and the module dependency graph hash is unchanged. Loaders' `digest` can be used as the key.
    - `collectionStorage` (`'single-file'|'chunked'|{type:'chunked',chunkSize}`).
  - Adapters can provide a custom prerenderer (`setPrerenderer()`, e.g. Cloudflare prerenders in `workerd`; `prerenderEnvironment: 'node'` opts out).
  - Source: `reference/routing-reference.mdx`, `guides/endpoints.mdx`, `reference/experimental-flags/*.mdx`, `reference/adapter-reference.mdx`, `guides/integrations-guide/cloudflare.mdx`.
- **Client-only / SPA routes and full SPA mode**: **Partial.**
  - Per component, `client:only="react|vue|svelte|solid-js|preact…"` skips SSR. The framework name is required, and a `slot="fallback"` child shows until the component loads.
  - There is no "SPA mode" output and no client-only route type. `<ClientRouter />` (docs: "SPA mode") gives client-side navigation, but every page is still rendered server- or build-side as HTML.
  - Embedding a whole SPA inside one island is described as possible.
  - Source: `reference/directives-reference.mdx`, `guides/view-transitions.mdx`, `concepts/islands.mdx`.
- **Partial hydration**: **Supported (core architecture).**
  - **Client islands**: UI framework components render to static HTML by default with no JS. Adding `client:*` hydrates that component alone.
  - Islands hydrate independently and in parallel, and different frameworks can be mixed on one page (only inside `.astro` files).
  - Props to hydrated islands are serialized. Supported types: plain object, number, string, Array, Map, Set, RegExp, Date, BigInt, URL, Uint8/16/32Array, Infinity. **Not supported: functions and circular structures.** Render props don't work; use named slots.
  - Children are passed as slots: React/Preact/Solid get a `children` prop and camelCased named-slot props; Vue/Svelte use `<slot name>`. React receives children as plain strings unless `experimentalReactChildren` is set.
  - **Astro components cannot be hydrated or imported into framework components.**
  - **Server islands**: `server:defer` on an Astro component renders it on demand separately. Details below.
  - Source: `concepts/islands.mdx`, `guides/framework-components.mdx`, `guides/integrations-guide/react.mdx`.
- **Static shell with dynamic holes (PPR-like)**: **Supported via server islands** (needs an adapter even if the page is prerendered; `NoAdapterInstalledServerIslands`).
  - At build time, the component is replaced by a small script plus any `slot="fallback"` content.
  - In the browser, each island fetches its HTML independently from a special route (`/_server-islands/<Name>`). A slow island doesn't block others.
  - Props travel **encrypted in a GET query string**, so the response is cacheable with `Cache-Control`. If the URL would exceed 2048 bytes, Astro switches to POST, which is not cached.
  - Prop serialization uses the same type list as client islands (no functions).
  - `security.serverIslandBodySizeLimit` defaults to 1 MB.
  - Inside an island, `Astro.url` is the island endpoint. To see the page URL, read the `Referer` header.
  - The encryption key is generated per build. Use `astro create-key` and the `ASTRO_KEY` env var to keep it stable across rolling deploys, multi-region hosting or CDN-cached pages.
  - Source: `guides/server-islands.mdx`, `reference/directives-reference.mdx`, `reference/configuration-reference.mdx`.
- **Per-route rendering-mode control**: **Supported.**
  - `export const prerender = true|false` must be statically analyzable: exactly `export const prerender = <literal>`, otherwise `InvalidPrerenderExport`.
  - Global default via `output`.
  - Integrations can set it with the `astro:route:setup` hook (`route.prerender`) or `injectRoute({ prerender })`. If the final value is undefined, the `output` default applies.
  - `export const partial = true` makes a page a fragment. It can be a boolean literal or an `import.meta.env` var.
  - `Astro.isPrerendered` (5.0) is available at runtime.
  - Source: `reference/routing-reference.mdx`, `reference/integrations-reference.mdx`, `reference/errors/invalid-prerender-export.mdx`.
- **Hydration strategies**: **Supported (directive per component instance).**

  | directive | value | when JS loads/hydrates |
  |---|---|---|
  | `client:load` | — | Immediately on page load (high priority). |
  | `client:idle` | optional `{{timeout: ms}}` | After initial load, on `requestIdleCallback` (falls back to `load`). `timeout` forces hydration after N ms. |
  | `client:visible` | optional `{{rootMargin: '200px'}}` | When the element (plus margin) enters the viewport (IntersectionObserver). |
  | `client:media` | media query string | When the media query matches. |
  | `client:only` | framework name (required) | No SSR; render and hydrate on load. Supports a `slot="fallback"`. |
  | custom `client:*` | — | Registered by integrations via `addClientDirective({name, entrypoint})`. Entrypoints are bundled with esbuild and should stay small. |
  | `server:defer` | — | Server island (see above). Supports a `slot="fallback"`. |

  Directives only work on framework components imported directly into `.astro`. They don't work on dynamic tags or on components passed via the MDX `components` prop. Source: `reference/directives-reference.mdx`, `reference/integrations-reference.mdx`.
- **Notable extras**:
  - **Plain `<script>` tags** in `.astro` are processed by default: TypeScript, npm imports bundled, `type="module"`, deduplicated per page, small ones inlined. Any attribute other than `src` makes the script `is:inline` (unprocessed). This is a no-framework interactivity path.
  - `define:vars` passes frontmatter values to `<style>`/`<script>`. On scripts it implies `is:inline`.
  - **Whitespace**: v7 default `compressHTML: 'jsx'` strips inter-element whitespace like React. `true` gives lossless HTML-aware compression; `false` preserves everything.
  - The Rust compiler (v7) passes invalid HTML through as-is rather than auto-correcting it.
  - Source: `guides/client-side-scripts.mdx`, `reference/directives-reference.mdx`, `reference/configuration-reference.mdx`, `guides/upgrade-to/v7.mdx`.

## 3. Data loading

- **Where data is fetched**: **Supported (component frontmatter; no loader abstraction).**
  - Any `.astro` component's frontmatter (`---` block) runs **on the server only**, with top-level `await` and global `fetch()`. It runs **at build time for prerendered pages** ("data fetched once, at build time"; on component refresh in dev) and **at request time for on-demand pages**.
  - Other sources:
    - Build-time content collections: `getCollection()`, `getEntry()`, `render()`.
    - Live collections, fetched per request: `getLiveCollection()`, `getLiveEntry()`. They need an adapter, are defined in `src/live.config.ts`, and have no built-in loaders.
    - `import.meta.glob()`.
    - `getStaticPaths()` props for static routes.
    - Framework components can fetch on the client. On the server, Solid can use `createResource`.
  - No `loader`/`load` export, and no `useLoaderData`.
  - Source: `guides/data-fetching.mdx`, `guides/content-collections.mdx`, `guides/integrations-guide/solid-js.mdx`.
- **Loader execution model**: **Implicit render tree.**
  - Page frontmatter runs first and can redirect or return a `Response`. Children (layouts are children) render afterwards in template order while HTML streams. Async siblings resolve in parallel and output in order.
  - No separate server and client loaders, and no route-level parallel loaders. `getStaticPaths()` runs once per route at build, isolated from the page scope.
  - Middleware runs before rendering and can pre-load into `locals`.
  - Source: `recipes/streaming-improve-page-performance.mdx`, `guides/routing.mdx`, `reference/routing-reference.mdx`.
- **Request deduplication**: **Not found in docs.**
- **Passing server data to client components**: **Supported (serialized props).**
  - Props on `client:*` islands are serialized into `<astro-island>` `props` attributes (type list in area 2).
  - Plain scripts read server data through `data-*` attributes or `define:vars`. `getImage()` URLs must be computed in frontmatter and passed down (it throws on the client).
  - Recommended for cross-island client state: **Nano Stores**. Writing to a store in frontmatter does not reach the client.
  - Source: `guides/framework-components.mdx`, `guides/client-side-scripts.mdx`, `recipes/sharing-state-islands.mdx`.
- **Client-side data cache**: **Not supported / not found.**
  - There is no client data layer. ClientRouter navigations re-fetch full HTML, relying only on the HTTP cache and prefetch.
  - Source: `guides/view-transitions.mdx`, `guides/prefetch.mdx`.
- **Deferred / streamed data**: **Partial.**
  - In-order HTML streaming of async components.
  - Server islands provide deferred fragments with fallback content, fetched by the client.
  - `set:html` accepts `Promise<string>` or `Promise<Response>` (e.g. streaming in fetched HTML).
  - No promise-passing from server to client (no `defer()`/`<Await>`).
  - Source: `guides/on-demand-rendering.mdx`, `guides/server-islands.mdx`, `reference/directives-reference.mdx`.
- **Dependency tracking & invalidation**: **Not supported for render data.**
  - Related mechanisms:
    - Route-cache tags and `cache.invalidate()` (area 5).
    - Live-loader `cacheHint` (tags, lastModified).
    - Content-loader `digest`.
    - Experimental incremental builds (`cacheKey` plus module-graph hash).
  - Source: `guides/caching.mdx`, `guides/content-collections.mdx`, `reference/experimental-flags/incremental-build.mdx`.
- **Access to request context**: **Supported.**
  - The `Astro` global in every `.astro` component, and the same object as `context` in endpoints and middleware.
  - Prerendered pages get no search params, no cookies, no `clientAddress` and no session.
  - Full table in area 6.
  - Source: `reference/api-reference.mdx`.
- **Notable extras**:
  - Calling an endpoint's `GET` directly from server code avoids an HTTP hop (recipe).
  - `Astro.callAction(action, input)` reuses action logic server-side.
  - **Live collections error model**: `getLiveEntry()` returns `{entry, error, cacheHint}`. Errors are `LiveEntryNotFoundError`, `LiveCollectionValidationError`, `LiveCollectionCacheHintError` or `LiveCollectionError`. Zod schemas validate at runtime.
  - Source: `recipes/call-endpoints.mdx`, `guides/actions.mdx`, `guides/content-collections.mdx`.

## 4. Mutations

- **Server functions / RPC / actions**: **Supported — Astro Actions** (`astro:actions`, since 4.15).
  - Defined as `export const server = { name: defineAction({...}) }` in `src/actions/index.ts`. Actions can be nested into groups (`actions.user.getUser`).
  - Called from client scripts or islands as `await actions.name(input)`, which returns a `SafeResult`.
  - **Requires server output (an adapter)** (`ActionsWithoutServerOutputError`).
  - Each action is a public POST endpoint at `/_actions/<name>` (e.g. `/_actions/blog.like`). Docs warn that you must authorize inside handlers.
  - Return values are serialized with **devalue**: JSON plus Date, Map, Set and URL.
  - Calling an action function directly from server code throws (`ActionCalledFromServerError`); use `Astro.callAction()` or `context.callAction()`.
  - `defineAction()` options:

    | option | values / default | behavior |
    |---|---|---|
    | `handler(input, context)` | required | Server logic. `context` is `ActionAPIContext` = APIContext **minus** `callAction`, `getActionResult`, `props`, `redirect`. Returning `undefined` is discouraged in favour of throwing `ActionError`. |
    | `input` | Zod schema (`astro/zod`, Zod 4), optional | Validated before the handler runs. On failure the handler is skipped and a `BAD_REQUEST` `ActionError` is returned. Without `input`, the handler gets `unknown` (JSON) or a raw `FormData` (form). |
    | `accept` | `'json'`(default) \| `'form'` | With `'form'`, a `z.object()` input auto-parses FormData by input `name`. `.refine/.transform/.pipe` and `z.discriminatedUnion()` are supported. |

  - Client API (`ActionClient`):
    - Call it as a function to get `{data, error}`.
    - `.orThrow(input)` returns the data directly and throws on error.
    - `.queryString` builds form `action` URLs.
    - `getActionPath(action)` (5.1) lets you call the action via `fetch()` or `sendBeacon` with custom headers or `keepalive`.
    - `ACTION_QUERY_PARAMS` gives the internal query-param names.
  - Types: `ActionReturnType`, `ActionInputSchema` (5.16), `SafeResult`, `ActionErrorCode`.
  - The `astro:actions` types require `astro sync` or a dev restart to update.
  - Source: `guides/actions.mdx`, `reference/modules/astro-actions.mdx`, `reference/errors/action-called-from-server-error.mdx`, `reference/errors/actions-without-server-output-error.mdx`.
- **Form handling without JS (progressive enhancement)**: **Supported.**
  - Use `<form method="POST" action={actions.x}>`. The `action` attribute becomes a `?_astroAction=` query string handled by the server, and the page then re-renders.
  - **The page must be on-demand rendered.** GET forms throw `ActionsUsedWithForGetError`.
  - The page reads the outcome with `Astro.getActionResult(actions.x)`, which returns `{data}`, `{error}`, or `undefined` if the action was not called this request.
  - File uploads need `enctype="multipart/form-data"`.
  - Form field coercion:
    - `number` inputs map to `z.number()`.
    - Checkboxes map to `z.coerce.boolean()`.
    - `file` inputs map to `z.instanceof(File)`.
    - Repeated names map to `z.array()`.
    - Everything else maps to `z.string()`.
    - **Empty inputs become `null`** (except arrays and booleans).
  - **Inputs are cleared on submit.** Keep values with ClientRouter plus `transition:persist` on the inputs.
  - Results live in the POST response only. On refresh the browser shows "confirm resubmission", and on revisit the result is `undefined`.
  - **POST/Redirect/GET is DIY.** In middleware, `getActionContext(context)` returns:
    - `action`: `{calledFrom: 'rpc'|'form', name, handler()}`.
    - `setActionResult(name, serialized)`, which disables Astro's own result handling.
    - `serializeActionResult()` and `deserializeActionResult()`.
  - Docs give an example that persists results in a session and redirects.
  - React: `withState(action)` (with `useActionState`) and `getActionState(ctx)` from `@astrojs/react/actions` "preserve metadata used for progressive enhancement".
  - With ClientRouter, `<form>` submits (GET and POST) become client-side navigations. `data-astro-reload` opts a form out.
  - Source: `guides/actions.mdx`, `reference/modules/astro-actions.mdx`, `guides/integrations-guide/react.mdx`, `guides/view-transitions.mdx`, `reference/errors/actions-used-with-for-get-error.mdx`.
- **Pending, error and validation-error state**: **Partial.**
  - Errors:
    - `ActionError({ code, message? })`: `code` is a human-readable HTTP status (e.g. `'UNAUTHORIZED'`, `'NOT_FOUND'`, `'PAYLOAD_TOO_LARGE'`) and sets the response status.
    - `isActionError()`.
    - `isInputError(error)` gives `error.fields[name]` messages when `input` is a `z.object()`.
  - No built-in pending state except React's `useActionState` `pending` via `withState`.
  - Source: `reference/modules/astro-actions.mdx`, `guides/integrations-guide/react.mdx`.
- **Optimistic UI**: **Not found in docs.**
- **Data refresh after a mutation**: **Manual.**
  - A form action re-renders the target page on the server, so data is naturally fresh.
  - An RPC call refreshes nothing; you update the UI yourself or `navigate()`.
  - To purge route cache, call `cache.invalidate({tags|path})` (available on `context` in endpoints; actions get a subset of `APIContext` that is not documented as excluding `cache` (inferred)).
  - Source: `guides/actions.mdx`, `guides/caching.mdx`.
- **Redirects after a mutation**: **Supported.**
  - Server: in the page, `if (result && !result.error) return Astro.redirect(...)`. Actions themselves can't redirect (`redirect` is excluded from `ActionAPIContext`).
  - Client: `navigate('/path')`.
  - PRG pattern via middleware (above).
  - Source: `guides/actions.mdx`.
- **File uploads**: **Supported.**
  - `z.instanceof(File)` validation.
  - `security.actionBodySizeLimit` defaults to 1 MB (1048576), configurable.
  - Node adapter `bodySizeLimit` defaults to 1 GB (`Infinity`/`0` disables).
  - Source: `guides/actions.mdx`, `reference/configuration-reference.mdx`, `guides/integrations-guide/node.mdx`.
- **Multiple actions per page**: **Supported.**
  - One form per action, each with its own `Astro.getActionResult(actions.x)`. `z.discriminatedUnion()` handles one form with multiple intents.
  - Source: `guides/actions.mdx`.
- **CSRF protection built in**: **Supported (origin check).**
  - `security.checkOrigin` is on by default (since 4.9).
  - It applies only to on-demand pages, for unsafe methods (POST/PATCH/PUT/DELETE) whose `content-type` is missing, `application/x-www-form-urlencoded`, `multipart/form-data` or `text/plain`.
  - It compares `Sec-Fetch-Site` (falling back to `Origin`) with the request URL. A cross-origin request gets **403** and the page isn't rendered.
  - `security.allowedDomains` protects `X-Forwarded-Host` from spoofing.
  - Source: `reference/configuration-reference.mdx`.
- **Notable extras**:
  - Gating all actions in middleware with `getActionContext()`.
  - `Astro.callAction()` for server reuse.
  - Plain endpoints (`POST` exports) remain an alternative for form handling (`recipes/build-forms-api.mdx`).
  - v6 removed `rewrite()` from the actions context.
  - Source: `guides/actions.mdx`, `guides/upgrade-to/v6.mdx`.

## 5. Caching & revalidation

- **Page/HTML caching (core route caching)**: **Supported, stable since v7.0. On-demand pages and endpoints only.**
  - Enable with `cache: { provider }` in config. Built-in `memoryCache()` comes from `astro/config`.
  - Per request: `Astro.cache` (pages) or `context.cache` (endpoints and middleware):

    | member | behavior |
    |---|---|
    | `cache.enabled` | `false` with no provider **or in dev**; `true` in production with a provider. |
    | `cache.set(options \| false)` | Sets or merges options for this response. `false` opts out (e.g. overrides a route rule). |
    | `cache.options` | Read-only merged snapshot. |
    | `cache.tags` | Read-only accumulated tags. |
    | `cache.invalidate({ path?, tags? })` | Purges entries. Path is **exact match only**, no globs. Tags purge any entry having any of them. Requires a provider. |

  - `CacheOptions`: `maxAge` (s), `swr` (s, stale-while-revalidate), `tags: string[]`, `lastModified: Date`, `etag: string`.
  - **Merge rules across multiple `set()` calls**: `maxAge`/`swr`/`etag` are last-write-wins, `lastModified` takes the most recent date, and `tags` accumulate. "Middleware, layouts, content loaders, and page code can each contribute".
  - Without a provider, `set()`, `tags` and `options` log a warning and `invalidate()` throws. `Astro.cache` without the feature enabled throws `CacheNotEnabled`.
  - **Dev**: the API is present but does nothing. Test with build + preview.
  - Source: `guides/caching.mdx`, `reference/api-reference.mdx`, `reference/errors/cache-not-enabled.mdx`.
- **Config-level rules**: `routeRules: { '<pattern>': { maxAge, swr, tags } }`.
  - Patterns use file-route syntax (`/about`, `/products/[id]`, `/docs/[...path]`) and the **same priority rules**. Glob `*` is not allowed.
  - Per-route `cache.set()` merges with or overrides the rule.
  - Source: `guides/caching.mdx`, `reference/configuration-reference.mdx`.
- **Providers**:
  - **Runtime providers** implement `onRequest(ctx, next)`. They cache in-process, add `X-Astro-Cache: HIT|MISS|STALE`, and can use `ctx.waitUntil` for background revalidation.
  - **CDN providers** implement `setHeaders(options, request)`. Those platform headers are stripped from the client response.
  - `memoryCache({ max = 1000, query: { sort = true, include?, exclude = [utm_*, fbclid, gclid, …, ref] } })` is an in-memory LRU for single-instance deploys. `include` and `exclude` are mutually exclusive (`CacheQueryConfigConflict`).
  - Memory provider cache key: URL with sorted query, tracking params removed, plus a variant per `Vary` request header. **`Cookie` is always ignored for Vary.**
  - **Experimental adapter CDN providers**:
    - `cacheNetlify()`: `Netlify-CDN-Cache-Control` and `Netlify-Cache-Tag`, durable cache.
    - `cacheVercel()`: `Vercel-CDN-Cache-Control` and `Vercel-Cache-Tag`. Tag purge is a soft, SWR-style invalidation.
    - `cacheCloudflare()`: `Cloudflare-CDN-Cache-Control` and `Cache-Tag`, and enables Workers Cache.
    - All three auto-tag responses by path so `invalidate({path})` works on tag-only platforms. They must be enabled manually for now.
  - Custom provider: a runtime module default-exporting `CacheProviderFactory(config) → { name, invalidate(), setHeaders?, onRequest? }`, plus a config helper returning `{ entrypoint, config }`.
  - Utilities in `astro/cache/provider-utils`: `buildCacheControlDirectives`, `pathTag` (`astro-path:{path}`), `setConditionalHeaders` (sets ETag and Last-Modified), `collectInvalidationTags`, `normalizeTags`.
  - Source: `reference/cache-provider-reference.mdx`, `guides/caching.mdx`.
- **Time-based revalidation (ISR)**: **Supported for on-demand routes.**
  - Core: `maxAge` + `swr` via route caching.
  - Prerendered pages are only refreshed by rebuilding. Experimental `incrementalBuild` speeds up rebuilds; there is no runtime ISR for prerendered output.
  - Adapter-level options:
    - Vercel `isr: true | { expiration, bypassToken, exclude }`. It caches on-demand pages like static ones after the first request. Middleware runs only on a miss unless `middlewareMode: 'edge'`. ISR requests get no search params.
    - Netlify `cacheOnDemandPages` (up to one year, overridable with headers).
  - Source: `guides/caching.mdx`, `guides/integrations-guide/vercel.mdx`, `guides/integrations-guide/netlify.mdx`.
- **On-demand revalidation (path / tag)**: **Supported.**
  - `cache.invalidate({ path })` (exact) or `({ tags })` from endpoints, middleware or pages.
  - Live-collection entries can be passed directly (`cache.invalidate(entry)`), and `cache.set(cacheHint | LiveDataEntry)` applies loader hints. Collection-level hints merge tags and take the most recent `lastModified`.
  - Vercel ISR: GET or HEAD with an `x-prerender-revalidate: <bypassToken>` header.
  - Source: `guides/caching.mdx`, `guides/content-collections.mdx`, `guides/integrations-guide/vercel.mdx`.
- **Data-level / function-level caching**: **Not supported** (no `cache()`/`"use cache"` equivalent).
  - Related: the content layer caches build-time collections in `.astro/data-store.json`. Asset caches persist optimized images in `cacheDir` (`node_modules/.astro`) between builds, and remote images respect `Cache-Control` with `ETag`/`Last-Modified` revalidation (5.1+). Font caches live in `.astro/fonts` and `node_modules/.astro/fonts`.
  - Source: `guides/images.mdx`, `guides/fonts.mdx`, `reference/experimental-flags/collection-storage.mdx`.
- **Client navigation cache**: **Not supported** beyond the browser HTTP cache used by prefetch and ClientRouter fetches. Source: `guides/prefetch.mdx`.
- **HTTP cache-header helpers**: **Partial.**
  - `Astro.response.headers.set('Cache-Control', …)` is page-level only.
  - Route caching emits headers and conditional headers (`etag`, `lastModified`) through providers.
  - Server-island GET responses can be cached with `Cache-Control`.
  - Node and Cloudflare adapters add long-lived cache headers to hashed `_astro/` assets.
  - Source: `guides/on-demand-rendering.mdx`, `reference/cache-provider-reference.mdx`, `guides/server-islands.mdx`, `guides/integrations-guide/node.mdx`.
- **Preview / draft-mode bypass**: **Not in core.**
  - Vercel adapter: Draft Mode with a `__prerender_bypass` cookie equal to `bypassToken`.
  - Source: `guides/integrations-guide/vercel.mdx`.
- **Notable extras**:
  - The caching pipeline stage `cache()` is exposed in `astro/fetch` for custom pipelines.
  - Prefetch effectiveness depends on cache headers (Firefox and Safari caveats).
  - Source: `reference/modules/astro-fetch.mdx`, `guides/prefetch.mdx`.

## 6. Server & API

- **API routes / endpoints**: **Supported.**
  - `.js`/`.ts` files in `src/pages/` export functions named after any HTTP method (`GET`, `POST`, …) or **`ALL`** as a catch-all. Each receives `APIContext` and returns a `Response`.
  - `HEAD` is auto-derived from `GET` (body stripped). An unmatched method falls through to the 404 page.
  - Static mode: called at build to emit files; the name carries the extension (`rss.xml.js` → `/rss.xml`). Static endpoints see only `request.url`. Prerendered dynamic endpoints use `getStaticPaths()` and can take `props`.
  - On demand (`prerender = false`): full request, params without `getStaticPaths()`, and `props` not supported.
  - Endpoint URLs with an extension never match a trailing slash.
  - `APIRoute` type; `PrerenderDynamicEndpointPathCollide` error when an `undefined` param would collide.
  - Source: `guides/endpoints.mdx`, `reference/errors/prerender-dynamic-endpoint-path-collide.mdx`.
- **Middleware**: **Supported (single global chain; integration-added pre/post; optional edge deployment).**
  - File: `src/middleware.(js|ts)` or `src/middleware/index.(js|ts)`, exporting a named `onRequest(context, next)` (not a default export). It must return a `Response`, either directly or from `next()`; otherwise `MiddlewareNoDataOrNextCalled`.
  - Helpers: `defineMiddleware()` (typing) and `sequence(...handlers)` (onion order: `a → b → c → page → c → b → a`).
  - `next(rewritePayload?)` rewrites in place without re-running middleware. The request is re-created, so you **can't consume the body** (it breaks HTML-form actions).
  - Middleware can mutate `locals`, short-circuit with a `Response`, and post-process the response (e.g. rewrite the HTML body).
  - **Runs at build time for prerendered pages** (classic mode) and per request for on-demand pages. Use `context.isPrerendered` to avoid header access.
  - Also attempts to run for 404 pages (adapter-dependent) and before 500 pages, unless the middleware itself failed.
  - No per-route middleware config: branch on `context.url`/`routePattern`, or use Hono route-scoped middleware in `src/fetch.ts`.
  - Integrations: `addMiddleware({ entrypoint, order: 'pre'|'post' })`.
  - Adapter feature `middlewareMode: 'classic'(default)|'edge'`:
    - Netlify edge: runs for **all** requests, including static assets and prerendered pages.
    - Vercel edge: runs for on-demand routes, including ISR cache hits.
    - In both, `locals` is JSON-serialized into a header to the function, and the function returns 403 to requests that did not come from the edge function.
  - Low-level: `createContext()` and `trySerializeLocals()` from `astro/middleware`.
  - Source: `guides/middleware.mdx`, `reference/modules/astro-middleware.mdx`, `reference/integrations-reference.mdx`, `reference/adapter-reference.mdx`, `guides/integrations-guide/netlify.mdx`, `guides/integrations-guide/vercel.mdx`.
- **Request context** (`Astro.*` and `context.*`): **Supported.**

  | member | notes |
  |---|---|
  | `request` | Standard `Request`. On prerendered pages there is no search params and endpoints see only `url`. |
  | `url` | Normalized `URL`. localhost in dev; built from `site` + `base` during build. |
  | `params` | Matched segments. |
  | `props` | Component props, or `getStaticPaths` props. |
  | `site` | `URL \| undefined`. |
  | `generator` | `"Astro vX"`. |
  | `clientAddress` | On-demand only; throws on prerendered pages. Supplied by the adapter from a trusted source. |
  | `isPrerendered` (5.0) | — |
  | `routePattern` (5.0) | — |
  | `originPathname` (5.0) | Path before rewrites. |
  | `locals` | Request-scoped object; the guide says it may hold any value, including functions and Maps. Mutate it, don't reassign it (`LocalsReassigned`). The error reference also lists a dev-only `LocalsNotSerializable`, which contradicts the guide; it is probably tied to locals serialization (e.g. edge middleware) (unverified). |
  | `cookies` | `get(key, {decode})` returns `AstroCookie{value, json(), number(), boolean()}`; `has`; `set(key, value, {domain, expires, httpOnly, maxAge, path, partitioned (5.17), sameSite, secure, encode})`; `delete`; `merge`; `headers()`; `consume()` (6.3). On-demand routes only. |
  | `response` | `{status, statusText, headers}`. Page-level only; `headers` can't be replaced (`AstroResponseHeadersReassigned`). |
  | `redirect(path, status?)` | — |
  | `rewrite(payload)` | — |
  | `session` | Out of scope. |
  | `csp` | `insertDirective`, `insertScriptResource/Hash`, `insertStyleResource/Hash`, with `kind` scoping (7.1). |
  | `cache` | See area 5. |
  | `logger` (7.0) | `info`/`warn`/`error`. |
  | `getActionResult()`, `callAction()` | Actions. |
  | `preferredLocale`, `preferredLocaleList`, `currentLocale` | i18n. |

  Source: `reference/api-reference.mdx`, `reference/errors/*`.
- **Advanced routing / custom pipeline** (stable since v7.0): **Supported.**
  - `src/fetch.ts` default-exports `{ fetch(request): Response }` or a Hono app. Rename it with `fetchFile` (default `'fetch'`, `null` disables). It also accepts `.js`, `.mjs` and `.mts`.
  - The default pipeline order is: trailing-slash, redirects, sessions, actions, user middleware, page rendering, i18n, caching.
  - Handlers in `astro/fetch` (Hono-middleware versions in `astro/hono`) all operate on a `FetchState`:

    | handler | behavior |
    |---|---|
    | `astro(state)` | Full default pipeline. |
    | `trailingSlash(state)` | Returns a redirect `Response` or `undefined`. |
    | `redirects(state)` | Config redirects. Returns a `Response` or `undefined`. |
    | `sessions(state)` | Registers the provider (lazy session). |
    | `actions(state)` | Returns a `Response` for RPC calls, `undefined` for form actions and non-action requests. |
    | `middleware(state, next)` | Runs `src/middleware`. |
    | `pages(state)` | Renders the matched page or endpoint. |
    | `notFound(state)` (7.4) | Renders a custom 404 for unmatched routes. Returns 400 for over-encoded paths, `undefined` if the route matched. |
    | `i18n(state, response)` | Post-processing. |
    | `cache(state, next)` | Wraps a render with the cache provider. |

  - `FetchState` fields: `request`, `url`, `pathname` (base-stripped, decoded), `routeData`, `cookies`, `locals`, `params`, writable `status`, `response`, and `rewrite()`.
  - **Security caveat from the docs**: don't authorize by string-matching the pathname in pre-processing, because the matched route can differ. Use a router (Hono) that owns matching.
  - The Cloudflare adapter ships companion handlers for this mode.
  - Source: `guides/routing.mdx`, `reference/modules/astro-fetch.mdx`, `reference/modules/astro-hono.mdx`, `guides/integrations-guide/cloudflare.mdx`.
- **Streaming responses and SSE**: **Partial / not explicitly documented.**
  - Pages stream HTML. Endpoints return a standard `Response`, so streaming bodies should work (inferred, not documented).
  - No SSE helper or example was found.
  - Source: `guides/endpoints.mdx`.
- **Running work after the response (`waitUntil`/`after`)**: **Partial (not a user-level core API).**
  - Adapters can pass `waitUntil` into `app.render(request, { waitUntil })` (6.2), and it is exposed to cache providers' `onRequest`.
  - Cloudflare exposes `Astro.locals.cfContext.waitUntil()`.
  - Source: `reference/modules/astro-app.mdx`, `reference/cache-provider-reference.mdx`, `guides/integrations-guide/cloudflare.mdx`.
- **Server-only code boundaries**: **Partial (by construction; no `server-only`/`.server` convention).**
  - `.astro` frontmatter, endpoints, middleware and actions never ship to the client.
  - Client-exposed env vars need the `PUBLIC_` prefix, and `astro:env` supports `context: 'server'` and `access: 'secret'`. `astro:env` imports fail outside the Astro context (`astro.config`, scripts).
  - Some modules throw on the client (`getImage()`; `ServerOnlyModule` error).
  - Source: `guides/environment-variables.mdx`, `reference/modules/astro-assets.mdx`, `reference/errors/server-only-module.mdx`.
- **Notable extras**:
  - **Security config**:

    | key | default | behavior |
    |---|---|---|
    | `security.checkOrigin` | `true` | CSRF origin check (area 4). |
    | `security.allowedDomains` | `[]` | Allowed `X-Forwarded-Host` patterns (`*.` = one level, `**.` = any depth, `{}` = all). Unconfigured means the header is ignored. |
    | `security.actionBodySizeLimit` | 1 MB | — |
    | `security.serverIslandBodySizeLimit` | 1 MB | — |
    | `security.csp` | `false` | Hash-based CSP (6.0). |

  - **CSP details**:
    - Adds a `<meta http-equiv="content-security-policy">` with auto-hashed `script-src`/`style-src`, or a real header via the adapter `staticHeaders` feature.
    - Options: `algorithm` (SHA-256/384/512), `directives[]`, `scriptDirective` and `styleDirective` (`{resources, hashes, strictDynamic}`, with `kind: element|attribute|default`).
    - Limitations: not in dev; no `<ClientRouter />`; no Shiki; external scripts need manual hashes; `'unsafe-inline'` suppresses hashes.
  - `Astro.locals` typing via `App.Locals`.
  - Programmatic adapter runtime API: `createApp()` → `app.render(request, {addCookieHeader, clientAddress, locals, prerenderedErrorPageFetch, waitUntil, routeData})`, `app.match()`.
  - Source: `reference/configuration-reference.mdx`, `reference/api-reference.mdx`, `reference/modules/astro-app.mdx`.

## 7. Loading & error states

- **Route-level loading UI**: **Not supported as a convention.**
  - Alternatives:
    - Server-island and `client:only` `slot="fallback"`.
    - ClientRouter events: show a spinner in `astro:before-preparation` and hide it in `astro:after-preparation`, or wrap `event.loader()` for async work.
  - Source: `guides/server-islands.mdx`, `reference/directives-reference.mdx`, `guides/view-transitions.mdx`.
- **Error boundaries**: **Not supported in Astro components** (not found in docs). Framework islands can use their own framework's boundaries (from memory, unverified).
- **Root/global error page**: **Supported for on-demand pages.**
  - `src/pages/500.astro` receives an `error` prop (`unknown`) for errors thrown in pages or middleware. The docs warn not to render stacks.
  - It is **not used for prerendered pages**: build errors fail the build.
  - If 500.astro itself errors, the host's default 500 page shows.
  - In dev, when a 500.astro exists, errors are logged to the terminal instead of the overlay.
  - Adapters can customize how prerendered error pages are fetched (`prerenderedErrorPageFetch`).
  - Source: `basics/astro-pages.mdx`, `reference/modules/astro-app.mdx`.
- **404 / not-found handling**: **Supported.**
  - `src/pages/404.astro` or `404.md` builds `404.html`, which hosts pick up.
  - On demand, unmatched routes render it and middleware attempts to run, depending on the adapter.
  - Programmatic options:
    - `return Astro.rewrite('/404')` (on-demand only)
    - `return new Response(null, {status: 404})`
    - `Astro.response.status = 404`
    - `return Astro.redirect('/404')`, shown in the docs' SSR example
  - Advanced routing: `notFound(state)` (7.4).
  - Endpoints with no matching method fall back to the 404 page.
  - Experimental `redirectPage`: custom `src/pages/3xx.astro` for static meta-refresh redirect pages (props `from`, `to`, `status`, `delay`; `RedirectPageProps`).
  - Source: `basics/astro-pages.mdx`, `guides/routing.mdx`, `guides/endpoints.mdx`, `reference/modules/astro-fetch.mdx`, `reference/experimental-flags/redirect-page.mdx`.
- **Helpers like `redirect()`, `notFound()`, `error()`**: **Partial.**
  - `Astro.redirect()`, `Astro.rewrite()` and `Response` returns. These are return values, not throwables, and must be returned from the page.
  - No throwable `notFound()` or `error()` in components. `ActionError` exists for actions.
  - Source: `reference/api-reference.mdx`.
- **Expected vs unexpected errors**: **Partial.**
  - Actions separate typed `ActionError` codes and input errors from unexpected throws (both arrive in `result.error`).
  - Live collections return typed error classes rather than throwing.
  - Everything else becomes a 500 or a build failure.
  - Source: `reference/modules/astro-actions.mdx`, `guides/content-collections.mdx`.
- **Error reporting hooks**: **Partial (no `onError` hook).**
  - The Logger API (v7) lets a custom destination receive all logs: `write`, `flush` (end of each request), `close` (shutdown).
  - `logHandlers.json/console/node/compose`.
  - Sentry via its integration (`@sentry/astro`).
  - Source: `reference/logger-reference.mdx`, `guides/backend/sentry.mdx`.
- **Notable extras**:
  - An exhaustive catalogue of named, documented errors (`reference/error-reference.mdx`, ~150 pages).
  - Dev error overlay is mentioned (Vite-based).
  - Source: `reference/error-reference.mdx`, `guides/routing.mdx`.

## 8. Type safety

- **Typed links and params**: **Not supported for links / static-only for params** (area 1).
  - `GetStaticPaths`, `InferGetStaticParamsType`, `InferGetStaticPropsType`, `GetStaticPathsOptions`.
  - Source: `guides/typescript.mdx`.
- **Typed server data to components**: **Partial (manual `Props`).**
  - Components declare `interface Props` (or `type`) in frontmatter. The editor tooling (VS Code extension / language server) checks it at usage sites.
  - Page props from `getStaticPaths` can be inferred.
  - Helpers: `HTMLAttributes<'tag'>`, `ComponentProps<typeof X>` (`astro/types`), `Polymorphic`, `HTMLTag`, `MarkdownLayoutProps`.
  - `tsc` ignores `.astro` files; use `astro check` (flags: `--watch`, `--tsconfig`, `--minimumFailingSeverity`, `--minimumSeverity`, `--preserveWatchOutput`, `--noSync`; exits 1 on errors).
  - tsconfig presets: `astro/tsconfigs/base|strict|strictest`.
  - Source: `guides/typescript.mdx`, `reference/cli-reference.mdx`.
- **Typed server calls**: **Supported.**
  - Actions infer input from the Zod schema and output from the handler (`SafeResult<T>`, `ActionReturnType`, `ActionInputSchema`).
  - Endpoints: `APIRoute`/`APIContext` (untyped bodies).
  - Middleware: `defineMiddleware` and `App.Locals`.
  - Source: `reference/modules/astro-actions.mdx`, `guides/middleware.mdx`.
- **Generated types**: **Supported (codegen).**
  - `astro sync` writes `.astro/types.d.ts` with types for `astro:content` (collections, inferred schemas since v6), `astro:env` and `astro:actions`.
  - It runs automatically in `dev`, `build` and `check`, and with the `s + enter` dev hotkey.
  - Integrations can add types with `injectTypes()` and `createCodegenDir()`.
  - Experimental `contentIntellisense` emits JSON schemas for frontmatter IntelliSense.
  - Source: `reference/cli-reference.mdx`, `reference/integrations-reference.mdx`, `reference/experimental-flags/content-intellisense.mdx`.
- **Typed search params**: **Not supported.**
- **Notable extras**:
  - `astro:env` schema with `envField` gives typed and validated env vars: four types (string, number, enum, boolean) × `context` (client/server) × `access` (public/secret). Client secrets are impossible.
  - Secrets are validated on any import of `astro:env/server` unless `env.validateSecrets` validates them at start.
  - `getSecret()` reads raw values. Adapters opt into `envGetSecret`.
  - Source: `guides/environment-variables.mdx`, `reference/configuration-reference.mdx`.

## 9. Metadata & SEO

- **Head/meta management per route**: **Manual (HTML).**
  - Write `<head>`, `<title>` and `<meta>` directly in pages or layouts. Pass values via props or named slots (e.g. `<slot name="head" />`).
  - Astro auto-adds `<!DOCTYPE html>` and its own head content (scoped styles, scripts) to pages.
  - No `<Head>` component, `metadata` export or deduping API.
  - With `<ClientRouter />`, head elements are diffed on navigation (stylesheets and scripts kept, the rest replaced, `transition:persist` honored) and the title is announced.
  - Source: `basics/astro-pages.mdx`, `basics/astro-components.mdx`, `guides/view-transitions.mdx`.
- **Metadata derived from loaded data**: **Supported (naturally).** Page frontmatter runs before the template, so fetched data can be used in `<head>`. Markdown layouts receive `frontmatter`. Source: `basics/layouts.mdx`.
- **Sitemap / robots / manifest**: **Partial (official integration plus conventions).**
  - `@astrojs/sitemap` (requires `site`) emits `sitemap-index.xml` and `sitemap-N.xml`. Options: `filter`, `customPages`, `customSitemaps`, `entryLimit`, `changefreq`/`lastmod`/`priority`, `serialize`, `chunks`, `i18n`, `xslURL`, `filenameBase`, `namespaces`.
  - **It cannot list dynamic SSR routes.**
  - `robots.txt` and `manifest.webmanifest` go in `public/`, or `robots.txt.ts` as an endpoint.
  - `@astrojs/rss` is documented in a recipe.
  - Source: `guides/integrations-guide/sitemap.mdx`, `basics/project-structure.mdx`, `recipes/rss.mdx`.
- **Open Graph image generation**: **Not built in.**
  - Documented pattern: an endpoint (e.g. `og.png.ts`) using Satori + Sharp, with `fontData` and `experimental_getFontFileURL()` from `astro:assets` to load self-hosted fonts.
  - CDN SDKs such as Cloudinary's `getCldOgImageUrl()` are another route.
  - Source: `guides/fonts.mdx`, `guides/media/cloudinary.mdx`.
- **Canonical etc.**: **Manual.**
  - `new URL(Astro.url.pathname, Astro.site)` or `page.url.current`.
  - `site` config is "strongly recommended" for sitemap and canonical URLs.
  - `Astro.generator` for `<meta name="generator">`.
  - `set:html` with `JSON.stringify` for JSON-LD.
  - Source: `reference/api-reference.mdx`, `reference/configuration-reference.mdx`, `reference/directives-reference.mdx`.
- **Notable extras**: i18n `hreflang` links come through the sitemap's `i18n` option. Source: `guides/integrations-guide/sitemap.mdx`.

## 10. Assets & styling

- **Image optimization**: **Supported (`astro:assets`, Sharp by default).**
  - `<Image />` props, in addition to all `<img>` attributes:

    | prop | values / default | behavior |
    |---|---|---|
    | `src` (required) | `ImageMetadata` (import) \| string (`public/` path or remote URL) \| `Promise<{default}>` | Local `src/` images must be imported. `public/` images are never optimized. Remote images are optimized only if authorized. |
    | `alt` (required) | string | Missing alt is an error. `""` marks the image as decorative. |
    | `width`/`height` | number | Inferred for `src/` images. **Required for `public/` images** and for remote images unless `inferSize`. Auto-computed when `layout` is set. |
    | `densities` | `(number\|'2x')[]` | Builds a `srcset`. Ignored when `layout` is set. Mutually exclusive with `widths`. Never upscales. |
    | `widths` | `number[]` | Builds a `srcset`. Requires `sizes`. Never upscales. |
    | `sizes` | string | Auto-generated for `constrained` and `full-width` layouts. |
    | `format` | `'webp'`(default)\|`avif`\|`png`\|`jpeg`\|`jpg`\|`svg`\|string | Output format. |
    | `quality` | `'low'\|'mid'\|'high'\|'max'` or 0–100 | Presets are normalized per format. |
    | `inferSize` | `false` | Fetches remote dimensions. **Allow-listed domains only** (since 5.17.3). |
    | `priority` | `false` | Sets `loading="eager"`, `decoding="sync"`, `fetchpriority="high"`. Otherwise output uses `loading="lazy"` and `decoding="async"`. |
    | `layout` | `'constrained'\|'full-width'\|'fixed'\|'none'`; default `image.layout` or `none` | Auto `srcset`/`sizes`, plus `data-astro-image` and CSS vars `--fit`/`--pos`. |
    | `fit` | `contain\|cover\|fill\|none\|scale-down`; default `image.objectFit` or `cover` | Crops by default since v6. |
    | `position` | CSS object-position; default `center` | — |
    | `background` (5.17) | color string | Flatten colour for formats without alpha. |

  - `<Picture />` adds:
    - `formats` (default `['webp']`; one `<source>` per format, in order).
    - `fallbackFormat` (default `png`, or `jpg` for JPGs, `gif` for animated, `svg` for SVG).
    - `pictureAttributes` (applied to `<picture>`; other attributes go on the inner `<img>`).
  - **When transforms happen**: at build for prerendered pages, on the fly at request time for on-demand pages (`image.endpoint`, default route `/_image`). The default service crops but never upscales (v6).
  - `getImage(options)` is server-only and returns a `GetImageResult` for custom components, CSS backgrounds or endpoints. `inferRemoteSize(url)`, `getConfiguredImageService()` and `imageConfig` are also exported.
  - Markdown `![]()` images in `src/` and remote images are optimized, and become responsive when `image.layout` is set globally. Raw `<img>` is not processed. Content-collection `image()` schema helper.
  - **SVG components**: `import Logo from './logo.svg'` then `<Logo width fill … />` inlines the SVG. Passed attributes override the file's. Type: `SvgComponent`. Experimental `svgOptimizer: svgoOptimizer(config)` optimizes every SVG component, with no per-file opt-out.
  - Image config:

    | key | default | behavior |
    |---|---|---|
    | `image.service` | Sharp (`astro/assets/services/sharp`) | Or `passthroughImageService()` (no-op), a custom entrypoint, or (7.4) `{build, runtime}` split. Prerendered images always build in Node. |
    | `image.service.config` | — | `limitInputPixels` (`true`), `kernel` (lanczos3), `jpeg`/`webp`/`avif`/`png` encoder defaults. Per-image `quality` wins. |
    | `image.domains` | `[]` | No wildcards. |
    | `image.remotePatterns` | `[]` | `protocol`/`hostname`/`port`/`pathname`. `**.` / `*.` host wildcards and `/**` / `/*` path wildcards. Redirect targets must also match. |
    | `image.layout` | undefined | — |
    | `image.objectFit` | `cover` | — |
    | `image.objectPosition` | `center` | — |
    | `image.breakpoints` | `[640…2560]` local / `[640…6016]` remote | — |
    | `image.responsiveStyles` | `false` | Global `:where()` styles. Disable to let Tailwind 4 layers win. |
    | `image.dangerouslyProcessSVG` | `false` | DoS risk. |
    | `image.endpoint` | `{route:'/_image'}` | — |

  - Adapter image services:
    - Vercel: `imageService`, `imagesConfig`, `devImageService`.
    - Netlify: Image CDN by default (`imageCDN` opt-out).
    - Cloudflare: `imageService` (`cloudflare-binding` default, `cloudflare`, `passthrough`, `compile`, `custom`, or `{build, runtime}`).
  - Source: `reference/modules/astro-assets.mdx`, `guides/images.mdx`, `reference/configuration-reference.mdx`, `reference/experimental-flags/svg-optimization.mdx`, `guides/integrations-guide/*.mdx`.
- **Font optimization**: **Supported (Fonts API, stable since v6).**
  - Configure with `fonts: [{ provider, name, cssVariable, ... }]`.
  - Providers: `fontProviders.local()`, `adobe`, `bunny`, `fontshare`, `fontsource`, `google`, `googleicons`, `npm`, or a custom provider.
  - Fonts are **downloaded and self-hosted**: `_astro/fonts` in builds with long HTTP caching; cached in `.astro/fonts` (dev) and `node_modules/.astro/fonts` (build).
  - Per-family options:

    | option | default |
    |---|---|
    | `weights` | `[400]` (ranges allowed for variable fonts) |
    | `styles` | `['normal','italic']` |
    | `subsets` | `['latin']` |
    | `formats` | `['woff2']` |
    | `fallbacks` | `['sans-serif']` |
    | `optimizedFallbacks` | `true` (metric-adjusted fallbacks generated from the last generic family) |
    | `display` | `swap` |

    Further options: `unicodeRange`, `stretch`, `featureSettings`, `variationSettings`, and provider-specific `options`. The same family can be declared several times to merge variants.
  - `<Font cssVariable preload? />` goes in the head and emits styles. `preload` is `false`, `true`, or `[{weight, style, subset}]`; a variable font file is preloaded if its range covers the requested weight.
  - `fontData` and `experimental_getFontFileURL()` give programmatic access.
  - Tailwind registration is documented.
  - Source: `guides/fonts.mdx`, `reference/configuration-reference.mdx`, `reference/modules/astro-assets.mdx`.
- **Third-party script loading**: **Partial.**
  - `<script is:inline src>` loads external or `public/` scripts as-is.
  - The `@astrojs/partytown` integration moves scripts to a web worker.
  - Integrations can `injectScript(stage, content)` with stages `head-inline`, `before-hydration`, `page`, `page-ssr`.
  - No `<Script strategy>` component.
  - Source: `guides/client-side-scripts.mdx`, `guides/integrations-guide/partytown.mdx`, `reference/integrations-reference.mdx`.
- **CSS support**: **Supported.**
  - `<style>` in `.astro` is **scoped by default**. `scopedStyleStrategy` is `'attribute'` (default, `data-astro-cid-*`, +1 specificity), `'class'` (+1) or `'where'` (0).
  - `is:global` and `:global()` for unscoped rules. `class:list` (clsx). `define:vars` for CSS variables.
  - Cascade order: `<link>` tags < imported CSS < scoped styles. Imported CSS can leak even from unused components.
  - Sass/SCSS, Less and Stylus via `<style lang>` (Vite).
  - LightningCSS via Vite config. PostCSS is built in (`postcss.config.cjs`).
  - CSS Modules (`*.module.css`) in framework components; Vue and Svelte scoped styles. CSS Modules inside `.astro` are not mentioned.
  - **Tailwind 4** via `@tailwindcss/vite` (`astro add tailwind`). Tailwind 3 via the legacy integration.
  - CSS-in-JS is not covered beyond React's `experimentalDisableStreaming` caveat.
  - Bundling: per-page plus shared chunks. `build.inlineStylesheets: 'auto'(default; under 4 kB inlined)|'always'|'never'`. `?raw` and `?url` imports bypass bundling.
  - v6+: `<script>` and `<style>` render in the order defined.
  - Source: `guides/styling.mdx`, `reference/configuration-reference.mdx`, `guides/upgrade-to/v6.mdx`.
- **MDX/Markdown as pages**: **Supported.**
  - `.md` (core) and `.mdx` (`@astrojs/mdx`) files in `src/pages/` become routes, with a `layout` frontmatter key.
  - The **v7 default processor is Sätteri** (native; GFM + SmartyPants). Use `markdown.processor: unified()` from `@astrojs/markdown-remark` for remark/rehype/recma plugins. The top-level `markdown.remarkPlugins`, `rehypePlugins`, `gfm`, `smartypants` and `remarkRehype` keys are deprecated.
  - `markdown.syntaxHighlight`: `'shiki'`(default, `github-dark`) | `'prism'` | `false`, with `excludeLangs: ['math']`.
  - `<Content />` and heading IDs. MDX supports custom `components` mapping, exported variables and an `optimize` option.
  - Partials are possible for `.mdx` but not `.md`.
  - **Content collections** (build-time `glob()`/`file()`/custom loaders; Zod schemas; `reference()`) and **live collections** (runtime loaders, cache hints) are Astro's content layer. They are noted here as Markdown/content capability only.
  - Source: `basics/astro-pages.mdx`, `guides/markdown-content.mdx`, `guides/integrations-guide/mdx.mdx`, `reference/configuration-reference.mdx`, `guides/content-collections.mdx`.
- **Notable extras**:
  - `public/` holds assets that are copied untouched.
  - `build.assetsPrefix` (string, or a per-extension map with `fallback`) serves assets from a CDN.
  - Adapters can append `client.assetQueryParams` to all asset URLs.
  - Source: `reference/configuration-reference.mdx`, `reference/adapter-reference.mdx`.

## 11. Build output & deployment

- **Output modes**: **Supported.**
  - `output: 'static'` (default) produces a fully static `dist/` with no adapter needed. Mixed output comes from per-route `prerender = false` plus an adapter.
  - `output: 'server'` makes everything on-demand by default.
  - There is no SPA or export-only mode distinct from static.
  - Features that need an adapter even on static sites: actions, server islands, sessions, on-demand image endpoints.
  - Adapters can force a shape with `adapterFeatures.buildOutput: 'static'|'server'`.
  - `build.format` (`directory` default, `file`, `preserve`) and the output directories `outDir`, `build.client` (`./client`), `build.server` (`./server`), `build.assets` (`_astro`), `build.serverEntry` (`entry.mjs`).
  - `build.redirects` (default `true`; static mode emits HTML redirects).
  - Source: `reference/configuration-reference.mdx`, `guides/on-demand-rendering.mdx`.
- **Supported runtimes and per-route runtime choice**:
  - Node (Node 22+ since v6).
  - Cloudflare Workers (`workerd` for dev, preview and prerender; `nodejs_compat` flag; `.wasm`/`.bin`/`.txt` imports; Cloudflare Pages support removed).
  - Netlify Functions and Edge Functions (middleware).
  - Vercel Serverless, plus an Edge Function for middleware.
  - Deno via `@deno/astro-adapter`, now maintained by Deno.
  - Bun: a recipe warns of "rough edges".
  - **Per-route runtime choice: Not supported.** Only middleware can move to the edge (`middlewareMode: 'edge'`). Cloudflare `prerenderEnvironment: 'workerd'|'node'` affects only prerendering.
  - Source: `guides/upgrade-to/v6.mdx`, `guides/integrations-guide/cloudflare.mdx`, `guides/integrations-guide/netlify.mdx`, `guides/integrations-guide/vercel.mdx`, `guides/integrations-guide/deno.mdx`, `recipes/bun.mdx`.
- **Adapters**:
  - **4 official**: `@astrojs/node`, `@astrojs/netlify`, `@astrojs/vercel`, `@astrojs/cloudflare`. Install with `astro add <name>`. Community adapters are listed in the integrations directory. About 30 host deploy guides exist (`guides/deploy/*`).
  - Key adapter options:
    - **Node**: `mode: 'standalone'|'middleware'` (middleware mode exports `handler` for Express or Fastify and does no static serving); `staticHeaders`; `experimentalDisableStreaming`; `bodySizeLimit` (1 GB); env vars `HOST`/`PORT`, `SERVER_CERT_PATH`/`SERVER_KEY_PATH` for HTTPS; filesystem session driver by default.
    - **Vercel**: `webAnalytics`, `imagesConfig`, `imageService`, `devImageService`, `isr`, `includeFiles`/`excludeFiles`, `maxDuration`, `skewProtection`, `staticHeaders`, edge middleware.
    - **Netlify**: edge middleware, `Astro.locals.netlify.context`, Image CDN, `_redirects` generation (appended to `public/_redirects`), Blobs sessions, `cacheOnDemandPages`, automatic skew protection, `includeFiles`/`excludeFiles` (globs), `devFeatures {images, environmentVariables, edgeFunctions}`, `staticHeaders`.
    - **Cloudflare**: Vite-plugin options (`auxiliaryWorkers`, `configPath`, `inspectorPort`, `persistState`, `remoteBindings`), `imageService`, `sessionKVBindingName` (`SESSION`), `imagesBindingName` (`IMAGES`), `prerenderEnvironment`; bindings via `cloudflare:workers`; `Astro.locals.cfContext`; `_headers` and `_redirects` in `public/`; advanced-routing companion handlers.
  - **Adapter API**: an integration calls `setAdapter({...})` in `astro:config:done`:

    | field | values / default | behavior |
    |---|---|---|
    | `name` | string | — |
    | `serverEntrypoint` | string \| URL | — |
    | `entrypointResolution` | `'auto'` recommended; `'explicit'` default but deprecated | With `explicit`, `createExports()`/`exports`/`args` are deprecated. |
    | `previewEntrypoint` | — | Backs `astro preview`. |
    | `client.internalFetchHeaders` | — | Headers injected into Astro's internal fetches for actions, view transitions, server islands and prefetch. Used for skew protection. |
    | `client.assetQueryParams` | — | Query params appended to asset URLs. |
    | `supportedAstroFeatures` | — | `staticOutput`, `hybridOutput`, `serverOutput`, `i18nDomains`, `envGetSecret`, `sharpImageService`. Each takes `'stable'\|'experimental'\|'limited'\|'deprecated'\|'unsupported'` or `{support, message, suppress: 'default'\|'all'}`. |
    | `adapterFeatures` | — | `middlewareMode: 'classic'\|'edge'`; `buildOutput`; `staticHeaders` (gets a `routeToHeaders` map in `astro:build:generated`); `preserveBuildClientDir`; `preserveBuildServerDir` (6.4). |

    Runtime and build helpers: `createApp()` from `astro/app/entrypoint` with `streaming`, `render`, `match`, `getAllowedDomains`, `removeBase` and `setCookieHeaders`; `createRequest` and `writeResponse` from `astro/app/node`; custom prerenderer via `setPrerenderer()` (6.0); `StaticPaths` from `astro:static-paths` for collecting paths in non-Node runtimes; the `envGetSecret` hook `setGetEnv()`.
  - Source: `guides/on-demand-rendering.mdx`, `reference/adapter-reference.mdx`, `reference/modules/astro-app.mdx`, `reference/modules/astro-static-paths.mdx`, adapter guides.
- **Config-level headers, redirects, rewrites, trailing slash, base path**:
  - **Headers**: `server.headers` applies to dev and preview only. No production headers config; production headers come through adapters (`staticHeaders` for CSP) or host files (`_headers`).
  - **Redirects**: **Supported.** `redirects: { '/old': '/new' | { status, destination } }`.
    - Dynamic redirects need matching params (`/blog/[...slug]` → `/articles/[...slug]`), and static and dynamic routes can't be mixed.
    - External `http(s)` destinations are allowed since 5.2.
    - Default status is 301 for GET and 308 for other methods.
    - Static output without an adapter uses meta refresh and ignores status. Adapters write host config (e.g. Netlify `_redirects`).
    - File routes win over redirects. Experimental `redirectPage` customizes the meta-refresh page.
  - **Rewrites in config**: **Not supported** (runtime only: `Astro.rewrite` or middleware).
  - **`trailingSlash`** and **`base`**: see area 1.
  - Source: `reference/configuration-reference.mdx`, `guides/routing.mdx`, `guides/integrations-guide/cloudflare.mdx`.
- **Standalone / self-contained output**: **Supported via Node `mode: 'standalone'`.**
  - Run `node ./dist/server/entry.mjs`. It serves `dist/client/` and adds immutable cache headers to `_astro/`.
  - A Docker recipe exists.
  - Source: `guides/integrations-guide/node.mdx`, `recipes/docker.mdx`.
- **Skew protection**: **Partial (adapter-level).**
  - Vercel `skewProtection` (Pro/Enterprise).
  - Netlify: automatic. The deploy ID is injected into internal fetches for actions, server islands, view transitions and prefetch; user fetches use `DEPLOY_ID`.
  - Generic hooks for adapters: `client.internalFetchHeaders` and `assetQueryParams`.
  - Server islands: `ASTRO_KEY` to share the encryption key across versions.
  - Source: `guides/integrations-guide/vercel.mdx`, `guides/integrations-guide/netlify.mdx`, `reference/adapter-reference.mdx`, `guides/server-islands.mdx`.
- **Notable extras**:
  - Build performance:
    - `build.concurrency`
    - experimental `parallelPrerender`, `incrementalBuild`, `collectionStorage: 'chunked'` (for per-asset size limits)
    - `astro build --timings` (7.4)
    - `--devOutput`
  - `cacheDir` persistence between CI builds speeds up image processing.
  - `vite` passthrough config.
  - Integration hooks across the build: `astro:build:start/setup/ssr/generated/done`.
  - Source: `reference/configuration-reference.mdx`, `reference/experimental-flags/*.mdx`, `reference/cli-reference.mdx`, `reference/integrations-reference.mdx`.

## 12. Dev tooling & observability

- **Dev server and HMR**: **Supported.**
  - `astro dev` runs on Vite 8 with HMR and unbundled assets.
  - Hotkeys: `s + enter` syncs content and types, `o + enter` opens the browser, `q + enter` quits.
  - Flags: `--port` (4321), `--host`, `--allowed-hosts`, `--open`, `--mode`, `--force` (clear the content-layer cache), `--verbose`, `--silent`, `--json`, `--background`, `--ignore-lock`.
  - Subcommands: `stop`, `status`, `logs [--follow]`.
  - Background servers write lock files (`.astro/dev.json`, `.astro/preview.json`).
  - `astro preview` serves the build through the adapter's preview entrypoint (Cloudflare uses `workerd`).
  - Programmatic: `dev()` returns a `DevServer {address, handle(req, res), watcher, stop()}`; also `build({devOutput, timings})`, `preview()`, `sync()`, `mergeConfig()`, `validateConfig()`.
  - Source: `reference/cli-reference.mdx`, `reference/programmatic-reference.mdx`.
- **Error overlay**: **Supported** (dev overlay, mentioned for rewrite errors; replaced by terminal logging if `500.astro` exists). Source: `guides/routing.mdx`, `basics/astro-pages.mdx`.
- **Devtools**: **Supported (Dev Toolbar).**
  - Built-in apps:
    - Astro Menu, including "Copy debug info", which runs `astro info`.
    - **Inspect**: lists islands with their props and client directives.
    - **Audit**: performance and accessibility checks with in-page highlights.
    - Settings.
  - Config: `devToolbar.enabled` (`true`), `devToolbar.placement` (`bottom-center` default, overridable in the UI and saved to localStorage). Per-user disable with `astro preferences disable devToolbar [--global]`.
  - Extensible through the Dev Toolbar App API: `addDevToolbarApp`, `defineToolbarApp({init, beforeTogglingOff})`, client and server messaging, and a web-component UI kit.
  - Experimental `chromeDevtoolsWorkspace` saves edits made in Chrome DevTools back to disk.
  - Framework devtools options exist for Vue, Preact and Solid.
  - Source: `guides/dev-toolbar.mdx`, `reference/dev-toolbar-app-reference.mdx`, `reference/configuration-reference.mdx`, `reference/experimental-flags/chrome-devtools-workspace.mdx`.
- **Type generation commands**: **Supported.** `astro sync` and `astro check` (area 8). Source: `reference/cli-reference.mdx`.
- **CLI scaffolding / generators**: **Partial.**
  - `npm create astro@latest` with `--template <example | user/repo>`, `--add <integration>` and other create-astro flags.
  - `astro add <integration>` installs and edits config.
  - `astro info`, `astro docs`, `astro create-key`, `astro preferences`, `astro telemetry`.
  - No route or component generators.
  - Source: `install-and-setup.mdx`, `reference/cli-reference.mdx`.
- **AI-agent support**: **Supported (docs MCP plus agent-aware CLI).**
  - **Astro Docs MCP server** at `https://mcp.docs.astro.build/mcp` (remote, Streamable HTTP, backed by kapa.ai). Setup steps are documented for many AI coding tools.
  - **Background mode** (v7): when an AI agent is detected on macOS or Linux, `astro dev` (and `astro preview` since 7.2) automatically detach, write lock files and use JSON logs. Opt out with `ASTRO_DEV_BACKGROUND` or `ASTRO_PREVIEW_BACKGROUND`. Windows stays in the foreground.
  - **Health endpoint** `/_astro/status` returns `{"ok":true}` (dev only).
  - The upgrade guide includes a copy-paste "Using a coding agent?" prompt.
  - Discord `#support-ai` bot.
  - **No `llms.txt`, AGENTS.md or bundled-docs convention was found in the docs.**
  - Source: `guides/build-with-ai.mdx`, `reference/cli-reference.mdx`, `guides/upgrade-to/v7.mdx`.
- **Instrumentation / OpenTelemetry hooks**: **Not found in docs.**
- **Server error reporting hooks**: **Partial.**
  - Logger API (stable in 7.0):
    - `logger: { entrypoint, config }`, or built-ins `logHandlers.json({pretty, level})`, `console({level})`, `node({level})` (the default) and `compose(...)`.
    - Custom destination functions: `write(message{label, level, message, newLine})`, `flush()` (end of each request), `close()` (shutdown).
    - Levels: `debug`, `info`, `warn`, `error`, `silent`.
    - `Astro.logger` adds runtime logs.
  - Sentry SDK integration (with Spotlight dev-toolbar app).
  - No `onError` or `handleError` hook.
  - Source: `reference/logger-reference.mdx`, `reference/configuration-reference.mdx`, `guides/backend/sentry.mdx`.
- **Web vitals reporting**: **Not in core.** The Vercel adapter's `webAnalytics` option only applies to `@vercel/analytics` ≤1.3. The dev toolbar Audit app does basic performance checks. Source: `guides/integrations-guide/vercel.mdx`, `guides/dev-toolbar.mdx`.
- **Notable extras**:
  - **Container API** (experimental): `experimental_AstroContainer.create()` and `renderToString` / `renderToResponse` render `.astro` components in isolation (Vitest, or non-Vite hosts like PHP or Elixir). v7 moved `getContainerRenderer()` to `@astrojs/<fw>/container-renderer`.
  - Integration API hooks for dev: `astro:server:setup` (Vite server, toolbar, `refreshContent`), `astro:server:start`, `astro:server:done`.
  - The `astro check` CI gate.
  - Source: `reference/container-reference.mdx`, `guides/upgrade-to/v7.mdx`, `reference/integrations-reference.mdx`.

## Out-of-scope features seen (one line each)
- **Sessions**: `Astro.session` (`get`, `set` with `ttl`, `regenerate`, `destroy`, `load`) is server-stored with a cookie holding only the ID, uses unstorage drivers, has adapter defaults (Node filesystem, Netlify Blobs, Cloudflare KV `SESSION`), and can be turned off with `session: false` (7.2). Source: `guides/sessions.mdx`, `reference/api-reference.mdx`, `reference/configuration-reference.mdx`.
- **i18n routing**: `i18n.locales`, `defaultLocale`, `fallback`, `routing.prefixDefaultLocale`/`redirectToDefaultLocale`/`fallbackType`, `domains`, plus `astro:i18n` helpers and `Astro.currentLocale`/`preferredLocale`. Source: `guides/internationalization.mdx`, `reference/configuration-reference.mdx`.
- **`astro:env`**: typed, validated env schema (summarized in area 8). Source: `guides/environment-variables.mdx`.
- **Content collections and live collections**: the content layer (loaders, Zod 4 schemas, references, JSON schemas, `legacy.collectionsBackwardsCompat`). Covered only as a content capability in area 10. Source: `guides/content-collections.mdx`, `reference/legacy-flags.mdx`.
- **Auth / backend / CMS / media guides**: third-party recipes only (Better Auth, Clerk, Supabase, Sentry, ~45 CMS guides). Source: `guides/authentication.mdx`, `guides/backend/`, `guides/cms/`.
- **Databases**: `@astrojs/db` was **removed in v7**; the docs point to `node:sqlite` or Drizzle instead. Source: `guides/upgrade-to/v7.mdx`.
- **Testing**: Vitest with the Container API, Playwright, Cypress. Source: `guides/testing.mdx`.
