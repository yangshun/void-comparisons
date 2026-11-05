# Void — feature inventory
Version documented: 1.5.0 (`packages/void/package.json` and every `packages/*/package.json` = 1.5.0; repo clone of github.com/voidzero-dev/void) · Docs commit: 2026-11-04 (HEAD `65eb7f0`, `git log -1 -- docs`)
Context: UI libraries React 19 (`@void/react`, peer `react ^19`), Vue 3.5 (`@void/vue`), Svelte 5 (`@void/svelte`, runes only), Solid 1.9 (`@void/solid`) · bundler Vite 8 (optionally Vite+ `vp`) · server engine Hono (every handler gets a Hono `Context`) · default runtime Cloudflare Workers (workerd/Miniflare in dev); alternative `target: "node" | "bun" | "deno"`.

Scope: native "Void app" mode only (`routes/`, `pages/`, `middleware/`, custom SSR `src/main.ssr.ts`, `output: "static"`). Framework mode (`voidPlugin()` inside Nuxt/SvelteKit/etc.) and platform admin docs are excluded.

Conventions in this file: "Source:" paths are relative to the repo root. "Undocumented (source: …)" = exists in code but not in `docs/`. "Not found" = I grepped docs **and** `packages/` for the listed terms and found nothing.

Three app shapes exist inside native mode (docs/guide/app-types.md):
1. **Pages mode** – `pages/` dir + adapter plugin (`voidReact()`, `voidVue()`, `voidSvelte()`, `voidSolid()`); Inertia.js-style protocol (server loader → props; client router fetches JSON page objects). This is the "full framework".
2. **Custom SSR** – `src/main.ssr.ts(x)` + `src/main.client.ts(x)`; user brings router/rendering; Void supplies asset tags, API routes, ISR, prerender (docs/guide/ssr.md).
3. **API-only / SPA + API** – `routes/` only, optional Vite SPA in `src/` (`inference.appType: "spa"`).

---

## 1. Routing

- **Route definition / file conventions**: Supported (file-based only; no config/code-based route table). Two trees share one parser (`packages/void/src/router/parse-filename.ts`):
  - `routes/` – HTTP endpoints; extensions `.ts .tsx .js .jsx .mts .mjs`. Each file exports named method constants `GET POST PUT PATCH DELETE OPTIONS` (OPTIONS accepted by source, `packages/void/src/router/detect-exports.ts`; docs only show GET/POST/etc.). Exporting `HEAD` is a build error ("HEAD requests are answered by the GET handler"). Undocumented: a route file with **no** method exports is mounted with `app.all(pattern, module.default)` (source: `packages/void/src/router/compile.ts`). `*.ws.ts` files are WebSocket routes (Cloudflare-only; out of scope).
  - `pages/` – UI components `.tsx .jsx .vue .svelte .md`; companion server file `<name>.server.{ts,tsx,js,jsx,mts,mjs}`. `about.tsx` and `about/index.tsx` map to the same URL; having both is a build error ("Multiple page files resolve to the same route") (source: `packages/void/src/pages/scan.ts`).
  - Parsing rules, applied in order: strip extension → strip `.dev`/`.prod` env suffix → strip trailing `index` → drop `(group)` segments → `[param]` → `:param`, `[...param]` → `:param{.+}`, bare `[...]` → `*` → prefix `/`.
  - Ignored: any path segment starting with `_` (except `pages/**/_layouts/`) and, in `routes/`, segments starting with `.` (but `.well-known` is kept) (docs/guide/server-routing.md).
  - Matching order: static < dynamic < catch-all, depth-first, then alphabetical (`compareRouteSpecificity`, `packages/void/src/router/scan.ts`). Two dynamic pages matching the same URLs (e.g. `[id]` vs `[slug]`) → warning "is never used" (first wins).
  - Precedence between trees: global middleware → `routes/` handlers → page GET/mutation handlers → not-found fallback. A `routes/` file and a page with the same pattern: the route wins for the methods it exports (registration order, `compile.ts`).
  - Hono strict routing: `/about/` does not match `/about`. Undocumented: in Pages apps the not-found fallback 301-redirects `/x/` → `/x` (source: `packages/void/src/runtime/routing-pages.ts` `createPagesFallback`).
  - Environment-only files: `name.dev.tsx` (dev server only), `name.prod.tsx` (build/deploy/preview only); a `.dev`+`.prod` pair for one URL is allowed; suffix must precede `.island` and be kept on companions (`home.dev.server.ts`). Resources used only by `.dev` files are not provisioned. Applies to `routes/` and `pages/`, not `middleware/` (docs/guide/pages-routing/overview.md, docs/guide/server-routing.md).
  - `sourceDir` config moves all conventions (`pages/`, `routes/`, `middleware/`, …) under e.g. `src/` (docs/reference/config.md).
  Source: docs/guide/server-routing.md, docs/guide/pages-routing/overview.md, docs/reference/structure.md.

- **Nested layouts**: Supported. `layout.{tsx,vue,svelte}` in any `pages/` directory wraps all pages beneath; chain = root layout + one per ancestor directory (innermost last) (`packages/void/src/pages/layout-resolution.ts`). Children injected as `children` (React/Solid/Svelte snippet) or default `<slot />` (Vue). Layouts persist component state across client navigations ("keep their component state as you navigate").
  - **Named layouts**: files in `_layouts/` (any level; only direct children). Page selects with `export const layout = 'name'` (component file; Svelte via `<script context="module">`) or Markdown frontmatter `layout:`. Values: `'name'` = replace innermost layout of the chain (outer layouts kept); `'!name'` = replace the whole chain; `false` = no layout. Closest `_layouts/` in page dir or ancestors wins; missing name = build error; a path-like value (`./x`, `/x`) only warns and falls back to defaults. Value must be a static literal (read by AST).
  - **Layouts have no loader**: layout files get no `.server.ts` companion lookup (scan.ts only looks up companions for pages). Data for layouts comes only from middleware `c.set('shared', …)` → `useShared()`.
  - Island constraint: a regular page under an `layout.island.*` is a build error ("Add a .island suffix"). Layouts on island pages are static (not hydrated).
  Source: docs/guide/pages-routing/layouts.md.

- **Dynamic segments / optional segments / catch-all**: Dynamic `[id]` and catch-all `[...path]` Supported (catch-all requires ≥1 char: pattern `:path{.+}`; typed URL helpers use `/files/:path{.+}`). **Optional segments: Not supported / not found** (grepped `[[`, "optional segment/param" in docs, `packages/void/src/router`, `packages/void/src/pages`; parser has no `[[x]]` rule). Optional catch-all (`[[...x]]`) likewise absent. Source: packages/void/src/router/parse-filename.ts.

- **Route groups / pathless layouts**: Partial. `(group)/` directories are stripped from URLs (both trees). But layouts are resolved by directory segments (`componentPath`), so a `(group)/layout.tsx` does wrap only that group — de facto pathless layout (inferred from `resolveLayoutDirectories` using file path; not explicitly documented). Named layouts provide per-page layout selection without URL changes. Source: docs/guide/server-routing.md; packages/void/src/pages/layout-resolution.ts.

- **Parallel routes / intercepting routes (modal routes)**: Not supported (not found). Grepped "intercept", "parallel route", "modal route", "@slot", "named slot" in docs and `packages/void/src/{pages,router}`: no hits beyond unrelated email-testing text. One page component renders per URL.

- **Typed links and typed route params**: Supported (opt-in strictness).
  - `routeUrl(pattern, { params, query, hash })` from `void/routes`: pattern autocomplete over page, HTTP, and WebSocket routes; required params checked; values `string | number`, URL-encoded; catch-all keeps `/`; invalid/missing params throw `TypeError` at runtime.
  - `RouteDestination` objects `{ pathname, params, query, hash }` accepted by `router.visit/prefetch/flush` and `c.rewrite()`.
  - `routing.typedRoutes: true` (default on in `void init` apps; off otherwise) type-checks plain strings in `Link href`, `router.visit/prefetch/flush`, `c.rewrite()`. Accepts route-matching strings with optional query/hash, same-page `?x`/`#x`, `http(s):`, `mailto:`, `tel:`. Rejects relative paths (`../x`). Dynamic segment matches any text incl. empty (so `/users/` passes for `/users/:id`). Escape hatch casts `as RouteUrl` / `as Href`. Restart dev server or `void prepare` after toggling.
  - `useParams<T>()` is a manual generic (defaults to `Record<string,string>`) — params are **not** inferred from the file path (packages/react/src/runtime/use-params.ts; same in other adapters).
  Source: docs/guide/type-safety.md, docs/reference/api/types.md, docs/reference/config.md.

- **Search-param handling**: Partial.
  - Reading: `useRouter().query` (`URLSearchParams`, untyped); server `c.req.query()`.
  - Building: `routeUrl(..., { query })` and `Link data={…}` (GET `data` merged into href query: primitives via `String()`, arrays → repeated keys, `null`/`undefined` omitted, nested objects throw). `RouteQuery` type is `Record<string, string|number|boolean|null|undefined|array>` — keys are not route-specific.
  - Validation: server-side only via `defineHandler.withValidator({ query: schema })` (Standard Schema; multi-value keys become arrays). On a page loader, a failed validation returns a raw 400 JSON response (no page-level error rendering).
  - No typed/validated search params on the client (no route-level search schema). Source: docs/guide/type-safety.md, packages/void/src/runtime/validator.ts.

- **Programmatic navigation**: Supported (Pages mode only; not on island pages). `useRouter()` (all four adapters) returns `{ url: URL, path, query: URLSearchParams, params, visit, refresh, prefetch, flush, flushAll }`.

  | method | args | behavior |
  |---|---|---|
  | `visit(dest, opts?)` | dest = string \| `URL` \| `RouteDestination` | Same-origin http(s)/`capacitor:` → client nav (fetch JSON page object); other-origin http(s) GET → full load; non-GET cross-origin throws; `javascript:`/`data:` etc. throw. |
  | `refresh(opts?)` | — | Re-fetch current page props, same history entry. |
  | `prefetch(dest, {cacheFor})` | GET only (else throws) | Loads code + data into prefetch cache; awaitable. |
  | `flush(dest, method='GET')` / `flushAll()` | — | Drop prefetch entries. |

  Visit options (`VisitOptions`, packages/void/src/pages/navigation-engine.ts): `method` (default GET; `POST/PUT/PATCH/DELETE` for action calls), `data` (body for non-GET; JSON, or `multipart/form-data` if it contains `File/Blob/FileList`), `preserveScroll` (default false), `preserveState` (default: `false` for GET, `true` for non-GET), `replace` (history.replaceState), `viewTransition` (override global), `resolveOn: 'data' | 'commit'` (**React only**; default `'commit'` waits for React to commit DOM+URL; `'data'` resolves when page data ready — for use inside `startTransition`/form actions).
  React navigations are scheduled as transitions. Concurrent visits: a new visit aborts the pending one; stale visits never commit. `useNavigation()` → `{ state: 'idle'|'loading'|'submitting', location, method }`.
  Source: docs/guide/pages-routing/overview.md, docs/reference/api/pages.md.

- **`Link` component**: Supported in all four adapters with identical props (Vue uses kebab-case attrs). Renders `<a>` for GET, `<button type="button">` for non-GET. Adds `style.touchAction = 'manipulation'`.

  | prop | values / default | behavior |
  |---|---|---|
  | `href` | `Href` (typed when `typedRoutes`) | destination |
  | `method` | `GET`(default)/`POST`/`PUT`/`PATCH`/`DELETE` (any case) | non-GET renders a button that performs an action visit |
  | `data` | object | GET: merged into query; non-GET: request body |
  | `prefetch` | `true`=`'hover'`, `false`, `'hover'\|'click'\|'mount'\|'visible'`, or array (first trigger wins) | GET only; non-GET + prefetch throws |
  | `cacheFor` | ms number, `'30s'`-style string (units ms/s/m/h/d), or `[fresh, expire]` pair | prefetch cache TTL (SWR window for pairs); `0` = single-use |
  | `preserveScroll` | false | keep scroll |
  | `preserveState` | false | keep page component state (adapter-specific, below) |
  | `replace` | false | replace history entry |
  | `reloadDocument` | false | let browser do a full navigation; GET only (throws otherwise); disables prefetch |
  | `viewTransition` | inherits plugin `viewTransitions` | per-link override |
  | `activeMatch` | `'exact'`(default) \| `'prefix'` | active-link marking |
  | `onNavigate` | `(e) => void`, `e.preventDefault()` cancels | runs after user onClick |

  Click handling skips: modified clicks (ctrl/meta/shift/alt/non-left), `download` attribute, `defaultPrevented`, cross-origin. Active links: exact match gets `aria-current="page"` + `data-void-active`; `prefix` match on nested paths gets only `data-void-active`; comparisons are case-sensitive, trailing-slash-significant, ignore query/hash; `/` is never a prefix match; user-supplied attributes win. Source: packages/void/src/pages/link.ts, packages/react/src/runtime/link.tsx, docs/reference/api/pages.md.
  - Adapter state differences on GET navigation: **Vue** remounts the page (`currentPageKey++`) unless `preserveState`; **Solid** re-creates the page on GET nav and on route/param change, keeps it for back/forward/mutations/refresh within the same record; **React** relies on React reconciliation (same component type keeps state; no remount key found in `packages/react/src/runtime/pages-client.ts`); **Svelte** swaps `$state` page/props in `App.svelte`. Layouts persist in all. Source: docs/reference/api/pages.md, packages/vue/src/plugin-pages.ts, packages/solid/src/plugin-pages.ts.

- **Prefetching**: Supported. Strategies `hover` (after `hoverDelay`, default 75 ms; also on keyboard focus and `touchstart`), `click` (on `mousedown`/`touchstart`), `mount` (on render), `visible` (IntersectionObserver, once). App-wide adapter option `prefetch: { defaultStrategy (default false), hoverDelay (75), cacheFor ('30s') }`; invalid strategy throws at plugin config time. Prefetch fetches **both code and data**: dynamic-imports the page + layout component chunks and requests the page JSON with headers `X-VoidPages: true`, `Purpose: prefetch`; deferred props are resolved inline in prefetch responses (no streaming). Prefetch runs the server loader ("keep loaders free of side effects"). Island targets get a `<link rel="prefetch" as="document">` instead. Not prefetched: other origins, the current URL, non-GET. Any non-GET visit flushes the entire prefetch cache. Static builds (`output: "static"`) prefetch from `/_void/pages/<path>.json` files when no redirects/rewrites/fallbacks exist (fast path). Source: docs/reference/api/pages.md#prefetching, packages/void/src/pages/navigation-engine.ts, packages/void/src/pages/prefetch.ts, packages/void/src/pages/static-data.ts.

- **Scroll restoration**: Supported (automatic, window-only). Back/forward and reload restore saved positions (key stored in `history.state.__voidScrollKey`, positions in `sessionStorage` with prefix `void:scroll:`); new navigation scrolls to top; hash targets `scrollIntoView`; same-page `#hash` links skip the server fetch. Opt-out per visit: `preserveScroll`. No per-element/scroll-container restoration found. Source: docs/guide/pages-routing/overview.md#scroll-restoration, packages/void/src/pages/scroll-restoration.ts.

- **View transitions**: Supported (all four adapters, Pages router only). `viewTransitions: true` on the adapter plugin enables `document.startViewTransition` for Link clicks, `router.visit`, back/forward; per-link `viewTransition` / per-visit override. Default cross-fade; customize with `::view-transition-*` CSS and `view-transition-name`. Unsupported browsers fall back silently. Island pages / full-page loads: no built-in cross-document transitions. Source: docs/guide/pages-routing/view-transitions.md, packages/void/src/pages/client.ts.

- **Route-level code splitting**: Supported (automatic). Client manifest maps each page/layout id to `() => import(...)` (packages/void/src/pages/manifest.ts); on GET visits the router starts importing the matched component in parallel with the data request. Server: route/page server modules are lazily imported and cached per isolate (cache disabled in dev) (`createModuleLoader`, packages/void/src/runtime/routing.ts). If every page is an island page, the pages-client bundle is not emitted.

- **Base path**: Not supported for routing (not found). No `basePath`/`base` routing option in `RoutingConfig` (packages/void/src/config.ts) or docs. Vite's `base` is honored only for assets (and forces all pages through the Worker on direct Cloudflare deploys, docs/guide/ssg.md). Route patterns are always root-relative.

- **Notable extras**:
  - `.dev`/`.prod` environment-only routes and pages.
  - Named/exclusive layouts (`'!name'`) and `layout = false`.
  - Rewrites as routing primitives: `routing.rewrites`, `routing.fallbacks`, `_redirects` `200`/`200!`, and middleware `c.rewrite()` (see §6/§11). Caveat: client-side `Link` navigation does not go through server rewrites for the purposes of loader selection: "a client-side `<Link href="/docs">` navigation may fetch loader data for `/docs` rather than the rewritten route" — use `<a>` (docs/guide/edge/rewrites.md#client-navigation).
  - Island pages and Markdown pages have **no client router**: all navigation to/from them is a full document load; `<Link>` must not be used inside island pages.
  - Hash-only/same-page navigation handled without fetch; `capacitor:` scheme supported for Capacitor iOS WebViews.

## 2. Rendering modes

- **SSR**: Supported (default for Pages, `output: "server"`). First request returns full HTML containing `<script id="__VOID_PAGE_DATA__" type="application/json">` (page object: `component, props, params, shared, url, errors, head, deferred*`) and `<div id="app">`. Subsequent client navigations request the same URL with `X-VoidPages: true` and receive JSON (`Vary: X-VoidPages`). Every page response carries `X-Powered-By: Void`. Per-adapter renderer (packages/*/src/plugin-pages.ts):

  | adapter | server API | client |
  |---|---|---|
  | React | `react-dom/server` `renderToReadableStream` (streaming); React 19 required | `hydrateRoot`; navigations as transitions |
  | Vue | `vue/server-renderer` `renderToString` (buffered) | `createSSRApp` hydrate |
  | Svelte | `svelte/server` `render` (sync, buffered); `<svelte:head>` output is injected into `<head>` (undocumented) | `hydrate` |
  | Solid | `renderToStringAsync` (buffered, waits for resources) + `generateHydrationScript` | hydrate |

  Custom SSR mode: you write `defineRender((c, assetTags) => Response)` (or named `render`), inserting `assetTags.css`, `assetTags.preloads` in `<head>`, `assetTags.body` before `</body>`; API routes and static files are served first, all other non-API requests go to `render`. Source: docs/guide/ssr.md, docs/reference/api/handlers.md#definerender-handler.

- **Streaming SSR**: Partial; differs by adapter.
  - Mechanism shared by all adapters: `defer()` props. The HTML (or JSON) is sent first, then each deferred group is appended as it resolves — in HTML as inline `<script>` calls to `window.__resolveDeferred(group, data)` / `__rejectDeferred`, in client navigations as NDJSON (`application/x-ndjson`, first line = page object, then `{__deferred, data|error}` lines). Deferred resolvers start only after the loader returns, run in parallel, and stream in completion order (packages/void/src/pages/protocol.ts `streamDeferredResponse`).
  - **React**: true React streaming (`renderToReadableStream`); deferred props are Promises read with `use()` under `<Suspense>`; with deferred props Void sends the Suspense-fallback shell then cancels React's stream at a shell marker and streams data via scripts (packages/react/src/runtime/pages-server.ts, page-streams.ts). User-level Suspense/lazy without `defer()` streams natively. Errors before the shell → server error page; after shell → logged.
  - **Vue/Svelte/Solid**: component HTML is fully buffered; only deferred data streams (as `{ loading, value, error }` reactive state). No component-level streaming.
  - Custom SSR: user returns any `Response` (can be a stream). Source: docs/guide/pages-routing/loaders.md#deferred-props, docs/reference/api/pages.md.

- **Static pre-rendering incl. dynamic params**: Supported, two flavors.

  | | `output: "static"` (build-time SSG) | `output: "server"` + `prerender = true` (deploy-time "edge prerendering") |
  |---|---|---|
  | default | every page `prerender = true` unless dynamic without `getPrerenderPaths` | `false`; opt in per page |
  | opt-out/in | `export const prerender = false` → rendered by Worker on request | `export const prerender = true` |
  | dynamic params | `export async function getPrerenderPaths()` returns `[{slug:'a'}, …]` (no arguments; runs inside the built Worker with bindings) | same, must also export `prerender = true` |
  | output | HTML in `dist/client/` + `/_void/pages/*.json` page data for client nav; default `404.html` generated if ≥1 page prerendered (override `public/404.html` or a `/404` page) | rendered once per deployment before traffic switches, stored in the ISR cache with TTL (default 1 year, override `export const revalidate`) |
  | failures | warn, don't fail build (packages/void/src/prerender.ts) | logged, never block deploy; page renders on first request |
  | runtimes | all targets | Cloudflare only (needs ISR); `routing.isr: false` disables |

  Extra: `routing.prerender: ['/', '/about']` explicit path list; custom SSR exports top-level `prerender = true` + `getPrerenderPaths()` returning full path strings. Auto-prerender: island pages with no loader and no params, and Markdown pages, even in `output: "server"`. `ssr`, `prerender`, `revalidate` exports must be static literals (`const`; read by AST in packages/void/src/pages/scan.ts); `revalidate` must be a non-negative integer. Param values are substituted into the pattern without URL-encoding (packages/void/src/router/compile.ts). Source: docs/guide/ssg.md, docs/guide/edge/prerendering.md, docs/reference/config.md#output.

- **Client-only / SPA routes and full SPA mode**: Supported.
  - Per page: `export const ssr = false` in the companion → loader still runs on the first request and its props are embedded; the HTML is a shell (`<div id="app" data-void-ssr="false">`) and the component mounts (not hydrates) in the browser; head still rendered server-side. Combinations: `ssr=false`+`prerender=true` → prerendered client shell with embedded loader data; island page + `ssr=false` → build error. No global "ssr: false for all pages" switch found in `VoidConfig`.
  - Full SPA: `inference.appType: "spa"` (Vite SPA in `src/` + optional `routes/` API); unmatched navigations serve `index.html` with 200 (on a Void platform, missing files under `/assets/` 404). `routing.fallbacks`/`routing.notFound: 'single-page-application'` for custom setups. Source: docs/guide/pages-routing/overview.md#how-navigation-works, docs/guide/app-types.md.

- **Partial hydration (islands / server components / server islands)**: Partial — islands only.
  - Island pages: filename suffix `.island.{tsx,jsx,vue,svelte}`; `.md` pages are implicitly island pages. Rendered on the server; layouts static; **only** components imported with an import attribute hydrate: `import Counter from './_Counter' with { island: 'load' }` (requires TS `"module": "ESNext"`). Unmarked imports ship zero JS. Island pages have no client router (full-page navigations), use `useIslandForm` (`useForm` import in an island page warns), and after a successful action reload the page via `window.location` (redirects followed). Island props are serialized with `JSON.stringify` into `data-props` on a wrapper `<div data-island data-hydrate>` — so functions/children/JSX/Date cannot be passed (inferred from packages/react/src/plugin-islands.ts). Each island hydrates as a separate root (no shared context between islands except `useFrontmatter()`).
  - Works in all four adapters (each has `plugin-islands.ts`).
  - **Server components / server islands: Not supported** (grepped "server component", "use server", "use client", "rsc", "server island" — RSC appears only for the out-of-scope vinext framework integration in packages/void/src/index.ts).
  Source: docs/guide/pages-routing/islands.md.

- **Static shell with dynamic holes (PPR-like)**: Not supported (not found; grepped "partial prerender", "ppr"). Closest approximations: ISR-cached HTML + `defer()` (but deferred data is part of the cached response), or island pages with client-side fetching.

- **Per-route rendering-mode control**: Supported via page exports: `ssr` (true/false), `prerender` (true/false), `revalidate` (seconds), `getPrerenderPaths()`, `.island` suffix; plus path-pattern `routing.revalidate` and `routing.prerender` in config. Per-route runtime choice: not applicable (one Worker/server). Source: docs/guide/pages-routing/overview.md (flag table), docs/guide/edge/revalidation.md.

- **Hydration strategies**: Partial. Regular pages: full hydration on load (whole layout+page tree). Island components: `'load'` (immediately), `'visible'` (IntersectionObserver), `'idle'` (`requestIdleCallback`, fallback `setTimeout(1)`), `'media:(query)'` (when `matchMedia` matches). No `client:only`-style (skip SSR) island, no on-interaction strategy found (packages/void/src/pages/client.ts `scheduleHydration`). Source: docs/guide/pages-routing/islands.md#hydration-strategies.

- **Notable extras**: environment-dependent auto-prerender rules; static deploys automatically skip the Worker for prerendered pages without `.server.ts` (hybrid deploy, docs/guide/ssg.md#deployment-behavior); `ssr=false` shells can be prerendered with loader data.

## 3. Data loading

- **Where data is fetched**: Pages: a single `loader` per page exported from the `.server.ts` companion, written with the same `defineHandler` as API routes (`(c: CloudContext) => props`). Layouts: no loaders; cross-page data comes from middleware via `c.set('shared', {...})` read with `useShared()`. Custom SSR / SPA: typed `fetch` from `void/client` (works isomorphically; server-side calls to the app's own routes skip HTTP and forward `cookie`/`authorization`). No server functions/RPC beyond route handlers, no client loaders, no composables like `useFetch`. Source: docs/guide/pages-routing/loaders.md, docs/guide/typed-fetch.md.
  - Loader return handling (packages/void/src/pages/protocol.ts `runLoader`): plain object → props; `Response` with status ≥300 (redirect/error) or non-JSON 200 (file, stream) → returned as-is (page not rendered); JSON 200 `Response` (e.g. `c.json()`) → parsed as props; `undefined` → `{}`. No loader → empty props.
  - Loader may use per-route middleware: `export const loader = defineHandler(mw1, mw2, handler)` (≤5); the middleware wraps the rendered page response.

- **Loader execution model**: Server-only, one loader per request (no nested loader tree, so no parallel-vs-waterfall question beyond the page itself). Order per request: edge rules → global middleware (numeric order) → per-route middleware → loader → `head()` → deferred resolvers (parallel, after loader). Runs on: initial document request, every client GET navigation (fresh JSON request unless prefetched), `router.refresh()`, after every successful action (same response), and on prefetch. Source: packages/void/src/pages/protocol.ts.

- **Request deduplication**: Partial. Client: prefetch cache keyed `METHOD:url` — concurrent prefetches share one promise; a visit consumes a usable prefetched entry; deferred groups share one resolver call when keys use the same `defer('group', fn)`. Server: no fetch/data dedup or memoization layer (not found). Source: packages/void/src/pages/prefetch.ts, docs/guide/pages-routing/loaders.md#grouped-deferred-props.

- **Passing server data to client components**: Supported. Loader return → page props (JSON-serialized; `Serialize<T>` type: `Date` → `string`; `bigint`, functions, `undefined` dropped). `useShared()` (middleware data), `useParams()`, `useRouter()`. Island components receive only JSON props passed by the island page. No rich serializer (no devalue/superjson; `JSON.stringify` + script escaping in packages/void/src/pages/serialize.ts). Source: docs/guide/type-safety.md#serialization.

- **Client-side data cache**: Partial. Only the prefetch cache (default 30 s, configurable `cacheFor`, `[fresh, expire]` gives stale-while-revalidate: stale entry used immediately, background refetch). Visited pages are **not** cached by default: back/forward re-fetches (an internal `cacheVisitedPageData` engine option exists but is not wired to any adapter plugin option — source: packages/void/src/pages/navigation-engine.ts). Initial page data is cached only when that option is on. No normalized/query cache.

- **Deferred / streamed data**: Supported. `defer(fn)` or `defer('group', fn)` (one call shared by all keys of a group; resolver receives `c`). React: `Deferred<T>` is `Promise<T>` → `use()` + `<Suspense>`; errors throw to nearest React error boundary. Vue/Svelte/Solid: `{ loading, value, error }` discriminated union. Production masks unexpected deferred errors as `"Internal Server Error"`; `HTTPException` messages pass through; dev shows raw message. Prefetch responses resolve deferred inline; per-group failures go into `deferredErrors`. After an action, deferred props keep their last resolved values until the next navigation (mutation responses strip deferred). ISR/static: static page-data fast path is skipped for pages with deferred keys. Source: docs/guide/pages-routing/loaders.md, packages/void/src/pages/protocol.ts.

- **Dependency tracking & invalidation**: Partial/manual. No automatic dependency tracking. Invalidation primitives: action responses re-run the current page's loader automatically; any non-GET visit flushes the whole prefetch cache; `router.refresh()`, `router.flush(url)`, `router.flushAll()`. No tag/key-based client invalidation or cross-page revalidation. Source: docs/guide/pages-routing/overview.md.

- **Access to request context**: Supported. Loader/action/head get the Hono `Context` (`CloudContext`): `c.req` (`param()`, `query()`, `header()`, `json()`, `parseBody()`, `raw`), `c.env` (typed bindings), `c.get/set` (typed via `declare module 'void' { interface CloudContextVariables {...} }`), `c.get('user'|'session')` (auth), `c.redirect`, `c.rewrite`, `c.originalUrl()`, `c.isRewritten()`, `c.executionCtx` (Cloudflare). Cookies via Hono helpers (`hono/cookie`; not specifically documented). No public `getRequest()`/`getContext()` helper for deep code (an internal `AsyncLocalStorage` `requestContext` exists and powers `getUser()`; source: packages/void/src/runtime/routing.ts). Source: docs/reference/api/types.md.

- **Notable extras**: typed `fetchStream()` (async iterator over SSE text chunks) in `void/client`; `useFrontmatter()` and `@void/md/pages` build-time metadata list for Markdown.

## 4. Mutations

- **Form handling without JS (progressive enhancement)**: **Not supported.** Evidence (source, docs silent — grepped "progressive", "without JavaScript", "no-js"):
  - React `Form` renders `<form action={form[method]}>` with a React 19 function action — no URL action before hydration (packages/react/src/runtime/form.tsx); submission payload is `form.data` (client state), not the FormData.
  - Vue/Svelte/Solid `Form` render `<form>` with no `action`/`method` and an `onSubmit` that calls `preventDefault()` (packages/vue/src/runtime/form.ts, packages/svelte/src/runtime/Form.svelte, packages/solid/src/runtime/form.tsx) — without JS the browser would GET the current URL.
  - `defineHandler.withValidator({ body })` parses only `c.req.json()` and returns 400 `Invalid JSON body` otherwise (packages/void/src/runtime/validator.ts), so urlencoded/multipart posts don't validate.
  - The server *can* answer a non-JS POST with full HTML (mutation without `X-VoidPages` re-renders HTML, packages/void/src/pages/protocol.ts), so a hand-written `<form method="post">` + unvalidated action that parses `c.req.parseBody()` would work for POST only.

- **Server functions / RPC / actions**: Partial (page actions + HTTP routes; no RPC/server functions).
  - Page actions in `.server.ts`: `export const action = defineHandler(...)` or `export const actions = { name: handler, default?: handler }` (not both). Registered for `POST PUT PATCH DELETE` on the page URL. Named action selected by the first query key: `/users/42?update`; unknown name → 404 `Unknown action: x`; lookup uses own properties only.
  - Action result handling (packages/void/src/pages/protocol.ts `respondToAction`):

    | action outcome | response |
    |---|---|
    | returns nothing / 204 | re-run page loader; JSON page object (client) or full HTML (no-JS) with fresh props |
    | `c.redirect(url)` (3xx) | passed through; client follows (fetch-followed redirect treated as GET of destination) |
    | throws `ValidationError({field: msg})` (from `void/handler`) | re-render page with `errors` (island pages: 422 `{errors}`) |
    | `withValidator` 400 with `issues` | flattened to `{ 'path.to.field': message }` errors, same as above |
    | other `Response` (incl. other 400s, JSON 200 from withValidator) | passed through as-is; a non-page 2xx response makes the client fall back to a full page load (packages/void/src/pages/navigation-engine.ts) |
    | throws `HTTPException`/other | Hono `onError` (see §7) |

    Plain `defineHandler(fn)` return values other than `Response` are ignored (page re-renders). There is no documented way to return arbitrary data from an action to the caller beyond the refreshed page props (`action()` returns `{ ok: true, pageData }`).
  - `action(url, { data, params, method })` one-shot helper (all adapters; default POST) → `{ ok: true, pageData } | { ok: false, error: VoidActionError }`; updates the page on success.
  - API routes + typed `fetch` for everything else.
  Source: docs/guide/pages-routing/actions-and-forms.md.

- **`useForm` / `Form` / `useIslandForm` options and state**: Supported.
  `useForm(url, defaults, options?)` — `url` autocompletes action URLs incl. `?name`; `defaults` typed from the action's body schema (falls back to `Record<string, unknown>` without a validator). Options: `params` (fills `:id` at submit time), `resetOnSuccess` (reset data **and** defaults to mount values on success), React only: `onSuccess`, `onError(fieldErrors | VoidActionError)` (async; `pending` stays true until they finish).

  | returned | behavior |
  |---|---|
  | `data` | reactive values (React/Solid also `setData(field, value)`; Vue/Svelte mutate/bind directly) — editing a field clears its error |
  | `errors` | field → message, keys typed |
  | `error` | `VoidActionError` (`status`, `statusText`, `body`, `url`, `limit`) or null |
  | `post/put/patch/delete` | React: native form-action callbacks `(formData) => void` (via `useActionState`; `useFormStatus` works); Vue/Svelte/Solid: `(opts?) => Promise<void>` where opts = visit options (`preserveScroll`, `preserveState`, `replace`, `viewTransition`, `data` override) |
  | `pending` | in-flight |
  | `hasChanges` | data ≠ current defaults |
  | `wasSuccessful` / `recentlySuccessful` | true after success / for 2 s |
  | `reset(...fields)` / `reset({initial:true}, ...)` | restore defaults (last successful submit) or mount values |
  | `setError`, `clearErrors(...fields)`, `clearError()` | client-side error control |

  `Form` props: `form` (required), `method` (`post` default/`put`/`patch`/`delete`), `renderError` (snippet in Svelte); renders `role="alert" data-void-form-error` message block, `aria-busy`, blocks resubmission until a known 429 retry deadline (`UsageLimit`), never auto-retries. `useIslandForm(defaults)`: same state; submit helpers take the URL (`post(url)`…; Vue/Svelte also `submit(url, method)`); success reloads page; 422 `{errors}` populates errors. Source: docs/guide/pages-routing/actions-and-forms.md, docs/reference/api/pages.md, packages/*/src/runtime/use-form*.

- **Pending, error and validation-error state**: Supported (above) + global `useNavigation().state === 'submitting'`. Error routing by status (packages/void/src/pages/action-result.ts): **call-site** (stored in `form.errors`/`form.error`, `action()` returns `ok:false`): 400, 402, 404, 408, 409, 412, 413, 415, 422, 429, 499; **thrown to framework error handling**: 401, 403, 405, 428, 5xx, others. Message = `HTTPException` message for 4xx, plain-text 4xx body, else `Action failed with <status> <text>`.

- **Optimistic UI**: Not supported (not found; grepped "optimistic" in docs and packages). React users can use React 19 `useOptimistic` themselves (from memory, unverified that it composes with `useForm`).

- **Data refresh after mutation**: Supported, automatic for the current page: void return → server re-runs the loader in the same response and the client applies new props (state preserved by default for non-GET). Other pages: prefetch cache fully flushed; no cross-page revalidation. Deferred props are not re-resolved until next navigation. ISR entries are not purged automatically — call `revalidate({ paths })` from `void/isr` in the action. Source: docs/guide/pages-routing/actions-and-forms.md, docs/guide/pages-routing/loaders.md#deferred-props-after-mutations.

- **Redirects after mutation**: Supported via `c.redirect(url | routeUrl(...), status?)`. Internal redirect targets merge the request's query (destination wins). Named-action key handling: redirects that become GET (303, or 301/302 after POST) drop `?actionName`; method-preserving redirects (307/308, or 301/302 after PUT/PATCH/DELETE) keep it. Cross-origin redirect → full page load. Source: docs/reference/api/rewrites.md#c-rewrite-destination, packages/void/src/runtime/routing.ts `redirectLocation`.

- **File uploads**: Supported (manual parsing). Put `File`/`Blob`/`FileList` in form data → client sends `multipart/form-data` (otherwise JSON). Server reads `await c.req.parseBody()`; `withValidator` body schemas do not apply to multipart (JSON-only parser). No size limits/streaming upload helpers documented. Source: docs/guide/pages-routing/actions-and-forms.md#file-uploads.

- **Multiple actions per page**: Supported via `export const actions = { a, b, default }`, each with its own validator and typed `useForm('/x?a', …)`. After a named POST renders or default-redirects, the action key is removed from the URL (`/users/42?update&tab=profile` → `/users/42?tab=profile`).

- **CSRF protection**: Partial. Page actions reject cross-origin browser submissions with 403 `Cross-origin page actions are not allowed.` — checks `Origin`, then `Sec-Fetch-Site`, then `Referer`; requests with none of them (non-browser clients) are allowed (packages/void/src/pages/protocol.ts `isSameOriginAction`). No CSRF tokens. API routes (`routes/`) get no automatic check — docs suggest Hono `csrf()`; Void-managed auth ignores the session on cross-origin non-GET unless in `trustedOrigins` (docs/guide/auth.md). Source: docs/guide/pages-routing/actions-and-forms.md#authentication-and-origin-checks.

- **Notable extras**: `Link method="post" data={…}` buttons for one-click mutations; `UsageLimit` 429 integration with `Form`; `ValidationError` usable from per-route middleware too.

## 5. Caching & revalidation

- **Page/HTML caching (ISR store)**: Supported on Cloudflare only (and Void platform); ignored on Node/Bun/Deno (warning). Caches complete `200` public responses of Pages, custom SSR, and `routes/` GET handlers whose URL matches a page pattern or `routing.revalidate` pattern; **never** caches `/api/*`. HTML and Pages JSON (`X-VoidPages`) are separate variants. Not stored/served when: response has `Cache-Control: private|no-store|no-cache`, any `Set-Cookie`, `Vary` on anything other than `X-VoidPages` (incl. `Vary: *`); request carries `Cookie`, `Authorization` or `Cf-Access-Jwt-Assertion` (bypass entirely — note any cookie, e.g. analytics, bypasses). If a cached public page later returns a private header, the entry is removed. Deploys clear the cache. Undocumented: cached responses carry `x-isr-cache: HIT|STALE` and `Cache-Control: public, s-maxage=<remaining>, max-age=0, must-revalidate` (source: packages/isr/src/core.ts). Source: docs/guide/edge/revalidation.md.
  - Cache key: destination pathname (+ original pathname for dispatch rewrites); query string **excluded** by default; `routing.revalidateQueryAllowlist: { '/search': ['q'], '*': [] }` keeps listed params; requests with non-allowlisted params get the cached page, or render live without storing if nothing is cached. Middleware `c.rewrite()` runs after ISR lookup (no extra variant).

- **Time-based revalidation (ISR)**: Supported (stale-while-revalidate). TTL sources, most specific wins: (1) response header `x-revalidate: <s>` (`0` = don't cache), (2) page export `export const revalidate = 120`, (3) `routing.revalidate` path pattern (first match wins; `*` matches across `/`), (4) global number or `'*'`. `0` = plain SSR; `31536000` = until next deploy (max). First request renders and caches; stale entry served while background re-render; uncached requests wait. Kill switch `routing.isr: false` (disables ISR + edge prerender, not `output: "static"`). On direct Cloudflare, `revalidate()` purges shared storage and only the **current data center's** edge cache; other colos serve until their TTL expires (docs/integrations/cloudflare.md#isr-self-host).

- **On-demand revalidation (by path, by tag)**: Partial. `revalidate({ paths: [...] })` or `revalidate({ all: true })` from `void/isr` (no-op in dev). Must purge the **destination** path for rewritten entries. **By tag: Not supported** (signature `{ paths?, all? }` only; grepped "tag" in packages/isr/src). CLI: `void project purge-cache` (Void platform). Source: docs/reference/api/resources.md#isr.

- **Data-level / function-level caching**: Not supported (not found). Only Hono's `cache()` middleware per route (Cloudflare Cache API; one response per URL, skips `Authorization` but not cookies — docs warn) and user-managed KV. Source: docs/integrations/hono.md.

- **Client navigation cache**: Partial — prefetch cache only (see §3); visited pages not cached by default; back/forward re-fetch.

- **HTTP cache-header helpers**: Partial. Config `routing.headers` (pattern → `"Name: value"` list; last match wins; user `Cache-Control` overrides defaults; not applied to ISR cache hits; hashed assets' `Cache-Control`/`Content-*` can't be overridden). Defaults: hashed `assets/*` `public, max-age=31536000, immutable`; other static files `public, s-maxage=31536000, max-age=0, must-revalidate`; ETag/304 for static assets. `x-revalidate` response header for ISR TTL. No typed cache-control helper API. Source: docs/guide/edge/headers.md, docs/guide/edge/static-assets.md.

- **Preview / draft mode bypass**: Not supported (not found; grepped "draft mode", "preview mode", "bypass token"). Only implicit bypass: any request with a cookie/authorization header skips ISR.

- **Notable extras**: deploy-time prerender seeding of the ISR cache; ISR also applies to framework apps (out of scope); prerendered pages default to 1-year TTL.

## 6. Server & API

- **API routes / endpoints per HTTP method**: Supported. `routes/**` named exports `GET POST PUT PATCH DELETE OPTIONS`; `GET` also answers `HEAD`. Return conversion (packages/void/src/runtime/response.ts): object/array/number/boolean → JSON; `string` → `text/html; charset=utf-8`; `null/undefined` → 204; `Response` passthrough. Full Hono API (`c.json`, `c.text`, `c.html`, `c.header`, `c.status`, `hono/streaming`). JSX handlers in `.tsx/.jsx` (React/Solid render to string themselves; Vue/Svelte/API-only apps configure Hono JSX). `defineHandler.withValidator({ body, query, params })` with any Standard Schema lib (Zod 3.25+/4, Valibot ≥1, ArkType ≥2; Drizzle-derived via `void/drizzle-zod|valibot|arktype`); failure → 400 `{ error: 'Validation failed', issues: [{ slot, issues: [{ message, path }] }] }`; body must be JSON (`Invalid JSON body` 400). Generators: `void gen route <path> --methods get,post,...`, `void gen model`. Source: docs/guide/server-routing.md, docs/reference/api/handlers.md.

- **Middleware**: Supported.
  - Global: `middleware/*.ts` default export `defineMiddleware(fn)` (or any Hono middleware); order by numeric prefix `01.`, `02.` (files without a number run last; `_`-prefixed ignored; nested dirs are still global). Runs on every request reaching the Worker (static assets usually bypass the Worker on Cloudflare; apps with middleware run app code before fallback HTML).
  - Per-route: `defineHandler(mw1, …, mw5, handler)` (≤5, typed), also for page `loader`/`action` (middleware sees the rendered page response).
  - Full app order (packages/void/src/router/compile.ts): context + request-context middleware → config redirects/rewrites (non-managed targets) → header rules → named-action marker → Void auth middleware → user global middleware → WebSocket upgrades → `/api/auth/*` → `routes/` → pages → not-found fallback.
  - Capabilities: short-circuit by returning a Response, post-process after `await next()`, `c.set()` typed variables, `c.set('shared', …)` (page-wide data), `c.set('headDefaults', HeadDescriptor)`, `c.rewrite(dest)` (internal re-dispatch; middleware re-runs on each hop — guard with `c.isRewritten()`; asset-extension destinations throw `VoidAssetRewriteError`; must start with single `/`), `c.redirect`. Built-in `basicAuth({ username, password, realm='Restricted', message='Authentication required' })` (values or functions; empty password throws; `/__void/*` exempt; 401 with `Cache-Control: no-store`). Any `hono/*` or `@hono/*` middleware (cors, cache, bearer-auth, csrf…). No per-directory scoped middleware convention.
  Source: docs/guide/server-routing.md#middleware, docs/guide/edge/rewrites.md, docs/reference/api/handlers.md.

- **Request context**: Supported — Hono `Context` (see §3). Typed `CloudContextVariables` augmentation; typed `c.env` bindings generated from `env.ts`; `env` proxy from `void/env` (Cloudflare only). Source: docs/guide/type-safety.md#context-variables.

- **Streaming responses and SSE**: Supported. Raw streams via Hono `stream()`/`Response(ReadableStream)`. `void/sse` `eventStream(start, { signal, keepAlive })` → `text/event-stream; charset=utf-8`, `Cache-Control: no-cache, no-transform`, `X-Accel-Buffering: no`; `stream.send({ id, event, retry, data })` (string or JSON), `stream.comment()`, `stream.closed`, keepalive every 15 s by default (`keepAlive: false | { intervalMs, comment }`); writing after close throws `SseStreamClosedError`; `getLastEventId(request)`; `formatSse/formatSseText`. Browser: `connectEventStream<EventMap>(url, { withCredentials })` from `void/sse/client` with typed `.on(event, cb)`. `void/live` topic fan-out (Durable Objects) is pub/sub (out of scope). Source: docs/guide/sse.md.

- **Running work after the response (waitUntil/after)**: Not documented. Hono's `c.executionCtx.waitUntil()` is reachable on the Cloudflare target (executionCtx is passed into `app.fetch`), but on Node/Bun/Deno targets the context is omitted (source: packages/void/src/router/compile.ts `nodeTarget` "omits executionCtx"; packages/void/src/runtime/routing.ts). Grepped `waitUntil`, `executionCtx`, `after(` in docs: no hits. Queues/cron exist but are out of scope.

- **Server-only code boundaries**: Partial.
  - `.server.ts` companions are server-only by convention (components should import only `type`s from them); no build error found for a value import from a `.server.ts` into a component (not found in packages/void/src).
  - Resource modules are stubbed in browser builds: `void/db`, `void/kv`, `void/ai`, `void/queues`, `void/storage`, `void/isr` become inert `{}`/no-op stubs (silent); `void/sandbox`, `void/email`, `void/live`, `void/durable` stubs throw "is server-only" at call time (packages/void/src/plugin-client-stubs.ts).
  - `void/env`: reading a non-`VITE_` key from client code fails the client build (packages/void/src/plugin-env-client-guard.ts); `VITE_*` keys are public and folded at build time.
  - No generic `server-only` package/`"use server"` marker equivalent.
  Source: docs/guide/env-vars.md.

- **Notable extras**: `c.originalUrl()`/`c.isRewritten()`; dev-only `X-Void-Routing` debug header showing the matched rule; `.dev`-only endpoints; typed `RewriteDestination`; `void/log` structured JSON logger (`logger.info/warn/error(msg, fields)`, `logger.child(fields)`); routes under `/api` never get HTML error pages and never ISR-cached.

## 7. Loading & error states

- **Route-level loading UI**: Not supported as a convention (no `loading.tsx` etc.; grepped `loading.(tsx|vue)`). Available primitives: `useNavigation()` (`idle|loading|submitting`, `location`, `method`), React Suspense fallbacks for `defer()` props, `{loading}` state for deferred props in other adapters, `form.pending`. React navigations run in transitions (old UI stays until commit). Source: docs/reference/api/pages.md.

- **Error boundaries (per route/segment, root/global)**: Not supported as a framework feature (grepped `ErrorBoundary`, `componentDidCatch`, `onErrorCaptured`, `svelte:boundary`, `+error`, `_error`, `error.(tsx|vue)` in adapters and docs). Users wrap with their UI library's own boundaries (docs explicitly suggest a React error boundary for rejected deferred props). Server-side failures become a whole-document error page:
  - Hono `app.onError`: if the error has `getResponse()` (Hono `HTTPException`) → that response (plain text/whatever it builds, **not** the HTML error page); otherwise `console.error` + 500.
  - 500 response: HTML only for document-like requests (GET/HEAD, not `/api`, no file extension, `Sec-Fetch-Dest` document/empty, `Accept` html or `*/*`), else plain text `Internal Server Error`. HTML = `public/500.html` if present (served via assets binding) else built-in page; production never includes exception details. **Custom `public/500.html` is undocumented** (source: packages/void/src/runtime/routing-errors.ts `serveCustomPage`).
  - Client navigation hitting an error: GET responses without `X-VoidPages` (error pages) cause a full document load to that URL (packages/void/src/pages/navigation-engine.ts); action errors follow the status categories in §4. A client render failure restores the previously committed page.

- **404 / not-found handling**: Partial.
  - Unmatched Pages requests: not-found fallback tries static assets → `routing.fallbacks` → trailing-slash 301 → `public/404.html` (custom) or built-in 404 page, with `X-Void-No-Match: 1` header; `/api/*` and non-GET get plain `Not Found` text (packages/void/src/runtime/routing-pages.ts). Custom 404 for server apps via `public/404.html` is documented only for static builds (docs/guide/ssg.md#404-pages); for Worker apps it's source-only.
  - No `not-found` page component convention; a `/404` page can be prerendered for static builds.
  - From a loader: `return c.notFound()` (Hono → Void's not-found fallback → 404 page) — documented only in a storage example (docs/guide/storage.md); `throw new HTTPException(404, { message })` → plain-text 404.
  - `routing.notFound: 'single-page-application' | '404-page' | 'none'` controls the asset layer (inferred if omitted).

- **Helpers like redirect(), notFound(), error()**: Partial — Hono context methods only: `c.redirect(url, status?)` (Void wraps it to accept `RouteDestination`/`routeUrl()` and to merge query/handle action keys), `c.notFound()`, `throw new HTTPException(status, { message })` (from `hono/http-exception`), `throw new ValidationError({...})` (actions). No `redirect()`/`notFound()` throwables usable from components. Source: docs/integrations/hono.md#utilities, docs/reference/api/rewrites.md.

- **Expected vs unexpected errors**: Supported in mutations (call-site vs boundary status lists, §4) and deferred props (HTTPException messages pass, others masked in production). Loaders: any thrown non-HTTPException → 500 page. Source: docs/guide/pages-routing/actions-and-forms.md#validation-errors, docs/guide/pages-routing/loaders.md.

- **Error reporting hooks**: Not supported (not found). No `onError`/`handleError`/instrumentation hook exposed; errors are `console.error`ed and visible via `void project logs` (Cloudflare live tail; hosted platform keeps history, `--level error` includes uncaught exceptions and 5xx). Hono's `c.error` after `await next()` in middleware may be usable (from memory of Hono, unverified for Void). Source: docs/reference/cli/project.md#void-project-logs.

- **Notable extras**: platform-level `public/usage-limit.html` / `public/execution-limit.html` custom pages for quota 429s (standalone HTML, scripts disabled) (docs/guide/deployment.md); dev error overlay (§12).

## 8. Type safety

- **Typed links and params**: Supported (§1): `routeUrl()`, `RouteDestination`, `Href`, `RouteUrl`, `RouteUrlInput`, `RoutePath`, `RoutePathMap`, `RouteOptions<P>`; strict string checking with `routing.typedRoutes`. `useParams` is not auto-typed per route.

- **Typed loader/server data → components**: Supported, semi-manual: `export type Props = InferProps<typeof loader>` in the `.server.ts`, then `import type { Props }` in the component (or `defineHandler<Props>(…)`). Type reflects JSON serialization only for typed fetch (`Serialize<T>`); page props types are the loader's raw return type (e.g. a `Date` is typed as `Date` but arrives as a string — inferred risk, docs show `Serialize` only for the client). `Deferred<T>` import from the adapter matches its runtime shape. `useShared()` type from `CloudContextVariables['shared']`. Source: docs/guide/pages-routing/loaders.md, docs/guide/type-safety.md.

- **Typed server calls**: Supported. `fetch` from `void/client` (built on ofetch): path must be a `RouteMap` key, method must be exported, `body/query/params` typed from validators, return type inferred. Options: `method` (default GET), `body` (JSON-serialized, sets `Content-Type`), `query`, `params`, `headers`, `signal`, `baseURL`, `retry` (ofetch default 1 for GET; retries 408/429/5xx), `timeout`. Non-2xx throws `FetchError { status, data, response }`; 204 → `undefined`. `useForm`/`action()` URLs, data, errors, params typed via generated `PageActionMap`. Source: docs/guide/typed-fetch.md, docs/reference/api/client.md.

- **Generated types**: Supported (codegen). `.void/` holds `routes.d.ts` (augments `void/routes`: `RouteMap`, `WebSocketRouteMap`, `PageActionMap`, `RoutePathMap`, `RewriteDestination`, action URL parsing types), `db.d.ts`, `env.d.ts`, generated `tsconfig.json` (projects `extends: "./.void/tsconfig.json"`). Regenerated by `vite dev`/`vite build`; `void prepare` for CI; `void env types` for env only; `void init --tsconfig` to wire an existing tsconfig. Source: docs/guide/type-safety.md#setup, packages/void/src/codegen/route-types.ts.

- **Typed search params**: Partial — `withValidator({ query })` types the server input and the typed `fetch` `query` option; client-side page search params (`useRouter().query`) are untyped `URLSearchParams`; `routeUrl` query accepts any keys.

- **Notable extras**: Drizzle schema → validator → handler → client type pipeline; typed `CloudContextVariables`; typed `env.ts` schema; typed `c.rewrite` destinations.

## 9. Metadata & SEO

- **Head/meta management per route**: Supported (server-defined). Page companion export `head = defineHead<Props>((c, props) => HeadDescriptor | undefined)` — runs server-side only, after the loader, **synchronously** (`headFn(c, props)` is not awaited; return type is not a Promise; packages/void/src/pages/protocol.ts). Layouts cannot define head. Three layers with precedence page > middleware (`c.set('headDefaults', …)`) > config (`head` in `void.config.ts`):

  | field | merge rule |
  |---|---|
  | `title` | page wins; config `titleTemplate` (`%s`) wraps it |
  | `meta` (`name`/`property`/`content`/`charset` only) | dedupe by `charset` / `property` / `name`; later layer replaces |
  | `link` (`rel`, `href`, any attrs) | concatenated config → middleware → page |
  | `script` (`src`, `innerHTML`, any attrs) | concatenated |
  | `htmlAttrs`, `bodyAttrs` | shallow merge, page wins |

  Client navigation: `title`, `meta`, `link` updated; `script`, `htmlAttrs`, `bodyAttrs` SSR-only. Markdown pages: frontmatter `title`/`description` → `<title>` + `meta description` without a server file. No component-level head API (no `useHead`/`<Head>`) — except Svelte, whose `<svelte:head>` output is injected on SSR (undocumented; packages/svelte/src/plugin-pages.ts). Source: docs/guide/pages-routing/head.md, docs/reference/config.md#head.

- **Metadata derived from loaded data**: Supported — `head(c, props)` receives resolved loader props (deferred props are still placeholders at that point).

- **Sitemap / robots / manifest generation**: Not supported (not found; grepped "sitemap", "robots.txt", "manifest.webmanifest"). Use `public/` files or a route handler. `@void/md/pages` gives a list of Markdown pages usable for building a sitemap manually.

- **Open Graph image generation**: Not supported (not found; grepped "og:image", "opengraph"). OG meta tags only via `head()`.

- **Canonical, etc.**: Partial — manual `link: [{ rel: 'canonical', href }]`; `c.originalUrl()` recommended for canonical URLs under rewrites (docs/guide/edge/rewrites.md#original-url-access). No JSON-LD helper, no `alternates`/hreflang helper.

- **Notable extras**: config `head` accepts `title`, `titleTemplate`, `meta`, `link`, `script`, `htmlAttrs`, `bodyAttrs` as site defaults; middleware `headDefaults` for e.g. pre-paint theme script.

## 10. Assets & styling

- **Image optimization**: Not supported (not found; grepped "image optim", "srcset", "sharp", "<Image" in docs and packages — `sharp` appears only as a pnpm build-script approval in docs/guide/quickstart.md). No image component, resizing, formats, or remote-image proxy. Markdown images get `loading="lazy"` and path normalization (packages/md/src/plugins/image.ts).

- **Font optimization**: Not supported (not found; grepped "font optim", "next/font", "fontsource", "preconnect").

- **Third-party script loading**: Partial — `head.script` entries (`src`, `innerHTML`, arbitrary attrs like `async`/`defer`) at config/middleware/page level; SSR-only (not re-applied on client nav). No loading-strategy component (not found; grepped "Partytown", "third-party script").

- **CSS support**: Not documented in Void docs (grepped "tailwind", "css modules", "scss", "postcss" in docs: no hits) — relies on Vite defaults (CSS imports, CSS Modules, Sass/Less/Stylus with preprocessors installed, PostCSS, Tailwind via its Vite plugin; from Vite knowledge, unverified in Void docs). Void-specific source behavior: per-route CSS collection (page + its layout chain manifest keys) so a page links only its CSS; dev SSR inlines CSS (`.css .scss .sass .less .styl .stylus .pcss .postcss`) as nonce'd `<style>` tags and patches CSP `style-src` to avoid FOUC (packages/void/src/pages/dev-css-assets.ts, packages/void/src/pages/protocol.ts); island pages link styles of hydrated and static components. Scoped styles: native to Vue SFC/Svelte. CSS-in-JS: no integration found. `@void/md` ships `theme.css` / `theme-content.css` (`.void-md` scope, CSS variables `--vmd-*`, dark mode via `prefers-color-scheme` and `[data-theme]`).

- **MDX / Markdown as pages**: Partial — Markdown yes, MDX no (not found; `@void/md` is markdown-it/`markdown-exit` based). `@void/md` + `voidMarkdown({ shiki: { themes: { light, dark } } })` (only option). `.md` in `pages/` = island page (zero JS except islands, a leading `<script>` client block, and code-copy buttons); frontmatter (`title`, `description`, `layout`, anything else via `useFrontmatter()`); components only as islands imported in the `<script>` block (`with { island: 'visible' }`) and used as uppercase tags; companion `.server.ts` allowed; auto-prerender when static. Features: GFM, Shiki dual-theme highlighting (languages on demand), `{1,3-5}` line highlights, `// [!code ++|--|focus|error|warning]`, `:line-numbers[=N]`, `:::tip|warning|danger|info|details` containers, GitHub alerts, emoji shortcodes, footnotes, `{.class #id}` attrs, heading anchors, `[[toc]]`, `.md` link rewriting. `@void/md/pages` virtual module → `[{ path, title, frontmatter, headings[] }]` sorted by path (HMR-updated). No custom markdown-it/remark plugin hook in options. Deprecated: `FrontmatterContext`, `setFrontmatter()` (use `useFrontmatter()`). Source: docs/guide/pages-routing/markdown.md, docs/reference/api/pages.md#markdown-package.

- **Notable extras**: static asset caching policy (hashed `build.assetsDir` immutable, honors custom `assetsDir`; `""` disables), ETag/304, `public/` served as-is.

## 11. Build output & deployment

- **Output modes**: Supported: `output: "server"` (default; Worker + assets), `output: "static"` (prerendered HTML in `dist/client/`, self-contained, deployable anywhere; hybrid Worker deployed automatically for non-prerenderable pages, API routes, middleware, cron, queues), `inference.appType: "spa"` / `"static"` for pre-built sites (`void deploy --dir <path> [--spa]`). Build layout: `dist/client/` (assets, `.vite/manifest.json`, prerendered HTML, `_void/pages/*.json`) + `dist/ssr/` (Worker or Node server). Source: docs/guide/ssg.md, docs/guide/app-types.md.

- **Supported runtimes and per-route runtime choice**: `target: "cloudflare"` (default; full features) | `"node"` (`@hono/node-server`, install separately) | `"bun"` (`Bun.serve`) | `"deno"` (`Deno.serve`); listens on `PORT` or 3000. Per-route runtime choice: Not supported (single target per app). Non-Cloudflare differences (docs/integrations/nodejs-bun-deno.md):

  | feature | Cloudflare | Node/Bun/Deno |
  |---|---|---|
  | routes, middleware, Pages SSR (all 4 adapters), typed fetch, `routing.headers`, `routing.redirects`, SSG | yes | yes |
  | ISR / `routing.revalidate`, edge prerendering | yes | no (`revalidate` ignored with warning) |
  | `routing.alwaysUseHttps` | yes | no (requires Cloudflare target) |
  | `void/db`, `kv`, `storage`, `auth`, `ai`, `sandbox`, `env` imports | yes | compile-time error |
  | `void deploy` | yes | no — `vite build` + own hosting |
  | cron | Cron Triggers | handler compiled, no scheduler |
  | `*.ws.ts`, inbound email | yes | no |
  | `c.executionCtx` | yes | not passed |

  `routing.rewrites`/`fallbacks` are not listed under "What Works" for Node but the source compiles redirect/rewrite rules into Hono middleware for non-managed targets (packages/void/src/router/compile.ts `compileRoutingRulesMiddleware`) — likely work, undocumented.

- **Adapters / presets for hosts**: Partial. Official deploy paths: (1) `void deploy --platform cloudflare` (direct to user's Cloudflare account: provisions D1/KV/R2/Hyperdrive/queues, applies migrations, staged deploy with readiness check and automatic rollback, `deploy.cloudflare.mode: 'staged'|'atomic'`, `void project rollback`, D1 restore points), (2) `void deploy --platform void` (self-hosted "Void platform", same app APIs), (3) Node/Bun/Deno standalone server for any host, (4) static output for any static host. No Vercel/Netlify/AWS/etc. presets; no public adapter API (not found). Named Cloudflare environments unsupported. `void init --github` generates a GitHub Actions workflow. Source: docs/guide/deployment.md, docs/integrations/cloudflare.md.

- **Config-level headers, redirects, rewrites, trailing slash, base path**:
  - `routing.headers` – `{ '/pattern/*': ['Name: value', …] }`; all matches merged, last wins; applies to assets, SSR, API; on a Void platform `Set-Cookie` is ignored and `Clear-Site-Data` restricted; framework/`public/_headers` files read first, config overrides.
  - `routing.redirects` – `{ '/old': '/new', '/blog/*': { to: '/posts/:splat', status: 301 } }`; statuses 301/302(default)/303/307/308; `*` matches across `/`, `:splat`; destination query merged (destination wins; `?` alone resets); first match wins; evaluated before Worker/ISR/SSR; host-prefixed sources `https://www.example.com/*` (literal https host, no port/wildcard, domain must be added with `void domain add`). `public/_redirects` file supported (config wins).
  - `routing.rewrites` (before assets and routes) and `routing.fallbacks` (only when nothing matched); `_redirects` `200` = fallback, `200!` = rewrite; destinations must be internal paths; middleware `c.rewrite()` for dynamic.
  - `routing.alwaysUseHttps` – 308 preserving method/path/query; Cloudflare target only; localhost exempt.
  - `routing.notFound`, `routing.isr`, `routing.revalidate`, `routing.revalidateQueryAllowlist`, `routing.prerender`, `routing.typedRoutes` (covered above).
  - Trailing slash: no `trailingSlash` config key (not in `RoutingConfig`). Behavior: Pages fallback 301s `/x/` → `/x` (undocumented, source); static asset trailing-slash handling only via passthrough `cloudflare.assets.html_handling` (`auto-trailing-slash` | `force-trailing-slash` | `drop-trailing-slash`, source: packages/edge/src/static.ts).
  - Base path: not supported (§1).
  - Dev visibility: `X-Void-Routing` header.
  Source: docs/guide/edge/headers.md, docs/guide/edge/redirects.md, docs/guide/edge/rewrites.md, docs/reference/config.md#routing.

- **Standalone / self-contained output**: Supported for Node/Bun/Deno: `dist/ssr/index.js` (starts server) + `dist/ssr/app.js` (exports Hono app for embedding/testing; used by `vite preview`); packages depending on `void` are bundled; native-addon deps must be added to app `dependencies`. Deploy `dist/ssr` + `dist/client` together. Static output self-contained. Source: docs/integrations/nodejs-bun-deno.md#build-output.

- **Skew protection**: Not supported (not found; grepped "skew", "version mismatch", "chunk load", "preloadError"). Mitigations only: hashed assets are immutable and "can be reused across deploys" (docs/guide/edge/static-assets.md); client router falls back to full document loads when a response isn't a Void page payload.

- **Notable extras**: staged deploys with readiness checks + automatic rollback on Cloudflare; `void project rollback`; resource inference/provisioning from imports; `worker.limits.cpu_ms`; Workers-Free-compatible-by-default policy; asset-worker bypass (prerendered pages served without invoking the Worker when no middleware/rules/base).

## 12. Dev tooling & observability

- **Dev server and HMR**: Supported via Vite (`vite dev` / `vp dev`, `npm run dev`); app runs in workerd via the Cloudflare Vite plugin (Node target: Node dev server). Pages directory rescanned on add/unlink (and on `.md` change); server modules are not cached in dev (`createModuleLoader` cache off); React Fast Refresh preamble injected into SSR HTML. Local D1/KV/R2 persisted to `.void/` (`persistTo` option); `remote: true` / `VOID_REMOTE=1` uses deployed D1/KV/R2. Source: docs/integrations/nodejs-bun-deno.md, docs/reference/api/plugin.md, packages/void/src/pages/plugin.ts.

- **Error overlay**: Partial / undocumented. Dev-only server error overlay injected into 500 HTML pages: error chain, parsed stack frames with editor links, minimize/restore toggle (source: packages/void/src/runtime/routing-errors.ts `renderDevErrorOverlay`); not mentioned in docs. Client/compile errors: Vite's standard overlay (Vite behavior).

- **Devtools**: Not supported (not found; grepped "devtools"). Dev-only `X-Void-Routing` header is the only routing inspector.

- **Type generation commands**: Supported — `void prepare` (all `.void/` types without dev/build), `void env types`, `void init --tsconfig`, automatic during `vite dev`/`vite build`. Source: docs/reference/cli/setup.md.

- **CLI scaffolding / generators**: Supported — `void init` / `npm create void@latest` (flags `--toolchain vite-plus|vite`, `--framework react|vue|svelte|solid`, `--starter sqlite|postgresql|mysql|static`, `--deploy cloudflare|void|none`, `--tsconfig`, `--github`, `--git/--no-git`); `void gen model <name> [col:type[?]…]` (Drizzle table + list/create/get-by-id routes with validator auto-detected: valibot/zod/arktype), `void gen route <path> [--methods]`, `void gen middleware <name>` (auto-numbered), `void gen ssr [--react|--vue|--svelte|--solid]`, `void gen migration`, `void gen cron`, `void gen queue`. No page/layout generator found. Source: docs/reference/cli/generate.md, docs/reference/cli/setup.md.

- **AI-agent support**: Partial. Bundled Markdown docs at `node_modules/void/docs/`; `void init` writes/updates a minimal `AGENTS.md` (asks first in existing projects; template packages/void/AGENTS_TEMPLATE.md) and links two skills (`void`, `migrate-vite-cloudflare-to-void`) into detected agent dirs (`.claude/skills/`, `.agents/skills/`). **MCP server: Not found. llms.txt: Not found** (grepped "llms", "MCP" in docs, docs/.vitepress/config.ts, packages/void/src). Source: docs/integrations/agents.md.

- **Instrumentation / OpenTelemetry hooks**: Not supported (not found; grepped "opentelemetry", "otel", "instrumentation"). Observability = `void/log` structured logger, `void project logs` (Cloudflare live tail; hosted platform 7-day history with `--level/--filter/--range/--deployment`), `void project requests` (hosted only; status/type/duration, no paths).

- **Server error reporting hooks**: Not supported (not found) — see §7.

- **Web vitals reporting**: Not supported (not found; grepped "web-vitals", "web vitals").

- **Notable extras**: `void env check [--remote]` env validation with value redaction (`VOID_ENV_UNMASK=1`); `void info` for resource names; dev email inbox and dev trigger endpoints (out of scope); `basicAuth` for preview gating.

---

## Per-UI-library differences (summary)

| aspect | React | Vue | Svelte | Solid |
|---|---|---|---|---|
| version | 19 required | 3.5 | 5 (runes) | 1.9 |
| SSR streaming | yes (`renderToReadableStream`, Suspense) | no (`renderToString`) | no (`render`) | no (`renderToStringAsync`) |
| `Deferred<T>` shape | `Promise<T>` + `use()` | `{loading,value,error}` | same | same |
| `useForm` submit | native form actions (`useActionState`), `onSuccess/onError` options, `useFormStatus` | `post(opts?)` Promise; v-model on `data` | Promise; `bind:value` | Promise; `setData` (store) |
| `setData` | yes | no | no | yes |
| `useIslandForm` `submit(url, method)` | no | yes | yes | no |
| `resolveOn` visit option | yes | — | — | — |
| page remount on GET nav | reconciliation | remount unless `preserveState` | state swap | re-create on GET/param change |
| component head | none (React 19 hoisting not wired; unverified) | none | `<svelte:head>` (undocumented) | none |
| Link/router/islands/view transitions/prefetch | same API in all four | | | |

## Out-of-scope features seen (one line each, optional)
- Auth: Better Auth integration (`void/auth`, `defineAuth`, 35 OAuth providers, `requireAuth`).
- Databases: Drizzle with D1 / PostgreSQL / MySQL (Hyperdrive), migrations, seeding, Drizzle Studio.
- KV (`void/kv`), R2 storage (`void/storage`), Durable State (`void/durable`).
- Queues (`queues/`, `defineQueue`), cron (`crons/`, `defineScheduled`).
- Email send/receive (`void/email`, `email/` handlers).
- Realtime: WebSockets (`*.ws.ts`, `void/ws`), Live event streams (`void/live`).
- AI (`void/ai`, Workers AI + AI Gateway), Sandboxes (`void/sandbox`).
- Self-hosted Void platform (teams, Zero Trust, managed GitHub builds).
