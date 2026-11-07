# 3. Data loading

**Versions:** Void 1.6.2 · Next.js 16.4 (App Router) · React Router 8 (framework mode) · TanStack Start 1.169 (React) · Nuxt 5.0 pre-release (4.x is stable) · SvelteKit 3.1 · SolidStart 2.0 · Astro 7.4

**Markers:** [exp] experimental, unstable or canary · [CC] Next.js with Cache Components on (the create-next-app default)

**Paths:** Void file paths are in the `voidzero-dev/void` repo. Short paths such as `pages/scan.ts` are under `packages/void/src/`; paths that start with a package name, such as `react/src/…`, are under `packages/`.

## At a glance

- **Model.** Void is Inertia-style. Each page has exactly **one server-only `loader`** in its `.server.ts` companion. Every GET navigation fetches one JSON page object. There are no layout loaders, no client or isomorphic loaders, no component-level fetching, and no data cache beyond the prefetch cache. The model is easy to reason about and has no loader waterfalls. It is also the narrowest model of the eight.
- **Biggest gap: layout and segment data.** All 7 peers let layouts or nested segments load their own data. In Void, cross-page data comes only from global middleware (`c.set('shared')` → `useShared()`), and that middleware runs on every navigation, mutation request and prefetch. It does not run again when the action re-runs the loader in the same response, so `shared` stays as the action left it (docs/guide/pages-routing/actions-and-forms.md).
- **Serialization is plain JSON.** Payloads go through `JSON.stringify`, so `Date` becomes a string, `Map`/`Set` become `{}`, and `BigInt` throws. Every peer documents at least some types beyond JSON. Three peers (Nuxt, SvelteKit, SolidStart) also have hooks for custom types.
- **Deferred data is solid but coarse.** `defer()` / `defer('group', fn)` stream, but only as **top-level** props. Resolvers start only **after** the loader returns and the first chunk is built, and after a mutation they keep their last values. React Router, TanStack Start, SvelteKit and SolidStart stream promises from anywhere in the returned data, and the work starts as soon as the promise is created.
- **There is no invalidation model beyond "refresh this page".** Void has no targeted invalidation by key, tag or URL (5 peers have it), no automatic dependency tracking (3 peers), and no per-route revalidation policy (4 peers). With a single loader, `router.refresh()` already re-runs everything there is to re-run.
- **The client cache is prefetch-only.** Back/forward navigation always refetches. Next.js, TanStack Start and SolidStart reuse cached data on back/forward. Void has an internal `cacheVisitedPageData` engine option, but no plugin option exposes it.
- **Strengths to keep:** single-request navigation, `defer` groups (one resolver call feeds several props), four prefetch triggers with an SWR `cacheFor: [fresh, expire]` pair, an awaitable `router.prefetch()`, a static `/_void/pages/*.json` fast path, typed props (`InferProps` / `Serialize<T>`), per-route middleware around the loader, and one API across four UI libraries.
- **Adapter split.** Deferred props are a `Promise` read with `use()` in React (with true Suspense streaming SSR) and a `{loading, value, error}` union in Vue, Svelte and Solid, whose component HTML is buffered.

## Gap list for this area

| Gap in Void | Who has it (mechanism, briefly) | Prevalence | Notes for design (constraints, dependencies, adapter impact) |
|---|---|---|---|
| Layout / nested-segment loaders | Next.js (layout RSC), React Router (layout-route loaders), TanStack Start (layout loaders + `beforeLoad`), Nuxt (composables in layouts), SvelteKit (`+layout` load), SolidStart (parent `preload` + queries), Astro (layout frontmatter) | Table stakes (7) | Needs: parallel execution, coalescing into one JSON response (SvelteKit, React Router Single Fetch), a parent-data API, per-layout revalidation (otherwise every nav re-runs every layout), and a page-object shape keyed by layout. Layout components persist across navigations in all four adapters, so props must update in place. Interacts with ISR variants and `defer`. |
| Serialization beyond JSON (`Date`, `Map`, `Set`, `BigInt`, …) | Next.js (Flight), React Router (turbo-stream), TanStack Start (Date/Error/FormData/undefined), Nuxt / SvelteKit / Astro actions (devalue), SolidStart (Seroval), Astro islands | Table stakes (7) | Touches the initial `<script>`, the JSON/NDJSON navigation payloads, prefetch, the static `/_void/pages/*.json` files and `Serialize<T>`. The JSON client parse is CSP-friendly; SolidStart defaults to Seroval `json` mode for the same reason. |
| Custom-type serialization hook | Nuxt (`definePayloadPlugin`), SvelteKit (`transport`), SolidStart (`serialization.plugins`) | Common (3) | Depends on the previous gap. |
| Client or isomorphic loaders | React Router (`clientLoader`), TanStack Start (isomorphic `loader`), Nuxt (composables), SvelteKit (universal load), SolidStart (isomorphic `query`) | Common (5) | Conflicts with Void's Inertia-style server-only model; would need a client data-source contract per adapter. |
| Component-level data fetching (server) | Next.js (any RSC), Nuxt (any component), SolidStart (`createAsync`), Astro (any `.astro`); SvelteKit remote `query` [exp] | Common (4 stable + 1 [exp]) | React-only with RSC; the other adapters would need a query primitive like SolidStart `query()` or SvelteKit remote `query`. |
| Promises anywhere in loader data, started at creation | Next.js, React Router, TanStack Start, SvelteKit (server load), SolidStart | Common (5) | Today: top-level `defer` keys only, started after the loader and the first chunk. Allowing an already-started promise inside `defer()` would close most of the gap without changing the protocol. |
| Visited-page cache with back/forward reuse | Next.js (router cache), TanStack Start (SWR cache), SolidStart (query cache) | Common (3) | Already implemented as `cacheVisitedPageData` in pages/navigation-engine.ts but not exposed in `voidReact/Vue/Svelte/Solid({ … })`. Must be invalidated by mutations (non-GET already flushes). |
| Configurable client data cache (stale time, GC, keys) | Next.js (`cacheLife` stale, `staleTimes` [exp]), TanStack Start (`staleTime`/`gcTime`/…), Nuxt (`getCachedData`), SvelteKit (dependency-retained), SolidStart (fixed 5 s / 3 min) | Common (5) | Void's `cacheFor` covers prefetched entries only. |
| Targeted invalidation by key, tag or URL | Next.js (`revalidateTag`/`updateTag`/`revalidatePath`), TanStack Start (`invalidate({ filter })`), Nuxt (`refreshNuxtData(keys)`), SvelteKit (`invalidate(url \| id)`), SolidStart (`revalidate(keys)`) | Common (5) | With one loader per page, the useful unit is "refresh these props" (partial reload by prop key) plus "invalidate cached pages matching X". |
| Automatic dependency tracking | SvelteKit (params / url / search keys / parent / fetch), SolidStart (reactive), Nuxt (reactive keys and options) | Common (3) | Only matters after layout loaders and client caching exist. |
| Per-route revalidation control | React Router (`shouldRevalidate`, `defaultShouldRevalidate`), TanStack Start (`staleTime`, `shouldReload`), Next.js (`cacheLife`), Nuxt (`getCachedData`) | Common (4) | Pairs with layout loaders. |
| Request-scoped dedupe / memoization | Next.js (fetch memo, `React.cache`), Nuxt (keys), SolidStart (`query()`); SvelteKit remote query [exp] | Common (3 + 1 [exp]) | Needed once there are several loaders per request. |
| Parent-data access from child loaders | SvelteKit (`parent()`), TanStack Start (`parentMatchPromise`, `beforeLoad` context), React Router (client `useRouteLoaderData`) | Common (3) | Depends on layout loaders. Mind SvelteKit's warning that a layout guard doesn't protect page loads unless they await the parent. |
| Prefetch-aware loaders (intent flag or opt-out) | TanStack Start (`preload`/`cause`, route `preload: false`), SolidStart (`intent`), Next.js (`prefetch()`/`navigation()` [CC], `force-disabled`) | Common (3) | Cheap: document the `Purpose: prefetch` header or add `c.get('prefetch')`. |
| Deferred props refreshed after mutation | React Router (loaders re-run), TanStack Start (`invalidate`), SvelteKit (loads re-run) | Common (3) | Void strips deferred from mutation responses and keeps stale values (docs/guide/pages-routing/loaders.md). |
| Deferred stream timeout | React Router (`streamTimeout`) | Differentiator (1) | Today a hung resolver keeps the response open. |

## Where Void is ahead

- **Single-request, single-loader navigation.** There are no waterfalls and no fan-out, and the cost per navigation is predictable. Middleware and the loader share one Hono context, unlike React Router, where client submissions send a separate POST and GET.
- **`defer('group', fn)`.** One resolver call feeds several props, with per-group error isolation. No peer has this as an API.
- **Prefetch ergonomics.** Four triggers plus arrays, per-link `cacheFor`, and an SWR pair `[fresh, expire]`. Code and data load in parallel, and `router.prefetch()` is awaitable. Deferred data is resolved inline, so a prefetched transition is instant. Static builds have a `/_void/pages/*.json` fast path.
- **Typed end to end without codegen per page.** `InferProps<typeof loader>`, and `Serialize<T>` reflects the JSON wire format honestly.
- **Per-route middleware around the loader** (`defineHandler(mw…, handler)`). It can edit the rendered page response after `next()`.
- **Production masking of deferred errors.** Messages from `HTTPException` pass through, so internal details don't leak.
- **Isomorphic typed `fetch`.** It runs in-process on the server and forwards `cookie`/`authorization`, similar to Nuxt `useRequestFetch` and the SvelteKit enhanced `fetch`.
- **One data API across React, Vue, Svelte and Solid.** Only the deferred shape and React's Suspense streaming differ. Don't break this when adding layout loaders.

## Data-loading model and which routes can load data

| Framework | Primitive | Page | Layout | Every nested segment | Any component (server data) | Notes |
|---|---|---|---|---|---|---|
| **Void** | `export const loader = defineHandler(c => props)` in the page's `.server.ts` companion | ✓ (exactly one) | ✗: layouts have no companion | ✗ | ✗: island components fetch client-side via typed `fetch` | Global data: middleware `c.set('shared', …)` → `useShared()`. Loaders may return a `Response` (redirects and errors pass through; a non-JSON 200, such as a file, is returned as is). Custom-SSR mode: isomorphic typed `fetch` from `void/client` (pages/protocol.ts `runLoader`). |
| **Next.js** | async Server Components (no loader abstraction) | ✓ | ✓ | ✓ | ✓ any server component | Server Functions *can* read but are dispatched one at a time from the client, so the docs steer reads to RSC or Route Handlers. |
| **React Router** | `loader` / `clientLoader` route-module exports | ✓ | ✓ (layout routes, including pathless ones) | ✓ | ✗ (fetchers call a route's loader) | RSC async server components are available [exp]. |
| **TanStack Start** | route `loader` + `beforeLoad`; `createServerFn` for server-only reads | ✓ | ✓ | ✓ | Server functions callable anywhere (no framework state); TanStack Query integration | |
| **Nuxt** | `useFetch` / `useAsyncData` composables in setup | ✓ | ✓ | ✓ | ✓ any component, plugin or route middleware | `$fetch` in setup fetches twice (no payload transfer). |
| **SvelteKit** | `load` in `+page(.server).js` / `+layout(.server).js`; remote `query` [exp] | ✓ | ✓ | ✓ | Remote queries awaited directly in components [exp] | |
| **SolidStart** | `query()` read via `createAsync`; route `preload` warms it | ✓ | ✓ (parent route modules export `route.preload`) | ✓ | ✓ any component (`createAsync`) | `"use server"` inside the fetcher makes it RPC. |
| **Astro** | `.astro` frontmatter (top-level `await`) | ✓ | ✓ (layouts are components) | n/a (no nested route data model) | ✓ any `.astro` component | Content collections and live collections [stable]. |

**Behavioral differences that matter:**
- In Void, data for a page comes only from that page's leaf. In every peer, a layout can own its data, and the layout keeps that data while the user moves between its children: Next.js reuses layout segments, SvelteKit and SolidStart reuse data whose dependencies did not change, and TanStack Start serves it from the SWR cache.
- Void's only cross-page mechanism, `shared`, comes from global or per-route middleware. It is not scoped to a layout subtree, it is untyped per page (one `CloudContextVariables` type for everything), and global middleware runs once per page request (HTML, JSON navigation, prefetch, and the action request). It does not run again for the loader re-run in that same response. The loader's own `defineHandler` middleware does (`protocol.ts` `runLoader`).

**Void gap: missing.** Void has no layout loader, so it also has no parent-data access (SvelteKit `parent()`, TanStack Start `parentMatchPromise` / `beforeLoad` context, React Router `useRouteLoaderData` on the client), no per-layout revalidation, and no component-level server fetching.

## Execution: server, client or isomorphic; parallel or sequential

| Framework | Server-only | Client-only | Isomorphic | How multiple loaders run | Notes |
|---|---|---|---|---|---|
| **Void** | `loader` (always) | — | — (typed `fetch` is isomorphic, but it is not a loader) | One loader per request. Order: edge rules → global middleware → per-route middleware (`defineHandler(mw…, handler)`, ≤5) → loader → `head()` → deferred resolvers | Runs on the document request, every client GET navigation (unless prefetched), `router.refresh()`, after every action (same response), and on prefetch. |
| **Next.js** | Server Components | `use()` of a promise passed in props; SWR or Query | — | Layouts and pages render **in parallel**; `await`s inside one component waterfall | "Preload" pattern: call a deduped fetcher without `await`. |
| **React Router** | `loader` | `clientLoader` (+ `clientLoader.hydrate = true` with `HydrateFallback`) | Pair `loader` + `clientLoader`; `serverLoader()` calls the server | Middleware runs first, sequentially; then **all matched loaders in parallel** | Parallel loaders mean a parent loader **cannot protect** its children. |
| **TanStack Start** | via `createServerFn` | `ssr: false` | `loader` (server on SSR, browser on client navigation); `ssr: 'data-only'` | `beforeLoad` runs **serially** parent→child, then loaders run **in parallel** | A child can wait for its parent via `parentMatchPromise`. |
| **Nuxt** | server routes, server islands | `server: false` | composables (an SSR result goes into the payload; hydration does not refetch) | A Suspense tree; sequential `await`s waterfall | Awaited calls block client navigation; `lazy: true` does not. |
| **SvelteKit** | `+*.server.js` load | universal load with `ssr = false` | universal `+*.js` load | All loads run **concurrently**; on client navigation all server loads are **coalesced into one request** | `await parent()` creates the only waterfall. The server load's output becomes the universal load's `data`. |
| **SolidStart** | `"use server"` inside the query fn | — | `query()` (default) | `preload` runs in parallel with render | Without `preload`, nested lazy routes can waterfall (inferred). |
| **Astro** | frontmatter | islands | — | A render tree: page first, then children in template order; async siblings run in parallel and stream in order | |

**Behavioral differences that matter:**
- With exactly one loader, Void can never have a loader waterfall or a fan-out. That advantage disappears once layout loaders exist, so any design for them needs React Router/SvelteKit-style parallel execution and coalescing into one request.
- Void cannot skip the server for client-side data. React Router's `clientLoader`, TanStack Start's isomorphic loaders, SvelteKit's universal load, SolidStart's isomorphic query and Nuxt composables can all call third-party APIs directly from the browser, or merge in local state.

**Void gap: partial.** Server-only loading works. Client or isomorphic loaders are missing.

## Loader arguments and request context

| Framework | Params | Search/query | Request & headers | Cookies | Parent data | Abort signal | Per-request context | Knows it is a prefetch |
|---|---|---|---|---|---|---|---|---|
| **Void** | `c.req.param()` | `c.req.query()` / `queries()` | `c.req.header()`, `c.req.raw` | Hono `hono/cookie` helpers (not covered by Void docs) | n/a | `c.req.raw.signal`, raw `Request` (not documented for loaders) | `c.get/set`, typed via `CloudContextVariables`; `c.env`; `c.get('user'\|'session')` | Only the `Purpose: prefetch` request header (pages/navigation-engine.ts); not documented |
| **Next.js** | `params` prop (Promise) | `searchParams` prop (pages only) | `headers()`, read-only | `cookies()` | — (dedupe with `React.cache` or the fetch memo instead) | — | none documented; pass data through Proxy headers | `await prefetch()` / `await navigation()` stage functions keep work out of prefetches [CC] |
| **React Router** | `params` | `url` (normalized), `request.url` (raw) | `request` | `createCookie().parse()` | none on the server (loaders are parallel) | `request.signal` | `context` (`RouterContextProvider`, set by middleware; reading an unset key throws) | not documented |
| **TanStack Start** | `params` | via `loaderDeps` only (`search` goes to `beforeLoad`) | in server fns: `getRequest()`, `getRequestHeader()` | `getCookie()` in server fns | `parentMatchPromise`, merged `beforeLoad` context | `abortController` (shared by joined preload and navigation) | router `context` + server request context | `preload: true`, `cause: 'preload'` |
| **Nuxt** | `useRoute()` | `useRoute()` | `useRequestEvent()`, `useRequestHeaders()`, `useRequestURL()` | `useCookie()` (isomorphic) | shared keys / `useState` | handler gets `{ signal }`; `timeout` option | `ssrContext`, event | — |
| **SvelteKit** | `params` (tracked) | `url` (tracked per property and per `searchParams` key) | server: `request`, `getClientAddress()` | server: `cookies` | `parent()` | — (not in `LoadEvent`) | `locals`, `platform`; `getRequestEvent()` | — |
| **SolidStart** | `preload({ params })`; query fn args | `location` | `getRequestEvent()` | `getCookie()` (`@solidjs/start/http`) | — | — | `event.locals` | `preload` `intent: 'preload'` |
| **Astro** | `Astro.params` | `Astro.url` | `Astro.request` | `Astro.cookies` | props down the tree | — | `Astro.locals` | — |

**Behavioral differences that matter:**
- Void's `c` is the full Hono context, so a loader can also set response headers, return redirects, or return a file. That is broader than React Router, TanStack Start or SvelteKit loader arguments. Per-route middleware (`defineHandler(mw…, handler)`) wraps the rendered page response, so it can edit the page after `next()`.
- Only TanStack Start and SolidStart pass the loader an explicit **prefetch flag**. Void runs the full loader on prefetch, and the only way a loader can detect it is by reading an undocumented header. The docs tell users to "keep loaders free of side effects" (docs/guide/pages-routing/overview.md).

**Void gap: partial.** Context is rich. Missing: a documented prefetch or intent flag, parent data (because there are no layout loaders), and documented cookie and abort-signal access.

## Return types and serialization

| Framework | Wire format | Documented types beyond JSON | Promises in data | Custom types | Notes |
|---|---|---|---|---|---|
| **Void** | `JSON.stringify` → `<script type="application/json">` (initial); JSON or NDJSON (navigation) | **none**. `Serialize<T>` types `Date` as `string` and drops `bigint`, functions and `undefined`. At runtime `JSON.stringify` turns `Map`/`Set` into `{}` and **throws** on `BigInt` | top-level `defer()` keys only | none | pages/serialize.ts, pages/protocol.ts `pageJsonResponse`. A JSON-200 `Response` from a loader is parsed into props. |
| **Next.js** | RSC Flight | "React-serializable" props, including promises (inventory). Per React's own docs (not re-checked here), that also covers `Date`, `Map`, `Set`, JSX and Server Function references | ✓ (promise props + `use()`) | `experimental.taint` blocks values | |
| **React Router** | turbo-stream (Single Fetch `.data`; one request per navigation, confirmed in CHANGELOG) | promises, `Map`, `Set`, `Date`, … ("aligned with RSC serializable types") | ✓ nested | — | |
| **TanStack Start** | router serializer | `undefined`, `Date`, `Error`, `FormData` (docs say `Map`/`Set`/`BigInt` need a custom serializer) | ✓ unawaited promises | not yet documented (RSC payloads use Flight) | |
| **Nuxt** | devalue payload (`__NUXT_DATA__`; `_payload.json`) | `Date`, `Map`, `Set`, `RegExp`, refs / `reactive`, `NuxtError` | ✗ | `definePayloadPlugin` + reducers/revivers | Server-route bodies are JSON. `pick`, `transform` and `serialize: false` (v4.6) trim the payload. Nuxt 5 makes payload extraction default to `'client'`. |
| **SvelteKit** | devalue | `Date`, `Map`, `Set`, `BigInt`, `RegExp`, `URL`, cyclic refs | ✓ server load, top-level or nested | `transport` hook (encode/decode) | A universal load may return non-serializable values such as classes or components. |
| **SolidStart** | Seroval (`serialization.mode: 'json'`, the v2 default, or `'js'`) | Seroval types + web types (`Headers`, `Request`, `Response`, `URL`, `FormData`, …), `Temporal` | ✓ nested in server-fn returns | `serialization.plugins` (`createPlugin`) | Binary and form types bypass Seroval. |
| **Astro** | island props attribute; Actions use devalue | `Map`, `Set`, `RegExp`, `Date`, `BigInt`, `URL`, typed arrays, `Infinity` | ✗ | — | Functions and cyclic structures are not supported. |

**Behavioral differences that matter:** Void is the only framework whose page data is plain JSON. A loader that returns a `Date` gives the component a string. The types say so, but it is a common source of bugs. Returning a `BigInt` crashes the response.

**Void gap: missing.** Void has no rich serializer and no custom-type hook. Since the client reads the payload with `JSON.parse`, switching to devalue, Seroval or turbo-stream would change the wire protocol: the initial `<script>`, the JSON and NDJSON navigation payloads, the prefetch payload, and the static `/_void/pages/*.json` files.

## Request deduplication

| Framework | Server (within one request) | Client | Notes |
|---|---|---|---|
| **Void** | No memo layer. N/A in practice with one loader. A `defer('group', fn)` group makes one resolver call for all its keys. Typed `fetch` to the app's own routes runs in-process but is not memoized | Prefetch cache keyed `METHOD:url`: concurrent prefetches share one promise, and a visit consumes a usable entry | pages/prefetch.ts |
| **Next.js** | `fetch` GET is memoized per render pass; `React.cache()`; `use cache: private` | Router cache; shared layouts deduplicated across prefetches (v16) | |
| **React Router** | none documented; Single Fetch coalesces all loaders into one request | A fetcher cancels its own pending request; stale revalidations are discarded | |
| **TanStack Start** | none for server fns or `fetch` (`React.cache` in RSC [exp]) | In-flight loader work for a match (path + params + `loaderDeps`) is shared by preload and navigation | Not shared across routes. |
| **Nuxt** | The same key is deduped within the SSR pass; `$fetch` to own routes runs in-process | Same key shares refs; `dedupe: 'cancel'` (default) or `'defer'` | `useFetch` keys include the call site, so two components fetching one URL make two requests unless they share `key`. |
| **SvelteKit** | Server loads coalesced; SSR `fetch` replayed during hydration; remote `query` cached per request, plus `query.batch` [exp] | Shared remote-query instance [exp]; preload reused | |
| **SolidStart** | `query()` request-scoped | Query cache by name + args | |
| **Astro** | not documented | — | |

**Void gap: partial.** This matters only once there are several data sources per request, such as layout loaders. Then Void would need request-scoped memoization like Next.js's `React.cache`, SolidStart's `query()` or Nuxt's keys.

## Client data cache (stale time, GC, keys)

| Framework | What is cached | Key | Freshness default | Retention | Back/forward | Controls |
|---|---|---|---|---|---|---|
| **Void** | **prefetched page objects only** | `METHOD:url` (full URL including query) | `cacheFor` `'30s'`; `cacheFor: [fresh, expire]` serves stale entries while refetching in the background; `0` = single-use | Timer deletes the entry at `expire` | **refetch**: visited pages are not cached | `Link cacheFor`, plugin `prefetch.cacheFor`; `router.flush(url)`, `flushAll()`; any non-GET visit flushes everything. The engine's `cacheVisitedPageData` option (reuse visited GET page objects, SWR) exists but is **not wired** to any plugin option (pages/navigation-engine.ts; only `react/src/runtime/pages-client.ts` passes it through). |
| **Next.js** | RSC payloads of visited and prefetched segments; layouts and loading states reused; pages not cached by default | segment | `cacheLife` `stale` (≥30 s enforced); `staleTimes` [exp]: dynamic 0 s, static 300 s | session; cleared by a hard refresh | reused | Any revalidation call from an action **clears the whole client cache**. |
| **React Router** | **none** (docs call client caching "redundant" given revalidation) | — | — | — | refetch | DIY `clientLoader` cache; `unstable_fetch` `force-cache` on POP [exp]; HTTP cache |
| **TanStack Start** | SWR router cache of loader data + preload lanes | path params + `loaderDeps` | `staleTime` 0 (background reload on re-entry); `preloadStaleTime` 30 s | `gcTime` 5 min; `preloadGcTime` 5 min | cached data shown, reloaded if stale | per route + router defaults; `shouldReload`; `staleReloadMode: 'background' \| 'blocking'` |
| **Nuxt** | `payload.data` / `static.data` per key | key | until refreshed | `purgeCachedData` (on by default) clears it on navigation | setup re-runs; `getCachedData` can serve it; `<KeepAlive>` | `getCachedData(key, nuxtApp, { cause })`; `useNuxtData` |
| **SvelteKit** | Load results are kept **until their tracked dependencies change**; remote queries live while in use [exp]; remote `prerender` results go in the Cache API | dependencies; query args | no TTL | — | not documented | — |
| **SolidStart** | query cache | `name` + `JSON.stringify(args)` (sorted keys) | preload reuse 5 s (fixed) | GC 3 min without subscribers (fixed) | **reused without calling `fn`** | `query.set/get/delete/clear`; `revalidate` |
| **Astro** | none (ClientRouter fetches full HTML) | — | — | — | HTTP cache | — |

**Behavioral differences that matter:**
- In Void, every back/forward or repeat visit runs the loader again. Next.js, TanStack Start and SolidStart reuse the data.
- Void's `[fresh, expire]` pair is the most ergonomic per-link SWR control here. It applies only to prefetched entries, and a background refresh updates the cache entry, not the page on screen.

**Void gap: partial.** Missing: a visited-page cache with back/forward reuse (Next.js, TanStack Start, SolidStart), a cache key or invalidation API other than the URL, and GC/stale settings for visited data. The engine option is a cheap first step.

## Deferred and streamed data

| Framework | API | Where promises can appear | When the work starts | Ordering | Errors | Timeout | Prefetch interaction | After a mutation |
|---|---|---|---|---|---|---|---|---|
| **Void** | `defer(fn)` or `defer('group', fn)`; each resolver receives `c` | **top-level loader keys only** (pages/defer.ts `separateDeferred`) | **After** the loader returns and the first chunk is built: page JSON, or the rendered HTML/shell (pages/protocol.ts `streamDeferredResponse`) | Completion order: inline `<script>` for HTML, NDJSON lines for navigation | React: `use()` throws → error boundary. Vue/Svelte/Solid: `{ error }`. Production masks non-`HTTPException` messages as `Internal Server Error` | none | The prefetch response **resolves every group inline**, so it waits for the slowest one. Per-group failures go to `deferredErrors` | Deferred props are **stripped** from mutation responses and **keep their last values** until the next navigation |
| **Next.js** | Suspense + async components; promise props + `use()` | anywhere | when created | out-of-order (Suspense) | nearest `error.js` / `catchError` | — | Prefetch goes down to `loading.js` or the App Shell | Revalidation re-renders |
| **React Router** | Un-awaited promises nested in the loader return (a bare top-level promise is not allowed); `<Await>` / `use()` | nested in the returned object | when created; streaming **starts after all loaders settle** | as they resolve | `errorElement` or route `ErrorBoundary` | `streamTimeout` (default 4950 ms) | `<link rel=prefetch>` of `.data` | All loaders re-run (including deferred) |
| **TanStack Start** | Un-awaited promises; `<Await>` / `use()`; server-fn `ReadableStream` / async generators | anywhere | when created | as they resolve | nearest error boundary; serialized error | — | Promises share the loader cache lifecycle and can be preloaded | `router.invalidate()` re-runs |
| **Nuxt** | No promise streaming: use `lazy`, `server: false` or `immediate: false` (client fetch). `ssrStreaming` [exp] streams Suspense HTML | — | — | — | `error` ref | — | — | — |
| **SvelteKit** | Promises from **server** load, top-level or nested; `{#await}` | server load | when created | as they resolve | `{:catch}` | — | preload runs load | Loads re-run |
| **SolidStart** | Suspense around `createAsync` reads; promises nested in server-fn returns; `deferStream: true` opts back into blocking | anywhere | when the query starts | out-of-order HTML | `<ErrorBoundary>` | — | `preload` warms queries | `revalidate` |
| **Astro** | In-order HTML streaming of async components; server islands (`server:defer`) | components | when rendered | document order | — | — | — | — |

**Behavioral differences that matter:**
- Void's resolvers start only after the loader returns and after the initial HTML render or page JSON. That is later than in React Router, TanStack Start, SvelteKit or SolidStart, where a promise begins work as soon as the loader creates it. A deferred request in Void therefore never overlaps the loader's own `await`s or the SSR render.
- Void's `defer('group', fn)` lets one slow call feed several props, a pattern no peer has as an API. Prefetch blocking on all deferred groups trades prefetch latency for an instant transition.
- Adapter difference: React has true Suspense streaming SSR. Vue, Svelte and Solid buffer component HTML, and only the deferred data streams.
- With `output: "static"`, the prerendered `/_void/pages/*.json` files carry deferred values already resolved. Page data parsed from HTML is not reused when it has deferred keys, and the (unexposed) visited-page cache skips deferred pages (pages/navigation-engine.ts). ISR caches the whole streamed response (area 5).

**Void gap: partial.** Missing options: promises nested inside props, start-at-creation semantics (let `defer` take an already-started promise), a stream timeout (React Router `streamTimeout`), and re-resolving deferred props after a mutation (React Router, TanStack Start and SvelteKit re-run them).

## Dependency tracking and invalidation

| Framework | Automatic tracking | Targeted invalidation | Revalidate all | Notes |
|---|---|---|---|---|
| **Void** | none | `router.flush(url[, method])` drops **only the prefetch entry**, not live data | `router.refresh(options?)` re-runs the current page loader (same history entry; keeps state and scroll); `router.flushAll()` empties the prefetch cache | Server HTML cache: `revalidate({ paths \| all })` from `void/isr` (area 5). |
| **Next.js** | none (explicit) | `revalidateTag` / `updateTag` (tags from `cacheTag()` or `fetch` `next.tags`), `revalidatePath`; implicit soft tags per path | `router.refresh()`, `refresh()` | Server caches and the client cache together. |
| **React Router** | none (router-driven) | per-route opt-out with `shouldRevalidate` | `useRevalidator().revalidate()` (window focus, polling) | Hot Data Revalidation in dev. |
| **TanStack Start** | path params + explicit `loaderDeps` | `router.invalidate({ filter, sync, forcePending })`, `router.clearCache({ filter })` | `router.invalidate()` (also re-runs `beforeLoad`) | Covers committed, cached and in-flight generations. |
| **Nuxt** | reactive `key`, reactive fetch options (auto-watched), `watch: [...]` | `refreshNuxtData(keys)`, `clearNuxtData(keys \| predicate)`, instance `refresh()` | `refreshNuxtData()` | `enabled` gate (v4.5). |
| **SvelteKit** | **fine-grained**: `params.x`, `url` properties, `searchParams` keys, `parent()`, URLs fetched in **universal** loads | `invalidate(url \| 'app:id' \| predicate)` + `depends()`; `untrack()` | `refreshAll()` (also refreshes active remote queries) | Server loads never auto-depend on fetched URLs. |
| **SolidStart** | reactive reads inside `createAsync` | `revalidate(key \| keys, force?)` with prefix matching (`q.key`, `q.keyFor(args)`) | `revalidate()` | Only refetches entries that have active subscribers. |
| **Astro** | none for render data | server route cache `cache.invalidate({ tags \| path })` | — | |

**Void gap: partial.** Revalidate-all exists through `router.refresh()`. Missing: invalidation by key, tag or URL of *live* data (5 peers); automatic dependency tracking (3 peers); refreshing only some props (Inertia-style partial reload; `refresh()` has no `only` option, client.ts `refresh(options?: VisitOptions)`).

## Revalidation policy on navigation

| Framework | Default on client GET navigation | Back/forward | Per-route control | Call-site control |
|---|---|---|---|---|
| **Void** | Always fetch the destination page object (loader + middleware) unless a usable prefetch entry exists | refetch | none | `Link prefetch` / `cacheFor`; `reloadDocument` |
| **Next.js** | Layouts are reused (partial rendering); page segments are refetched unless still within their stale time | router cache | `cacheLife` stale; segment `export const prefetch` | `<Link prefetch>`; `router.prefetch(href, { kind })` [EXP: 16.5 canary] |
| **React Router** (SSR) | **All active loaders** on every navigation | all loaders | `shouldRevalidate({ currentUrl, nextUrl, currentParams, nextParams, formMethod, formAction, formData, json, text, actionResult, actionStatus, defaultShouldRevalidate })` | `defaultShouldRevalidate` on `<Form>`, `<Link>`, `useSubmit`, `fetcher.submit`, `useNavigate` |
| **TanStack Start** | SWR: show cached data, reload in the background when stale (`staleTime` 0) | cached | `staleTime`, `gcTime`, `shouldReload`, `staleReloadMode`, `loaderDeps` | `router.invalidate`, `router.load` |
| **Nuxt** | The new page's composables run; persistent layouts don't re-run unless their key or watch sources change | setup re-runs | `getCachedData`, `watch: false`, `key` | — |
| **SvelteKit** | Only loads whose **tracked dependencies changed** | loads re-run | implicit (tracking + `untrack`) | `goto(url, { refreshAll })` |
| **SolidStart** | Route `preload` runs; queries reuse fresh entries (5 s preload window, active subscribers) | reused | — | `revalidate` |
| **Astro** | Full document (MPA), or ClientRouter fetches the full HTML | HTTP cache | — | — |

**Behavioral differences that matter:** Void behaves like React Router's SSR default (re-run everything), but with one loader there is little to skip. Once layouts get loaders, Void will need either SvelteKit-style tracking or React Router-style `shouldRevalidate`, or every navigation will re-run every layout loader.

**Void gap: missing.** Void has no per-route or call-site revalidation policy. Today that is low impact; it becomes required alongside layout loaders.

## Data for layouts and shared data

| Framework | Layout-level data | Global shared data | How children reach parent data | Re-run behavior |
|---|---|---|---|---|
| **Void** | ✗ | Middleware `c.set('shared', {...})` → `useShared()`, typed through `CloudContextVariables` | n/a | Global middleware runs once per request, including JSON navigations and prefetches. An action's loader re-run does not run it again; update `shared` in the action, or redirect |
| **Next.js** | Layout Server Components | Root layout / context providers; promise shared via context | `React.cache` dedupe | Layouts are not re-rendered on navigation |
| **React Router** | Layout-route loaders | Root loader; middleware `context` | Client: `useRouteLoaderData(id)`, `useMatches()`. Server: middleware context | Revalidated on every navigation by default |
| **TanStack Start** | Layout-route `loader` / `beforeLoad` | Router `context` (DI) | `beforeLoad` context merged downward; `parentMatchPromise` | SWR |
| **Nuxt** | Composables in layouts | `useState`, plugins, `callOnce` | Shared keys | The layout instance persists |
| **SvelteKit** | `+layout(.server).js` load | Root layout; `page.data` | `parent()`; `page.data` (ancestors read descendant data) | Re-runs only when its dependencies change |
| **SolidStart** | Parent route `preload` + queries | `rootPreload` | Shared query keys | Query cache |
| **Astro** | Layout frontmatter | Middleware `locals` | Props | Per request |

**Void gap: missing** (see "Data-loading model" above). `useShared()` covers auth and the user, but it cannot load data for a section such as `/dashboard/**` without running for every request.

## Preload hooks (prefetch × data)

| Framework | Triggers | What a prefetch runs | Loader-side control | Freshness of prefetched data | Manual API |
|---|---|---|---|---|---|
| **Void** | `hover` (75 ms; also focus and `touchstart`), `click` (`mousedown`/`touchstart`), `mount`, `visible`, or an array (first trigger wins); default `false` | Page and layout chunks **in parallel with** the page JSON (loader runs; deferred resolved inline). Island targets get `<link rel=prefetch as=document>`. Static builds use `/_void/pages/*.json` | none (undocumented `Purpose: prefetch` header) | `cacheFor` (`'30s'`; `[fresh, expire]` SWR; `0` single-use) | `router.prefetch(dest, { cacheFor })`, awaitable |
| **Next.js** | viewport + hover; Partial Prefetching App Shell / per-link | RSC segments (static down to `loading.js`) | `export const prefetch = 'partial' \| 'force-disabled'`; `await prefetch()` / `await navigation()` [CC] | stale time; `onInvalidate` | `router.prefetch(href, { kind?, onInvalidate? })` |
| **React Router** | `none` (default) \| `intent` \| `render` \| `viewport` | modules + loader data through `<link rel=prefetch>` / `modulepreload` | — | browser HTTP cache | `<PrefetchPageLinks page>` |
| **TanStack Start** | `intent` (50 ms) \| `viewport` \| `render` | chunk + every `beforeLoad` + `loader` | `preload` / `cause` args; route `preload: false` skips the loader | `preloadStaleTime` 30 s, `preloadGcTime` 5 min; navigation re-runs `beforeLoad` but can reuse loader data | `router.preloadRoute()`, `loadRouteChunk()` |
| **Nuxt** | visibility (default) / interaction; idle-only; skipped on 2G or save-data | chunks + middleware + layouts + `_payload.json` (prerendered or ISR routes only) | `link:prefetch` hook | static cache | `preloadRouteComponents()` |
| **SvelteKit** | data: `hover` / `tap`; code: `eager` / `viewport` / `hover` / `tap` | load functions | — | reused by the next navigation | `preloadData(href)` (returns the result), `preloadCode(routeId)` |
| **SolidStart** | hover (~20 ms) / focus | route `preload` with `intent: 'preload'` | `intent` | 5 s | `usePreloadRoute()(url, { preloadData })` |
| **Astro** | hover / tap / viewport / load | full HTML document | — | HTTP cache | `prefetch(url, { eagerness })` (`clientPrerender` [exp]) |

**Void gap: partial.** Prefetching is strong. Missing: a documented prefetch flag for loaders (TanStack Start, SolidStart), and per-route opt-out of data prefetch (TanStack Start route `preload: false`, Next.js `force-disabled`).
