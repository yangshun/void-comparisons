# 2. Rendering modes

**Versions:** Void 1.5.0 · Next.js 16.4 (App Router) · React Router 8 (framework mode) · TanStack Start 1.169 (React) · Nuxt 5.0 pre-release (4.x is stable) · SvelteKit 3.1 · SolidStart 2.0 · Astro 7.4

**Markers:** [exp] experimental, unstable or canary · [CC] Next.js with Cache Components on (the create-next-app default) · [prev] Next.js's pre-16 caching model, still documented

**Paths:** Void file paths are in the `voidzero-dev/void` repo. Short paths such as `pages/scan.ts` are under `packages/void/src/`; paths that start with a package name, such as `react/src/…`, are under `packages/`.

## At a glance

- **SSR is solid but uneven by adapter.** React pages stream (`renderToReadableStream`). Vue (`renderToString`), Svelte (`render`) and Solid (`renderToStringAsync`) buffer the whole page. Island pages buffer in every adapter, React included (`renderToString`).
- **The biggest rendering gap is in deferred data: it never reaches server HTML.** Void's `defer()` streams *data* (`<script>__resolveDeferred(...)`) after `</html>`. When a page has deferred props, the React adapter cuts React's stream at a shell marker (`packages/react/src/runtime/page-streams.ts` `readDeferredShell`), so resolved Suspense content is rendered on the client in **all four adapters**. Next.js, React Router, TanStack and SolidStart stream the resolved boundary HTML, Astro streams async components in order, and Nuxt does so under its experimental streaming flag. Crawlers and no-JS clients see only the fallback in Void.
- **Void is ahead on response correctness.** Status, headers and `head()` are all settled before the first byte. The loader runs first and `head()` is synchronous, so Void has no "200 on a streamed 404", no dropped headers and no head patch scripts. Next.js, Nuxt, SvelteKit, SolidStart and Astro all document those hazards.
- **Void's islands are Astro-style and work across all four libraries.** They are marked with import attributes, and an island page with no islands ships zero JS. Partners have more strategies: Void has 4 (`load`, `visible`, `idle`, `media:`). It lacks interaction, delay, condition, never and client-only strategies, has no options on idle or visible, and offers no custom strategies. Island props go through `JSON.stringify`, and children/slots cannot be passed. Strategies apply only on island pages, which have no client router.
- **No server components, no server islands, no PPR-style static shell.** Next.js (PPR, stable) and Astro (server islands, stable) have shells with dynamic holes. RSC is stable in Next.js and experimental in React Router, TanStack and Nuxt.
- **Per-route control is per page only.** The `.server.ts` exports are `ssr`, `prerender`, `revalidate` and `getPrerenderPaths`, plus the `.island` suffix. Layouts have no companion, so nothing inherits down a subtree, and `ssr` has no config-pattern form. In Pages mode there is no global SPA switch and no component-level client-only helper (`<ClientOnly>`/`useHydrated`), while 5 of the 7 have each.
- **Prerendering is unusually strong at deploy time.** Pages render inside the built Worker with production bindings, before traffic switches, and seed the ISR cache. The build side is thinner than the field: no crawling, fixed concurrency (4), and failures only warn, with no option to fail the build. TanStack, Nuxt, SvelteKit and SolidStart all offer crawl and fail-on-error, and Next.js fails the build by default.
- **`ssr = false` is "data-only".** The loader runs on the server and its props are embedded, then the page *mounts* rather than hydrates. That matches TanStack's `ssr: 'data-only'` but applies to the whole page, layouts included. It combines with `prerender = true` to give a prerendered client shell carrying build-time loader data, which no other framework offers per page.

## Gap list for this area

| Gap in Void | Who has it (mechanism, briefly) | Prevalence | Notes for design (constraints, dependencies, adapter impact) |
|---|---|---|---|
| Deferred/Suspense content rendered as **HTML** in the stream (SEO, no-JS) | Next.js, React Router, TanStack, SolidStart (out-of-order boundary HTML); Astro (in-order async components); Nuxt [exp] | Table stakes (6; 5 stable) | React: stop cancelling at `__VOID_DEFERRED_SHELL_END__`; resolve deferred promises server-side so React streams `$RC` chunks, and keep data scripts for client state. Vue/Svelte/Solid need streaming renderers first (row below). ISR already stores full streams. Keep the status/head-before-first-byte guarantee |
| Component streaming in Vue/Solid adapters | SolidStart (default `mode: "stream"`); Nuxt [exp] `renderToWebStream`. SvelteKit doesn't (Svelte parity) | Per-adapter partner: Solid behind a stable partner; Vue behind an experimental one | `solid-js/web` `renderToStream`, Vue `renderToWebStream`. Island pages would also need it |
| Static shell with dynamic holes (PPR / server islands) | Next.js (PPR, default with CC); Astro (`server:defer`) | Differentiator (2) | Server islands fit Void's island wrapper + edge ISR. Needs an island endpoint, encrypted or signed props, per-island cache key, and cookie-bypass rules |
| Server components | Next.js (stable); React Router, TanStack, Nuxt [exp] | Common (4; 1 stable) | React-only in practice. Conflicts with Void's Inertia-style JSON page protocol; large dependency (`@vitejs/plugin-rsc`) |
| Global SPA switch for Pages mode (shell + loading template) | React Router (`ssr:false`, root prerendered), TanStack (`spa.enabled`, `/_shell.html`), Nuxt (`ssr:false` + `spaLoadingTemplate`), SvelteKit (root `ssr=false` + fallback), SolidStart (`ssr:false`) | Common (5) | Void's loaders are server-only, so the SPA shell would still call the Worker for page JSON. Could reuse `ssr=false` + `routing.fallbacks` |
| Component-level client-only rendering | Next.js (`dynamic ssr:false`, `use(browser())`), TanStack (`<ClientOnly>`, `useHydrated`), Nuxt (`<ClientOnly>`, `.client.vue`), SolidStart (`clientOnly()`), Astro (`client:only`) | Common (5) | Needed in all 4 adapters, plus a `client:only`-style island strategy |
| Subtree/pattern inheritance of mode flags (`ssr`, zero-JS, prerender) | Next.js (layout segment config), TanStack (parent→child `ssr`), Nuxt (`routeRules` globs), SvelteKit (layout cascade) | Common (4) | Layouts have no companion file. Either add layout `.server.ts` exports or a `routing.ssr` pattern map like `routing.revalidate` |
| SSR'd fallback / parent layouts for client-only pages | React Router (`HydrateFallback`, ancestors SSR'd), TanStack (`pendingComponent`, ancestors SSR'd), Nuxt (`spaLoadingTemplate`) | Common (3) | Today `ssr=false` blanks the whole `#app`. Rendering layouts server-side with a page placeholder needs adapter work |
| Lazy-hydration options: idle `timeout`, visible `rootMargin`/`threshold` | Nuxt, TanStack [exp], Astro | Common (3) | Attribute syntax is a string. Options need syntax (`'visible:200px'`?) or a second attribute. Also validate strategy strings (typos silently never hydrate today) |
| `interaction` hydration (with event replay) | Nuxt (`hydrate-on-interaction`), TanStack [exp] (`interaction()`, re-dispatch) | Differentiator (2) | Island wrapper `div` can listen; replay is library-specific |
| `never` / `condition` / `delay` strategies | Nuxt (`hydrate-never`, `hydrate-when`, `hydrate-after`); TanStack [exp] (`never()`, `condition()`) | Differentiator (2; delay 1) | `never` ≈ an unmarked import in Void; `condition` needs a client-side signal API |
| Lazy hydration inside routed (non-island) pages | Nuxt (`Lazy*` + `hydrate-*`), TanStack [exp] (`<Hydrate>`) | Differentiator (2) | Library-specific: Vue has `hydrateOn*` built in, React needs boundary tricks |
| Island props beyond JSON + children/slots | Astro (Map/Set/Date/BigInt/URL/… + slots), Nuxt (interactive parent slots), Next.js (RSC props + interleaving) | Common (3) | Swap `JSON.stringify` for devalue-style serialization. Slots need SSR-rendered HTML passed as static children per adapter (the Vue wrapper drops slots today) |
| Prerender crawling | TanStack (`crawlLinks`), Nuxt, SvelteKit (`crawl`), SolidStart (Nitro `crawlLinks`) | Common (4) | Runner already fetches HTML; parse `<a href>` and enqueue |
| Fail the build on prerender errors | Next.js (fails by default), TanStack/Nuxt/SolidStart (`failOnError`), SvelteKit (`handleHttpError: 'fail'` default) | Common (5) | Void always warns. Deploy-time prerender intentionally "never blocks deploy" (keep that default there) |
| Configurable prerender concurrency / retries / filter | Concurrency: React Router, TanStack, Nuxt, SvelteKit, SolidStart, Astro. Retries: TanStack, Nitro. Filter/ignore: TanStack, Nuxt, SolidStart | Table stakes (6) for concurrency | Void is parallel (4) by default, so this is about control, not speed |
| Hydration mismatch guidance/helpers | Next.js, React Router, TanStack, Nuxt | Common (4) | Docs + `ClientOnly`/`useHydrated` + React `onRecoverableError` passthrough |
| Per-request render-mode decision | TanStack (`ssr` fn), SolidStart (`createHandler` options fn, inferred) | Differentiator (2) | Could hang off middleware (`c.set('ssr', false)`) |
| Parent→child static-param chaining | Next.js (`generateStaticParams` receives parent params) | Differentiator (1) | Void has no layout companions to host it |
| Stream timeout for deferred data | React Router (`streamTimeout`, 4950 ms default) | Differentiator (1) | Reject pending groups with `__rejectDeferred` after N ms |
| Bot-aware buffering | Next.js (`htmlLimitedBots`), Nuxt (`botRegex`) | Differentiator (2) | Only useful once deferred HTML streams |
| User-owned document shell in Pages mode | Next.js, React Router, TanStack, SvelteKit, SolidStart, Astro | Table stakes (6) | Void offers head + `htmlAttrs`/`bodyAttrs` only (Nuxt is similar). Custom SSR mode already gives full control |

## Where Void is ahead

- **Deploy-time prerendering in the production Worker** (real bindings, before traffic switches, seeding the edge ISR cache, never blocking the deploy) is unique. Prerendered pages without `.server.ts` skip the Worker entirely in hybrid deploys.
- **Correct status, headers and head with streaming.** All of them are decided before the first byte, so Void never sends a 200 for a streamed 404, never drops headers (Nuxt), never patches head after flush (Nuxt), and never raises `ResponseSentError` (Astro) or "Cannot set headers" (SolidStart).
- **Uniform deferred data across four UI libraries**, with grouped resolvers (one call shared by several keys), NDJSON for client navigations, and inline resolution in prefetch responses. Nuxt has no deferred-data primitive at all.
- **Islands in React, Vue, Svelte and Solid with one API, coexisting with client-routed pages in the same app.** Astro has no SPA pages; Nuxt islands are experimental. Island pages with no loader or params, and Markdown pages, are **auto-prerendered**.
- **`ssr = false` + `prerender = true`** gives a prerendered client-render shell carrying build-time loader data, per page. React Router's SPA root-loader-at-build is root-only.
- **`ssr = false` keeps the loader on the server** (TanStack `'data-only'` semantics): no client data code and no secret leakage.
- **Parallel prerendering by default** (4 workers, safe serial fallback on output collisions, path-traversal guard). React Router, SvelteKit and Astro default to 1.

## SSR (renderer per UI library)

| Framework | Default | Server renderer | Buffered vs streaming | Who owns the HTML document | Notes |
|---|---|---|---|---|---|
| **Void** | On for Pages (`output: "server"`) | React `renderToReadableStream`; Vue `renderToString`; Svelte `render`; Solid `renderToStringAsync` + `generateHydrationScript` | React streams. Vue, Svelte and Solid buffer. **Island pages buffer in all four adapters** (React islands use `renderToString`, `packages/react/src/plugin-islands.ts`) | A fixed Void skeleton (`<head>` from `head()`/config/middleware `headDefaults`, `htmlAttrs`/`bodyAttrs`, `<div id="app">`). The user cannot add a document component. Custom SSR mode (`defineRender((c, assetTags) => Response)`) gives full control | Page object goes into `<script id="__VOID_PAGE_DATA__">`. Client navigations get JSON (`X-VoidPages: true`, `Vary: X-VoidPages`). The whole tree is wrapped in an outer `<Suspense fallback={null}>` (React) |
| Next.js | On | RSC + `react-dom` | Streaming (required for RSC/PPR) | Root `layout` renders `<html>` | Client navigations fetch the RSC payload. Every segment renders, parallel slots included |
| React Router | `ssr: true` | `renderToPipeableStream` (Node) / `renderToReadableStream` (other runtimes); `future.unstable_enableNodeReadableStream` | Streaming | `entry.server.tsx` `handleRequest(request, status, headers, routerContext)` returns the `Response`; root `Layout` | Omitting `<Scripts/>` gives a no-JS MPA |
| TanStack | On | `defaultStreamHandler`; non-streaming `defaultRenderHandler` / `renderRouterToString` | Streaming by default | The root route renders `<html>` (`shellComponent`). Customise via `defineHandlerCallback` | `<Scripts/>` is required |
| Nuxt | `ssr: true` | Vue `renderToString`; `renderToWebStream` under `experimental.ssrStreaming` | **Buffered by default**; streaming is [exp] | `app.vue` inside `#__nuxt`, plus Nitro `render:html` hooks (no user document) | `experimental.writeEarlyHints` |
| SvelteKit | On | Svelte `render` | Buffered HTML plus streamed **data** | `src/app.html` placeholders; `transformPageChunk` | |
| SolidStart | `ssr: true` | `createHandler` `mode: "stream"` (default) \| `"async"` \| `"sync"` | Streaming by default | `entry-server.tsx` `<StartServer document={...}>`, user-written JSX | `onCompleteShell`/`onCompleteAll` can `write()` into the stream. `options` may be a function of the `PageEvent` (per request) |
| Astro | Static by default; per-page `prerender = false` needs an adapter | Astro pipeline + per-integration renderers | In-order HTML streaming | `.astro` pages/layouts write `<html>` | Opt out via `createApp({streaming:false})`, Node/React `experimentalDisableStreaming` |

**Behavioral differences that matter:**
- The adapter-vs-partner picture: **React** streams like Next.js/React Router/TanStack (with the deferred caveat below). **Vue** buffers like stable Nuxt, which streams only under an experimental flag. **Svelte** matches SvelteKit (buffered HTML plus streamed data). **Solid** is behind SolidStart, which streams out-of-order Suspense by default while Void buffers with `renderToStringAsync`.
- Pages-mode HTML is a fixed template (`packages/void/src/pages/protocol.ts` `renderClientOnlyPage`, `packages/react/src/runtime/pages-server.ts`). Everything outside `<div id="app">` comes from head descriptors. React Router, TanStack, SvelteKit, SolidStart, Next.js and Astro all let the app own the document. Nuxt, like Void, uses head attrs plus hooks.

**Void gap:** partial. Vue/Svelte/Solid adapters and island pages have no component streaming. Pages mode has no user-owned document shell. There is no per-request render-mode option (SolidStart's `createHandler(fn)`).

## Streaming SSR mechanics

### What streams, and when

| Framework | Deferred primitive | Consumed with | What the stream carries | Order | First byte waits for | Timeout | Bots |
|---|---|---|---|---|---|---|---|
| **Void** | `defer(fn)` / `defer('group', fn)` props returned by the loader. Resolvers start **after the loader returns**, run in parallel, and a group shares one call | React: `Deferred<T>` = `Promise<T>` + `use()` under `<Suspense>`. Vue/Svelte/Solid: `{ loading, value, error }` | **Data only.** One `<script>window.__resolveDeferred(group,data)</script>` (or `__rejectDeferred`) per group, appended after the page HTML. With deferred props the React stream is **cancelled at a `<template id="__VOID_DEFERRED_SHELL_END__">` marker**, so resolved boundaries render client-side. With no `defer()`, user `<Suspense>`/`lazy` streams natively. Client navigations get NDJSON (page object line, then `{__deferred, data\|error}` lines). Prefetch responses resolve deferred data inline | Completion order (`protocol.ts` `streamDeferredResponse`) | Middleware, loader, `head()` and the shell render. React renders the shell; other adapters render the whole page | **None.** A hanging resolver keeps the response open | **None.** Crawlers get the fallback / `loading` state |
| Next.js | Async Server Components under `<Suspense>`/`loading.js`; unawaited promises passed to client `use()` | `<Suspense>`, `use()` | **HTML** of resolved boundaries plus RSC | Out-of-order | [CC] the prerendered static shell goes out immediately. [prev] until the first fallback | Not documented | `htmlLimitedBots` (UA regex) get blocking metadata and, with PPR, a request-time render |
| React Router | Unawaited promises **nested in the loader's returned object** (a bare top-level promise isn't allowed) | `<Await resolve\|unstable_promise errorElement>`, `use()` | HTML of resolved boundaries plus data | Out-of-order | **All matched loaders settle** (`Promise.all`) | `export const streamTimeout` in `entry.server` (default **4950 ms**) rejects outstanding promises. Docs recommend aborting React at timeout + 1 s | Not documented |
| TanStack | Unawaited promises in the loader return (`defer()` deprecated) | `<Await promise>`, `use()` | Inline scripts with resolved values (or serialized errors) **plus boundary HTML** | Out-of-order | `beforeLoad` + awaited loader parts | Not documented | Not documented |
| Nuxt **(exp `ssrStreaming`)** | Vue `<Suspense>` / async setup; **no deferred-data primitive** | n/a | HTML streams progressively after the shell (nested Suspense included) | Not documented | First render pass (head, entry styles, preload hints, entry scripts) | — | `botRegex` → buffered. The default list covers indexing crawlers only, and setting it replaces the list |
| SvelteKit | Promises (top-level or nested) returned from **server** `load`. Universal-load promises are not streamed | `{#await}` | **Data only** (serialized as each resolves). Needs `csr = true` | Completion | All `load`s return | Not documented | None |
| SolidStart | Query reads under `<Suspense>` (`createAsync`) | `<Suspense fallback>` | HTML of resolved boundaries | Out-of-order | Shell; `createAsync(..., { deferStream: true })` makes the server wait for that resource | Not documented | Not documented |
| Astro | Async child components (top-level page `await` blocks the whole document) | n/a | HTML | **In document order**; sibling async components fetch in parallel | Page frontmatter | — | None |

### Response mutations and errors after the first byte

| Framework | Status / headers / cookies / redirect after first byte | Head tags after first byte | Error after shell |
|---|---|---|---|
| **Void** | **Can't happen.** The loader (and per-route middleware) decides status, headers, cookies and redirects before rendering. Deferred resolvers can only return data or throw | `head(c, props)` is synchronous and built from loader props before render, so it is **always in the initial `<head>`** | React: thrown before the shell → server error page; after the shell → `console.error`. A rejected deferred group → `__rejectDeferred` → React error boundary via `use()`, or the `error` field in other adapters. Production masks messages as `"Internal Server Error"` except for `HTTPException` |
| Next.js | Status is fixed at 200. A later `notFound()` emits `<meta name="robots" content="noindex">`; a later `redirect()` emits a meta refresh. [CC] request-time checks keep 200 even when the shell is empty, so the docs say "check in Proxy" | Metadata streams, except to HTML-limited bots | Nearest error boundary |
| React Router | Loaders settle first, so loader status/headers/meta are honored. Streamed promises can't change them | From loaders, so in the shell | `errorElement`, else the route `ErrorBoundary`. The default `handleError` sees only shell errors; later chunks need `onError`. Node: a streamed promise rejecting before loaders settle is an unhandled rejection that can crash the process |
| TanStack | "Once the entry has returned its `Response`, errors in the streamed body cannot change status/headers" | From awaited loader data | Nearest error boundary (serialized error) |
| Nuxt [exp] | `setResponseStatus`, `useResponseHeader`, `useCookie` writes and h3 setters after the flush are **dropped** (dev warns). Do these in plugins | Sent as **inline patch scripts**. No-JS clients and crawlers not matched by `botRegex` miss them (except JSON-LD, `noscript` and body tags) | `payload.error` is set, the document closes cleanly, and `error.vue` renders on the client (NUXT_E8009 if that fails) |
| SvelteKit | `set_headers_after_response`, `cookies_set_after_response`; no redirect inside streamed promises | n/a | Rejections need a `.catch` (handled automatically for `fetch`) |
| SolidStart | "Cannot set headers after they are sent to the client". The fix is `deferStream: true` | — | Error boundaries |
| Astro | `ResponseSentError` when a component or layout sets them; do it in the page | — | — |

**Behavioral differences that matter:**
- Void's design trades **HTML streaming for deferred content** against **always-correct status and head**. Others stream the resolved HTML, so their SEO and no-JS output includes it. Void, like SvelteKit, sends the fallback and fills it on the client in every adapter, React included.
- Void's deferred resolvers start only after the loader returns. React Router's streamed promises start inside the loader, so they can overlap the loader's own awaits. Void's resolvers receive `c`, and grouping de-duplicates work across keys.
- Deferred data streams uniformly across all four Void adapters. Nuxt has no deferred-data primitive at all, which puts Void's Vue adapter ahead of stable Nuxt for slow data.
- With ISR, Void caches the **complete** streamed response, deferred scripts included, so a cache hit replays build/first-render data. Nuxt never streams cached routes.
- Void has no stream timeout (React Router defaults to 4950 ms). On Workers, a stuck resolver runs until the platform kills the request.

**Void gap:** partial.
- (1) Resolved deferred content is never server-rendered as HTML. The React adapter would need to stop cancelling at the shell marker and let React's out-of-order `$RC` chunks flow, with data scripts interleaved.
- (2) Vue, Svelte and Solid adapters have no component-level streaming. Solid's `renderToStream` and Vue's `renderToWebStream` exist.
- (3) No `streamTimeout`-style limit on deferred resolvers.
- (4) No bot-aware buffering. This only matters once (1) exists.

## Static prerendering

| Framework | When | Opt-in / default | Dynamic-param enumeration | Crawl links | Concurrency | Failure behavior | Output files | Client-nav data files | Unlisted params at runtime |
|---|---|---|---|---|---|---|---|---|---|
| **Void** | **Build** (`output: "static"`), or **deploy time** (`output: "server"` + `prerender = true`; Cloudflare only, because it needs ISR). Deploy-time rendering happens once per deployment, **before traffic switches**, and is stored in the ISR cache | `static`: every page unless `prerender = false` (dynamic pages need `getPrerenderPaths`). `server`: opt in per page. Explicit list `routing.prerender: string[]`. **Auto**: island pages with no loader and no params, and Markdown pages, even under `output: "server"` | `export async function getPrerenderPaths()` (no args) returns param objects. It **runs inside the built Worker with bindings** via an internal `POST /__void/prerender-paths`. Custom SSR returns full path strings. No parent→child chaining. Param values are substituted unencoded | **No** | Fixed **4** parallel; drops to 1 when output paths could collide. Not configurable (`packages/void/src/prerender-render.ts` `renderConcurrency`) | Non-2xx → `voidWarn`, and build/deploy continues. **No fail-build option.** Redirect responses are skipped. Paths that resolve outside `dist/client` are rejected | `dist/client/<path>.html` (`/` → `index.html`; no subfolder-index option). Default `404.html` when at least one page is prerendered (override with `public/404.html` or a `/404` page) | `/_void/pages/<path>.json` (page object). Pages with deferred props still embed them unresolved, so client navigations call the server | `server`: rendered on the first request, then ISR-cached with the page's TTL (default **1 year**). `static` hybrid: the Worker renders them. No "404 for unlisted" switch |
| Next.js | Build (dev calls `generateStaticParams` on navigation; ISR does not re-call it) | Automatic per route, by what it reads | `generateStaticParams()` in pages, layouts and route handlers. **Parent→child chaining** (a child receives the parent's `params`). [CC] must return ≥1 set (empty → build error). `fetch` inside it is memoized | No | Not stated | **Build fails** (`G/building.mdx`) | HTML + RSC (+ segment prefetch files) | RSC payload | [CC] App Shell served immediately, rendered in the background, saved and reused. [prev] `dynamicParams` (`false` → 404) |
| React Router | Build | `prerender: true \| string[] \| async ({getStaticPaths}) => string[] \| {paths, concurrency}` | Config function only | No | `concurrency` (default 1) | Build-time validation errors for `ssr:false` exports. Render failures not documented | `build/client/<path>/index.html` | `<path>.data` | `ssr:true` → SSR. `ssr:false` → SPA fallback (`index.html` or `__spa-fallback.html`) |
| TanStack | Build | `prerender.enabled`, `autoStaticPathsDiscovery` (default true; excludes param routes, pathless layouts, API routes), `pages[]` with per-page overrides, `filter` | Crawl or `pages[]` list only (no per-route hook) | `crawlLinks` (default true) | `concurrency` | `failOnError`, `retryCount`/`retryDelay`, `maxRedirects`, `onSuccess` | `autoSubfolderIndex` (default `/page/index.html`) | Static Server Functions [exp]: JSON keyed by function ID + payload hash | SSR |
| Nuxt | Build (`nuxt generate`, `--prerender`, route rule `prerender`) | Route rule `prerender: true` with globs; `defineRouteRules` **(exp `inlineRouteRules`)** | `prerender.routes`, `prerender:routes` hook (`ctx.routes.add`), runtime `prerenderRoutes()`, Nitro `prerender:generate` (`route.skip`) | **Yes**, recursively from `/` | `nitro.prerender.concurrency` | `nitro.prerender.failOnError` | HTML + `200.html` + `404.html`; `prerenderErrorPages` [exp] | `_payload.json`; `sharedPrerenderData` (on) | SSR with hybrid builds ("hybrid not available with `nuxt generate`") |
| SvelteKit | Build | `export const prerender = true \| false \| 'auto'` (page/layout, cascades); `prerender.entries` (default `['*']`) | `export function entries()` (`EntryGenerator`), also on `+server.js` | `prerender.crawl` (default true) | `prerender.concurrency` (default 1) | `handleHttpError` / `handleMissingId` / `handleEntryGeneratorMismatch` / `handleInvalidUrl` / `handleUnseenRoutes` = `'fail'` (default) \| `'warn'` \| `'ignore'` \| fn | `about.html` vs `about/index.html` per `trailingSlash`. Name clashes are build errors | Not stated in inventory | `'auto'` → SSR on demand. `true` → removed from the server manifest |
| SolidStart | Build (Nitro) | `nitro.prerender.routes`; no per-route export | List or crawl | `crawlLinks` | Nitro option | `failOnError`, retry, `ignore` | `.output/public` (`autoSubfolderIndex` is a Nitro option) | — | SSR |
| Astro | Build (default output) | `export const prerender` (literal); `output` default | `getStaticPaths()` (`params`, `props`) + `paginate()` | No | `build.concurrency` (default 1); `parallelPrerender` [exp]; `incrementalBuild` [exp] (`cacheKey`) | Not stated in inventory | HTML; endpoints become files (`data.json.ts`). Adapter prerenderers (Cloudflare prerenders in `workerd`) | — (MPA) | Static: only the listed paths exist |

**Behavioral differences that matter:**
- Deploy-time prerendering with production bindings and seeding of the edge cache is **unique to Void**. Astro's Cloudflare prerenderer runs in `workerd`, but at build time.
- `getPrerenderPaths` is per page, like `generateStaticParams`, `entries()` and `getStaticPaths()`. It takes no arguments, so a child can't enumerate per parent (Next.js can).
- Void prerenders 4 pages in parallel by default where React Router, SvelteKit and Astro default to 1. You cannot raise or lower that number, add retries, filter, or make failures fatal. A CMS outage at build time silently ships a site with missing pages, and only warnings are printed.
- Void's static builds with a Worker behave like SvelteKit's `prerender = 'auto'`: listed params are static, everything else renders live. You cannot get the strict "404 unlisted" mode (Next.js [prev] `dynamicParams=false`, SvelteKit `prerender=true`).

**Void gap:** partial.
- No link crawling.
- No `concurrency`, `retry`, `filter` or `failOnError`-style options.
- No output naming option.
- No parent→child param chaining.
- No strict mode for unlisted params.

## Client-only routes and full SPA mode

| Framework | Per-route client-only switch | Server work for that route | What the shell contains | Hydrate vs mount | Global SPA mode | Component-level client-only |
|---|---|---|---|---|---|---|
| **Void** | `export const ssr = false` in the page's `.server.ts`. **Page only**: no layout, pattern or global form | Loader runs on the server and its props are embedded in `__VOID_PAGE_DATA__`; `head()` renders on the server (= TanStack `'data-only'`) | Empty `<div id="app" data-void-ssr="false">`. **Layouts are not SSR'd and there is no loading/fallback UI** | **Mount** (`createApp` vs `createSSRApp`, etc.; each adapter checks `data-void-ssr`) | **None in Pages mode.** `inference.appType: "spa"` is a plain Vite SPA (bring your own router; Pages features unavailable) + `routes/` API; `routing.fallbacks` / `notFound: 'single-page-application'` | **None** (no `<ClientOnly>`, `useHydrated`, or `ssr:false` dynamic import in any adapter). `ssr=false` + `prerender=true` gives a prerendered shell with build-time loader props. `ssr=false` on an island page is a build error |
| Next.js | None | — | — | — | `output: 'export'` gives a static multi-page SPA; no single-`index.html` mode | `next/dynamic(..., {ssr:false})` (client components only), `use(browser())` (React 19.3; suspends at prerender), `useEffect` guards |
| React Router | A route with only `clientLoader` (no `loader`) implies `hydrate = true`. SSR renders the nearest `HydrateFallback`, bubbling up; **parents still SSR** | None for that route | Ancestors + `HydrateFallback` | Hydrate | `ssr: false`: the build SSRs **the root route only** into `index.html`. The root `loader` runs **at build** and goes into `HydrateFallback`'s `loaderData`. Host rewrites to `index.html`. `ssr: "unstable_api-only"` [exp] | Not built in |
| TanStack | `ssr: false \| 'data-only' \| ({params, search}) => …`; `defaultSsr` | `'data-only'`: server `beforeLoad`/`loader`. `false`: both run on the client during hydration | Parents SSR'd + the first non-SSR route's `pendingComponent` (shown for at least `pendingMinMs`) | Hydrate | `spa: { enabled, maskPath, prerender }` → `/_shell.html` (root route + pending fallback; root loader baked in at build); `router.isShell()` | `<ClientOnly fallback>`, `useHydrated()`, `createClientOnlyFn` |
| Nuxt | Route rule `ssr: false` (globs); `.client.vue` page. The page component is dropped from the server bundle | — | Empty `#__nuxt` (+ loader template) | Mount | `ssr: false` + `spaLoadingTemplate` (`null`/`false`/`true`/path); `experimental.spaLoadingTemplateLocation: 'body' \| 'within'`; `app.spaLoaderTag/Attrs`. `nuxt generate` → `index.html`, `200.html`, `404.html` | `<ClientOnly>` (`placeholder`/`fallback`, `#fallback`; default slot tree-shaken from the server), `.client.vue` components |
| SvelteKit | `export const ssr = false` on a page **or layout** (cascades) | Universal `load` runs only in the browser | Empty shell from `app.html` | Mount | Root layout `ssr = false` + `adapter-static({ fallback: '200.html' })`; `router.type: 'hash'` | Not built in |
| SolidStart | None (`ssr` is global) | — | — | — | `solidStart({ ssr: false })`; keeps file routes and server functions; host rewrite | `clientOnly(() => import(...), { lazy })` with an SSR'd `fallback` prop |
| Astro | None | — | — | — | None (`<ClientRouter/>` is client navigation over server HTML) | `client:only="react\|vue\|svelte\|solid-js\|…"` + `slot="fallback"` |

**Behavioral differences that matter:**
- Void's `ssr=false` keeps server data (secure loaders, no client data code), which is ahead of SvelteKit/TanStack `false` for data safety. It costs the whole layout tree, with no fallback, so the user sees a blank page until JS mounts. React Router and TanStack keep ancestors SSR'd and render a fallback in the shell.
- The spec asked whether loaders run on the server for client-only pages: in Void they **always** do. There is no client loader, so TanStack/SvelteKit-style "data on the client too" is not possible. That is by design for Void.

**Void gap:** partial.
- No global SPA switch for Pages.
- No subtree/pattern `ssr` control.
- No SSR'd fallback/pending UI or SSR'd parent layouts for client-only pages.
- No component-level client-only helper in any adapter.

## Partial hydration: islands and server components

| Framework | Model / status | Marker and granularity | Props crossing the boundary | Children / slots | Shared state between islands | Router interaction |
|---|---|---|---|---|---|---|
| **Void** | Client islands (stable), **island pages only** (`*.island.{tsx,jsx,vue,svelte}`, Markdown pages implicit). All 4 adapters | `import X from './_X' with { island: 'load' \| 'visible' \| 'idle' \| 'media:(q)' }` (needs TS `"module": "ESNext"`). **One strategy per import**, so every usage on the page shares it. Strategy strings are **not validated**: an unknown value never hydrates, silently (`packages/void/src/pages/island-imports.ts`, `client.ts scheduleHydration`). Unmarked imports ship no JS. Layouts are static | `JSON.stringify` into `data-props`: `Date` → string, `Map`/`Set` → `{}`, functions and `undefined` dropped | **Not supported.** The Vue wrapper forwards only `$attrs` (slots dropped). React/Svelte/Solid children can't round-trip JSON | Each island is a separate root (`hydrateRoot` etc.; `data-hydrated="true"` once done). The framework provides only `useFrontmatter()`. Module-level stores share a module graph (inferred) | **No client router on island pages.** `<Link>` to an island page falls back to a document load. Forms use `useIslandForm`, and a successful action reloads via `window.location` |
| Next.js | **RSC (stable)**; Server Components by default | `'use client'` module boundary: the module and everything it imports become client code | React-serializable: primitives, plain objects, Date, Map, Set, promises (unwrap with `use()`); Server Components as props | **Yes**: Server Components passed as `children`/props stay server-rendered (interleaving) | Context providers in client components | Full client router; RSC payload per navigation |
| React Router | RSC [exp] (`unstable_reactRouterRSC` + `@vitejs/plugin-rsc`) | `ServerComponent` export; loaders/actions return elements; `"use client"` | Flight | Yes (RSC) | — | Full router; `"use server"` functions revalidate routes |
| TanStack | RSC [exp], "client-led": RSC output produced in **server functions** and returned through loaders | `renderServerComponent(<El/>)`, `createCompositeComponent` + `<CompositeComponent src>` | Flight-serializable slot args | `children`, render props, component props (opaque proxies on the server) | — | Router cache keys RSC by path + params + `loaderDeps` |
| Nuxt | Server components / islands **(exp `componentIslands: 'auto'`)** | `*.server.vue`, `components/islands/`, `.server.vue` pages; `<NuxtIsland name lazy props context source>` | Sent as **GET query params** (JSON, URL-length limited, untrusted). B3015 for non-serializable values | **Slots from the parent are interactive**; `nuxt-client` makes selected children hydrate (`selectiveClient: 'deep'` also allows slots, server-rendered) | **None**: each island is an isolated Vue app (no provide/inject, `useState` or Pinia). Plugins rerun, route middleware doesn't | Inline on the first SSR. On client navigation each island is a round trip (blocking unless `lazy` + `#fallback`). Remote islands via `source` |
| SvelteKit | **None** (whole-page hydration). `csr = false` for zero-JS | — | — | — | — | — |
| SolidStart | **None in v2** (`experimental.islands` accepts only `false`). v1 had experimental islands | — | — | — | — | — |
| Astro | Client islands (core) + server islands (stable) | `client:*` **per component instance**; only in `.astro` files. Frameworks can be mixed on one page | Plain object, number, string, Array, **Map, Set, RegExp, Date, BigInt, URL, typed arrays, Infinity**; no functions or circular refs | **Yes**, as slots: React/Preact/Solid get `children` + camelCased named slots; Vue/Svelte get `<slot name>`. React children are strings unless `experimentalReactChildren` | Not stated in inventory | Optional `<ClientRouter/>` |

**Behavioral differences that matter:**
- Void's island model is closest to Astro's, but strategies are per import rather than per instance, props are JSON-only, and children/slots can't be passed. Astro components can't import framework islands into other framework components either.
- Void is the only framework where the **same app** mixes fully routed SPA-style pages and islands pages across four libraries. Astro mixes libraries per page but has no SPA pages.
- Nuxt, Next.js, React Router and TanStack (the last three via RSC) let server-rendered regions live **inside** a client-routed app. Void islands require giving up the client router for that page.

**Void gap:** partial.
- Server components: missing.
- Islands lack rich props, children/slots, per-instance strategies and strategy validation.
- No islands-in-routed-pages.

## Lazy-hydration strategies

Next.js, React Router and SvelteKit have none: React selective hydration is automatic, and SvelteKit/SolidStart offer full hydration only.

| Strategy | **Void** (island pages only) | Nuxt (stable; any `Lazy*` component in a full app) | TanStack `<Hydrate when>` [exp]; inside the single React tree | Astro (islands) |
|---|---|---|---|---|
| Immediate | `'load'` | (non-lazy component) | `load()` | `client:load` |
| Idle | `'idle'`: `requestIdleCallback`, falling back to `setTimeout(cb, 1)`. **No timeout option** | `hydrate-on-idle` = max timeout (ms) | `idle({ timeout })`, default 2000 | `client:idle={{timeout}}` |
| Visible | `'visible'`: IntersectionObserver, once. **No `rootMargin`/`threshold`** | `hydrate-on-visible` = IO options | `visible({ rootMargin = '600px', threshold })` | `client:visible={{rootMargin}}` |
| Media query | `'media:(q)'` | `hydrate-on-media-query` | `media(q)` | `client:media` |
| Interaction | — | `hydrate-on-interaction`: event or array; default `pointerenter`, `click`, `focus` | `interaction({ events })`: default `pointerenter`, `focusin`, `pointerdown`, `click`; **re-dispatches** the triggering event | — (custom directive) |
| Delay | — | `hydrate-after` (ms) | — | — |
| Condition | — | `hydrate-when` (reactive boolean) | `condition(bool \| fn)` | — |
| Never | Unmarked import (static) | `hydrate-never` (any prop change forces hydration) | `never()` | No directive |
| Client-only (no SSR) | — | `<ClientOnly>`, `.client.vue` | `<ClientOnly>` | `client:only` |
| Custom | — | — | Function form of `when` | `addClientDirective({name, entrypoint})` |
| Separate prefetch trigger | — | — | `prefetch` prop (strategy or async fn with `preload()`/`waitFor()`) | — |
| Granularity | Per import | Per component instance (literal props; no `v-bind` spread) | Per boundary; children split into their own chunk (`split`, default true) | Per instance |
| Hydrated signal | `data-hydrated="true"` attribute | `@hydrated` | `onHydrated` | — |

**Behavioral differences that matter:**
- Nuxt and TanStack bring lazy hydration **into full-hydration apps**, keeping their router and shared state. In Void, lazy hydration means switching the page to island mode.
- TanStack's `interaction()` re-dispatches the triggering event after hydration, so the first click isn't lost. Nuxt's Vue strategy and Void have no equivalent.
- Nuxt `experimental.stripNeverHydratedData` drops payload for `hydrate-never` subtrees. In Void, island pages never embed the page payload (only island `data-props`), which is already lean.

**Void gap:** partial.
- Missing strategies: `interaction`, `delay`, `condition`, `client-only` and custom.
- No options on `idle` (timeout) or `visible` (rootMargin/threshold).
- No hydrated callback.
- No per-instance strategy.
- No lazy hydration outside island pages.

## Static shell with dynamic holes

| Framework | Mechanism | Shell built when | Holes filled by | Cacheability | Status |
|---|---|---|---|---|---|
| **Void** | **None** (grepped `partial prerender`, `ppr`, `server island`, `postpone`). Approximations: ISR-cached page + `defer()` (deferred data is **inside** the cached response, so it isn't per-request); island page + client fetch inside an island; `ssr=false` + `prerender` shell | — | — | — | — |
| Next.js | **PPR**, the default with Cache Components. Static shell (HTML + RSC) from `use cache` output, Suspense fallbacks and deterministic work. Uncached I/O and runtime APIs must sit behind `<Suspense>` + `connection()`/`io()`. Separate **App Shell** (URL-independent) for unknown params and prefetch | Build (+ ISR) | Same response: resume request (`next-resume: 1`, `postponedState`) streams only deferred boundaries | Shell is static; holes are dynamic. Validated by `instant` / `ensureStatic` | Stable (16.x) |
| Astro | **Server islands**: `server:defer` + `slot="fallback"` | Build (prerendered page) or on demand | Browser fetches `/_server-islands/<Name>` per island, independently | GET with **encrypted props** in the query (POST when the URL exceeds 2048 bytes, uncacheable); `Cache-Control` per island. `ASTRO_KEY` keeps the key stable across deploys. `Astro.url` is the island URL (read `Referer`). Needs an adapter | Stable |
| Nuxt | Not a feature. Islands render inline on the first SSR. `<NuxtIsland lazy>` + `#fallback` fetches separately (client navigation); SWR page + `<ClientOnly>`/`server:false` holes | — | — | Island endpoint responses are CDN-cacheable (GET props) | [exp] islands |
| SvelteKit | Data-level only: remote `prerender` functions [exp] on otherwise dynamic pages | Build | — | CDN + browser Cache API until deploy | [exp] |
| React Router / TanStack / SolidStart | None (streaming, SPA shells and client-only holes as approximations) | — | — | — | — |

**Void gap:** missing. Differentiator: Next.js and Astro, both stable. Void already has the parts: edge ISR for shells, an island wrapper with props serialization, Worker endpoints. A Void "server island" (deferred island rendered by a Worker endpoint and fetched by a tiny loader script) would compose with prerendered/ISR shells. It needs its own cache key (props) and the same cookie-bypass rules.

## Per-route rendering-mode control

| Framework | Where it is set | Knobs | Inheritance | Static analysis | Per-request decision |
|---|---|---|---|---|---|
| **Void** | Page `.server.ts` exports + filename suffix + config patterns + response header | `ssr` (bool), `prerender` (bool), `revalidate` (non-negative int s), `getPrerenderPaths()`, `.island` suffix. Config: `output`, `routing.revalidate` (patterns, first match), `routing.prerender` (paths), `routing.revalidateQueryAllowlist`, `routing.isr` (kill switch). `x-revalidate` response header | **None.** Layouts have no companion; `ssr` has no pattern form | `const` literal read from the AST (`packages/void/src/pages/scan.ts`). **Non-literal or invalid values are silently ignored**, with no error | Only the TTL, via `x-revalidate` |
| Next.js | Segment config exports in `layout`/`page` + component structure | `ensureStatic` (`'auto'\|'shell'\|'prefetch'\|'navigation'\|false`, 16.4), `instant`, `prefetch`, `maxDuration`, deprecated `runtime`/`preferredRegion`; [prev] `dynamic`, `revalidate`, `fetchCache`, `dynamicParams` | A descendant may be stricter, not weaker (`ensureStatic`). [prev] lowest `revalidate` wins. `preferredRegion` child overrides | Literal | `connection()`/`io()` and runtime APIs make subtrees dynamic |
| React Router | Global config + route exports | `ssr` (global), `prerender` (paths), `clientLoader`/`HydrateFallback`, RSC `ServerComponent` [exp] | — | — | — |
| TanStack | Route option | `ssr: true \| 'data-only' \| false \| fn`; `defaultSsr` in `createStart` | **Children inherit and can only become more restrictive** | — | `ssr` function (server only, initial request; receives validated `params`/`search`) |
| Nuxt | `routeRules` (rou3 globs; `*` any depth in Nuxt 5) + `defineRouteRules()` [exp] + file suffixes | `ssr`, `noScripts`, `streaming`, `appMiddleware`, `appLayout`, `prerender`, `swr`, `isr`, `cache`, `redirect`, `proxy`, `headers`, `cors`. `routeRules` is still labelled "Experimental" | Glob patterns; client sees rules via `appManifest` | — | `render:route` hook: `ctx.prefersStream` (streaming only) |
| SvelteKit | `+page`/`+layout` (`.server`) exports | `prerender`, `ssr`, `csr`, `trailingSlash`, `config`, `entries` | **Cascades from layouts**; child overrides | Literals statically; otherwise the module is imported on the server | Mentioned for `handle`, mechanism not detailed |
| SolidStart | Global + per resource / component | `ssr` global; Nitro prerender list; `deferStream`; `clientOnly` | — | — | `createHandler(options)` as a function of `PageEvent` (inferred) |
| Astro | Page export + config + integrations | `export const prerender` (literal, else `InvalidPrerenderExport`), `output`, `astro:route:setup` (`route.prerender`), `injectRoute({prerender})`, `export const partial` | — | Enforced, with an error | — |

**Behavioral differences that matter:**
- Void is the only framework where TTL, prerender and SSR flags sit together on one page export. That is good locality, but setting `ssr=false` for an `/admin/**` subtree means editing every page. Nuxt, SvelteKit, TanStack and Next.js do it once.
- Void silently ignores `export const revalidate = 60 * 5`. Astro errors on non-literals.

**Void gap:** partial.
- No layout/subtree inheritance.
- No config-pattern `ssr`.
- No per-request mode function.
- No error on non-literal flag values.

## Zero-JS pages

| Framework | Mechanism | Scope | Notes |
|---|---|---|---|
| **Void** | Island page with no `island`-attributed imports (also Markdown pages) | Per page (filename) | Only island chunks ship when islands exist. No `__VOID_PAGE_DATA__` on island pages. Navigation is full-document |
| Next.js | None (React runtime + RSC always ship) | — | — |
| React Router | Omit `<Scripts/>` in root | Global | Progressive enhancement keeps `<Link>`/`<Form>` working |
| TanStack | None (`<Scripts/>` required) | — | — |
| Nuxt | `features.noScripts: 'production' \| 'all'` or the `noScripts: true` route rule | Global or glob | Keeps CSS. Emits **speculation rules** (prefetch/prerender) and cross-document view transitions. NUXT_E8007 warns when client JS is needed |
| SvelteKit | `export const csr = false` | Page or layout (cascades) | `csr = dev` keeps HMR |
| SolidStart | None | — | — |
| Astro | Default (`.astro` ships none) | Everything | Plain `<script>` is bundled |

**Void gap:** none functionally (4 of 7 have it; Void is at parity). Minor: no subtree/global toggle, and no speculation-rules emission like Nuxt.

## Hydration mismatch handling

| Framework | What exists |
|---|---|
| **Void** | **Nothing documented.** No hydration error hook (`onRecoverableError` is not wired), no `<ClientOnly>`/`useHydrated`, no mismatch guide. A pre-hydration inline script is possible via head `script` (`docs/guide/pages-routing/head.md`, theme example) |
| Next.js | Guide `G/preventing-flash-before-hydration.mdx` (inline script + `suppressHydrationWarning`); `use(browser())`; `dynamic(..., {ssr:false})` |
| React Router | Docs warn that `loader` and `clientLoader` must return the same data when SSR'ing then hydrating (`docs/how-to/client-data.md`) |
| TanStack | `guide/hydration-errors.md`: deterministic locale/time-zone middleware, `<ClientOnly>`, `useHydrated`, `ssr: 'data-only' \| false`, `suppressHydrationWarning`; `ScriptOnce` |
| Nuxt | `<NuxtTime>` (mismatch-free dates), `onPrehydrate`, `useId` caveats in islands, `<NuxtClientFallback>` [exp] (client re-render when SSR throws), `__VUE_PROD_HYDRATION_MISMATCH_DETAILS__` define |
| SvelteKit | Not found. SSR `fetch` responses are replayed during hydration, so data doesn't refetch |
| SolidStart | `createAsync` hydration mocks `fetch`/`Promise`; serialized query values are reused. No mismatch guide |
| Astro | n/a (islands) |

**Void gap:** missing. Common (Next.js, React Router, TanStack, Nuxt). Low effort: a guide, a `ClientOnly`/`useHydrated` per adapter, and an `onRecoverableError` passthrough for React.
