# Next.js (App Router) — feature inventory
Version documented: **16.4** (stable), with a few 16.5-canary items. How I determined it: version-history tables across `docs/01-app` top out at `v16.4.0` (~15 entries, e.g. `ensureStatic`, `prefetch()`/`navigation()`, `next analyze export`); there is exactly one `v16.5.0` entry (the `kind` option on `router.prefetch`), which reads as in-flight canary work. The upgrade guides target 16 (`G/upgrading/version-16.mdx`), and `G/ai-agents.mdx` describes 16.2/16.3 features as shipped. · Docs commit: 2026-11-03 (`a4795950`, sparse clone of vercel/next.js `docs/`)
Context: React only. The App Router bundles React canary; the docs cite React 19.2 (v16 upgrade) and React 19.3 (`<ViewTransition>`, `browser()`). Bundler: **Turbopack** by default, Webpack via `--webpack`. Server engine: the built-in Next.js Node server (`next start`), with an optional custom server or a standalone `server.js`. Default runtime: **Node.js ≥ 20.9**. The Edge runtime is deprecated. Go Route Handlers are experimental.

Path abbreviations (relative to repo root): `GS/` = `docs/01-app/01-getting-started/`, `G/` = `docs/01-app/02-guides/`, `FC/` = `docs/01-app/03-api-reference/03-file-conventions/`, `SEG/` = `FC/02-route-segment-config/`, `FN/` = `docs/01-app/03-api-reference/04-functions/`, `CMP/` = `docs/01-app/03-api-reference/02-components/`, `CFG/` = `docs/01-app/03-api-reference/05-config/01-next-config-js/`, `ADP/` = `docs/01-app/03-api-reference/07-adapters/`, `DIR/` = `docs/01-app/03-api-reference/01-directives/`.

**The big switch:** most behavior now depends on **Cache Components** (`cacheComponents: true`). It is stable since 16.0, on by default in `create-next-app` (`--cache-components`), and works with **Partial Prefetching** (`partialPrefetching: true`, added in 16.3). Docs say both "will be enabled everywhere in the next major release, and the options will be removed" (`CFG/cacheComponents.mdx`, `CFG/partialPrefetching.mdx`). Many APIs exist only with Cache Components. The pre-16 "previous model" (`dynamic`, `revalidate`, `fetchCache` segment exports, fetch caching, `unstable_cache`) is still documented in `G/caching-without-cache-components.mdx`. Below, **[CC]** marks Cache-Components-only behavior and **[prev]** marks previous-model behavior.

---

## 1. Routing

- **Route definition / file conventions**: Supported (file-based only). Folders under `app/` (or `src/app/`) are URL segments. A segment becomes public only when it has a `page` file (`.js/.jsx/.tsx`) or a `route` file (`.js/.ts`). Special files: `layout`, `page`, `loading`, `not-found`, `error`, `global-error`, `route`, `template`, `default`, plus experimental `global-not-found` and `forbidden`/`unauthorized`. Render hierarchy inside a segment: `layout` > `template` > `error` (boundary) > `loading` (Suspense) > `not-found` > `page`/child layout. Colocation is safe because non-special files are never routed. `_folder` makes a folder private (excluded from routing); `%5Ffolder` gives a URL segment that starts with `_`. A `page` and a `route` cannot coexist in the same segment ("Conflict"). Routes in different groups must not resolve to the same URL (error). A config- or code-based route API is **not found in docs**; `rewrites` and a custom server are the only programmatic mapping. `pageExtensions` applies to the Pages Router (and to MDX setup); the Proxy and instrumentation filenames must follow it. Source: `GS/02-project-structure.mdx`, `FC/page.mdx`, `FC/route-groups.mdx`, `GS/15-route-handlers.mdx`.
  - **Experimental `route.go`**: Go Route Handlers. Requires `experimental.goRoutes` and Turbopack, plus Go 1.24+ at dev/build time. Each route directory is a `package main` with `GET/POST/...(w http.ResponseWriter, r *http.Request)` functions. Behavior: HEAD without a handler falls back to GET with the body suppressed; OPTIONS without a handler returns `204` with a sorted `Allow` header; any other unhandled method returns `405`. Parameters are read with `r.PathValue()` or the generated `ParamValues(r,name)`. Go handlers are always dynamic: no ISR, no `generateStaticParams`, no segment config. Unsupported: static export, `output:'standalone'`, WebSocket upgrades, CGO, cross-compilation. Adapters must support `runtime:'go'`. Source: `FC/route-go.mdx`.
- **Nested layouts**: Supported. `layout.js` receives `children` (required) and `params` (a Promise). The root layout is required and must render `<html>` and `<body>`. Do not hand-write `<head>` tags; use the Metadata API. You can have **multiple root layouts** (via groups, or by omitting `app/layout`). Navigating *across* root layouts triggers a **full page load**. Layouts **do not re-render on navigation**. As a result they get no `searchParams`, no pathname, and no request object (read `headers()`/`cookies()` instead). They cannot pass data to `children` (refetch and dedupe with `fetch` memoization or `React.cache`), and they cannot see child segments (use `useSelectedLayoutSegment(s)` in a client component). Interaction with `loading.js`: uncached or runtime data in a layout is not covered by the same segment's `loading.js`. [prev] navigation then blocks; [CC] it must be wrapped in its own `<Suspense>`, or the build errors. Type helper: global `LayoutProps<'/route'>` types `params` and **named parallel slots**. Source: `FC/layout.mdx`.
  - **`template.js`**: a layout-like wrapper with a unique key per segment level. It remounts when *its* segment, including that segment's dynamic params, changes. Deeper navigations do not remount higher templates, and search-param changes do not trigger remounts. On remount, client state resets, effects re-run, and the DOM is recreated. Suspense fallbacks inside a template show on every navigation; inside a layout they show only on first load. Source: `FC/template.mdx`.
- **Dynamic, optional and catch-all segments**: Supported. `[slug]` gives `{slug:string}`, `[...slug]` gives `{slug:string[]}`, and `[[...slug]]` gives `{slug?:string[]}` (`/shop` → `undefined`). Values are passed as a **Promise** `params` to `layout`, `page`, `route`, `default`, `generateMetadata`, and image routes. Since v15 they must be awaited or read with `use()`; sync access in 15 is a compat shim slated for deprecation. Optional *single* segments (e.g. `[[id]]` on its own) are not found in docs; only optional catch-all exists. **Root params**: dynamic segments above the root layout (e.g. `app/[lang]/layout`) can be read from any Server Component via `next/root-params` getters (`import { lang } from 'next/root-params'`, async; added 16.3). Getter names must be valid JS identifiers (kebab-case segments are an error). Root params are not available in Client Components, Server Actions, or Route Handlers ("planned"). A `use cache` key includes only the root params a function actually reads. With multiple root layouts, the type is `string|undefined`. Source: `FC/dynamic-routes.mdx`, `FN/next-root-params.mdx`.
- **Route groups / pathless layouts**: Supported. `(folder)` is omitted from the URL. Uses: section layouts, opting a subset of routes into a layout or `loading.js`, multiple root layouts. If you use multiple root layouts with no top-level layout, `/` must live inside a group. Source: `FC/route-groups.mdx`.
- **Parallel routes**: Supported. `@slot` folders become props on the parent layout. `children` is an implicit slot (`app/page` ≡ `app/@children/page`). Slots do not affect URLs. All slots at a level must share one static/dynamic mode ("if one slot is dynamic, all slots at that level must be dynamic"). **Soft navigation** keeps each slot's active subpage even when it no longer matches the URL. **Hard navigation** (reload) renders the slot's `default.js`. Without one, a named slot is an **error** (a v16 change; previously 404), and the `children` slot gives a 404. Writing a `default.js` that calls `notFound()` restores the old behavior. Each slot can have its own `layout` (tab groups), `loading`, and `error`, and slots stream independently. Conditional slots (e.g. role-based) **all render on the server and are included in the response** regardless of which one the layout returns, so authorization must happen inside each slot. `useSelectedLayoutSegment(s)(parallelRouteKey)` reads a slot's active segment. Source: `FC/parallel-routes.mdx`, `FC/default.mdx`.
- **Intercepting routes (modals)**: Supported. `(.)x` matches the same level, `(..)x` one level up, `(..)(..)x` two levels up, and `(...)x` the app root. Matching is by *route segments*, not the filesystem (`@slot` folders don't count). Combined with parallel routes you get deep-linkable modals: client navigation shows the intercepted modal, while a refresh or direct visit shows the full page. Close a modal with `router.back()`, or by making the slot match a `null`-returning `page`/catch-all (`@auth/[...catchAll]/page`). Interception relies on the `next-url` request header, which CDNs must forward or interception silently degrades to the target page. **Not supported with static export.** Source: `FC/intercepting-routes.mdx`, `G/cdn-caching.mdx`, `G/static-exports.mdx`.
- **Typed links / typed params**: Supported, stable. `typedRoutes: true` (formerly `experimental.typedRoutes`; TypeScript required) generates a route union in `.next/types`. It validates literal `href` strings (including dynamic segments) on `<Link>` and the `next/navigation` `push/replace/prefetch` methods. Non-literals need a cast `as Route`, and wrapper components can use a generic `Route<T>`. `next/router` is not typed. Typed params come from global `PageProps<'/blog/[slug]'>`, `LayoutProps<'/x'>`, and `RouteContext<'/x'>`. Types are generated by `next dev`, `next build`, or `next typegen`. A static route's `params` is `{}`. Source: `CFG/typedRoutes.mdx`, `docs/01-app/03-api-reference/05-config/02-typescript.mdx`, `FC/page.mdx`.
- **Search params**: Partial (untyped and unvalidated). `page` gets a `searchParams` Promise that resolves to a plain object (`?a=1&a=2` → `{a:['1','2']}`). It is a request-time API: [prev] it makes the page dynamic; [CC] the read location determines the static-shell boundary. Only `page` (and `generateMetadata` of a page) receive it, layouts do not. In client components, `useSearchParams()` returns a read-only `URLSearchParams`. During prerender it client-renders up to the nearest `<Suspense>`; without a boundary, a static page **fails the build** ("Missing Suspense boundary with useSearchParams"). [CC] If any other part of the route reads request data, the boundary is server-rendered with the real params instead. Updates go through `<Link>`, `router.push`, `<Form action="">` (GET), or native `history.pushState/replaceState` (synced with `usePathname`/`useSearchParams`). A schema, validation, or typed search-param API is **not found in docs**; `PageProps` types it as a generic record. Source: `FC/page.mdx`, `FN/use-search-params.mdx`, `GS/04-linking-and-navigating.mdx`.
- **Programmatic navigation**: Supported. `useRouter()` from `next/navigation` (client only) provides:

  | method | behavior |
  |---|---|
  | `push(href, {scroll?, transitionTypes?})` | client navigation that adds a history entry; `transitionTypes` is passed to `React.addTransitionType` |
  | `replace(href, opts)` | same, without a new history entry |
  | `refresh()` | re-requests the current route's RSC, re-runs Server Components, and merges while preserving client state and scroll; clears the Client Cache for the current route; **does not** invalidate the server cache |
  | `prefetch(href, {kind?: 'auto'\|'full', onInvalidate?})` | `onInvalidate` (15.4) is called at most once when the prefetched data goes stale; `kind:'full'` (16.5) matches `<Link prefetch={true}>` |
  | `back()` / `forward()` | history traversal |
  | `bfcacheId` | opaque per-segment id that changes on fresh push/replace and stays stable on back/forward, `refresh`, or search/hash-only changes; use it as a React `key` to reset state on fresh navigations only |

  There are no `router.events`; compose `usePathname` + `useSearchParams` instead, or use `onRouterTransitionStart` in `instrumentation-client`. `javascript:` URLs passed to push/replace execute, so the docs warn about XSS. Server side: `redirect()`/`permanentRedirect()` (see §7). Source: `FN/use-router.mdx`.
- **Prefetching**: Supported, with an extensive, layered model. **Prefetching runs in production only.**
  - `<Link prefetch>` values: `"auto"`/`null` (default) = static route prefetched in full; dynamic route prefetched only down to the nearest `loading.js` (skipped if there is none). `true` = full route for static and dynamic. `false` = never, neither on viewport entry nor on hover. Prefetch fires when a link enters the viewport. If the data has expired, hovering re-prefetches. Prefetching starts only after `<Link>` hydrates. Source: `CMP/link.mdx`.
  - Scheduler: a small task queue ordered as in-viewport links, then hovered or touched links, with newer links replacing older ones and links scrolled offscreen discarded. Since v16 shared layouts are **deduplicated** across prefetches and prefetching is **incremental** (only missing parts are fetched). The trade-off: more requests that are smaller. `experimental.prefetchInlining` (behavior on by default since 16.3; only the config is experimental) bundles small segment responses together, with `maxSize` 2048 B per segment gzip and `maxBundleSize` 10240 B; `false` gives one request per segment. Source: `G/prefetching.mdx`, `G/upgrading/version-16.mdx`, `CFG/prefetchInlining.mdx`.
  - **Partial Prefetching** (`partialPrefetching: true`, requires `cacheComponents`; unset logs a warning): a default `<Link>` prefetches one reusable **App Shell** per *route* (static, cached, and session content that doesn't depend on the link's URL). Links to the same route share it, and it is cached on the client. If the shell reads `cookies()` or `headers()`, it is cached per session. `<Link prefetch={true}>` or `router.prefetch(href,{kind:'full'})` adds a **per-link prefetch**: a server render with `params`, `searchParams`, and the URL resolved, which includes `use cache` / `use cache: private` content (costs a server invocation per link). Invalidations (`revalidateTag`/`revalidatePath`) silently refresh affected prefetches. Source: `CFG/partialPrefetching.mdx`, `GS/08-caching.mdx`.
  - Per-segment `export const prefetch = 'partial' | 'force-disabled'` ([CC]; stable 16.3; not allowed in client components). `'partial'` opts one route into Partial Prefetching. `'force-disabled'` never prefetches the segment's data (route metadata is still fetched), though a per-link prefetch of an ancestor still includes deeper force-disabled segments. Source: `SEG/prefetch.mdx`.
  - Stage-deferral functions from `next/cache` ([CC]; stable names in 16.4): `await prefetch()` keeps the code below it out of the App Shell but allows it in a per-link prefetch. `await navigation()` keeps it out of all prefetches until the user actually navigates. Both throw inside `use cache`, `after`, `generateStaticParams`, or client components, and both have no effect on initial page load. Source: `FN/prefetch.mdx`, `FN/navigation.mdx`.
  - `<Form>` (string `action`) prefetches its target's layout and loading UI when visible. Hover-only prefetch is a documented pattern: wrap `Link` with `prefetch={false}` and call `router.prefetch` on `onMouseEnter`. `useLinkStatus()` (from `next/link`, must be a descendant of `<Link>`) returns `{pending}`. Pending is skipped if the route was already prefetched, and only the last-clicked link shows pending. Source: `CMP/form.mdx`, `G/prefetching.mdx`, `FN/use-link-status.mdx`.
- **Scroll restoration**: Supported. `<Link scroll>` defaults to `true`, which *maintains* scroll if the new page is visible, otherwise scrolls to the first page element. The scroll target search skips sticky/fixed and non-visible elements; use CSS `scroll-padding-top` for sticky headers. `scroll={false}` (or `router.push(h,{scroll:false})`) disables this. Hash links scroll to `id`. Back/forward preserve position, and [CC] Activity keeps hidden routes mounted. Since v16 Next.js no longer temporarily overrides `scroll-behavior: smooth`; opt back in with `<html data-scroll-behavior="smooth">`. Source: `CMP/link.mdx`, `G/upgrading/version-16.mdx`.
- **View transitions**: Supported, no config. React's `<ViewTransition>` and `addTransitionType` (React 19.3, bundled canary) work because App Router navigations are transitions. `<Link transitionTypes={['nav-forward']}>` (16.2) and `router.push/replace(..., {transitionTypes})` tag navigations. Browser back/forward carries no type. A shared-element morph happens only when the destination renders in the same commit, i.e. a prefetched/cached destination; if it suspends into a fallback, it plays an enter animation instead. Enter/exit wrappers belong in `page`, not `layout`, because layouts persist. No `experimental.viewTransition` flag found. Source: `G/view-transitions.mdx`, `CMP/link.mdx`.
- **Route-level code splitting**: Supported automatically per route segment. `next/dynamic` and `React.lazy` cover component-level splitting. `next/dynamic(..., {ssr:false})` is allowed only in Client Components (it errors in Server Components). Turbopack dev has `experimental.turbopackLazyDynamicImports` / `turbopackLazyDynamicImportsSSR` (16.4) to compile dynamic imports on first request. Source: `G/prefetching.mdx`, `G/lazy-loading.mdx`, `CFG/turbopackLazyDynamicImports.mdx`.
- **Base path**: Supported. `basePath: '/docs'` is a build-time setting inlined into client bundles. It auto-prefixes `next/link` and `next/router` hrefs and config `redirects`/`rewrites`/`headers` (opt out per rule with `basePath:false`). It is **not** applied to `next/image` `src` or `<Form formAction>`; prefix those manually. Under Turbopack, `import.meta.env.BASE_URL` exposes it with a trailing slash. Separate `assetPrefix` serves assets from a CDN. Source: `CFG/basePath.mdx`, `CMP/form.mdx`, `docs/01-app/03-api-reference/08-turbopack.mdx`.
- **Notable extras**:
  - **State preservation with React `<Activity>`** [CC]: routes you navigate away from are set `hidden` instead of unmounted. State persists, effects are cleaned up and re-created on re-show, and a heuristic keeps a few recent routes while older ones leave the DOM. This affects dropdowns, dialogs, and test selectors (`G/preserving-ui-state.mdx` has patterns). Source: `CFG/cacheComponents.mdx`.
  - `<Link onNavigate={e => e.preventDefault()}>` (15.3) blocks client navigation, e.g. unsaved-changes guards. It doesn't fire for modifier-clicks, external URLs, or `download` links. Source: `CMP/link.mdx`.
  - **Offline support** (experimental `experimental.useOffline`): detects connectivity through `offline`/`online` events and failed fetches, polls with `HEAD` and backoff, and auto-retries blocked navigations, prefetches, and Server Actions. Exposes `useOffline()` from `next/offline`, which is always `false` without the flag. Source: `CFG/useOffline.mdx`, `FN/use-offline.mdx`.
  - **Instant-navigation validation** (`export const instant`, see §2), **Multi-Zones** (several Next.js apps under one domain via rewrites/proxy; `G/multi-zones.mdx`), `useSelectedLayoutSegment(s)`, `usePathname`, and `useParams` (in [CC] it suspends for params not covered by `generateStaticParams`).

## 2. Rendering modes

- **SSR**: Supported, the default. Layouts and pages are React Server Components. The server renders the RSC Payload plus HTML on first load. Later navigations fetch only the RSC payload; client components then render purely on the client. Rendering is split per route segment, and parallel slots render whether or not they are shown. Source: `GS/05-server-and-client-components.mdx`, `GS/04-linking-and-navigating.mdx`.
- **Streaming SSR**: Supported via React Suspense: `loading.js` wraps the page in `<Suspense>`, or use explicit `<Suspense>` boundaries. Behavior details:
  - **Status code is fixed when streaming starts.** Streaming responses begin with `200`. `notFound()`/`forbidden()`/`unauthorized()`/`redirect()` after that point are streamed: an HTML `<meta name="robots" content="noindex">` for 404s, or a meta redirect for redirects. [prev] streaming starts when a `loading`/`Suspense` fallback renders. [CC] the prerendered shell is sent first, so request-time checks inside the page keep `200` *even if the shell is empty*. Only interrupts that run during prerendering keep their status. To get a real 404/401/403, check in Proxy first. Source: `FC/loading.mdx`, `FN/not-found.mdx`.
  - **Bots**: HTML-limited bots (default UA list; override with `htmlLimitedBots` regex) get blocking metadata in `<head>`, and with PPR they skip the static shell and get a request-time render. Data sources used at build time must be reachable at request time, or those bots get a 500. Source: `GS/08-caching.mdx`, `FN/generate-metadata.mdx`.
  - Some browsers buffer streams until 1024 bytes. Self-hosting needs proxy buffering disabled (nginx `X-Accel-Buffering: no`) and LBs that pass chunked responses through. Source: `FC/loading.mdx`, `G/self-hosting.mdx`.
- **Static prerendering incl. dynamic params**: Supported. `generateStaticParams()` (pages, layouts, route handlers) returns `{param: string | string[]}[]`. Parent→child chaining is supported: a child's `generateStaticParams` gets the parent's `params` and runs once per parent set. Dev calls it on navigation; build runs it before rendering; ISR does not re-call it. [prev] An empty array means "render all on first visit", and **you must return an array or the route is dynamic**. `dynamicParams` (default `true`; `false` returns 404 for unlisted params) is **[prev] only**. [CC] it must return **≥1 param set** (an empty array is a build error) so the build can validate runtime-API use. Unlisted params serve the App Shell immediately, render in the background, are saved to disk, and are reused. Build validation only covers code paths exercised by the sample params; other branches validate on their first request. `fetch` in `generateStaticParams` is memoized. Source: `FN/generate-static-params.mdx`, `FC/dynamic-routes.mdx`, `SEG/dynamicParams.mdx`.
- **Client-only / SPA**: Partial. Client Components are still SSR-prerendered. To skip SSR for a component use `next/dynamic(..., {ssr:false})`, `useEffect` guards, or React 19.3 `use(browser())`, which suspends during prerender so the fallback becomes the HTML. `output:'export'` gives a static multi-page SPA with one HTML file per route and client navigation. A "single `index.html`" strict-SPA mode or a per-route "client-only" flag is **not found in docs**. Source: `G/single-page-applications.mdx`, `G/static-exports.mdx`.
- **Partial hydration**: Supported via **React Server Components**. Server Components ship no JS. `'use client'` marks a module-graph boundary: everything that module imports and directly renders becomes client code, while Server Components passed as `children`/props stay server-rendered. React Selective Hydration prioritizes by interaction. Islands or `client:*`-style hydration directives are not found. Source: `GS/05-server-and-client-components.mdx`, `FC/loading.mdx`.
- **Static shell with dynamic holes (PPR)**: Supported, and the **default with Cache Components** (`experimental.ppr` and `export const experimental_ppr` were removed in 16.0). At build time the tree renders, and `use cache` output, `<Suspense>` fallbacks, and "predictable" work (module imports, `fs.readFileSync`, sync DB drivers, pure computation) go into a static shell (HTML + RSC). Uncached I/O, runtime APIs, and non-deterministic values (`Math.random`, `Date.now`, `crypto.randomUUID`; `performance.now` is exempt) must be either cached, or behind `<Suspense>` plus `connection()`/`io()`. Otherwise the dev overlay or build shows a **blocking-route insight** with fix cards. Every route must produce a non-empty static shell; validation is opt-out via `instant = false` high in the tree. Two shells are distinguished: the **static shell** (with known params) and the **App Shell** (URL-independent, served for unknown params and for prefetch). For adapters, `onBuildComplete` exposes `prerenders[].fallback.{filePath, postponedState}`, and the resume protocol is a POST with header `next-resume: 1` and body `postponedState`, which streams only the deferred boundaries. Source: `GS/08-caching.mdx`, `CFG/cacheComponents.mdx`, `ADP/06-implementing-ppr-in-an-adapter.mdx`, `ADP/07-runtime-integration.mdx`.
- **Per-route rendering-mode control**: Supported. [CC] Control is by component structure plus route-segment exports (pages/layouts; client components throw):

  | export | values / default | behavior |
  |---|---|---|
  | `ensureStatic` (16.4) | `'auto'` (default) \| `'shell'` \| `'prefetch'` \| `'navigation'` \| `false` | Requires a navigation stage to be static. `'shell'`: App Shell static (needs Partial Prefetching, else warns). `'prefetch'`: App Shell + per-link prefetch static. `'navigation'`: whole server render static; validated in dev and build; uncached data, `connection()`, runtime APIs, cacheLife under thresholds, and request-dependent promises passed to client components all fail even inside Suspense; dynamic routes must export `generateStaticParams` with complete param sets; unlisted params wait for static generation. `false`: forbids other segments from applying a level. A descendant may be stricter but not weaker (build error). Parallel routes rendered together must agree. |
  | `instant` (stable 16.3) | `true` \| `false` \| `{level:'warning'}` | Dev-time validation that navigations into the segment render UI immediately. Checked at every shared-layout boundary; errors show in the dev overlay. `false` exempts a blocking ancestor and, when highest in the tree, disables static-shell validation. Global default via `experimental.instantInsights.validationLevel: 'warning'` (every Page/Default validated) or `'manual-warning'` (opt-in only). |
  | `prefetch` | `'partial'` \| `'force-disabled'` | see §1 |
  | `maxDuration` | number (seconds) | platform execution limit; on a page it also applies to that page's Server Actions |
  | `runtime` | `'nodejs'` (default) \| `'edge'` (**deprecated**) | **must be removed entirely under CC**; not allowed in Proxy |
  | `preferredRegion` | **deprecated**; `'auto'`/`'global'`/`'home'`/string/string[] | passed to the platform; inherits from the parent layout, child overrides without merging |
  | `dynamicParams` | `true` | [prev] only |

  [prev] also has `dynamic` (`'auto'`, `'force-dynamic'`, `'error'`, `'force-static'` which makes cookies/headers/useSearchParams return empty), `revalidate` (`false` | `0` | n seconds; statically analyzable literal; the lowest value across segments wins), and `fetchCache` (`'auto'`, `'default-cache'`, `'only-cache'`, `'force-cache'`, `'default-no-store'`, `'only-no-store'`, `'force-no-store'`; cross-segment compatibility rules apply). Source: `SEG/index.mdx`, `SEG/ensureStatic.mdx`, `SEG/instant.mdx`, `SEG/runtime.mdx`, `SEG/preferredRegion.mdx`, `SEG/maxDuration.mdx`, `G/caching-without-cache-components.mdx`.
- **Hydration strategies**: Partial. React 19 selective hydration and Suspense-gated hydration are available. `'use client'` boundaries are the only lever. There are no lazy/visible/idle hydration directives (not found). [CC] Activity keeps hidden routes hydrated. `instrumentation-client.js` runs after the HTML loads and before hydration (sync top-level code only is guaranteed; it warns if it takes more than 16 ms in dev). Source: `FC/loading.mdx`, `FC/instrumentation-client.mdx`.
- **Notable extras**:
  - `connection()` (`next/server`) and `io()` (`next/cache`, 16.3) mark "wait for a request" or "exclude from prerender". `io()` resolves immediately inside `use cache`, during requests, and in the browser, so it can be shared between cached and uncached code. `connection()` throws in cache scopes. Docs say to prefer `io()`. `unstable_noStore` is legacy. Source: `FN/connection.mdx`, `FN/io.mdx`.
  - Build hang guard: filling a `use cache` entry with request-derived promises times out after **50 s** with a specific error. `next build --debug-prerender` gives source-mapped prerender errors. Source: `DIR/use-cache.mdx`, `G/building.mdx`.
  - Navigation Inspector in Next.js DevTools [CC]: "Pause on navigations" freezes the page-load or client-nav shell. `@next/playwright` `instant()` e2e helper; `experimental.exposeTestingApiInProductionBuild` exposes it in prod builds. Source: `G/instant-navigation.mdx`, `SEG/instant.mdx`.

## 3. Data loading

- **Where data is fetched**: Server Components are `async` and can call `fetch`, ORMs, or the filesystem directly. There is no loader abstraction. Other server entry points: `generateMetadata`, `generateViewport`, `generateStaticParams`, Route Handlers. On the client: React `use(promise)` with a promise passed from a Server Component, or SWR / TanStack Query (guides provided). Server Functions *can* be called for reads, but the client dispatches them **one at a time**, so the docs steer fetching to Server Components or Route Handlers. A file-level `use cache` module's exports can be imported and called from client components and behave like Server Functions. Source: `GS/06-fetching-data.mdx`, `GS/07-mutating-data.mdx`, `DIR/use-cache.mdx`.
- **Execution model**: Layouts and pages in a route render **in parallel**. Inside a component, sequential `await`s waterfall, so docs recommend starting requests then `Promise.all`/`allSettled`. The "preload" pattern calls a deduped fetcher without `await` earlier in the tree. Everything is server-side; there is no "client loader" concept. Conditional parallel slots all execute. Source: `GS/06-fetching-data.mdx`, `FC/parallel-routes.mdx`.
- **Request deduplication**: Supported.
  - `fetch` GET with the same URL and options is **memoized per render pass** across layouts, pages, `generateMetadata`, `generateStaticParams`, and `generateViewport`. Opt out with an `AbortController` signal. Not applied in Route Handlers.
  - `React.cache()` dedupes per request for non-fetch calls. Inside `use cache` it is isolated: values cached outside are invisible inside.
  - `use cache` dedupes across requests.
  - `use cache: private` reuses matching calls within one request (production).

  Source: `FN/fetch.mdx`, `GS/06-fetching-data.mdx`, `DIR/use-cache-private.mdx`.
- **Passing server data to client components**: Supported. Props must be React-serializable. You can pass **promises** and unwrap them with `use()`, which streams; or share one promise via a context provider rendered in a layout. Server Components can be passed as `children`/props into client components (interleaving). `experimental.taint` adds React taint APIs to block objects or values from crossing. Only `NEXT_PUBLIC_*` env vars are inlined into client bundles; others become `''`. Source: `GS/05-server-and-client-components.mdx`, `G/single-page-applications.mdx`, `CFG/taint.mdx`.
- **Client-side data cache**: Partial. The router **Client Cache** holds RSC payloads for visited and prefetched segments: layouts and loading states are reused, pages are not cached by default, back/forward reuses them, and a page refresh clears it. Freshness comes from the `cacheLife` `stale` time (sent as the `x-nextjs-stale-time` header; **min 30 s enforced**) or experimental `staleTimes` (`dynamic` default 0 s, `static` default 300 s). There is no built-in client *data* cache (query cache); docs defer to SWR or TanStack Query, including coordination guides. Source: `docs/01-app/04-glossary.mdx`, `FN/cacheLife.mdx`, `CFG/staleTimes.mdx`, `G/client-side-data-fetching/index.mdx`.
- **Deferred / streamed data**: Supported via Suspense, either by awaiting inside a suspended child component or by passing an unawaited promise to a client component that calls `use()`. There is no special `defer()` API. Errors mid-stream go to the nearest error boundary. Source: `GS/06-fetching-data.mdx`, `G/streaming.mdx`.
- **Dependency tracking & invalidation**: Partial (explicit tags and paths, no automatic tracking). Tags come from `cacheTag()` inside `use cache` or `fetch(..., {next:{tags}})`. Invalidation: `revalidateTag`, `updateTag`, `revalidatePath`, `refresh()`, `router.refresh()`. Next.js also derives implicit "soft tags" from route paths so `revalidatePath` can find entries (`G/how-revalidation-works.mdx`). After a Server Action that revalidates, the current route re-renders in the same response (§4). Source: `FN/cacheTag.mdx`, `G/how-revalidation-works.mdx`.
- **Access to request context**: Supported, as async functions:
  - `cookies()` and `headers()` from `next/headers`; headers are read-only.
  - `draftMode()`.
  - `params`/`searchParams` props.
  - `next/root-params` getters.
  - `connection()`.
  - In Route Handlers and Proxy, a `NextRequest` with `.cookies` and `.nextUrl` (`basePath`, `buildId`, `pathname`, `searchParams`); `ip`/`geo` were removed in v15.
  - `userAgent()` from `next/server`.

  Layouts never get the raw request. A per-request "locals/context object" is **not found in docs**; the documented way to pass data from Proxy is request headers via `NextResponse.next({request:{headers}})`, cookies, rewrites, or the URL. Under [CC], runtime APIs cannot be called inside `use cache` (error `next-request-in-use-cache`, which follows the call stack). Source: `FN/cookies.mdx`, `FN/next-request.mdx`, `FC/proxy.mdx`, `DIR/use-cache.mdx`.
- **Notable extras**: In dev, `fetch` responses are cached across HMR refreshes (`serverComponentsHmrCache`, experimental toggle), and a hard refresh (`cache-control: no-cache`) bypasses fetch caching. `logging.fetches` (`fullUrl`, `hmrRefreshes`) logs fetches in dev. Since v15, request APIs and params are async. Source: `FN/fetch.mdx`, `CFG/logging.mdx`.

## 4. Mutations

- **Progressive enhancement (no-JS forms)**: Supported. `<form action={serverAction}>` in a **Server Component** submits without JS. In Client Components, submissions are **queued until hydration**, and those forms get hydration priority. After hydration, submits don't reload the page. A no-JS submission followed by `redirect()` returns **303**. `<Form>` from `next/form`:

  | `action` type | props | behavior |
  |---|---|---|
  | string | `action` (URL; `""` = same route), `replace` (default false), `scroll` (default true), `prefetch` (default true) | GET form: fields are encoded as search params; prefetches the target's layout and loading UI when visible; client-side navigation on submit |
  | function (Server Action) | `action` | React form behavior; `replace`/`scroll` are ignored; no prefetch |

  Caveats:
  - `formAction` on buttons overrides `action` and navigates client-side, but without prefetch.
  - `key` is not supported with a string action.
  - `onSubmit` + `preventDefault` cancels the navigation.
  - `method`, `encType`, and `target` are unsupported (use `formMethod` etc. to fall back to native behavior).
  - `<input type=file>` with a string action submits the filename only.
  - With `basePath`, you must prefix `formAction` yourself.

  Source: `GS/07-mutating-data.mdx`, `CMP/form.mdx`, `FN/redirect.mdx`.
- **Server functions / actions**: Supported (React Server Functions). Define them with `'use server'` inline in a Server Component or at the top of a file. They cannot be *defined* in client components but can be imported there or passed as props. They are invoked with `<form action>`, `<button formAction>`, event handlers or `useEffect` wrapped in `startTransition`. Transport: **POST to the page that invokes it**, the only allowed method. Extra arguments come via `.bind()` (supports progressive enhancement) or hidden inputs. `Object.fromEntries(formData)` includes `$ACTION_*` keys. The **client dispatches actions sequentially**, so `Promise.all` doesn't parallelize them; the server does not queue. Next.js-specific security:
  - **Action IDs** are encrypted and non-deterministic, regenerated per build (cached at most 14 days).
  - **Dead-code elimination** removes unused actions, so they get no endpoint.
  - **Closure variables are encrypted** with a per-build key. Set `NEXT_SERVER_ACTIONS_ENCRYPTION_KEY` (base64 AES-128/192/256) for multi-instance deployments.
  - A client running an old build gets "Failed to find Server Action".

  Source: `G/server-actions.mdx`, `G/forms.mdx`, `G/data-security.mdx`.
- **Pending / error / validation state**: Supported via React primitives. `useActionState` (`[state, action, pending]`; the action receives `prevState` first) and `useFormStatus` (pending, data, method, action). Expected errors should be *returned* as state, not thrown. Thrown errors go to the nearest `error.js` / `catchError` boundary; errors in `startTransition` bubble there too. Validation is BYO (Zod/Valibot examples); there is no framework validation API. Source: `G/forms.mdx`, `GS/10-error-handling.mdx`.
- **Optimistic UI**: Supported via React `useOptimistic`. Docs show a shared reducer applied both optimistically and on the server. Source: `G/forms.mdx`, `G/single-page-applications.mdx`.
- **Data refresh after mutation**: Partial (manual, but single round trip). The action response carries the return value **and** a newly rendered RSC payload for the current route *if* the action called `updateTag`, `revalidatePath`, or `refresh()`, mutated cookies via `cookies().set/delete`, or called `redirect()`. `revalidateTag(tag, profile)` with stale-while-revalidate deliberately does **not** re-render. With no invalidation call, only the return value comes back and nothing re-renders automatically. Calling any revalidation function from an action **clears the entire client cache**, bypassing `stale`. `revalidatePath` in an action currently also causes *all previously visited pages* to refresh on the next visit; docs call this temporary. Client state is preserved for re-rendered components. Source: `G/server-actions.mdx`, `FN/cacheLife.mdx`, `FN/revalidatePath.mdx`, `FN/cookies.mdx`.
- **Redirects after mutation**: Supported. `redirect(path, type?)` throws `NEXT_REDIRECT`, so call it outside `try` or use `unstable_rethrow`. In actions it defaults to `push`; elsewhere to `replace`. With JS it performs a client navigation and streams the destination RSC in the same response; without JS it returns 303. Revalidate *before* redirecting. Source: `FN/redirect.mdx`, `G/server-actions.mdx`.
- **File uploads**: Partial. Files arrive in `FormData`. `serverActions.bodySizeLimit` defaults to **1 MB** (bytes or a string like `'3mb'`) and counts the raw multipart body, so docs suggest 10–20 KB headroom. Route Handlers read with `request.formData()`; Go routes use `ParseMultipartForm`. There are no upload, streaming-to-storage, or progress helpers, and `proxyClientMaxBodySize` is experimental. Source: `CFG/serverActions.mdx`, `FC/route.mdx`, `CFG/proxyClientMaxBodySize.mdx`.
- **Multiple actions per page**: Supported. Use multiple forms, or `formAction` on `<button>`/`<input type=submit|image>` inside one form (e.g. "save draft" vs "publish"), and pass actions as props. Source: `G/forms.mdx`.
- **CSRF protection**: Supported, built in.
  - Only POST can invoke actions.
  - The `Origin` host is compared with `X-Forwarded-Host` or `Host`, and mismatches are rejected. A request **without an `Origin` header is allowed with a warning**.
  - `serverActions.allowedOrigins` adds hosts. It matches host plus optional port; `*` = one label, `**` = one or more labels (only as a prefix); ports can't be wildcarded; no partial-label wildcards. It applies in production too.

  Source: `CFG/serverActions.mdx`, `G/data-security.mdx`.
- **Notable extras**:
  - The Proxy matcher also gates actions, since they are POSTs to the page path, so excluding a path silently skips Proxy for actions there.
  - Dev logs each Server Function call with name, args, and duration (`logging.serverFunctions`).
  - `experimental.useOffline` keeps an interrupted action pending and retries it when the network returns.
  - Experimental `authInterrupts` enables throwing `forbidden()`/`unauthorized()` from actions.
  - The MCP tool `get_server_action_by_id` maps an action ID to its source.

  Source: `FC/proxy.mdx`, `CFG/logging.mdx`, `CFG/useOffline.mdx`, `G/mcp.mdx`.

## 5. Caching & revalidation

- **Page/HTML caching**: Supported. [CC] the static shell or full prerender is stored as HTML and RSC on disk when self-hosting, or in platform durable storage. [prev] static routes are fully cached. Generated `Cache-Control` headers:
  - static: `s-maxage=31536000`
  - ISR: `s-maxage={revalidate}, stale-while-revalidate={expire−revalidate}`
  - dynamic: `private, no-cache, no-store, max-age=0, must-revalidate`
  - hashed `/_next/static`: `public, max-age=31536000, immutable`, which cannot be overridden

  `expireTime` sets the CDN SWR expiry for ISR. All server caches are **per-deployment**: the build ID (or `deploymentId`) is part of keys. On-demand revalidation does **not** purge CDNs; it only purges the Next.js server cache. Source: `GS/08-caching.mdx`, `G/cdn-caching.mdx`, `CFG/expireTime.mdx`, `CFG/headers.mdx`.
- **Time-based revalidation (ISR)**: Supported. [CC] per cached function via `cacheLife`. After `revalidate`, the next request is served stale while the entry regenerates in the background. After `expire` with no traffic, the next request blocks. [prev] use `export const revalidate = n`, `fetch(..., {next:{revalidate}})`, or `unstable_cache({revalidate})`; the lowest value in a route wins. ISR with [CC] for unknown params serves the App Shell, then upgrades and caches the concrete page. The Edge runtime does not support ISR. Source: `FN/cacheLife.mdx`, `G/incremental-static-regeneration-cache-components.mdx`, `G/caching-without-cache-components.mdx`.
  - `cacheLife` presets (`stale` / `revalidate` / `expire`):

    | profile | stale | revalidate | expire |
    |---|---|---|---|
    | `default` | 5 min | 15 min | never |
    | `seconds` | 30 s | 1 s | 1 min |
    | `minutes` | 5 min | 1 min | 1 h |
    | `hours` | 5 min | 1 h | 1 d |
    | `days` | 5 min | 1 d | 1 wk |
    | `weeks` | 5 min | 1 wk | 30 d |
    | `max` | 5 min | 30 d | 1 yr |

    Built-in profiles can be redefined, and custom named profiles can be added, in `next.config` `cacheLife: {name:{stale,revalidate,expire}}`. Omitted fields inherit from `default`. Inline objects are allowed: `cacheLife({})` = default. `expire` must be greater than `revalidate` (validated). Only one `cacheLife` call may execute per invocation; conditional calls are fine. It is not allowed at module scope. Types are generated from config. **Prerender thresholds**: `revalidate:0` or `expire<5min` means excluded from prerender (a dynamic hole); `stale<30s` means excluded; `30s≤stale<5min` means prerendered but kept out of the App Shell. Only `seconds` crosses a threshold. **Nesting**: an explicit outer `cacheLife` always wins. Without one, the outer cache uses `default` but can be *shortened* by inner caches. A short-lived inner cache inside an outer one without an explicit `cacheLife` **errors at prerender**. Source: `FN/cacheLife.mdx`, `CFG/cacheLife.mdx`.
- **On-demand revalidation**: Supported.

  | API | where callable | semantics |
  |---|---|---|
  | `revalidateTag(tag, profile)` | Server Functions, Route Handlers (not Client Components or Proxy) | Marks the tag stale. The next request is served stale while revalidation runs. `profile` (or `{expire}` in seconds) bounds how long stale may be served: `'max'` (recommended, ~1 yr), any profile (only its `expire` is read), `{expire:0}` (no stale, blocking). The **one-arg form is deprecated** and behaves like `{expire:0}`. Revalidation is triggered per request, not at call time. In actions it does not re-render. |
  | `updateTag(tag)` | **Server Actions only** | Expires immediately; the next read waits (read-your-own-writes); re-renders in the action response |
  | `revalidatePath(path, type?)` | Server Functions, Route Handlers | Literal path or pattern (`/product/[slug]` requires `type:'page'\|'layout'`). A `layout` type invalidates nested layouts and pages; a `page` type doesn't invalidate deeper pages. Takes the **destination** path when rewrites apply. Max 1024 chars, case-sensitive, trailing slash optional. `revalidatePath('/', 'layout')` purges all data plus the Client Cache. In Route Handlers it only marks paths for the next visit. |
  | `refresh()` | Server Actions only | Re-renders the current route; does not touch tagged data |

  Tag limits: 256 chars per tag, 128 tags per `cacheTag()` call (excess is dropped with a warning; the same limits apply to `fetch` `next.tags`). Multi-instance: `revalidateTag` only invalidates the local instance unless the cache handler implements `refreshTags()`, which is called before each request. Source: `FN/revalidateTag.mdx`, `FN/updateTag.mdx`, `FN/revalidatePath.mdx`, `FN/refresh.mdx`, `FN/cacheTag.mdx`, `G/self-hosting.mdx`.
- **Data-level / function-level caching**: Supported, and the most developed area.
  - **`'use cache'`** [CC; stable 16.0] goes at the file, component, or function level, and functions must be async. **Cache key** = build ID (or `deploymentId`) + function ID (a hash of location and signature) + serialized args, where **captured closure variables are bound as args** + the HMR hash in dev + root params actually read. Arguments use RSC-serializable types (primitives, plain objects, arrays, Date, Map, Set, TypedArrays; JSX only as pass-through). Return values use client-serializable types, and JSX is allowed. Class instances, functions (except pass-through), symbols, and `URL` are not supported. `children` and Server Actions pass through without affecting the key. Each `page`/`layout`/slot file is cached independently, and a cached layout doesn't cache its `children`. Storage is an in-memory LRU by default (`cacheMaxMemorySize`). On serverless, runtime entries typically don't survive between requests, but build-time ones do. Hosts may replace the handler. Draft Mode makes every cached scope re-execute with no writes. `'use cache'` has no effect in Proxy, where `cacheLife`/`cacheTag` throw. Debug with `NEXT_PRIVATE_DEBUG_CACHE=1`; in dev, console replays show a `Cache` prefix. Source: `DIR/use-cache.mdx`.
  - **`'use cache: remote'`**: uses a durable shared handler (`cacheHandlers.remote`), intended for request-time content with a high hit rate. It costs a network round trip and is still **not persisted across deploys**. Nesting: remote can nest in remote or default caches. Remote and private cannot nest in each other. Source: `DIR/use-cache-remote.mdx`.
  - **`'use cache: private'`**: may read `cookies()`, `headers()`, `searchParams` (not `connection()`). It has no cross-request server cache in production, only per-request dedupe plus a **browser** cache for `stale`, and it can be included in per-link prefetches. `stale` ≥ 30 s allows prefetch; ≥ 5 min allows the App Shell. `cacheLife({stale: Infinity})` avoids lowering the route's stale time. Not customizable via handlers. Source: `DIR/use-cache-private.mdx`.
  - **Custom handlers**: `cacheHandlers: {default, remote, <name>}`, referenced by `'use cache: <name>'`. The interface has `get`, `set`, `refreshTags`, `getExpiration`, `updateTags`, with a streamed entry value and soft tags. The singular `cacheHandler` (ISR, route handlers, patched fetch, `unstable_cache`, images) has `get`, `set`, `revalidateTag`, `resetRequestCache`. Source: `CFG/cacheHandlers.mdx`, `CFG/incrementalCacheHandlerPath.mdx`.
  - [prev] **`fetch` cache**: `cache: 'no-store' | 'force-cache'`. The default "auto no cache" means fetched at build if reached before request APIs, otherwise per request. `force-cache` keys on URL, method, headers, and body, and stores only 200 responses. `next.revalidate: false | 0 | n` and `next.tags` are also available. Conflicting options are ignored, with a dev warning. **`unstable_cache(fn, keyParts, {tags, revalidate})`**: per the docs, still the way to get caches that **persist across deployments**. Source: `FN/fetch.mdx`, `FN/unstable_cache.mdx`.
- **Client navigation cache**: Supported (see §3). Per-route `stale` comes from the shortest `stale` among the route's cache entries. Experimental `staleTimes` changing `static` also changes `default.stale`. Loading boundaries are reusable for the `static` period. Shared layouts are never refetched on navigation (partial rendering). Back/forward caching is unaffected. Source: `CFG/staleTimes.mdx`, `FN/cacheLife.mdx`.
- **HTTP cache-header helpers**: Partial. There is no dedicated API. Options are config `headers()` rules (`source`, `headers`, `has`/`missing` matchers; later rules override earlier ones for the same key), setting headers on a `Response` in Route Handlers or Proxy, and auto-generated `Cache-Control`. Also available: `generateEtags` (default on), `compress` (gzip default on), images `minimumCacheTTL` (default 4 h; `max(minimumCacheTTL, upstream max-age)`; no invalidation mechanism), and `supportsImmutableAssets` (content-addressed `/_next/static/immutable/*` without `?dpl`). Source: `CFG/headers.mdx`, `CMP/image.mdx`, `CFG/supportsImmutableAssets.mdx`.
- **Preview / draft mode bypass**: Supported. `draftMode()` has `isEnabled`, `enable()`, and `disable()`. Enable/disable only in Route Handlers or Server Actions; they throw in cache scopes. A `__prerender_bypass` cookie is regenerated per build. While on, `use cache` re-executes with no writes, the fetch cache is bypassed for both reads and writes, and `isEnabled` is readable inside cache scopes. Not available with static export. Source: `FN/draft-mode.mdx`, `DIR/use-cache.mdx`.
- **Notable extras**:
  - CDN integration: App Router responses vary on `rsc`, `next-router-state-tree`, `next-router-prefetch`, `next-router-segment-prefetch`, and `next-url` headers. The `_rsc` query hash is a cache-key fallback; a wrong `_rsc` gets a 307 to the correct one. [CC] segment prefetches use pathname-based URLs (`/page.segments/_tree.segment.rsc`). The planned direction is fully pathname-based keys (`.rsc`). Source: `G/cdn-caching.mdx`.
  - Platform matrix: a single `next start` supports everything. Streaming is *required* for RSC, PPR, `use cache`, and actions. A shared cache is *recommended* for ISR and `use cache` on multiple instances. Source: `G/deploying-to-platforms.mdx`.

## 6. Server & API

- **API routes / endpoints**: Supported. `route.js|ts` exports `GET`, `POST`, `PUT`, `PATCH`, `DELETE`, `HEAD`, `OPTIONS`; any other method returns **405**. Signature: `(request: NextRequest, context: {params: Promise<...>})`, typed with global `RouteContext<'/x'>`. Handlers are not cached by default (GET changed from static to dynamic in v15). [prev] Opt GET into caching with `dynamic='force-static'` etc.; other methods are never cached. [CC] GET handlers follow the page prerender model: prerendered unless they touch request data, uncached I/O, or nondeterminism; `use cache` must be in a helper function, not the handler body. `generateStaticParams` is supported. `fetch` memoization does not apply. A handler cannot coexist with `page` in the same segment, and it doesn't take part in layouts or client navigation. Metadata files (`sitemap`, `robots`, `manifest`, `icon`, `opengraph-image`) are special static-by-default Route Handlers. With static export only `GET` works, with `force-static`. Auto-implemented `OPTIONS`/`HEAD` for JS handlers is not stated explicitly; the Go page implies "same conventions" (204 `Allow` / GET fallback), so treat it as implied, unverified for JS. Source: `FC/route.mdx`, `GS/15-route-handlers.mdx`, `FC/route-go.mdx`.
- **Middleware**: Supported, as a **single global Proxy** (renamed from `middleware`; `middleware.ts` deprecated in 16.0; codemod `middleware-to-proxy`).
  - **File and runtime**: `proxy.ts|js` at the project root or `src/`, exporting a default or named `proxy` function `(request: NextRequest, event: NextFetchEvent)` (type `NextProxy`). Only one per project; the docs suggest composing modules inside it. **Runtime: Node.js by default**, and `export const runtime` throws in Proxy (Edge pages say Proxy can still use Edge APIs).
  - **`config.matcher`**: a string, an array, or objects `{source, locale?, has?, missing?}`. Uses path-to-regexp syntax (`:param`, `*`, `+`, `?`, `(regex)`), must be statically analyzable constants, and is anchored at the start. With **no matcher it runs on every request including `_next/static`, `_next/image` and `public/`**. `_next/data` is always invoked even if excluded.
  - **Capabilities**: `NextResponse.next({request:{headers}})` to forward request headers upstream (passing `headers` without `request` sends them to the client), `rewrite`, `redirect`, `Response.redirect`, returning a full Response, reading and writing cookies (`get/getAll/set/delete/has/clear`), response headers, and `event.waitUntil(promise)`.
  - **Limits**: directives have no effect (`use cache`, `use server`); `fetch` cache options don't cache; RSC Flight headers are stripped from `request.headers`. `skipProxyUrlNormalize` (formerly `skipMiddlewareUrlNormalize`) and `skipTrailingSlashRedirect` are escape hatches.
  - **Order**: config `headers` → config `redirects` → Proxy → `beforeFiles` rewrites → filesystem (`public`, `_next/static`, static pages) → `afterFiles` → dynamic routes → `fallback` rewrites.
  - **Testing**: `next/experimental/testing/server` (`unstable_doesMiddlewareMatch`, `isRewrite`, `getRewrittenUrl`).
  - **Per-route middleware chains and ordering**: **not supported** (single file; route by matcher or inline logic).

  Source: `FC/proxy.mdx`, `GS/16-proxy.mdx`, `FC/middleware.mdx`, `docs/01-app/03-api-reference/07-edge.mdx`.
- **Request context**: Supported (see §3). `cookies()`:
  - Methods: `get`, `getAll`, `has`, `set(name, value, opts)`, `delete`, `toString`.
  - Options: `expires`, `maxAge`, `domain`, `path` (only default: `'/'`), `secure`, `httpOnly`, `sameSite`, `priority`, `partitioned`.
  - **set/delete only in Server Functions or Route Handlers**, never during Server Component render, because headers can't change after streaming starts.
  - Setting a cookie in an action re-renders the current page and layouts.

  `headers()` is read-only. No locals object (not found). Source: `FN/cookies.mdx`, `FN/headers.mdx`.
- **Streaming responses / SSE**: Partial. Route Handlers can return Web `ReadableStream` responses, and the docs cover streaming in Route Handlers and LLM/AI SDK streams. Server-Sent Events (`text/event-stream`) is **not specifically documented** but works with standard Web streams (from memory, unverified). Go routes stream via `http.Flusher`. Platforms may buffer. Source: `FC/route.mdx`, `G/streaming.mdx`, `FC/route-go.mdx`.
- **Running work after the response**: Supported.
  - **`after(cb)`** (`next/server`; stable 15.1) is callable from Server Components (including `generateMetadata`), Server Functions, Route Handlers, and Proxy. It runs after the response *or prerender* finishes; on a static page it runs at build or revalidate time. It also runs when the response errored, `notFound()`, or `redirect()`. It doesn't make a route dynamic and calls can be nested.
  - `cookies()`/`headers()` work inside the callback in actions and Route Handlers, but **throw inside the callback in Server Components** (read them beforehand).
  - Duration is bounded by `maxDuration`. Not supported in static export.
  - Serverless hosts must provide `globalThis[Symbol.for('@next/request-context')].get().waitUntil`. When self-hosting, a graceful shutdown on SIGINT/SIGTERM drains pending `after` callbacks (10–30 s drain recommended).
  - Proxy also has `event.waitUntil`, and adapters get `ctx.waitUntil`.

  Source: `FN/after.mdx`, `G/self-hosting.mdx`, `ADP/07-runtime-integration.mdx`.
- **Server-only code boundaries**: Supported.
  - **Directives**: `'use client'` marks a client module graph; `'use server'` marks server functions.
  - **Marker packages**: `import 'server-only'` / `'client-only'` give a build-time error when imported in the wrong environment. Next.js handles them internally, installing them is optional, and types are provided.
  - **Env vars**: non-`NEXT_PUBLIC_` variables are replaced with `''` in client bundles.
  - **Implicitly server-only modules**: `next/root-params` and `next/headers` (`next/root-params` fails at build time if imported in client code).
  - **Tainting**: `experimental.taint`.
  - **External packages**: `serverExternalPackages` uses native `require` instead of bundling.
  - **Not supported**: `.server.ts` file-suffix conventions (not found).

  Source: `GS/05-server-and-client-components.mdx`, `FN/next-root-params.mdx`, `CFG/taint.mdx`.
- **Notable extras**:
  - The **Edge runtime is deprecated** for routes; the API surface is documented for Proxy and adapters.
  - A **custom server** is possible but incompatible with `standalone`.
  - **Go route handlers** (experimental).
  - A Backend-for-Frontend guide covers Route Handlers and Proxy as a BFF.
  - Webhooks get the raw body (no `bodyParser`).
  - Dev logs every incoming request (`logging.incomingRequests`, filterable).

  Source: `docs/01-app/03-api-reference/07-edge.mdx`, `G/custom-server.mdx`, `G/backend-for-frontend.mdx`, `CFG/logging.mdx`.

## 7. Loading & error states

- **Route-level loading UI**: Supported. `loading.js` (Server Component by default, may be a client component, no props) wraps `not-found`, `page`, and nested layouts in `<Suspense>`. It does not wrap the same segment's `layout`, `template`, or `error`. The fallback is **prefetched**, so navigation feels instant; navigation is interruptible and shared layouts stay interactive. [CC] it is treated as an ordinary Suspense boundary, not a prefetch marker. Use `loading.js` inside a route group to scope it to one page. Source: `FC/loading.mdx`, `GS/02-project-structure.mdx`.
- **Error boundaries**: Supported.
  - **`error.js`** (must be a Client Component) wraps `loading`, `not-found`, `page`, and nested layouts, but not its own segment's `layout`/`template`.
  - **Props**: `error` (Server Component errors arrive as an `Error` with a generic `message` in production plus `digest` to correlate server logs; client-thrown values arrive as-is and may not be `Error`); **`retry()`** (stable 16.3) re-fetches and re-renders the boundary's children inside a transition; `reset()` clears error state *without* re-fetching, so it can't recover Server Component errors. Rethrow to bubble up.
  - **`global-error.js`** replaces the root layout when active. It must render its own `<html>/<body>` and import global styles, doesn't support `metadata` (use React `<title>`), and is shown in dev since 15.2.
  - **`catchError(fallback)`** (`next/error`; stable 16.3) creates a component-level boundary anywhere. The fallback is `(props, {error, retry, reset}) => UI` and must be a client component. It doesn't catch `redirect()`/`notFound()` signals and clears on client navigation to another route.
  - Event-handler and async errors are not caught by boundaries; `startTransition` errors are.

  Source: `FC/error.mdx`, `FN/catchError.mdx`, `GS/10-error-handling.mdx`.
- **404 / not-found**: Supported.
  - **`notFound()`** throws `NEXT_HTTP_ERROR_FALLBACK;404`. It works in Server Components, Server Functions, and Route Handlers (returns a 404 there). It must be in the render path, since an un-awaited promise is an unhandled rejection. `try/catch` swallows it unless you use `unstable_rethrow` (unstable).
  - **`not-found.js`** renders the nearest boundary. The status is 404 if the interrupt happens before streaming, otherwise 200 plus an injected `noindex` meta. Root `app/not-found.js` also handles all unmatched URLs.
  - **Every `not-found.js` is shipped with every route under its segment**, including its client imports, so docs say to keep it server-only. It supports `metadata`/`generateMetadata`.
  - **`global-not-found.js`** (**experimental**, `experimental.globalNotFound`, 15.4) skips rendering entirely for unmatched URLs and must return a full document. Useful with multiple root layouts or a dynamic root segment.

  Source: `FC/not-found.mdx`, `FN/not-found.mdx`, `FN/unstable_rethrow.mdx`.
- **Helpers**:
  - `redirect(path, 'replace'|'push')`: 307, or 303 for no-JS actions; push in actions, replace elsewhere; `type` is ignored in Server Components. Usable in render of Server *and Client* Components (SSR does a server redirect) but **not in event handlers**. Absolute external URLs are allowed. In streaming contexts it emits a meta redirect.
  - `permanentRedirect`: 308.
  - `RedirectType` enum.
  - `forbidden()` / `unauthorized()` plus `forbidden.js` / `unauthorized.js` (403 / 401; **experimental**, `experimental.authInterrupts`); these files are also shipped with every route under their segment.
  - There is no generic `error(status)` helper (not found).

  Source: `FN/redirect.mdx`, `FN/permanentRedirect.mdx`, `FC/forbidden.mdx`, `CFG/authInterrupts.mdx`.
- **Expected vs unexpected errors**: Supported by convention. Expected errors are *return values* (`useActionState` state, conditional render or redirect in Server Components). Unexpected errors are thrown to boundaries. Production masks Server Component error messages, leaving only the digest. Source: `GS/10-error-handling.mdx`.
- **Error reporting hooks**: Supported. `instrumentation.ts` `onRequestError(error, request{path,method,headers}, context{routerKind, routePath, routeType:'render'|'route'|'action'|'proxy', renderSource, revalidateReason:'on-demand'|'stale'|undefined, renderType:'dynamic'|'dynamic-resume'})`; await async work inside it, and the error may be React-processed (use `digest`). Client-side reporting goes through `instrumentation-client.ts` (Sentry-style init), with `instrumentationClientInject` letting config plugins inject modules ahead of it. Source: `FC/instrumentation.mdx`, `FC/instrumentation-client.mdx`, `CFG/instrumentationClientInject.mdx`.
- **Notable extras**: Default 404 and global-error UIs follow OS `prefers-color-scheme` and ignore app theme classes. Under [CC], status-code fidelity requires checks before the shell (Proxy) because the shell starts the 200. Dev overlay "fix cards" have a **Copy prompt** for agents. Source: `FC/not-found.mdx`, `FC/loading.mdx`, `G/ai-agents.mdx`.

## 8. Type safety

- **Typed links and params**: Supported. Literal-href checking via `typedRoutes` (stable, opt-in) covers `<Link>` and `next/navigation`. Generated global helpers: `PageProps<'/r'>` (`params` + `searchParams`), `LayoutProps<'/r'>` (`params` + named slots), `RouteContext<'/r'>`. `next/root-params` getters are typed per root layout. Param values are deliberately wide: `string`, `string[]`, or `undefined`. Source: `docs/01-app/03-api-reference/05-config/02-typescript.mdx`, `FC/page.mdx`, `FC/layout.mdx`.
- **Typed loader/server data to components**: Supported implicitly. There is no loader layer: data is fetched in the component, so TypeScript inference is direct and Server Components can use `Date`, `Map`, `Set` without serialization. Data passed to client components must be serializable, but there are no generated types for that boundary. Source: `docs/01-app/03-api-reference/05-config/02-typescript.mdx`.
- **Typed server calls**: Supported via inference. Server Actions are ordinary imported TS functions, so argument and return types flow through the import. Route Handlers are untyped for clients: there is no typed client or RPC generator (not found). Source: `GS/07-mutating-data.mdx`.
- **Generated types**: Supported. `next typegen [dir]` (15.5) writes to `<distDir>/types` (`.next/dev/types` in dev, `.next/types` in prod) and refreshes `next-env.d.ts` (which belongs in gitignore; don't edit it). It loads config in the production phase. Also generated during `next dev`/`next build`. `cacheLife` profile names and JSDoc are generated from config. `experimental.typedEnv` generates env var IntelliSense. The TS plugin warns on invalid segment config values, misuse of `'use client'`, and client hooks in Server Components. `next build` type-checks with the project-local `tsc` CLI by default (TS 7 supported; `experimental.useTypeScriptCli:false` switches to the compiler API). `typescript.ignoreBuildErrors` and `typescript.tsconfigPath` are available. Minimum TS 5.1. Source: `docs/01-app/03-api-reference/06-cli/next.mdx`, `docs/01-app/03-api-reference/05-config/02-typescript.mdx`, `FN/cacheLife.mdx`.
- **Typed search params**: Not supported beyond a generic record (`string | string[] | undefined`). No schema or validation integration found. Source: `FC/page.mdx`.
- **Notable extras**: `next.config.ts` supports native ESM via the Node ≥ 22.10 TypeScript resolver. Segment-config literal unions are typed (`ensureStatic`, `instant`, `prefetch`). `Instrumentation.onRequestError` and `NextProxy` types are provided. Source: `docs/01-app/03-api-reference/05-config/02-typescript.mdx`.

## 9. Metadata & SEO

- **Head/meta per route**: Supported. Export a static `metadata` object or `generateMetadata({params, searchParams}, parent)` from `layout`/`page`; it is **Server Component only**. `searchParams` is available only in pages. `parent` is a promise of the resolved parent metadata. `redirect()`/`notFound()` work inside it. **Evaluation order** runs from the root layout to the page. **Merge is shallow**: a later segment *replaces* whole nested objects (`openGraph`, `robots`), so share fragments by spreading. Default `<meta charset>` and `<meta viewport>` are always emitted. Field families:
  - **Basics**: `title` (string | `{default, template, absolute}`; a template applies only to *child* segments, `default` is required with a template, and a template in `page` has no effect), `description`, `generator`, `applicationName`, `referrer`, `keywords`, `authors`, `creator`, `publisher`, `formatDetection`.
  - **URL composition**: `metadataBase` (relative URL fields without it are a **build error**; slashes are normalized; `/x` is treated as relative; must be a string if returned from `use cache`).
  - **Social and app**: `openGraph`, `twitter`, `robots`, `icons`, `manifest`, `verification`, `appleWebApp`, `alternates` (canonical + `languages` hreflang + media/types), `appLinks`, `archives`, `assets`, `bookmarks`, `pagination`, `category`, `facebook`, `pinterest`, `other`.
  - **Moved**: `viewport`, `themeColor`, and `colorScheme` moved to `viewport` / `generateViewport` (fields `themeColor`, `width`, `initialScale`, `maximumScale`, `userScalable`, `colorScheme`) in v14.
  - **Unsupported**: `http-equiv`, `<base>`, `<noscript>`, `<style>`, `<script>`, stylesheets, preload. For resource hints use `ReactDOM.preload`/`preconnect`/`prefetchDNS`, which work in client components only.

  Source: `FN/generate-metadata.mdx`, `FN/generate-viewport.mdx`.
- **Metadata derived from loaded data**: Supported. `fetch` is memoized between `generateMetadata` and the page. **Streaming metadata** (15.2): the UI is sent without waiting, and tags are appended to `<body>` when resolved, which is verified for JS-executing bots. HTML-limited bots (UA list; `htmlLimitedBots` regex override; `/.*/` disables streaming) get blocking `<head>` metadata. [CC] if metadata reads runtime or uncached data while the rest of the page is fully prerenderable, it's an **error**: either cache it (`'use cache'` in `generateMetadata`) or add an explicit dynamic marker (`<Suspense><Connection/></Suspense>`). Source: `FN/generate-metadata.mdx`, `CFG/htmlLimitedBots.mdx`.
- **Sitemap / robots / manifest**: Supported.
  - `app/sitemap.xml` (static) or `sitemap.(js|ts)` returning `MetadataRoute.Sitemap`, with `url`, `lastModified`, `changeFrequency`, `priority`, `alternates.languages`, `images`, and `videos`. Nested `sitemap` files per segment are allowed.
  - `generateSitemaps()` returns `[{id}]` and produces `/…/sitemap/[id].xml`. In v16 the `id` arrives as a Promise.
  - `robots.txt|js|ts` (`rules` per user-agent, `sitemap`, `host`; `other` for non-standard directives, 16.3).
  - `manifest.json|webmanifest|js|ts` (`MetadataRoute.Manifest`).
  - These are special Route Handlers, static unless they use request APIs.

  Source: `FC/01-metadata/sitemap.mdx`, `FN/generate-sitemaps.mdx`, `FC/01-metadata/robots.mdx`, `FC/01-metadata/manifest.mdx`.
- **Open Graph image generation**: Supported.
  - **Files**: `opengraph-image` / `twitter-image` as static files (`.jpg/.jpeg/.png/.gif`; OG ≤ 8 MB, Twitter ≤ 5 MB, otherwise the build fails) plus `.alt.txt`, or as code (`.js/.ts/.tsx`) default-exporting a function that returns a `Response`.
  - **Code-generated images**: they receive `params` (Promise, v16) and can export `alt`, `size`, `contentType` and segment config. They are prerendered at build unless they use request APIs. `generateImageMetadata` produces multiple images, each with an `id` prop.
  - **`ImageResponse`** (`next/og`; Satori + Resvg, PNG output): options `width` (1200), `height` (630), `emoji` (`twemoji`/`blobmoji`/`noto`/`openmoji`), `fonts[]` (ttf/otf/woff only), `debug`, `status`, `statusText`, `headers`. Only flexbox and a CSS subset are supported (no grid), with a **500 KB bundle limit**.
  - **Icons**: `favicon.ico` (root only), `icon.(ico|jpg|png|svg)`, `apple-icon`, numbered variants, and code-generated icons; `sizes` and `type` are inferred.

  Source: `FC/01-metadata/opengraph-image.mdx`, `FN/image-response.mdx`, `FC/01-metadata/app-icons.mdx`.
- **Canonical, etc.**: Supported via `alternates.canonical` and `alternates.languages` (hreflang), resolved against `metadataBase`. 404s automatically get `noindex`. JSON-LD has no API; render a native `<script type="application/ld+json">` (not `next/script`) and sanitize `<`. Source: `FN/generate-metadata.mdx`, `G/json-ld.mdx`.
- **Notable extras**: `not-found` / `global-not-found` support metadata. Metadata is resolved before streaming for bots, which affects TTFB for those UAs. Source: `FC/not-found.mdx`.

## 10. Assets & styling

- **Image optimization**: Supported. `next/image` `<Image>` props:

  | prop | values/default | behavior |
  |---|---|---|
  | `src` (req) | path \| absolute URL (must match `remotePatterns`) \| static import | the default loader **does not forward request headers** to the source |
  | `alt` (req) | string | `""` for decorative images |
  | `width`/`height` | px int | intrinsic size, used only for aspect ratio; required unless the image is a static import or uses `fill` |
  | `fill` | bool | absolute-positioned to fill a positioned parent; combine with `objectFit` |
  | `loader` | `({src,width,quality})=>url` | per instance; a function prop requires a client component |
  | `sizes` | string | no sizes + width gives a 1x/2x srcset; no sizes + fill uses `deviceSizes`; with sizes, a full `w` srcset |
  | `quality` | 1–100 | coerced to the nearest `qualities` entry (dev warning) |
  | `preload` (16.0) | bool, false | inserts `<link rel=preload>` in head; docs prefer `loading="eager"` or `fetchPriority="high"` |
  | `priority` | — | **deprecated in 16** in favor of `preload` |
  | `loading` | `lazy` (default) \| `eager` | |
  | `placeholder` | `empty` \| `blur` \| `data:image/...` | `blur` needs `blurDataURL`, which is auto-generated for static jpg/png/webp/avif imports (not animated) |
  | `blurDataURL`, `onLoad`, `onError`, `unoptimized`, `overrideSrc`, `decoding` (`async`/`sync`/`auto`), `style` | | `onLoadingComplete` deprecated; `srcSet` not allowed |

  `images` config:
  - **Source allowlists**: `localPatterns`; `remotePatterns` (protocol/hostname/port/pathname/search, `*` / `**` wildcards, `URL` objects; omitted fields imply `**`).
  - **Loader and endpoint**: `loaderFile`; `path` (`/_next/image`).
  - **Sizes and quality**: `deviceSizes` [640…3840]; `imageSizes` [32,48,64,96,128,256,384]; **`qualities` [75]** (effectively required since 16; unlisted values via the REST API return 400).
  - **Output and caching**: `formats` (`['image/webp']`; add `'image/avif'`; first match by `Accept`); `minimumCacheTTL` 14400 s; `disableStaticImages`.
  - **Remote fetching limits**: `maximumRedirects` 3 (redirect targets are not re-validated against patterns); `maximumDiskCacheSize` (default 50% of free disk; LRU; 16.1.7); `maximumResponseBody` 50 MB (16.1.2).
  - **Security**: `dangerouslyAllowLocalIP` false (SSRF guard); `dangerouslyAllowSVG` false (`.svg` src is auto-unoptimized); `contentDispositionType` `attachment`; `contentSecurityPolicy`; `unoptimized`.
  - **Deprecated**: `domains`, `next/legacy/image`.

  `getImageProps()` is for `<picture>`, art direction, and theme switching. `next/image-optimizer-transform` (`imageOptimizerTransform`, `getSharp`, `optimizeImage`) exposes the sharp pipeline as a standalone module, with experimental knobs `imgOptConcurrency`, `imgOptMaxInputPixels`, `imgOptTimeoutInSeconds` (7), and `imgOptMozjpeg`. Static export needs a custom loader. Source: `CMP/image.mdx`, `FN/image-optimizer-transform.mdx`, `G/upgrading/version-16.mdx`.
- **Font optimization**: Supported. `next/font/google` and `next/font/local` self-host fonts at build time, so the browser makes no requests to Google, and they compute size-adjusted fallbacks to avoid CLS.
  - **Options**: `src` (local; string or `[{path,weight,style}]`), `weight` (required for non-variable fonts; string, range, or array), `style`, `subsets` (google; preload warns if missing), `axes` (google variable), `display` (`swap` default), `preload` (true), `fallback`, `adjustFontFallback` (google `true`; local `'Arial'` \| `'Times New Roman'` \| `false`), `variable` (CSS var name), `declarations` (local `@font-face` descriptors).
  - **Usage**: the result exposes `className`, `style`, and `variable`. A font is preloaded only on routes whose page or layout calls the loader (the root layout means all routes). Each call creates one instance, so a shared definitions file is recommended. Tailwind integration goes through CSS variables.

  Source: `CMP/font.mdx`.
- **Third-party script loading**: Supported. `next/script`:
  - **`strategy` values**:
    - `beforeInteractive`: root layout only; injected into the head and fetched before first-party code; does not block hydration; runs once per document, not on client navigations.
    - `afterInteractive`: the default.
    - `lazyOnload`: browser idle time.
    - `worker`: experimental, **Pages Router only**, needs `nextScriptWorkers`; Turbopack doesn't support it.
  - **Callbacks**: `onLoad` (client components only; not with `beforeInteractive`), `onReady` (every mount), `onError` (not with `beforeInteractive`).
  - **Inline scripts**: allowed with an `id`. The `crossOrigin` config sets the attribute on generated scripts.
  - **Embeds**: `@next/third-parties` (Google Analytics, Tag Manager, Maps, YouTube embeds).

  Source: `CMP/script.mdx`, `G/scripts.mdx`, `G/third-party-libraries.mdx`.
- **CSS support**: Supported.
  - **Tailwind**: v4 is the `create-next-app` default (PostCSS plugin); a v3 guide exists.
  - **CSS Modules** (`.module.css`): Turbopack doesn't support `:local`/`:global` pseudo-classes standalone, `@value`, ICSS, or `composes` from a non-module file.
  - **Global CSS**: importable anywhere, but stylesheets **are not removed on navigation** (React stylesheet integration), so docs advise care.
  - **Sass** (`.scss/.sass`, modern API; `sassOptions`; `sassOptions.functions` unsupported in Turbopack).
  - **External stylesheets**: package CSS imports, or React 19 `<link rel=stylesheet>`.
  - **CSS-in-JS** in client components only: a style registry plus `useServerInsertedHTML`; works with styled-components, styled-jsx, MUI, Chakra, Panda, StyleX, vanilla-extract and others; emotion is listed as "working on support".
  - **Processing**: CSS order follows import order. Production output is chunked and minified CSS that loads without JS.
  - **Experimental flags**: `cssChunking`, `inlineCss`, `useLightningcss`; `turbopackLocalPostcssConfig` (16.3).
  - **Scoped styles**: no Vue/Svelte-style scoped styles beyond CSS Modules (not applicable).

  Source: `GS/11-css.mdx`, `G/sass.mdx`, `G/css-in-js.mdx`, `docs/01-app/03-api-reference/08-turbopack.mdx`.
- **MDX/Markdown as pages**: Supported via `@next/mdx`. `withMDX` in `next.config.mjs` plus `pageExtensions` lets `.mdx` (or `.md` via the `extension` option) be pages, routes, or imports. A root **`mdx-components.tsx` exporting `useMDXComponents` is required** in the App Router. Global, local, and layout-based component mapping is available. remark/rehype plugins work; under Turbopack, plugins must be referenced by string name with serializable options. Remote MDX is supported. **Frontmatter is not supported by default** (use remark-frontmatter etc.). `experimental.mdxRs` gives a Rust compiler and is not for production. Metadata exports work in MDX pages. Source: `G/mdx.mdx`, `FC/mdx-components.mdx`, `CFG/mdxRs.mdx`.
- **Notable extras**:
  - Turbopack has Vite-compatible **`import.meta.glob`** (lazy, eager, named, query, negation, `base` option) and **`import.meta.env`** (`DEV`, `PROD`, `MODE`, `BASE_URL`, `SSR`; no `VITE_*`). The Vite migration guide notes these work unchanged.
  - `optimizePackageImports` (experimental), `transpilePackages`, `urlImports` (experimental; not planned for Turbopack).
  - The `public/` folder.
  - `G/videos.mdx` covers `<video>`/embeds; there is no video component.

  Source: `docs/01-app/03-api-reference/08-turbopack.mdx`, `G/migrating/from-vite.mdx`.

## 11. Build output & deployment

- **Output modes**: Supported.
  - **Default** `.next` output, run with `next start`, which supports *all* features.
  - **`output:'standalone'`** produces `.next/standalone` with traced `node_modules` and a minimal `server.js` (`PORT`/`HOSTNAME` env). It doesn't copy `public` or `.next/static` (copy them or use a CDN), can't be combined with a custom server, and isn't relocatable on Windows if junctions are used.
  - **`output:'export'`** produces a static site in `out/`, with HTML per route (`trailingSlash` gives `/about/index.html`).
    - Supported: Server Components at build, client components, GET Route Handlers with `force-static`, and images via a custom loader.
    - **Unsupported**:
      - Routing: dynamic routes without `generateStaticParams` or with `dynamicParams:true`, intercepting routes.
      - Request-time features: cookies, request-reading route handlers, draft mode.
      - Server features: Proxy, Server Actions, ISR, default image optimization.
      - Config: rewrites, redirects, headers.
      - Also: `use cache`, `after`, streaming `loading` (per their platform tables).
  - Output file tracing uses `@vercel/nft`, and Turbopack `.nft.json` adds `fileHashes`, `symlinks`, and `additionalRoots`. Config: `outputFileTracingRoot`, `outputFileTracingIncludes`/`Excludes` (route-glob keys).

  Source: `CFG/output.mdx`, `G/static-exports.mdx`, `GS/17-deploying.mdx`.
- **Supported runtimes**: Partial. **Node.js** (≥ 20.9) is the only first-class rendering runtime, and Cache Components *requires* it. **Edge runtime: deprecated** for routes; segment `runtime` export deprecated and forbidden under CC; Proxy defaults to Node; Edge API surface is still documented and adapters can receive `runtime:'edge'` outputs. **Go**: experimental, for Route Handlers only. Bun runs via a verified adapter. Deno and Cloudflare Workers are only via third-party integrations (Deno Deploy; Cloudflare's own Next.js integration). "Other server-side JavaScript runtimes are not guaranteed to work" with CC. Per-route runtime choice exists only as the deprecated `runtime` export (and `route.go`). Source: `CFG/cacheComponents.mdx`, `SEG/runtime.mdx`, `docs/01-app/03-api-reference/07-edge.mdx`, `GS/17-deploying.mdx`.
- **Adapters / presets**: Supported via the **Deployment Adapter API**: `adapterPath` (stable 16.2) or the `NEXT_ADAPTER_PATH` env var.
  - **Interface** (`NextAdapter`): `modifyConfig(config, {phase, nextVersion, projectDir})` and `onBuildComplete({routing, outputs, projectDir, repoRoot, distDir, config, nextVersion, buildId})`.
  - **`routing`** phases: `beforeMiddleware`, `middlewareMatchers`, `beforeFiles`, `afterFiles`, `dynamicRoutes`, `onMatch`, `fallback`, `shouldNormalizeNextData`, `rsc`.
  - **`outputs`**: `pages`, `pagesApi`, `appPages`, `appRoutes`, `prerenders`, `staticFiles`, `middleware`. With `export`, only `staticFiles` is populated.
  - **Entrypoints** are invoked as `handler(req, res|ctx)` with `ctx.waitUntil` and `requestMeta.onCacheEntryV2`.
  - **Helpers and PPR**: `@next/routing` `resolveRoutes()` reproduces Next.js routing in adapters. A PPR resume protocol is documented.
  - **Runtime caching** goes through `cacheHandler` / `cacheHandlers`, not the adapter, which is build-time only.
  - **Compatibility**: a test harness (`NEXT_TEST_DEPLOY_SCRIPT_PATH` etc.) and a public results matrix.
  - **Verified adapters** (open source, run the suite): **Vercel, Bun**. Cloudflare and Netlify are "working on" verified adapters. Unverified own integrations: Appwrite, AWS Amplify, Cloudflare, Deno Deploy, Firebase App Hosting, Netlify. Templates exist for many Docker and Node hosts.

  Source: `ADP/*.mdx`, `CFG/adapterPath.mdx`, `GS/17-deploying.mdx`, `G/deploying-to-platforms.mdx`.
- **Config-level headers, redirects, rewrites, trailing slash, base path**: Supported.
  - **`redirects()`** (sync or async): `{source, destination, permanent (308/307) | statusCode, basePath:false, locale:false, has[], missing[]}`. `has`/`missing` items are `{type:'header'|'cookie'|'host'|'query', key, value?}` with named regex captures usable in the destination. Path-to-regexp patterns. The query string is passed through. Checked before the filesystem.
  - **`rewrites()`**: an array (afterFiles) or `{beforeFiles, afterFiles, fallback}`. Supports external URLs (incremental adoption / proxying) and applies to client-side routing. Params go into the query only if not used in the destination.
  - **`headers()`**: same matcher syntax.
  - **`trailingSlash`** (default false: `/about/` → `/about`; true reverses it, except files and `.well-known/`). `skipTrailingSlashRedirect`.
  - **`basePath`** (§1), `assetPrefix`.

  Source: `CFG/redirects.mdx`, `CFG/rewrites.mdx`, `CFG/headers.mdx`, `CFG/trailingSlash.mdx`.
- **Standalone / self-contained output**: Supported (`output:'standalone'`, above). Self-hosting topics:
  - `sharp` for image optimization.
  - Env vars: runtime env is read during dynamic rendering; `NEXT_PUBLIC_*` is inlined at build.
  - Build cache.
  - Multi-instance needs a shared encryption key, `deploymentId`, a shared cache handler, and `refreshTags` coordination.
  - Graceful shutdown.
  - Streaming through proxies.

  Source: `G/self-hosting.mdx`.
- **Skew protection**: Supported, but routing by deployment is the host's job. Set `deploymentId` (or `NEXT_DEPLOYMENT_ID`; config wins). Effects:
  - appends `?dpl=<id>` to JS/CSS/image URLs
  - sends an `x-deployment-id` request header on navigations
  - returns an `x-nextjs-deployment-id` response header
  - adds `data-dpl-id` on `<html>`
  - includes the ID in `use cache` keys
  - **on mismatch the client does a hard reload**

  Next.js does not *route* on `?dpl`; the host or CDN must. `supportsImmutableAssets` plus `outputHashSalt` give cross-deploy immutable assets that avoid skew. Server Action IDs rotate per build, so an old client gets "Failed to find Server Action"; rolling deploys and a stable `NEXT_SERVER_ACTIONS_ENCRYPTION_KEY` are recommended. Source: `CFG/deploymentId.mdx`, `G/self-hosting.mdx`, `ADP/12-immutable-static-assets.mdx`, `G/server-actions.mdx`.
- **Notable extras**:
  - `generateBuildId`, `distDir`, `poweredByHeader`, `httpAgentOptions`, `crossOrigin`, `productionBrowserSourceMaps`.
  - `enablePrerenderSourceMaps` (default true since 16.3).
  - `next build --debug-build-paths=<patterns>` builds selected routes. `--experimental-build-mode compile|generate`. `--experimental-app-only`.
  - Experimental build knobs: `staticGenerationRetryCount` (1), `staticGenerationMaxConcurrency` (8 pages per worker), `staticGenerationMinPagesPerWorker` (25).
  - Multi-Zones for splitting one domain across several apps.
  - The docs say a PPR "edge stitching" CDN integration is a performance (not correctness) concern.

  Source: `docs/01-app/03-api-reference/06-cli/next.mdx`, `G/deploying-to-platforms.mdx`.

## 12. Dev tooling & observability

- **Dev server and HMR**: Supported. `next dev` uses Turbopack by default (`--webpack` / `--custom-webpack` to switch). Options: `-p` (3000) / `-H` (0.0.0.0), `--experimental-https[-key|-cert|-ca]` (self-signed cert generation), `--experimental-cpu-prof`, and `--experimental-upload-trace`. Fast Refresh covers JS, TS, and CSS, and Server Component changes refresh with a fetch HMR cache. The Turbopack filesystem cache persists between runs (on by default for builds since 16.3). Experimental memory knobs: `turbopackMemoryEviction`, `turbopackGc`, lazy dynamic-import compilation. Dev and build can run concurrently (v16). `.next/dev/lock` records PID, port, and URL; a second `next dev` prints the existing server instead of starting another. `allowedDevOrigins` restricts cross-origin dev requests. Source: `docs/01-app/03-api-reference/06-cli/next.mdx`, `docs/01-app/03-api-reference/08-turbopack.mdx`, `G/ai-agents.mdx`, `CFG/allowedDevOrigins.mdx`.
- **Error overlay**: Supported. Source-mapped server and client errors and build errors are shown. [CC] **blocking-route insights** come with labeled fix cards linking to `/docs/messages/*` and a **Copy prompt** button for agents; the same menu prints in the terminal and in build output. A **Vulnerability Insight** appears when the installed version has a known CVE. Browser console output is forwarded to the terminal via `logging.browserToTerminal` (`'warn'` default \| `'error'` \| `true` \| `false`, with source locations; stable since 16.2). Source: `G/ai-agents.mdx`, `CFG/logging.mdx`.
- **Devtools**: Supported. The on-screen **Next.js DevTools** indicator (`devIndicators: {position}` or `false`; default `bottom-left`) shows whether a route is static or dynamic. The **Navigation Inspector** [CC] freezes page-load and client-nav shells. A Node inspector link is available from the overlay (`G/debugging.mdx`). React DevTools is recommended for Suspense and error boundary toggling. Source: `CFG/devIndicators.mdx`, `G/instant-navigation.mdx`.
- **Type generation commands**: Supported. `next typegen` (see §8).
- **CLI scaffolding / generators**: Partial.
  - **`create-next-app`** flags:
    - Language: `--ts` (default) / `--js`.
    - Styling and compiler: `--tailwind` (default), `--react-compiler`.
    - Rendering: `--cache-components` (default for App Router).
    - Linting: `--eslint`, `--biome`, `--no-linter`.
    - Project shape: `--app`, `--api` (route-handlers-only project), `--src-dir`, `--empty`.
    - Bundler: `--turbopack` / `--webpack`.
    - Setup: `--import-alias`, `--use-npm|pnpm|yarn|bun`, `--example`, `--skip-install`, `--disable-git`.
    - Agents: `--agents-md` (default), `--agent-feedback`.
  - **Other commands**: `next upgrade [--revision] [--agent security|latest|experimental-future]` (16.1); codemods (`@next/codemod`); `next info`; `next telemetry`; `next analyze` (Turbopack bundle analyzer UI, `--snapshot`, `-o`) plus `next analyze export` (16.4); `next build --analyze`.
  - **Gaps**: no in-project generators for routes or components (not found). The `next lint` command was removed in 16 in favor of the ESLint CLI.

  Source: `docs/01-app/03-api-reference/06-cli/create-next-app.mdx`, `docs/01-app/03-api-reference/06-cli/next.mdx`, `G/upgrading/version-16.mdx`.
- **AI-agent support**: Supported, and extensive.
  - **Bundled version-matched docs** in `node_modules/next/dist/docs/` (16.2+).
  - **Managed `AGENTS.md` block**: `next dev` creates or updates it when it detects an agent (default on since 16.3; `agentRules` config, `false` removes the block). For older versions, `npx @next/codemod agents-md` downloads docs to `.next-docs/`.
  - **llms.txt**: `nextjs.org/docs/llms.txt` and `llms-full.txt`, `.md` URL variants, and `Accept: text/markdown`.
  - **Built-in MCP endpoint** at **`/_next/mcp`** in dev (Next.js 16+; disable with `experimental.mcpServer:false`). Tools: `get_errors`, `get_logs`, `get_page_metadata`, `get_project_metadata`, `get_routes`, `get_server_action_by_id`, `get_compilation_issues`, `compile_route` (the last two Turbopack only), and `get_request_insights` (needs `experimental.requestInsights`). The `next-devtools-mcp` bridge package adds `nextjs_index`, `nextjs_call`, `nextjs_docs`, and `browser_eval`.
  - **Skills** (skills.sh): `next-dev-loop`, `next-bundle-optimizer` (16.4), `next-cache-components-adoption`, `next-cache-components-optimizer`, `next-partial-prefetching-adoption`, `next-partial-prefetching-optimizer`; plus a `vercel-react-view-transitions` skill.
  - **Agent-guided upgrades**: `next upgrade --agent` and `experimental.agentUpgrade` security reminders.
  - **Agent feedback**: `experimental.agentFeedback` (requires telemetry; opens anonymized issue-report forms).

  Source: `G/ai-agents.mdx`, `G/mcp.mdx`, `CFG/agentRules.mdx`, `CFG/agentFeedback.mdx`, `CFG/agentUpgrade.mdx`, `G/upgrading/agent-upgrade.mdx`.
- **Instrumentation / OpenTelemetry**: Supported. `instrumentation.ts` `register()` runs once per server instance, before the server is ready, and may be async. Use `process.env.NEXT_RUNTIME` to branch on Node vs Edge. Next.js is pre-instrumented with OTel: use `@vercel/otel` or a manual `NodeSDK`. There are default spans (e.g. `[http.method] [next.route]`, render, fetch), `NEXT_OTEL_VERBOSE=1` for more, and `NEXT_OTEL_FETCH_DISABLED=1`. Client side: `instrumentation-client.ts` runs before hydration and can export **`onRouterTransitionStart(url, navigationType:'push'|'replace'|'traverse', event?)`**. The experimental third `event` arg (16.3) carries `id`, `timestamp`, `fromRoutes`, and `prefetchIntent:'full'|'auto'|'none'|null`. Hook errors are isolated. Source: `FC/instrumentation.mdx`, `G/open-telemetry.mdx`, `FC/instrumentation-client.mdx`.
- **Server error reporting hooks**: Supported. `onRequestError` (see §7) covers render, route, action, and proxy errors, including PPR resume (`renderType:'dynamic-resume'`) and revalidation (`revalidateReason`). Source: `FC/instrumentation.mdx`.
- **Web vitals reporting**: Supported. `useReportWebVitals(cb)` from `next/web-vitals`, used in a client component, reports TTFB, FCP, LCP, CLS, and INP. Each metric has `id`, `name`, `delta`, `entries`, `navigationType`, **soft-navigation fields** (`navigationId`, `navigationURL`, `navigationStartTime`, `navigationInteractionId`), `rating`, and `value`. Keep the callback reference stable. `experimental.webVitalsAttribution` adds attribution. The `next-dev-loop` skill gets Web Vitals via `agent-browser`. Source: `FN/use-report-web-vitals.mdx`, `CFG/webVitalsAttribution.mdx`.
- **Notable extras**:
  - Dev logging: `logging.fetches`, `serverFunctions`, `incomingRequests`, `browserToTerminal`, or `logging:false`.
  - `next build --debug` / `--debug-prerender` / `--profile` / `--no-mangling`.
  - CPU profiling for dev, build, and start.
  - React Compiler is stable (`reactCompiler`); a Rust port is experimental (`turbopackRustReactCompiler`).
  - `experimental.turbopackPluginRuntimeStrategy`.
  - ESLint 10 support in `eslint-config-next` (16.4).
  - `@next/playwright` `instant()` e2e helper.

  Source: `CFG/logging.mdx`, `docs/01-app/03-api-reference/06-cli/next.mdx`, `CFG/reactCompiler.mdx`.

---

## Out-of-scope features seen (one line each)
- Auth: authentication guides (DAL, sessions, `authInterrupts`); `G/authentication.mdx`, `G/authentication-with-cache-components.mdx`.
- i18n: `G/internationalization.mdx` (route-based `[lang]`, root params; no built-in App Router i18n routing config).
- Testing: Vitest, Jest, Playwright, Cypress guides; Proxy unit-test helpers.
- PWA: `G/progressive-web-apps.mdx` (manifest, push notifications via web-push, service workers).
- Multi-tenant: `G/multi-tenant.mdx`.
- Analytics: `G/analytics.mdx`.
- CSP: nonce-based CSP guide (`G/content-security-policy.mdx`).
- WebSockets: not supported in Go routes; not documented for JS handlers.
