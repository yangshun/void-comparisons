# SvelteKit — feature inventory
Version documented: **3.x (SvelteKit 3 major; exact minor not stated)**. Determined from `60-appendix/35-migrating-to-sveltekit-3.md` (full v2→v3 breaking-change list), legacy notes such as "`base`, `assets`, and `resolveRoute` were removed in 3.0" (`98-reference/20-$app-paths.md`) and "`$env/*` … deprecated in SvelteKit 3 … will be removed in SvelteKit 4" (`99-legacy-reference/*`), and v3 minimums (Node 22.17, TypeScript 6, Svelte 5.57.1, Vite 8.0.12 with Rolldown v1, vite-plugin-svelte 7). · Docs commit: fe4deb1, 2026-11-04 (sparse clone of sveltejs/kit `documentation/docs`).
Context: Svelte 5 (runes; Svelte's *experimental* async `await` mode needed for remote functions) · Vite 8 / Rolldown · SvelteKit's own web-standards `Request → Response` server (`server.respond()`; no Nitro/H3) · default runtime Node (`adapter-node`; `vite preview` also runs in Node). First-party adapters for Node, Bun, Cloudflare (Workers and Pages), Netlify, Vercel and static. `adapter-auto` is the scaffold default.

**Conventions used here**
- Source paths are relative to `documentation/docs/` in the repo root. `+assets/messages.json [key]` refers to the docs' error/warning catalog, which holds 255 runtime and build messages with explanations. It is a rich source of edge-case behaviour.
- The generated API reference pages (`98-reference/10-@sveltejs-kit.md`, `$app-navigation`, `@sveltejs-kit-vite` config, etc.) are stubs (`> MODULE: …`) that are built from type definitions. Those type definitions are not in this checkout. Option lists below are therefore assembled from the narrative docs and the message catalog. Anything filled from memory is marked "(from memory, unverified)".
- Status markers: **[stable]**, **[EXPERIMENTAL]**, **[deprecated]**, **[removed in v3]**, **[new in v3]**.

**Notable v3 changes (summary)**
- Config moves out of `svelte.config.js` (no longer read; error `config_file_unsupported`) and into `sveltekit({...})` in `vite.config.js`. Former `kit.*` keys are now top-level.
- `$lib` is replaced by a user-declared `#lib` subpath import in `package.json`.
- `$app/stores` and `$service-worker` are removed. `$app/environment` is renamed to `$app/env`. `$env/*` is deprecated in favour of explicit env vars (`src/env.ts` + `$app/env/private|public`).
- Shallow routing moves from `pushState`/`replaceState` to `goto(url, { shallow: true })`. `invalidateAll` becomes `refreshAll`. `goto` options were renamed (`replace`, `reset`, `refreshAll`).
- `handleError` receives *all* errors with a `kind` discriminant. `App.Error.status` always exists. `error(status, message, props)` has a new signature.
- Param matchers are consolidated into `src/params.ts` via `defineParams` (function or Standard Schema, can transform and type the value).
- Server-only marking widened to any `server` filename segment or directory.
- CSRF is always on (`csrf.trustedOrigins`). New `paths.origin`. External `redirect` needs opt-in.
- Tracing and instrumentation are no longer experimental (`tracing.server`, `src/instrumentation.server.js` auto-loaded).
- `adapter-vercel` drops the edge runtime. New `adapter-bun`.
- Remote functions are **still experimental**.

---

## 1. Routing

- **Route definition / file conventions**: Supported (file-based only) [stable]. Routes are directories under `src/routes` (configurable via `files.routes`; error `routes_not_found` if empty). Route files carry a `+` prefix:

  | File | Runs on | Purpose / allowed exports |
  |---|---|---|
  | `+page.svelte` | server (SSR) + client | Page component. Props: `data`, `form` (if actions), `params` (typed; since 2.24). Page options exported here are ignored (`page_option_in_component`). |
  | `+page.js` (universal) | server during SSR + client | `load` (`PageLoad`), page options `prerender`, `ssr`, `csr`, `trailingSlash`, `config`, `entries`. |
  | `+page.server.js` | server only | `load` (`PageServerLoad`), `actions`, page options (same set). |
  | `+layout.svelte` | server + client | Must `{@render children()}` (warning `layout_children_missing`). Props `data`, `children`. |
  | `+layout.js` / `+layout.server.js` | as above | `load` (`LayoutLoad`/`LayoutServerLoad`), page options act as defaults for children. |
  | `+error.svelte` | server + client | Error boundary for its subtree. |
  | `+server.js` | server only | HTTP verb handlers `GET POST PUT PATCH DELETE OPTIONS HEAD QUERY` + `fallback`. Page options `prerender`, `trailingSlash`, `config`, `entries`. |

  Rules:
  - Any other `+`-prefixed file is reserved (`route_file_reserved`).
  - Files containing `.test.`, `.spec.` or `.stories.` are ignored.
  - Non-`+` files in route dirs are ignored, so colocation is fine.
  - Unknown exports are rejected (`invalid_export`) unless prefixed `_`. Exports in the wrong file kind are also rejected (`invalid_export_location`).
  - At most one file of each kind per directory (`route_duplicate_files`, e.g. `+page.js` plus `+page.ts`).
  - Near-miss names trigger "did you mean" warnings (`route_file_prefix_missing`, `file_name_misspelled`).

  Other special files in `src/`: `app.html` (template), `error.html` (static fallback), `hooks.server.js`, `hooks.client.js`, `hooks.js`, `params.js`, `env.js`, `instrumentation.server.js`, `service-worker/index.js`. Config/code-based routing does not exist; the closest equivalents are `reroute` (URL→route remap) and `handle` (can return a `Response` without touching the router). Source: `20-core-concepts/10-routing.md`, `10-getting-started/30-project-structure.md`, `+assets/messages.json`.
- **Nested layouts**: Supported [stable]. Directory hierarchy equals layout hierarchy. The root `+layout.svelte` defaults to `{@render children()}`. On client navigation, components common to both pages are **preserved, not recreated**. Only the `data` prop updates, so non-reactive code and `onMount` don't rerun. Use `$derived`, `afterNavigate`/`beforeNavigate`, or `{#key page.url.pathname}` to force a remount. `+layout` files have no effect on `+server.js`. Source: `20-core-concepts/10-routing.md`, `20-core-concepts/50-state-management.md`.
- **Dynamic segments**: Supported. `[param]`, including partial segments like `foo-[c]` and multiple params per segment if separated (`[foo]-[bar]` is OK; `[foo][bar]` gives `route_params_adjacent`). Param and matcher names may contain only alphanumerics, `_` and `-` (`route_param_invalid`). Special characters are escaped as `[x+nn]` (2 hex digits, lowercase) or `[u+nnnn]` (4–6 digits). Example: `src/routes/[x+2e]well-known/` for `.well-known`. `#` in dir names is disallowed (`route_hash_character`). Source: `30-advanced/10-advanced-routing.md`, `+assets/messages.json`.
- **Optional segments**: Supported. `[[lang]]/home` matches `/home` and `/en/home`. Restrictions:
  - An optional segment cannot follow a rest segment (`route_optional_after_rest`).
  - `[[...rest]]` is invalid (`route_optional_rest`) because rest is already optional.
  - An optional param creates two routes, which can conflict (`route_conflict`).

  Source: `30-advanced/10-advanced-routing.md`.
- **Catch-all / splat**: Supported. `[...rest]` matches **zero or more** segments: `a/[...rest]/z` matches `/a/z`. The value is the joined string (`'y/z'`). Recommended pattern for custom nested 404s: `[...path]/+page.js` that calls `error(404)`. Without it, unmatched URLs go to the root `+error.svelte` as `kind: 'framework'`. Source: `30-advanced/10-advanced-routing.md`.
- **Param matchers (validation and typing)**: Supported [changed in v3]. Declared in a single `src/params.ts` (path configurable via `files.params`):
  - Export `params = defineParams({...})` from `@sveltejs/kit/params`.
  - Each entry is either a function `(param: string) => value | undefined` or a **Standard Schema**.
  - The returned or parsed value becomes the param value and its type. It must be string, number, boolean or bigint (`param_matcher_result_invalid`). Example: `[id=number]` yields `typeof params.id === 'number'`.
  - Matchers must be **synchronous** (no async schemas; `param_matcher_async`).
  - Transformations should be symmetrical, so that `resolve('/blog/[id=number]', {id: 1})` round-trips.
  - Matchers run on server and in browser. A failed match falls through to the next route by sort order and finally to 404.
  - v2's `src/params/*.js` with `match()` returning a boolean is replaced.

  Source: `30-advanced/10-advanced-routing.md`, `60-appendix/35-migrating-to-sveltekit-3.md`.
- **Route priority / sorting**: Deterministic rules, applied in order:
  1. More specific (fewer params) wins.
  2. Matcher params beat plain params.
  3. `[[optional]]` and `[...rest]` are ignored unless they are the final segment, in which case they have the lowest priority.
  4. Ties are broken alphabetically.

  Overlapping pathnames (e.g. `/(a)/about` vs `/(b)/about`) are a build error (`route_conflict`). Source: `30-advanced/10-advanced-routing.md`.
- **Route groups / pathless layouts**: Supported. `(group)` directories don't affect the URL. A `+page` may sit directly in a group. Layout **reset/escape**:
  - `+page@[id].svelte`, `+page@item.svelte`, `+page@(app).svelte`, or `+page@.svelte` (root) picks which ancestor layout to inherit from.
  - `+layout@.svelte` resets a whole subtree.
  - Only `.svelte` files can carry `@` (`route_named_layout_in_module`); the sibling `+page.js` belongs to the component in the same dir.
  - A missing segment gives `route_layout_segment_missing`.

  Source: `30-advanced/10-advanced-routing.md`.
- **Parallel routes / intercepting routes**: Not supported (no slots or intercept conventions in docs). The documented substitute for modal routes is **shallow routing**: `preloadData(href)` to run the target route's loads, then `goto(href, { shallow: true, state: { selected: result.data } })`, then render the imported `[id]/+page.svelte` inside a modal with `data={page.state.selected}`. A reload lands on the real URL. Source: `30-advanced/67-shallow-routing.md`.
- **Typed links and typed route params**: Partial.
  - Navigation uses plain `<a href>`; there is no `<Link>` component and **hrefs are not type-checked**.
  - Typed helper: `resolve()` from `$app/paths`. Either `resolve('/blog/[slug]', { slug })` with a typed route ID and params, or `resolve('blog/hello')` with a typed `Path` (no leading slash in v3). Missing params, absolute URLs, and param values with leading or trailing `/` throw (`resolve_params_missing`, `resolve_url_input`, `route_param_slash`). Non-primitive values are rejected.
  - `$app/types` exports `RouteId`, `PageRouteId`, `EndpointRouteId`, `Path`, `ResolvedPathname` (type of `page.url.pathname`), `AssetPath`, `RouteParams<'/blog/[slug]'>` and `LayoutParams<...>` (includes optional child params). Since 2.26.
  - `params` in load, endpoints and pages are typed via generated `./$types`, including matcher output types.

  Source: `98-reference/22-$app-types.md`, `60-appendix/35-migrating-to-sveltekit-3.md`, `+assets/messages.json`.
- **Search-param handling**: Partial (untyped, unvalidated).
  - `url.searchParams` is a standard `URLSearchParams` in `load`, hooks and endpoints. Components use `page.url.searchParams`.
  - v3 makes `page.url` a `ReadonlyURL` with `ReadonlyURLSearchParams`; mutating it is a type error, so copy with `new URL(page.url.href)`.
  - Load dependency tracking is per key: `searchParams.get/getAll/has('x')` reruns only when `x` changes. Other `searchParams` access behaves like `url.search`.
  - Reading `url.search` or `searchParams` during prerendering throws (`url_search_unavailable_prerender`).
  - `url.hash` is unavailable in load (`url_hash_unavailable`).
  - Query keys starting `x-sveltekit-` are reserved (`reserved_query_parameter`).
  - No typed or validated search-param API (remote `query` args can be schema-validated, but that is separate from the URL).

  Source: `20-core-concepts/20-load.md`, `60-appendix/35-migrating-to-sveltekit-3.md`, `+assets/messages.json`.
- **Programmatic navigation**: Supported. `goto(url, opts)` from `$app/navigation`:

  | Option | Values / default | Behaviour |
  |---|---|---|
  | `replace` | bool, `false` | Replace the history entry instead of pushing. Renamed from `replaceState` (old name deprecated, warns). |
  | `reset` | bool; `true` for normal navs, `false` for shallow navs | `reset: false` preserves scroll position **and** focused element. Replaces the removed `noScroll` + `keepFocus` (`goto_options_removed`). |
  | `refreshAll` | bool, `false` | Rerun every load function **and all active remote queries** after navigating. Renamed from `invalidateAll` (deprecated). |
  | `state` | object (typed by `App.PageState`) | Sets `page.state` for the new history entry. |
  | `shallow` | bool, `false` | Create a history entry without navigating or rendering (see shallow routing). |
  | `persistState` | bool, `false` | Reapply `page.state` after a full reload. Ignored when a reload lands on a `page.shallow.url`. |

  Behaviour notes:
  - `goto` returns a Promise and **rejects** for external URLs and for same-origin URLs that resolve to no `+page` route (`navigation_route_missing`, v3). Use `window.location` for those.
  - Shallow `goto` cannot run before the router starts (`navigation_before_start`).
  - Direct `history.pushState/replaceState` usage triggers a warning (`history_api_conflict`).
  - More than 20 chained redirects aborts with `redirect_loop`.
  - Related functions: `invalidate(url | predicate)`, `refreshAll()`, `preloadData(href)`, `preloadCode(routeId)`, `beforeNavigate`, `onNavigate`, `afterNavigate`, `disableScrollHandling()`, `snapshot()`. `pushState` and `replaceState` are **deprecated** (still exported).
  - v3: navigation events carry `shallow`; `delta` is only set for `popstate`.
  - Navigation `type` values `enter | link | goto | popstate | form | leave` and `cancel()` in `beforeNavigate` (from memory, unverified; docs confirm `type === 'goto'` and `shallow`).
  - `onNavigate` receives `navigation.complete` (Promise) and may return a Promise to delay the DOM update (used for view transitions).
  - v3: clicking a link to the *current* URL performs `refreshAll()` instead of nothing.

  Source: `60-appendix/35-migrating-to-sveltekit-3.md`, `30-advanced/67-shallow-routing.md`, `60-appendix/10-faq.md`, `+assets/messages.json`.
- **Prefetching**: Supported, with code and data separated. Configured with `data-sveltekit-*` attributes on `<a>` or **any ancestor element** (default template puts `data-sveltekit-preload-data="hover"` on `<body>`). The same attributes apply to `<form method="GET">`.

  | Attribute | Values | Behaviour |
  |---|---|---|
  | `data-sveltekit-preload-data` | `"hover"` (mouse rests; `touchstart` on mobile), `"tap"` (`touchstart`/`mousedown`), `false` | Imports route code **and runs its `load` functions** ahead of the click. Not done when `navigator.connection.saveData` is true. A failed preload logs `preload_data_failed`; data loads again on real nav. |
  | `data-sveltekit-preload-code` | `"eager"` (immediately), `"viewport"` (on entering viewport), `"hover"`, `"tap"`, `false` | Code only. Only effective if more eager than the `preload-data` value. `eager`/`viewport` apply only to links present right after navigation (links added later wait for hover/tap). Respects saveData. |
  | `data-sveltekit-reload` | presence / `false` | Full-page browser navigation. `rel="external"` behaves the same and is also skipped by the prerender crawler. |
  | `data-sveltekit-replacestate` | presence / `false` | Use `replaceState` instead of `pushState`. |
  | `data-sveltekit-reset` | `"false"` | Keep scroll position and focus. Replaces v2 `data-sveltekit-keepfocus`/`noscroll` (`link_option_replaced`). |

  - Disable inside a subtree with `="false"` (v3 removed `"off"`).
  - Conditional usage: `data-sveltekit-preload-data={cond ? 'hover' : false}`. Invalid values warn (`link_option_invalid`).
  - Programmatic: `preloadData(href)` returns `{type:'loaded', status, data} | {type:'redirect', location, status} | {type:'error', status, error}` (error branch new in v3). It reuses an in-flight hover preload.
  - `preloadCode(routeId)` takes a **route ID** in v3 (pathnames rejected with `preload_route_is_pathname`). Convert a URL with `match(url)` from `$app/paths`, which returns `{ id, ... }`. It fails for endpoint-only routes.
  - No automatic viewport *data* prefetch and no prefetch cache TTL is documented.

  Source: `30-advanced/30-link-options.md`, `60-appendix/35-migrating-to-sveltekit-3.md`, `+assets/messages.json`.
- **Scroll restoration**: Supported.
  - Default on internal nav: scroll to 0,0, or to the element whose id matches the `#hash`, then reset focus.
  - Back/forward restores scroll. The router stores scroll positions, snapshots and `page.state` in history entries.
  - Opt out with `data-sveltekit-reset="false"`, `goto(..., { reset: false })`, or `disableScrollHandling()`. The latter is only valid during a navigation update, e.g. `onMount`/`afterNavigate` (`scroll_handling_outside_navigation`).
  - Shallow navigations preserve scroll and focus by default.
  - Prerender warns about links to missing `#id`s (`prerender.handleMissingId`).

  Source: `30-advanced/30-link-options.md`, `30-advanced/67-shallow-routing.md`, `+assets/messages.json`.
- **View transitions**: Partial (manual). There is no built-in integration. The documented recipe is `onNavigate(nav => new Promise(res => document.startViewTransition(async () => { res(); await nav.complete; })))`. Source: `60-appendix/10-faq.md`.
- **Route-level code splitting**: Supported by default. Per-route chunks plus `modulepreload` (always on in v3; the `preloadStrategy` option was removed). `output.bundleStrategy` accepts `'split'` (default), `'single'` (one JS/CSS bundle, recommended for Capacitor/HTTP1 or embedded devices) and `'inline'` (from catalog; inlines into HTML). Source: `40-best-practices/05-performance.md`, `10-getting-started/25-project-types.md`, `+assets/messages.json [config_server_resolution_bundle_strategy]`.
- **Base path**: Supported.
  - `paths.base` must be `''` or a root-relative path that starts but doesn't end with `/` (`config_paths_base_invalid`).
  - Internal links must include it; use `resolve(...)`. Prerender flags links outside base (`prerender_path_outside_base`).
  - `paths.assets` is an absolute URL (CDN) without a trailing slash, and is incompatible with service workers.
  - `paths.relative` (default `true` since v2) makes `%sveltekit.assets%` and asset paths relative. The SPA fallback page always uses absolute paths.
  - `asset('file.png')` resolves static assets (no leading `/` in v3; `asset_leading_slash`).
  - `$app/paths` v3 exports `asset`, `resolve`, `match`. `base`, `assets`, `resolveRoute` were **removed in v3**.

  Source: `60-appendix/35-migrating-to-sveltekit-3.md`, `25-build-and-deploy/55-single-page-apps.md`, `+assets/messages.json`.
- **Notable extras**:
  - **`reroute` hook** (`src/hooks.js`, universal) maps an incoming URL to a different pathname for route matching without changing the address bar or `event.url`. It can be async since 2.18 and receives `fetch`. It must be pure and idempotent; the result is cached client-side per unique URL. Typical use: translated slugs.
  - **Content negotiation**: a `+page` and a `+server` can share a route. `PUT/PATCH/DELETE/OPTIONS/QUERY` always go to `+server`. `GET/POST/HEAD` go to the page when `Accept` prefers `text/html`. GET responses add `Vary: Accept`.
  - **`trailingSlash`** page option (`'never'` default, `'always'`, `'ignore'`) redirects to the canonical form.
  - **Hash router**: `router.type: 'hash'` makes the whole app client-side with hash URLs. Server files are forbidden (`route_server_file_hash_router`) and page options are ignored (`router_hash_page_options`).
  - **Server-side route resolution**: `router.resolution: 'server'` versus default `'client'`. The browser asks the server which route matches instead of shipping the full route manifest. Incompatible with `bundleStrategy` `single`/`inline` and with the hash router. With client resolution, routes without `+page` are unknown to the browser.
  - **Route announcements and focus management** for accessibility: a live region announces the new `<title>`, focus moves to `<body>` (or to an `[autofocus]` element) after navigation and after enhanced form submission.
  - **`page` object** (`$app/state`, fine-grained Svelte 5 state): `url`, `params`, `route.id`, `status`, `error`, `data`, `form`, `state`, `shallow` (v3). Readable on the server only during component render (`state_read_outside_render`). `navigating` and `updated` are also exported.
  - **Version skew handling**: on route-module load failure or error status, if version polling sees a new deploy, the service worker is updated and SvelteKit does a full-page navigation.

  Source: `30-advanced/20-hooks.md`, `20-core-concepts/10-routing.md`, `20-core-concepts/40-page-options.md`, `40-best-practices/10-accessibility.md`, `98-reference/20-$app-state.md`, `30-advanced/40-service-workers.md`, `+assets/messages.json`.

## 2. Rendering modes

- **SSR**: Supported, on by default [stable]. The first request is server-rendered, then hydrated, then a client router takes over ("transitional app"). Page options are evaluated statically if they are boolean or string literals. Otherwise the `+page.js`/`+layout.js` module is imported on the server (at build and runtime) to read them, so browser-only code must not run at module load. Source: `20-core-concepts/40-page-options.md`, `10-getting-started/25-project-types.md`.
- **Streaming SSR**: Partial (data streaming, not component Suspense streaming).
  - **Promises returned from *server* `load`** (top-level or nested) are serialized as they resolve and streamed after the initial HTML. Consume them with `{#await}` for skeleton states.
  - Requires JS and `csr = true`; otherwise they never resolve (`streaming_without_csr`, dev warning).
  - Promises from *universal* load are **not** streamed; they are recreated in the browser.
  - Status and headers are fixed once streaming starts, so no `setHeaders`, `cookies.set` or `redirect` inside streamed promises (`set_headers_after_response`, `cookies_set_after_response`).
  - Rejections need handling: `load`'s `fetch` handles them automatically; otherwise attach a noop `.catch`.
  - Platforms that buffer (AWS Lambda, Firebase) or buffering proxies (NGINX) defeat streaming.
  - Dependency tracking stops once `load` returns (`load_tracking_after_return`).
  - `transformPageChunk` receives HTML in chunks split at `%sveltekit.head%` and layout/page boundaries.
  - With experimental Svelte async, components can `await` remote queries under `<svelte:boundary>`. Whether that streams HTML out-of-order is not described in the docs.

  Source: `20-core-concepts/20-load.md`, `30-advanced/20-hooks.md`, `+assets/messages.json`.
- **Static pre-rendering incl. dynamic params**: Supported. `export const prerender = true | false | 'auto'`:
  - Default is `false` (not prerendered).
  - `true` removes the route from the SSR server manifest, giving a smaller server.
  - `'auto'` prerenders but keeps the route in the manifest, so un-crawled params SSR on demand. This gives "prerender popular, SSR the long tail".

  How pages are discovered:
  - The crawler starts from entry points. Default entries are all non-dynamic routes; `prerender.entries` accepts `'*'` or absolute paths.
  - It follows `<a>` links in prerendered SSR pages.
  - **`export function entries()`** (may be async) in `+page(.server).js` or `+server.js` returns param sets, typed `EntryGenerator`.
  - `+server.js` routes are prerenderable (GET only; other methods or `fallback` give `prerender_endpoint_methods`). They inherit prerenderability from pages that fetch them.

  Output and limits:
  - Output file naming follows `trailingSlash`: `about.html` vs `about/index.html`.
  - Directory/file name clashes are a build error. Use extensions such as `foo.json/+server.js`.
  - Not prerenderable: pages with actions (`prerender_actions`); a route with both `+page` and `+server` (`route_prerender_page_and_endpoint`); a root `+server` returning non-HTML; pages reading `url.searchParams`; `getClientAddress()` (`prerender_client_address`); `csp.mode: 'nonce'` or a nonce placeholder in the template (`prerender_nonce`).
  - Routes marked prerenderable but never reached raise an error (`prerender_unseen_routes`; handler `prerender.handleUnseenRoutes`).

  Build-time behaviour:
  - Handlers `prerender.handleHttpError`, `handleMissingId`, `handleEntryGeneratorMismatch`, `handleInvalidUrl` and `handleUnseenRoutes` accept `'fail'` (default) | `'warn'` | `'ignore'` | a function.
  - `prerender.concurrency` is a positive integer.
  - `building` from `$app/env` is true during prerender; `handle` and `load` run there.
  - `paths.origin` supplies `url.origin` during prerender (replaces the removed `prerender.origin`).

  Source: `20-core-concepts/40-page-options.md`, `+assets/messages.json`.
- **Client-only / SPA routes and full SPA mode**: Supported.
  - Per route: `export const ssr = false` renders an empty shell, and universal `load` runs only in the browser. If `ssr` and `csr` are both false, nothing renders.
  - Whole app: `ssr = false` in the root `+layout.js`, plus `adapter-static({ fallback: '200.html' })` when there are no server files. The fallback page is generated from `app.html` by rendering the root layout without a page (`prerender_fallback_failed` if that errors). Avoid naming it `index.html` because it overwrites the prerendered home page (`adapter_fallback_overwrites`).
  - Individual pages can opt back in with `prerender = true; ssr = true`.
  - Alternatively `router.type: 'hash'`.
  - Docs warn strongly about SPA performance and SEO cost. Recommended only for wrapped mobile or desktop apps (Tauri, Capacitor, Wails, Electron) or local-network apps.

  Source: `25-build-and-deploy/55-single-page-apps.md`, `20-core-concepts/40-page-options.md`, `10-getting-started/25-project-types.md`.
- **Partial hydration (islands / server components / server islands)**: Not supported. There is no islands or RSC concept; hydration is whole-page. The closest options:
  - **`csr = false`** per page or layout ships **zero JS**. `<script>` blocks are removed, links become full-page navigations, forms can't be enhanced, and HMR is disabled. Use `export const csr = dev` to keep HMR in dev.
  - MPA style via `<body data-sveltekit-reload>`.

  Source: `20-core-concepts/40-page-options.md`, `10-getting-started/25-project-types.md`.
- **Static shell with dynamic holes (PPR-like)**: Partial (data-level only). Remote **`prerender`** functions [EXPERIMENTAL] can be used "on pages that are otherwise dynamic, allowing for partial prerendering of your data". Their results are computed at build time, served from CDN, and cached in the browser's Cache API until a new deployment. There is no HTML-shell-plus-streamed-holes mechanism. `prerender = 'auto'` is a per-route hybrid, not per-component. Source: `20-core-concepts/60-remote-functions.md`.
- **Per-route rendering-mode control**: Supported. Page options `prerender`, `ssr`, `csr`, `trailingSlash`, `config` and `entries` are exported from `+page(.server).js` or `+layout(.server).js` (some also from `+server.js`). They cascade from layouts, and child values override parent values; set app-wide in the root layout. Per-route deployment target or runtime is set via adapter `config` (see §11). The same `config` must be exported by `+page` and `+server` files in one route (`route_config_mismatch`). v3: universal `config` takes precedence over server `config`. Source: `20-core-concepts/40-page-options.md`, `60-appendix/35-migrating-to-sveltekit-3.md`.
- **Hydration strategies**: Not supported beyond full hydration plus the `csr` toggle. No lazy, visible or idle hydration. The client `init` hook delays hydration while it awaits. SSR `fetch` responses are inlined into HTML and replayed during hydration so universal loads don't refetch. Source: `30-advanced/20-hooks.md`, `20-core-concepts/20-load.md`.
- **Notable extras**:
  - Rendering mode can also be switched in `handle` (SEO doc mentions disabling SSR there; mechanism not detailed).
  - CSP support (`csp.mode: 'auto' | 'hash' | 'nonce'`; `'auto'` uses nonces only for dynamic pages and hashes for prerendered ones), `csp.directives`, `csp.reportOnly` (must include `report-to` or `report-uri`). Trusted Types need the `'sveltekit-trusted-url'` and `'svelte-trusted-html'` policies.
  - `app.html` placeholders: `%sveltekit.head%`, `%sveltekit.body%`, `%sveltekit.assets%`, `%sveltekit.nonce%`, `%sveltekit.env.NAME%`, `%sveltekit.version%`. `%sveltekit.body%` should be wrapped in an element (`app_body_unwrapped`).
  - Vite `transformIndexHtml` plugins don't run (`transform_index_html_unsupported`).

  Source: `10-getting-started/30-project-structure.md`, `+assets/messages.json`.

## 3. Data loading

- **Where data is fetched**:
  1. `load` in `+page.js`/`+layout.js` (**universal**: server during SSR, then browser on later navigations).
  2. `load` in `+page.server.js`/`+layout.server.js` (**server-only**; on client navigation, called via an internal JSON data request).
  3. **Remote functions** [EXPERIMENTAL]: `query`, `query.batch`, `query.live`, `prerender` from `$app/server`, exported from `*.remote.ts` modules and **awaited directly in components** (needs Svelte `compilerOptions.experimental.async`) or in universal loads and event handlers.
  4. `+server.js` endpoints fetched manually.

  Load dependencies also work when `ssr = false` (universal load runs client-only). Source: `20-core-concepts/20-load.md`, `20-core-concepts/60-remote-functions.md`.
- **Load event properties**:

  | Property | Universal | Server | Notes |
  |---|---|---|---|
  | `params` | ✓ | ✓ | Typed; matcher-transformed values. Accessing a param tracks it. |
  | `route` (`.id`) | ✓ | ✓ | E.g. `'/a/[b]/[...c]'`. |
  | `url` | ✓ | ✓ | `URL`; `hash` unavailable. Property access is tracked; `request.url` is not. |
  | `fetch` | ✓ | ✓ | Enhanced fetch (below). |
  | `setHeaders(obj)` | ✓ (no-op in browser) | ✓ | Once per header per request (except `server-timing`, which merges); no `set-cookie`. Dev-time validation of `cache-control`/`content-type`. |
  | `parent()` | ✓ | ✓ | Merged data of ancestor loads. Server `parent()` sees only server layouts. Universal `parent()` sees universal layouts; a missing `+layout.js` acts as `({data}) => data`. |
  | `depends(...ids)` | ✓ | ✓ | Custom `[a-z]+:` ids (avoid Firefox-special schemes `moz-icon:`, `view-source:`, `jar:`) or URLs. |
  | `untrack(fn)` | ✓ | ✓ | Exclude reads from tracking. |
  | `data` | ✓ | – | Server load output when both a server and a universal load exist. |
  | `cookies`, `locals`, `platform`, `request`, `getClientAddress()` | – | ✓ | Inherited from `RequestEvent`. |

  Source: `20-core-concepts/20-load.md`, `+assets/messages.json`.
- **Loader execution model**:
  - All loads for a navigation run **concurrently**. A waterfall happens only via `await parent()`, so call it late.
  - When a route has both, the server load runs first and its output becomes the universal load's `data`.
  - On client navigation, all server loads are **grouped into a single HTTP response** (request coalescing). The page renders after all loads return, except streamed promises.
  - If a layout load throws, the page load still runs but its data isn't delivered. Auth guards in a layout don't protect page loads unless the pages `await parent()`; the docs recommend `handle` or per-page guards.
  - Output rules:
    - Server load must return a plain object (or null/undefined; `load_not_plain_object`) that devalue can serialize: JSON plus `Date`, `Map`, `Set`, `BigInt`, `RegExp`, `URL`, repeated/cyclic refs and promises. Custom classes go through the `transport` hook.
    - Universal load may return anything (classes, component constructors).
    - Merged `data` uses last-key-wins (page overrides layout).
  - Loads run at build time for prerendered pages. `getRequestEvent()` (`$app/server`) exposes the current event inside server loads, actions, endpoints, hooks and remote functions. It needs `AsyncLocalStorage` to work after an `await`; otherwise read it synchronously.

  Source: `20-core-concepts/20-load.md`, `40-best-practices/05-performance.md`, `+assets/messages.json`.
- **Enhanced `fetch` (in load, hooks, endpoints, remote functions)**:
  - On the server it inherits `cookie` and `authorization` from the page request (same origin, or a more specific subdomain; not sibling subdomains or the parent domain). `credentials: 'include'` does not forward other cookies; use `handleFetch` for that.
  - Relative URLs work on the server. The global `fetch` errors on relative URLs (`fetch_relative_url`).
  - Internal `+server` requests call the handler directly with no HTTP round-trip.
  - During SSR, `text()`, `json()` and `arrayBuffer()` results are **inlined into the HTML and replayed during hydration**. Headers are excluded unless allowed by `filterSerializedResponseHeaders` (`load_response_header_not_serialized`).
  - Cross-origin requests from universal load are CORS-checked on the server too (`load_fetch_cors`).
  - Using `window.fetch` in load warns (`window_fetch_in_load`). Calling `fetch` eagerly during component SSR warns (`ssr_fetch_eager`).
  - Returning a fetched compressed response directly errors (`fetch_response_decoded`).

  Source: `20-core-concepts/20-load.md`, `30-advanced/20-hooks.md`, `10-getting-started/40-web-standards.md`, `+assets/messages.json`.
- **Request deduplication**: Partial.
  - SSR→hydration replay of `fetch`.
  - Hover-preload results reused by navigation and by `preloadData`.
  - Server-load coalescing into one request.
  - **Remote `query`**: the argument is devalue-serialized into a cache key, with object, Map and Set keys sorted so that `{a,b}` and `{b,a}` share a key. There is a **request-scoped cache on the server** (the same query runs once per request) and a **shared instance on the client** (`getPosts() === getPosts()`; all consumers share one instance and network call).
  - **`query.batch(schema, fn)`** batches calls made in the same macrotask. The server callback gets an array of args and returns `(arg, index) => result`, which solves n+1.
  - No dedup for raw `load` across different routes is documented.

  Source: `20-core-concepts/60-remote-functions.md`, `40-best-practices/05-performance.md`.
- **Passing server data to client components**:
  - Load `data` becomes the page or layout `data` prop, typed via `PageProps`/`LayoutProps`.
  - Any ancestor can read descendant data via `page.data` (typed by `App.PageData`). A common pattern is the root layout setting `<title>` from `page.data.title`.
  - Remote query results serialized during SSR are reused during hydration.
  - Custom types use `transport` in `src/hooks.js`: `{ Name: { encode: v => v instanceof X && [...], decode: arr => new X(...) } }`. It applies to load, actions, remote args and returns, and snapshots.
  - Avoid module-level shared state on the server; use Svelte context.

  Source: `20-core-concepts/20-load.md`, `30-advanced/20-hooks.md`, `20-core-concepts/50-state-management.md`.
- **Client-side data cache**: Partial.
  - There is no general TTL or stale-while-revalidate cache for `load`. Instead, load results are **kept until their tracked dependencies change** ("conservative invalidation"), so layout data isn't refetched between sibling pages.
  - Remote `query` instances are cached while "in active use" (rendered, being awaited, or referenced) and released when unused.
  - `query.live` connections are shared and disconnect when unused.
  - Remote `prerender` results persist in the browser Cache API across reloads until a new deployment.
  - Snapshots persist UI state (not data) to `sessionStorage`.

  Source: `20-core-concepts/20-load.md`, `20-core-concepts/60-remote-functions.md`.
- **Deferred / streamed data**: Supported for server-load promises (see §2). Remote **`query.live`** [EXPERIMENTAL]:
  - The callback is an async generator or (async) iterable.
  - SSR `await` returns the first yielded value, then closes the iterator; that value is serialized for hydration. The generator must yield at least once (`remote_query_live_no_value`).
  - The client keeps one shared connection while in use and exposes `connected` and `reconnect()`. It auto-reconnects with exponential backoff and on the `navigator.onLine` false→true transition.
  - Instances are async-iterable (`for await`). Slow consumers see only the latest value ("not event logs").
  - There is no `refresh()`.
  - Don't cache these responses in a service worker; they are `Cache-Control: no-store`.

  Source: `20-core-concepts/60-remote-functions.md`.
- **Dependency tracking and invalidation**: Supported (fine-grained, automatic). A load reruns when:
  - a referenced `params.x` changes;
  - a referenced `url` property changes (`pathname`, `search`, etc.);
  - a specific `searchParams.get/getAll/has` key changes;
  - it called `parent()` and a parent reran;
  - a child server load that called `parent()` reruns and the parent is a server load (a universal child reuses the parent's data instead);
  - `invalidate(url | 'app:id' | predicate)` matches a `depends()` id, or a URL **fetched in a universal load**. Server loads never auto-depend on fetched URLs, to avoid leaking secrets; `dangerZone.trackServerFetches` was removed in v2;
  - `refreshAll()` was called (reruns all loads **and active remote queries**; unlike deprecated `invalidateAll`, it doesn't reset `page.state`).

  Further rules:
  - Reruns update `data` without remounting components.
  - v3: calling `invalidate`/`invalidateAll` during an in-flight navigation no longer aborts it.
  - Remote queries are **not** rerun on navigation unless their argument changes. Refresh them with `query().refresh()`, server-side `.refresh()`/`.set()` in mutations, or `refreshAll()`.

  Source: `20-core-concepts/20-load.md`, `60-appendix/35-migrating-to-sveltekit-3.md`, `60-appendix/30-migrating-to-sveltekit-2.md`.
- **Access to request context**:
  - Server loads get `cookies`, `locals` (populated in `handle`), `platform`, `request`, `getClientAddress`.
  - Any server code in the request can call `getRequestEvent()`.
  - In remote **queries**, `event.url`, `params` and `route` **throw** (v3; `remote_request_property`) because queries are cached by argument. Pass values as args, or derive context in `handle` into `locals`. For query requests, `handle` sees the remote endpoint's URL.
  - In `form`/`command`, `url`/`params`/`route` reflect the *calling page* and are client-controlled, so they must not be used for authorization.

  Source: `20-core-concepts/20-load.md`, `20-core-concepts/60-remote-functions.md`, `30-advanced/20-hooks.md`.
- **Remote `query` API detail** [EXPERIMENTAL; opt in via `experimental.remoteFunctions: true` plus `compilerOptions.experimental.async: true`; remote files without the flag cause an error]:
  - `query(fn)` or `query(schema | 'unchecked', fn)`. The schema is any Standard Schema (Zod, Valibot, ArkType). An invalid validator gives `remote_invalid_validator`.
  - The resource is thenable and has `.loading`, `.error` (typed `App.Error | undefined` in v3), `.current`, `.refresh()`. Server side also has `.set(value)`.
  - `<svelte:boundary>` handles pending and failed states when `await`ed.
  - Args and returns are devalue-serialized; `RegExp` and promises are rejected as args.
  - `query` cannot be called while prerendering (`remote_query_prerender`). Pages fully prerendered (e.g. `adapter-static`) can't use queries.
  - Cookies are readable but not writable in queries. Headers cannot be set in any remote function (`remote_headers_forbidden`).
  - `redirect()` is allowed in query, form and prerender, but not in command.
  - Remote modules:
    - Name contains a `remote` segment: `x.remote.ts`, `remote.ts`, `x.remote.test.ts`.
    - May live anywhere in `src` except `server` dirs (`remote_module_server_only`). Third-party packages that peer-depend on kit can ship them.
    - May only export remote functions (`remote_module_invalid_export`; type-only exports allowed) and named exports only, no `default`.
    - Schemas cannot be exported from them.

  Source: `20-core-concepts/60-remote-functions.md`, `60-appendix/35-migrating-to-sveltekit-3.md`, `+assets/messages.json`.
- **Notable extras**:
  - `untrack` in load.
  - Remote **`prerender(fn | schema, fn, { inputs?: () => args[], dynamic?: boolean })`**: build-time data. Calls found while crawling are saved automatically. By default the function is excluded from the server bundle, so un-prerendered args fail (`remote_prerender_not_dynamic`) unless `dynamic: true`.
  - `read(asset)` from `$app/server` reads imported assets at runtime (adapter must support it via `supports.read`).
  - `$app/state.page.data`.

## 4. Mutations

- **Form handling without JS (progressive enhancement)**: Supported. Two mechanisms.

  **(a) Form actions** [stable, "feature-complete"; new work focuses on remote functions]:
  - `export const actions = { default: async (event) => {...} }` or named actions in `+page.server.js`. Use `<form method="POST">` with no JS needed.
  - Named actions are invoked with `action="?/name"` or `action="/other/page?/name"`, or with `<button formaction="?/name">`.
  - `default` and named actions cannot coexist (`action_default_with_named`). `?/default` is reserved.
  - Actions always use POST. A POST to a page without actions gives a 405 framework error.
  - Pages with actions can't be prerendered.

  **(b) Remote `form`** [EXPERIMENTAL]:
  - `export const createPost = form(schema, async (data, issue) => {...})`, then `<form {...createPost}>`.
  - The spread object includes `method` and `action` for no-JS submission, plus an **attachment** that enhances when JS is present.

  Source: `20-core-concepts/30-form-actions.md`, `20-core-concepts/60-remote-functions.md`.
- **Action anatomy and results**:
  - An action receives the `RequestEvent` and reads `await request.formData()`.
  - Returned data must be devalue-serializable, not a `Response` (`action_response_not_serializable`). It becomes the page's `form` prop and `page.form` "until the next update", so it is ephemeral and vanishes on reload.
  - **`return fail(status, data)`** reports validation errors; `throw fail` is an error (`action_throw_fail`). The status is exposed as `page.status`.
  - Status codes with `use:enhance` or `accept: application/json`:
    - `fail()` gives that status (v3; previously always 200);
    - returned data gives 200;
    - `undefined` gives **204**.
  - **`redirect(303, url)`** and **`error(...)`** throw. `return redirect()` and `return error()` are flagged (`action_return_redirect`, `action_return_error`).
  - After a successful non-redirect action, the page re-renders and **its `load` functions rerun**. `handle` runs once before the action and is *not* rerun before the loads, so update `event.locals` yourself after changing session cookies.
  - With `ssr = false`, no-JS action data and errors are lost (`form_action_data_without_ssr`, `form_action_error_without_ssr`); use `use:enhance`.

  Source: `20-core-concepts/30-form-actions.md`, `+assets/messages.json`.
- **`use:enhance` (`$app/forms`)**: Supported [changed in v3].
  - Only on `method="POST"` forms that target `+page.server.js` actions (`enhance_invalid_method`).
  - Forms with file inputs must have `enctype="multipart/form-data"` (`enhance_file_without_enctype`).

  Default behaviour, emulating native submission without a reload:
  - Same-page action: update `form`, `page.form` and `page.status` on success or failure.
  - **Different-page action (v3)**: navigate to `result.location` (the action URL minus `?/name`, other query params kept), pushing a history entry and populating that page's `form`. Errors render the boundary nearest the *action's* route.
  - Reset the `<form>`.
  - `refreshAll` on success.
  - `goto` on redirect.
  - Render the nearest `+error` on unexpected error.
  - Reset focus.

  Customising with a `SubmitFunction`:
  - Input: `{ formElement, formData, action, cancel(), submitter }`. It runs before submit and may return `async ({ result, update }) => {}`.
  - Returning a callback **overrides** the default behaviour. Calling `update(opts)` restores it:

  | `update` option | Default | Behaviour |
  |---|---|---|
  | `reset` | `true` | Reset form values after success. |
  | `refreshAll` | `true` on success, `false` on failure | Refresh all data. Deprecated alias `invalidateAll`. When navigating cross-page, `false` only allows reuse of shared layout data. |
  | `navigate` | `true` | `false` applies a non-redirect result to the current page (v2 behaviour). Redirects are always followed. |

  Related helpers:
  - `applyAction(result)`: success/failure sets `page.status` and `form`; redirect calls `goto(location, { refreshAll: true })`; error renders the nearest `+error`. Focus is always reset. It does **not** navigate to a non-redirect `location` or refresh data.
  - Manual enhancement: `fetch(form.action, { method: 'POST', body })`, then `deserialize(await res.text())`. `JSON.parse` is insufficient because of `Date`/`BigInt`.
  - Header `x-sveltekit-action: true` routes the POST to the action when a sibling `+server.js` exists.
  - Relative `action="?/delete"` drops existing query params; preserve them with `action="?page=2&/delete"`.
  - GET forms are handled by the client router like links and honour `data-sveltekit-*`.

  Source: `20-core-concepts/30-form-actions.md`, `60-appendix/35-migrating-to-sveltekit-3.md`, `+assets/messages.json`.
- **Remote `form` detail** [EXPERIMENTAL]:
  - **Fields**:
    - `form.fields.<path>.as(type, value?, checked?)` returns `name`, `type`, `value` and `aria-invalid`.
    - Types: input types plus `'select'`, `'select multiple'`, `'file multiple'`, `'submit'`, `'hidden'`, `'radio'`, `'checkbox'`. `radio`, `submit`, `hidden` and checkbox-array options require a value (`form_input_missing_value`).
    - Nested paths use JS notation (`info.height`, `attributes[0]`); keys needing quotes are not allowed (`form_field_invalid_name`). `__proto__`, `constructor` and `prototype` are forbidden. `$` is reserved.
    - Numbers and booleans are coerced via `n:`/`b:` name prefixes. Unchecked checkboxes are absent from the submission, so schema defaults are needed.
    - **v3**: every named control must use `.as()`; a hand-written `name` causes rejection (`form_field_unbound`). Duplicate single-value names are rejected.
  - **Validation**:
    - The server schema runs first; on failure the callback is skipped.
    - `fields.x.issues()` and `fields.allIssues()` return `{message}[]` or `undefined`.
    - `validate({ includeUntouched })` validates programmatically; untouched fields are ignored by default.
    - `form.preflight(clientSchema)` runs client-side validation and blocks the submit.
    - Inside the handler, `invalid(issue.field('msg'), 'form-level msg')` from `@sveltejs/kit` throws. Using `fail()` in a remote form is an error (`remote_form_fail`).
    - Unread issues trigger a dev warning (`remote_form_issues_ignored`).
    - Invalid argument validation (non-form) gives a generic **400** and `handleError({ kind: 'validation', issues })`.
  - **State and value access**:
    - `fields.x.value()` and `fields.value()` read live values. `fields.set({...})` and `fields.x.set(v)` write them.
    - Without JS, invalid submissions re-populate values, except names prefixed `_` (e.g. `_password`), which are never echoed back.
    - Field props are proxies; don't enumerate them (`form_fields_enumerated`).
  - **Result and enhancement**:
    - Returned data is available as `form.result` (ephemeral).
    - `pending` is a count used e.g. as `disabled={!!modify.pending}`.
    - `form.enhance(async (f) => { if (await f.submit()) ... })`: `submit()` resolves to a boolean for valid/invalid and throws on error. `f.element` is the form element. There is no automatic reset with `enhance`.
    - `form.for(id)` creates isolated instances for lists. One instance attaches to one `<form>` (`remote_form_multiple_elements`).
    - Multiple submit buttons are modelled as a schema field: `fields.action.as('submit', 'login')`.
  - **Errors**: an error renders the nearest `+error.svelte`.

  Source: `20-core-concepts/60-remote-functions.md`, `60-appendix/35-migrating-to-sveltekit-3.md`, `+assets/messages.json`.
- **Server functions / RPC**: Supported [EXPERIMENTAL] via remote functions (`query`, `form`, `command`, `prerender`). On the client they become `fetch` wrappers to a generated endpoint.
  - **`command(schema?, fn)`** is callable from anywhere (event handlers).
  - Restrictions:
    - Not during render or SSR (`remote_command_render`).
    - Not inside query or prerender functions (`remote_command_readonly`).
    - Not from read-only HTTP handlers such as GET (`remote_command_method`).
    - **No `redirect`** (`remote_command_redirect`); return a value and `goto` client-side instead.
    - Commands can write cookies (absolute `path` required for remote cookie writes; `remote_cookie_path_relative`) and accept `File` args.
  - Docs say "prefer `form` where possible" because it degrades without JS.
  - `+server.js` endpoints remain the plain-HTTP option.

  Source: `20-core-concepts/60-remote-functions.md`, `+assets/messages.json`.
- **Pending, error and validation-error state**:
  - Form actions: no built-in pending flag. Use the `SubmitFunction` (before/after callbacks) and `navigating` from `$app/state`. Validation goes through `fail()` → `form`; errors through `+error.svelte`.
  - Remote form: `pending`, `issues()`, `allIssues()`, `result`, `aria-invalid`.
  - Remote query: `loading` / `error` / `current`.
  - Command: try/catch around the call.

  Source: as above.
- **Optimistic UI**: Supported [EXPERIMENTAL] via client-requested updates: `await submit().updates(getPosts({ filter }).withOverride(posts => [newPost, ...posts]))`.
  - The override applies immediately and is replaced by the server-refreshed value in the same response.
  - One override per query instance per call (`remote_updates_duplicate_override`). `.updates()` can be called once per invocation; calling `.updates()` with no args opts out of auto-invalidation (`remote_updates_repeated`).
  - Form actions have no built-in optimistic helper; it is manual via the `use:enhance` callback.

  Source: `20-core-concepts/60-remote-functions.md`, `+assets/messages.json`.
- **Data refresh after mutation**:
  - **Form actions / `use:enhance`**: the page's loads rerun after the action; enhanced submissions call `refreshAll()` on success.
  - **Remote `form`**: by default invalidates **all queries and load functions** after success. Calling `refresh()`, `set()` or `reconnect()` on any query inside the handler replaces that with a targeted update.
  - **`command`**: refreshes **nothing** by default.
  - **Single-flight mutations**: server-side `void getPosts().refresh()`, `getPost(id).set(value)` or `liveQuery(arg).reconnect()` inside `form`/`command` ship the refreshed query data in the **same response** (the framework awaits the floating promise).
  - **Client-requested refreshes**: `submit().updates(getPosts, getPosts(arg), override...)` or `myCommand(arg).updates(...)`. The server must accept them with `requested(getPosts, limit)`:
    - Iterate `{ arg, query, ignore }`. Every request must be refreshed, set, reconnected or ignored, or that client query errors.
    - Shorthands: `.refreshAll()` (not for live queries; `reconnectAll()` for those) and `.ignoreAll()`. Use `for await` if the validator is async.
    - **`limit` is mandatory** (DoS protection; `Infinity` allowed but discouraged). Extra requests fail client-side.
    - `requested` is only valid inside command/form.
  - Docs give the rationale: bundle size, since only named queries are bundled into the command, and DoS.

  Source: `20-core-concepts/30-form-actions.md`, `20-core-concepts/60-remote-functions.md`, `+assets/messages.json`.
- **Redirects after mutation**:
  - Actions: `redirect(303, ...)`; enhanced forms `goto` the location.
  - Remote `form`: `redirect()` allowed. `command`: not allowed.
  - The redirect status must be 300–308 (`invalid_redirect_status`).
  - **v3 external redirects** require `redirect(status, url, { external: true | ['https://origin', 'javascript:'] })`. `true` still blocks `javascript:` and `data:`. `//host` and `\\host` count as external.
  - Don't call `redirect()` inside `try` (it throws).

  Source: `20-core-concepts/30-form-actions.md`, `60-appendix/35-migrating-to-sveltekit-3.md`, `+assets/messages.json`.
- **File uploads**: Supported.
  - Native multipart `request.formData()` in actions and endpoints.
  - Remote form `v.file()` fields with `.as('file')` or `.as('file multiple')` (array field `name[]` required for `multiple`). File and non-file inputs can't be mixed under one name. Requires `enctype="multipart/form-data"`.
  - Commands accept `File` args.
  - Body size limits: `BODY_SIZE_LIMIT` (adapter-node and adapter-bun default 512K; `Infinity` disables), enforced while streaming. Excess returns a 413 framework error.
  - No resumable or chunked upload helpers.

  Source: `20-core-concepts/60-remote-functions.md`, `25-build-and-deploy/40-adapter-node.md`, `25-build-and-deploy/45-adapter-bun.md`, `30-advanced/25-errors.md`.
- **Multiple actions per page**: Supported. Named actions, `formaction`, and an `id` in returned data to tell forms apart. Remote: many `form` exports, `form.for(key)` instances, and submit-button fields. Source: `20-core-concepts/30-form-actions.md`, `20-core-concepts/60-remote-functions.md`.
- **CSRF protection**: Supported, built in and **always on in v3**.
  - Cross-origin form submissions and remote function calls are checked against the app origin: derived from headers, or `paths.origin` if set. The adapter-node `ORIGIN` env var was replaced by `paths.origin`.
  - Allow other origins with `csrf.trustedOrigins: ['https://…']`. `csrf.checkOrigin` was removed.
  - v3: cross-origin mutative requests **without a `Content-Type`** are rejected.
  - Misconfigured origins behind proxies produce "Cross-site POST form submissions are forbidden".

  Source: `60-appendix/35-migrating-to-sveltekit-3.md`, `25-build-and-deploy/40-adapter-node.md`.
- **Notable extras**: Programmatic validation issues (`invalid`, `issue.<field>()`). `applyAction`, `deserialize`. Remote functions' 'unchecked' validator opt-out. Validation failures don't help attackers (generic 400). Version-skew note: changed remote signatures between deploys surface as validation errors.

## 5. Caching & revalidation

- **Page / HTML caching**: Partial (header-based).
  - `setHeaders({ 'cache-control': ..., age })` from any server or universal load (SSR only), or `response.headers.set` in `handle`. Each header can be set once per request.
  - Prerendered pages are static files served by the adapter or host.
  - Page and endpoint GETs vary on `Accept`.
  - No framework HTML cache store.

  Source: `20-core-concepts/20-load.md`, `20-core-concepts/10-routing.md`.
- **Time-based revalidation (ISR)**: Partial (Vercel adapter only). Per-route `export const config = { isr: { expiration, bypassToken?, allowQuery? } }`:
  - `expiration` (seconds, or `false` = never) is required.
  - `allowQuery` lists the query params that form the cache key (default: all ignored).
  - ISR is ignored on prerendered routes and should not be used for user-specific content.
  - Other adapters: not found in docs.

  Source: `25-build-and-deploy/90-adapter-vercel.md`.
- **On-demand revalidation (by path / by tag)**: Partial. Vercel only, by route: `GET`/`HEAD` with header `x-prerender-revalidate: <bypassToken>`. The token must be at least 32 chars and is fixed at build time. **No tag-based revalidation** is documented. Source: `25-build-and-deploy/90-adapter-vercel.md`.
- **Data-level / function-level caching**: Partial [EXPERIMENTAL].
  - Remote query: request-scoped server cache plus a client instance cache while in use.
  - Remote `prerender`: build-time results, CDN-served, browser Cache API until the next deployment.
  - No persistent server data cache (no `unstable_cache`/`"use cache"` equivalent) and no TTL options.

  Source: `20-core-concepts/60-remote-functions.md`.
- **Client navigation cache**: Partial. No router cache with TTL. Behaviour is dependency-based reuse of load data, preload (`hover`/`tap`) result reuse, and component reuse. Back/forward reruns loads ("re-running any `load` functions"), except where dependencies are unchanged. Source: `30-advanced/67-shallow-routing.md`, `20-core-concepts/20-load.md`.
- **HTTP cache-header helpers**: Partial. Headers go through `setHeaders` (no typed `cacheControl()` builder). Dev-only validation warns on invalid or empty `cache-control` directives and invalid `content-type`.
  - Hashed immutable assets under `/_app/immutable` (from memory, unverified for path; `appDir` default `_app`). Bun adapter sets `Cache-Control: public,max-age=31536000,immutable`.
  - adapter-node and adapter-bun serve static files with content-hash ETags (node: no `Last-Modified`; only GET/HEAD).
  - Precompressed `.br`/`.gz` variants are negotiated per request.

  Source: `+assets/messages.json`, `25-build-and-deploy/40-adapter-node.md`, `25-build-and-deploy/45-adapter-bun.md`.
- **Preview / draft mode bypass**: Partial (Vercel only). The `__prerender_bypass=<bypassToken>` cookie renders an ISR route at request time (Vercel Draft Mode). Not found for other platforms. Source: `25-build-and-deploy/90-adapter-vercel.md`.
- **Notable extras**: Service worker precaching (versioned caches via `version` and `$app/manifest`). Version polling: `version.pollInterval` defaults to **1 hour in v3**, which sets `updated.current`. `updated` also flips on server data fetches, remote calls, and window focus or visibility.

## 6. Server & API

- **API routes / endpoints (per HTTP method)**: Supported. `+server.js` exports any of `GET POST PUT PATCH DELETE OPTIONS HEAD QUERY` plus **`fallback`** for any other method (e.g. `MOVE`).
  - Handlers receive a `RequestEvent` and must return a `Response` (`endpoint_invalid_response`).
  - A HEAD request falls back to `GET` with `content-length` (GET beats `fallback`).
  - v3: empty 2xx (e.g. 204) responses have no body.
  - `json()`/`text()` helpers are **deprecated** in favour of `Response.json()` and `new Response()`.
  - Thrown `error()` or unexpected errors produce JSON or the `src/error.html` fallback depending on `Accept`; `+error.svelte` is not used.
  - Dev caveat: Vite injects CORS headers on `OPTIONS` (not present in prod). OPTIONS handlers need `server.cors.preflightContinue: true` if Vite's CORS is configured (`cors_preflight_continue`). v3 delegates dev static-asset CORS to Vite.
  - Endpoints are prerenderable (GET only). Types: `RequestHandler` from `./$types`.

  Source: `20-core-concepts/10-routing.md`, `60-appendix/35-migrating-to-sveltekit-3.md`, `+assets/messages.json`.
- **Middleware**: Partial (one global server hook; no per-route middleware files).
  - **`handle({ event, resolve })`** in `hooks.server.js` runs for every SvelteKit request: pages, endpoints, data requests, remote calls, and also during prerender. It does **not** run for static assets or already-prerendered pages.
  - It can return a custom `Response` (bypassing routing), mutate `event.locals`, and modify `response.headers` (beware immutable headers from `Response.redirect`).
  - Compose with **`sequence(...handles)`** from `@sveltejs/kit/hooks`.
  - `resolve(event, opts)` always returns `Promise<Response>` (v3 typing) and never throws:

  | `resolve` option | Default | Behaviour |
  |---|---|---|
  | `transformPageChunk({ html, done })` | identity | Transform streamed HTML chunks. Removing Svelte's hydration comments breaks hydration (`transform_page_chunk_comments`). |
  | `filterSerializedResponseHeaders(name, value)` | none included | Which `fetch` response headers are serialized into the page for hydration replay. |
  | `preload({ type: 'js'\|'css'\|'asset'\|'font', path, filename? })` | `js` and `css` preloaded; assets and fonts not | Controls `<link rel=preload/modulepreload>` (or `Link` headers if `output.linkHeaderPreload`). Not called in dev. `filename` (source path) is given for fonts. |

  - Errors thrown in `handle` itself are fatal and produce JSON or `error.html`.
  - Per-route logic: layout server loads (pages only), `+server` handlers, or path checks in `handle`.
  - Node `connect` middleware: in dev via a Vite plugin `configureServer`; in prod via adapter-node `handler.js` with Express or Polka.
  - `sequence` ordering semantics for resolve options are not documented here.

  Source: `30-advanced/20-hooks.md`, `60-appendix/10-faq.md`, `25-build-and-deploy/40-adapter-node.md`.
- **Request context (cookies, headers, locals)**: Supported. `RequestEvent` fields:
  - `request`, `url`, `params`, `route`, `cookies`, `fetch`, `locals` (typed via `App.Locals`), `platform` (typed via `App.Platform`; adapter-specific, e.g. Bun `platform.server`, Netlify `platform.context`), `getClientAddress()`, `setHeaders()`, `tracing` (`enabled`/`root`/`current` spans).
  - `isDataRequest`, `isSubRequest`, `isRemoteRequest` (from memory, unverified).

  **Cookies** (`get`, `getAll`, `set(name, value, opts)`, `delete(name, opts)`, `serialize`):
  - Security defaults for `httpOnly`, `secure` and `path` (v3: **path defaults to `'/'`**). `httpOnly: true`, `secure: true` except on localhost, and `sameSite: 'lax'` (from memory, unverified).
  - cookie v2 rules: ASCII names only.
  - `set` after the response is generated errors. `serialize` only works after route resolution. More than 4096 bytes warns in dev. Path-mismatch warnings appear in dev.
  - Cookies set in `load`/actions are applied to `event.fetch` sub-requests.
  - `setHeaders` cannot set `set-cookie`.

  Source: `20-core-concepts/20-load.md`, `30-advanced/20-hooks.md`, `60-appendix/35-migrating-to-sveltekit-3.md`, `+assets/messages.json`.
- **`handleFetch({ event, request, fetch })`**: Supported (server hook). Intercepts or rewrites `event.fetch` calls made on the server or during prerender, from endpoints, load, actions, `handle`, `handleError` and `reroute`. Uses: rewriting public API URLs to internal ones, or forwarding cookies to sibling subdomains. During `reroute`, `params` and route `id` are unavailable. Source: `30-advanced/20-hooks.md`.
- **Streaming responses and SSE**: Supported via web standards. Return `new Response(readableStream)` from `+server.js`. Docs mention SSE is possible "unless deploying to platforms that buffer responses, like AWS Lambda". adapter-node recommends `@polka/compression` because the `compression` package breaks streaming. adapter-bun disables the idle timeout for `text/event-stream` and adds `X-Accel-Buffering: no`. Remote `query.live` [EXPERIMENTAL] is a framework-level streaming primitive. Source: `20-core-concepts/10-routing.md`, `25-build-and-deploy/40-adapter-node.md`, `25-build-and-deploy/45-adapter-bun.md`.
- **Running work after the response (waitUntil / after)**: Not supported as a framework API. Platform-specific options:
  - Cloudflare: `import { waitUntil } from 'cloudflare:workers'` (v3; `platform.ctx` removed).
  - Vercel: `@vercel/functions`.
  - Node/Bun: process event `sveltekit:shutdown` (reason `SIGINT` | `SIGTERM` | `IDLE`) for async cleanup.
  - `getRequestEvent()` is unavailable after the response (e.g. in `setTimeout`).

  Source: `60-appendix/35-migrating-to-sveltekit-3.md`, `25-build-and-deploy/90-adapter-vercel.md`, `25-build-and-deploy/40-adapter-node.md`, `+assets/messages.json`.
- **Server-only code boundaries**: Supported (build-time import-graph enforcement) [changed in v3].
  - **Any filename with a `server` segment** (`x.server.ts`, `server.ts`, `x.server.test.ts`) and **any `server/` directory** except within `src/routes` and `static`. v2 recognised `src/lib/server` only.
  - `$app/server` and `$app/env/private` are always server-only.
  - Importing these from client-reachable code fails the build with the full import chain, even for unused re-exports and dynamic or interpolated `import()`. `import type` is fine.
  - Client entry points include `+page.svelte`, universal `+page.js`, `src/params.js` and the service worker.
  - `node_modules` and files outside the project are exempt; packages can opt in with `import '$app/server'`.
  - Detection is disabled when `process.env.TEST === 'true'`.
  - Remote modules may import server-only code but may not themselves be server-only.

  Source: `30-advanced/50-server-only-modules.md`, `60-appendix/35-migrating-to-sveltekit-3.md`, `+assets/messages.json`.
- **Environment variables** [new in v3; stable; v2.62 experimental]:
  - `src/env.ts` exports `variables = defineEnvVars({ NAME: EnvVarConfig })` (from `@sveltejs/kit/env`).
  - `EnvVarConfig` fields:

  | Field | Default | Behaviour |
  |---|---|---|
  | `public` | `false` (private) | Private vars import from `$app/env/private` (server-only). Public vars from `$app/env/public`, also usable in `app.html` as `%sveltekit.env.NAME%` (falls back to `''`). |
  | `static` | `false` (dynamic) | `true` inlines the value at build, enabling dead-code elimination. |
  | `schema` | none, so the var is **required** | Standard Schema or `(value) => value` function (sync only). Validated **at build and at startup**; failure stops the app. Use `building` from `$app/env` to make it optional at build. Can transform values (e.g. string to boolean). |
  | `description` | – | Shown on hover in the IDE. |

  - Names must be valid identifiers.
  - `src/env` may only import `$app/env` (not other `$app/*`, and not `$app/env/*`, which would be circular). Instrumentation can't intercept modules imported by `src/env`.
  - `.env`/`.env.local` are loaded in dev and build. In production, the node adapter needs `node --env-file`; Bun loads `.env` automatically.
  - `$env/static|dynamic/public|private` and `$app/environment` are **deprecated** (removed in v4).
  - Dynamic env vars cannot be read during prerender (v2 rule).

  Source: `20-core-concepts/70-environment-variables.md`, `+assets/messages.json`, `60-appendix/30-migrating-to-sveltekit-2.md`.
- **Other hooks**:
  - `init()` runs once on server start (`hooks.server`) or app start (`hooks.client`), for async setup. The client `init` delays hydration.
  - Module top-level code in hooks also runs at startup. `getRequestEvent` isn't available in `init`.
  - Hook files: `hooks.server.js` (`handle`, `handleFetch`, `handleError`, `init`), `hooks.client.js` (`handleError`, `init`), `hooks.js` universal (`reroute`, `transport`). Types come from `@sveltejs/kit/hooks` (v3): `Handle`, `HandleFetch`, `HandleServerError`, `HandleClientError`, `ServerInit`, `Reroute`, `Transport`.

  Source: `30-advanced/20-hooks.md`, `60-appendix/35-migrating-to-sveltekit-3.md`.
- **Notable extras**:
  - `getRequestEvent()` gives implicit request context (AsyncLocalStorage; on Cloudflare needs `nodejs_als`).
  - `read()` reads bundled assets at runtime on serverless platforms.
  - `QUERY` HTTP method support.
  - `getClientAddress()` with proxy-aware config: `ADDRESS_HEADER` and `XFF_DEPTH`, read from the right of the list.
  - Static assets and prerendered pages bypass `handle`.

## 7. Loading & error states

- **Route-level loading UI**: Not supported as a file convention (no `+loading.svelte`). Ways to show progress:
  - **`navigating`** from `$app/state` (non-null during navigation, with `from`/`to`/`type`; e.g. a global progress bar).
  - Streamed promises with `{#await}`.
  - With experimental Svelte async, `<svelte:boundary>` pending UI around awaited remote queries ("Until the promise resolves … the nearest `<svelte:boundary>` will be invoked").
  - Remote query `.loading`.
  - `beforeNavigate`/`afterNavigate`.

  The page renders only after all non-streamed loads resolve. Source: `20-core-concepts/20-load.md`, `20-core-concepts/60-remote-functions.md`, `98-reference/20-$app-state.md`.
- **Error boundaries (per route / root)**: Supported.
  - `+error.svelte` per directory; SvelteKit walks up the tree to the nearest one. Errors in a layout's `load` use the `+error.svelte` **above** that layout.
  - Errors in root `+layout(.server).js` load, or failures rendering the error page, fall to the static **`src/error.html`** (placeholders `%sveltekit.status%`, `%sveltekit.error.message%`). The same applies to errors in `handle` and `+server` (JSON or HTML by `Accept`).
  - **v3: rendering errors** (in component script or template) also go through `handleError` and then to the nearest boundary. A `<svelte:boundary>` is auto-created for each `+error.svelte`. Custom granular boundaries use `<svelte:boundary>{#snippet failed(error: App.Error)}`.
  - The `+error.svelte` prop is `error` (v3), or read `page.error` and `page.status`.
  - An async client `handleError` during render needs `compilerOptions.experimental.async`; otherwise the result is replaced by a generic error (`handle_error_async_without_async_svelte`).

  Source: `20-core-concepts/10-routing.md`, `30-advanced/25-errors.md`, `60-appendix/35-migrating-to-sveltekit-3.md`, `+assets/messages.json`.
- **404 / not-found handling**: Supported. Unmatched routes render the root `+error.svelte` with a 404 as `kind: 'framework'`. Nested 404 UIs need a `[...path]` route calling `error(404)` (then `kind: 'app'`). `error(404, ...)` works from load, actions, endpoints and remote functions. Source: `30-advanced/10-advanced-routing.md`.
- **Helpers**: Supported. From `@sveltejs/kit`:
  - **`error(status 400–599, message: string, extraProps?)`** throws an expected error (v3 signature; passing an object as the 2nd argument is deprecated).
  - **`redirect(status 300–308, location, { external? })`** throws.
  - **`fail(status, data)`** returns (actions only).
  - **`invalid(...issues)`** throws (remote forms).
  - `isHttpError()` and `isRedirect()` for checks. v3: these refer to public types; `instanceof` on internal classes is no longer supported.
  - No separate `notFound()`.

  Source: `30-advanced/25-errors.md`, `20-core-concepts/20-load.md`, `+assets/messages.json`.
- **Expected vs unexpected errors**: Supported. **All errors pass through `handleError`** (v3; v2 skipped expected ones) with a `kind`:

  | `kind` | Source | `error` value received | Default returned to user |
  |---|---|---|---|
  | `'app'` | `error(...)` | The `App.Error` body (safe) | Same body |
  | `'framework'` | 404, 405 (POST without actions), 413 (body too large), etc. | `{ status, message }` (safe, e.g. "Not Found") | Same |
  | `'validation'` (server only) | Remote function arg failed schema | `{ status: 400, message: 'Bad Request' }`; issues in `issues` | `error` (issues not exposed unless returned) |
  | `'unknown'` | Anything else thrown | Raw thrown value (unsafe) | `{ status: 500, message: 'Internal Error' }` |

  - The hook returns an `App.Error`-shaped object. `status` and `message` are optional overrides, so **the hook can change the HTTP status** (v3). Additional *required* `App.Error` fields must be returned.
  - Redirects never reach the hook.
  - Errors already transformed on the server aren't re-passed to the client hook.
  - In dev, Svelte syntax errors carry `frame`.
  - If the hook throws, SvelteKit responds with a generic Internal Error (`handle_error_hook_failed`).
  - `App.Error` always includes `status` and `message`. Remote resources' `.error` is typed `App.Error | undefined`.
  - The top-level `status`/`message` args of `handleError` are deprecated.
  - Parameterize `HandleServerError<Issue>` to type validation issues.

  Source: `30-advanced/20-hooks.md`, `30-advanced/25-errors.md`, `60-appendix/35-migrating-to-sveltekit-3.md`, `+assets/messages.json`.
- **Error reporting hooks**: Supported. Server and client `handleError` (Sentry example with `@sentry/sveltekit`, `captureException`). Unknown errors are logged to the console or server logs by default. Avoid logging routine framework 404s. Source: `30-advanced/20-hooks.md`, `30-advanced/25-errors.md`.
- **Notable extras**:
  - Sourcemaps are generated by default and applied to production stack traces (v3; first-party adapters still in progress).
  - Dev-only `full_reload_after_error`: failed client navigation does a full reload and pauses on `debugger` if devtools are open.
  - `hmr_reload_after_error`: the next HMR update reloads the page after an unexpected error.
  - Remote function errors render the nearest `+error.svelte`.

## 8. Type safety

- **Typed links and params**: Partial. `resolve()` is typed against `RouteId` and `Path` with param objects. `params` are typed per route, with matcher output types (number, boolean, bigint). `<a href>` is untyped. Generated `$app/types` (`RouteId`, `RouteParams<T>`, `LayoutParams<T>`, `Path`, `ResolvedPathname`, `AssetPath`). Source: `98-reference/22-$app-types.md`, `30-advanced/10-advanced-routing.md`.
- **Typed loader/server data to components**: Supported (codegen). `./$types` per route provides:
  - `PageLoad`, `PageServerLoad`, `LayoutLoad`, `LayoutServerLoad`, `RequestHandler`, `Actions`, `EntryGenerator`;
  - `PageData`, `LayoutData`, `ActionData` (union of action returns);
  - `PageProps` (`data`, `form`, `params`) and `LayoutProps` (`data`, `children`).

  Imported as siblings via `rootDirs`. **Zero-config**: the Svelte language tools and `svelte-check` inject these types automatically, so annotations can be omitted. `page.data` is typed via `App.PageData`. Source: `20-core-concepts/10-routing.md`, `98-reference/54-types.md`.
- **Typed server calls (actions / RPC / fetch)**:
  - Remote functions [EXPERIMENTAL] are end-to-end typed. The arg type is inferred from the Standard Schema (validated at runtime); `'unchecked'` gives a TS-only type. Return types are inferred. Form fields are typed from the schema. Types `RemoteQuery`, `RemoteForm`, `RemoteCommand`, `RemoteQueryFunction`, `RemoteLiveQueryFunction` and `RemoteQueryUpdate` live in `$app/server` (v3).
  - Form actions: `ActionData` is typed. `use:enhance` result typing is generic `ActionResult`.
  - `+server` `fetch` calls are untyped (no typed fetch client).

  Source: `20-core-concepts/60-remote-functions.md`, `60-appendix/35-migrating-to-sveltekit-3.md`.
- **Generated types (codegen step or inferred)**: Codegen. `svelte-kit sync` (runs as the `prepare` script and during dev/build) writes `.svelte-kit/types/**/$types.d.ts` and the tsconfig module.
  - v3: the user's `tsconfig.json` must `"extends": "$app/tsconfig"` with explicit `include`/`exclude` (`tsconfig_extends_missing`).
  - Requirements: `types` must include `"$app/types"`, `isolatedModules: true`, `verbatimModuleSyntax: true`, and `paths` must not be overridden (derived from the deprecated `alias` option plus `package.json` `imports`). Violations warn (`tsconfig_invalid`).
  - The service worker gets a separate project via `$app/tsconfig/service-worker`.
  - `typescript.config` hook is deprecated.
  - `$app/env/private` and `public` exports are typed from `src/env.ts` schemas, with descriptions on hover.

  Source: `98-reference/52-cli.md`, `98-reference/20-$app-tsconfig.md`, `20-core-concepts/70-environment-variables.md`, `+assets/messages.json`.
- **Typed search params**: Not supported (plain `URLSearchParams`; `page.url` readonly). Source: `20-core-concepts/50-state-management.md`.
- **Notable extras**:
  - `App` namespace in `src/app.d.ts`: `Error`, `Locals`, `PageData`, `PageState`, `Platform` (types `page.error`, `locals`, `page.data`, `page.state`, `platform`).
  - Adapters provide `Config` types for `export const config`.
  - The `transport` hook preserves custom class types across the boundary.
  - Typed `snapshot<T>`.

  Source: `98-reference/54-types.md`, `30-advanced/67-shallow-routing.md`, `20-core-concepts/40-page-options.md`.

## 9. Metadata & SEO

- **Head/meta management per route**: Partial (Svelte primitive). `<svelte:head>` in any page or layout component, including `<title>` and `<meta>`. There is no metadata export or merge API and no dedupe rules documented. Source: `40-best-practices/20-seo.md`.
- **Metadata from loaded data**: Supported by pattern. Return SEO fields from page `load`, then render `<svelte:head><title>{page.data.title}</title>` in the root layout. Source: `40-best-practices/20-seo.md`, `20-core-concepts/20-load.md`.
- **Sitemap / robots / manifest generation**: Not supported (manual). Sitemap via a `src/routes/sitemap.xml/+server.js` endpoint (can be prerendered). `robots.txt` goes in `static/`. No generators. Source: `40-best-practices/20-seo.md`, `10-getting-started/30-project-structure.md`.
- **Open Graph image generation**: Not found in docs.
- **Canonical, etc.**: Partial. Automatic trailing-slash normalization via redirects (`trailingSlash`) avoids duplicate URLs. Canonical tags are manual. Source: `40-best-practices/20-seo.md`.
- **Notable extras**:
  - SSR on by default.
  - The route-announcer reads `<title>` for accessibility, so unique titles are needed.
  - Per-request `<html lang>` via the `%lang%` placeholder plus `transformPageChunk` in `handle`.
  - `%sveltekit.env.PUBLIC_VAR%` in `app.html` for analytics IDs.
  - Prerender crawler checks broken `#id` links.
  - The docs say dynamic rendering (bot-specific) is possible but not recommended.

  Source: `40-best-practices/10-accessibility.md`, `20-core-concepts/70-environment-variables.md`.

## 10. Assets & styling

- **Image optimization**: Supported via the separate plugin **`@sveltejs/enhanced-img`** (`enhancedImages()` must precede `sveltekit()` in the Vite plugins). It works in any Vite project.
  - `<enhanced:img src="./img.jpg" alt>` is build-time only. Output: a `<picture>` with avif/webp plus the original format, intrinsic `width`/`height` inserted (prevents CLS), EXIF stripped. Cache: `node_modules/.cache/imagetools`.
  - Dynamic choice: `import x from './a.jpg?enhanced'` or `import.meta.glob(..., { query: { enhanced: true } })`.
  - `sizes` triggers `srcset` generation (smallest auto width 540px). Custom widths via `?w=1280;640;400`.
  - Without `sizes`, 1x and 2x variants are generated; provide 2x source images and don't upscale.
  - Per-image imagetools directives via the query string (`?blur=15`, quality, rotate, etc.).
  - SVG supported statically only. CSS selectors need `enhanced\:img`.
  - **Remote or CMS images are not handled**. Docs point to CDNs and `@unpic/svelte`, Cloudinary, or CMS image APIs.
  - `adapter-vercel` `images` config (`sizes`, `formats`, `minimumCacheTTL`, `domains`) configures Vercel image optimization (Build Output API). No first-party runtime `<Image>` component that uses it is documented.
  - Plain Vite asset imports get hashed filenames and inlining below `assetsInlineLimit`.

  Source: `40-best-practices/07-images.md`, `25-build-and-deploy/90-adapter-vercel.md`.
- **Font optimization**: Partial. No font component, subsetting or self-hosting automation. Fonts are **not preloaded by default**. Opt in via `handle` → `resolve(event, { preload: (a) => a.type === 'font' && a.filename === 'node_modules/@fontsource/...woff2' })`; `filename` is the source path (v3). Docs recommend manual subsetting. Source: `40-best-practices/05-performance.md`, `30-advanced/20-hooks.md`.
- **Third-party script loading**: Not supported as an API. Add scripts in `app.html` (with `%sveltekit.env%` and `%sveltekit.nonce%`) or `<svelte:head>`. Docs recommend Partytown's SvelteKit integration and server-side analytics. Source: `40-best-practices/05-performance.md`, `20-core-concepts/70-environment-variables.md`.
- **CSS support**: Supported.
  - Svelte component-**scoped `<style>`**.
  - `vitePreprocess({ style: true (default), script: false (default) })` enables PostCSS, SCSS, Less, Stylus and SugarSS. `script: true` is only for pre-Svelte-5 or TS features that emit code.
  - `svelte-preprocess` alternative (Pug, Babel, global styles). CoffeeScript is unsupported.
  - Tailwind via `npx sv add tailwind`.
  - CSS modules and CSS-in-JS: not found in SvelteKit docs (Vite handles `.module.css`; from memory, unverified).
  - Critical CSS: JS and CSS are preloaded per route.
  - `inlineStyleThreshold` config inlines small CSS (from memory, unverified).

  Source: `60-appendix/20-integrations.md`, `40-best-practices/06-icons.md`.
- **MDX / Markdown as pages**: Partial (add-on). `mdsvex` via `npx sv add mdsvex`, with the `extensions` option (e.g. `['.svelte', '.svx']`, multi-part like `.svelte.md` allowed) so route files can be Markdown. Not built in. Source: `60-appendix/20-integrations.md`, `+assets/messages.json [config_extension_invalid]`.
- **Notable extras**:
  - `static/` directory: served as-is, bypasses `handle`, listed in `$app/manifest.assets` and the typed `AssetPath`.
  - `asset()` helper.
  - `read()` for runtime asset reads.
  - Icons guidance: prefer Iconify CSS or Tailwind/UnoCSS over one-`.svelte`-file-per-icon libraries, which slow Vite dep optimization.
  - Video guidance.

  Source: `10-getting-started/30-project-structure.md`, `40-best-practices/06-icons.md`, `40-best-practices/05-performance.md`.

## 11. Build output & deployment

- **Output modes**:
  - Server (any SSR adapter).
  - Static export (`adapter-static`; `strict: true` by default checks that everything is prerendered or a `fallback` is set).
  - SPA (`adapter-static` `fallback`, or `router.type: 'hash'`).
  - Hybrid per route (`prerender` true/'auto' alongside SSR).

  `vite build` runs two stages: Vite builds server, client and service worker (prerendering happens here), then the adapter adapts. Build-time analysis imports route modules, so guard side effects with `building`. Missing adapter: build succeeds but isn't deployable (`adapter_missing`). Source: `25-build-and-deploy/10-building-your-app.md`, `25-build-and-deploy/50-adapter-static.md`.
- **Supported runtimes and per-route runtime choice**:

  | Adapter | Runtime / target | Key options (default) | Notes |
  |---|---|---|---|
  | `adapter-node` | Node ≥22.17 standalone server | `out` (`build`), `precompress` (`true`; br+gz), `envPrefix` (`''`) | Env vars: `PORT` (3000), `HOST` (0.0.0.0), `SOCKET_PATH`, `PROTOCOL_HEADER`/`HOST_HEADER`/`PORT_HEADER`, `ADDRESS_HEADER`/`XFF_DEPTH`, `BODY_SIZE_LIMIT` (512K; K/M/G; `Infinity`), `SHUTDOWN_TIMEOUT` (30s), `IDLE_TIMEOUT` (systemd socket activation sleep), `KEEP_ALIVE_TIMEOUT`, `HEADERS_TIMEOUT`, `LISTEN_PID`/`LISTEN_FDS`. Graceful shutdown: close → closeIdle → closeAll after timeout, emits `sveltekit:shutdown`. `handler.js` for Express/Polka/http (only the request-level env vars apply). v3: bundled with Rolldown (devDeps bundled, deps external); static files from a build-time list; content-hash ETags; non-GET/HEAD to assets gets 405; `ORIGIN` env var removed. |
  | `adapter-bun` [new] | Bun ≥1.4 (`Bun.serve`; build must run in Bun: `bun run --bun build`) | `out`, `precompress` (opt-in), `envPrefix` (unknown prefixed vars fail startup), `serverOptions` (`hostname, port, unix, reusePort, ipv6Only, idleTimeout, maxRequestBodySize, development`), `buildOptions` (`compile`, `minify`, `bytecode`, `sourcemap` default external, etc.) | **`compile: true` gives a single self-contained executable** (embeds runtime, assets, deps; cross-compile via `target`). Assets as native Bun routes with ETags/304/ranges. Env: `HOST`, `PORT`, `SOCKET_PATH`, `REUSE_PORT`, `IPV6_ONLY`, `BODY_SIZE_LIMIT`, `CONNECTION_IDLE_TIMEOUT` (0–255s), `DEVELOPMENT`, proxy headers (scheme assumed https), `ADDRESS_HEADER`/`XFF_DEPTH` (default 1), `SHUTDOWN_TIMEOUT` (second signal exits 1). `platform.server`. No WebSocket/TLS via `serverOptions`. |
  | `adapter-cloudflare` | Workers (Static Assets) and Pages | `config` (wrangler path), `platformProxy` (getPlatformProxy options for dev/preview bindings), `fallback` (`'plaintext'` \| `'spa'` 404), `routes` (Pages `_routes.json`; `include` default `['/*']`, `exclude` default `['<all>']`; special `<build> <files> <redirects> <prerendered>`; max 100 rules) | v3: bindings from `import { env, waitUntil } from 'cloudflare:workers'`, `request.cf`, global `caches` (removed from `platform`); `wrangler types`; wrangler ≥4.67. Durable Objects and Workflows (custom class exports) not supported. No `fs`; use `read()`. Single-file worker size limits. `nodejs_als`/`nodejs_compat` flags. `_headers`/`_redirects` apply only to static assets. |
  | `adapter-cloudflare-workers` [deprecated] | Workers Sites | `config`, `platformProxy` | Migrate to `adapter-cloudflare`. |
  | `adapter-netlify` | Netlify Functions (Node) or Edge Functions | `edge` (`false`), `split` (`false`), `publish` (`'build'`; v3 option rather than read from `netlify.toml`) | v3: Netlify Frameworks API output, CLI ≥17.31, edge target es2022. `platform.context` (Netlify Identity, etc.). `_headers`/`_redirects`/`[[redirects]]` for static assets. Netlify Forms need prerendered pages. |
  | `adapter-vercel` | Vercel Functions: Node (`nodejs22.x/24.x/26.x`) or Bun (`bun1.x`, `bun1.4.x`). **Edge runtime removed in v3.** | Per-route or adapter-level `config`: `runtime`, `regions` (default `['iad1']`; multi-region needs Enterprise), `split`, `memory` (1024MB; 128–3008), `maxDuration` (plan defaults 10/15/900s), `isr`; adapter `images` | ISR, bypass token, draft mode, skew protection. `api/` dir functions shadow `/api/*`. Use `@vercel/functions` for `waitUntil`. |
  | `adapter-static` | Any static host | `pages` (`build`), `assets` (= pages), `fallback` (none), `precompress` (`false`), `strict` (`true`) | Zero-config on Vercel. GitHub Pages recipe (`paths.base`, `404.html` fallback, `.nojekyll`). Set `trailingSlash: 'always'` if the host doesn't map `/a` to `a.html`. |
  | `adapter-auto` (default) | Detects Cloudflare, Netlify, Vercel, Azure SWA (community), AWS via SST (community), Google Cloud Run and Render (→ node) | none (install the concrete adapter for options) | Installs the adapter at deploy time. Pin the real adapter in devDeps. |

  - Per-route runtime: only via adapter `config` (Vercel `runtime`/`regions`/`split`/`memory`; Netlify `split` is app-level). `config` merges shallowly from layouts.
  - Deno: not found in docs, apart from a generic web-standards mention.
  - Note: `10-getting-started/25-project-types.md` and `30-adapter-auto.md` still mention an `edge` option for adapter-vercel, which contradicts the v3 migration guide (docs inconsistency).

  Source: `25-build-and-deploy/*.md`, `60-appendix/35-migrating-to-sveltekit-3.md`.
- **Adapters / presets (count, official vs community, adapter API)**: 6 official current adapters (node, bun, static, cloudflare, netlify, vercel), plus deprecated cloudflare-workers, plus `adapter-auto`. Community adapters are listed at `/packages`.

  **Adapter API** (`Adapter` object; types from `@sveltejs/kit/adapter`, from memory):
  - Required: `name`, `adapt(builder)`.
  - Optional:
    - `emulate()` → `{ platform({ config, prerender }) }` provides `event.platform` in dev, build and preview.
    - `supports.read({ config, route })` and `supports.instrumentation()`.
    - **`vite`** (v3): `getRequest`, `setResponse` (e.g. WebSockets), `plugins: { pre, post }` to augment the Vite config.
  - Builder methods: `writeClient`, `writeServer`, `writePrerendered`, `generateServerInstance()` (replaces the removed `generateManifest`), `builder.manifest`, `compress` (returns files), `createInstrumentationInitializer({ outputDirectory, environment? })` and `instrument({ entrypoint, instrumentation, initializer })`, `builder.config` (v3, no `.kit`). `mkdirp`/`rimraf` are deprecated; `createEntries` was removed.
  - Server contract: `await server.init({ env, read })`, then `server.respond(request, { getClientAddress, platform })`. The `Server` class is deprecated.
  - `@sveltejs/kit/node` `getRequest`/`setResponse` are synchronous in v3.

  Source: `25-build-and-deploy/20-adapters.md`, `25-build-and-deploy/99-writing-adapters.md`, `60-appendix/35-migrating-to-sveltekit-3.md`.
- **Config-level headers, redirects, rewrites, trailing slash, base path**:
  - Headers, redirects and rewrites: **not supported in SvelteKit config**. Implement in `handle`, `+server`, or `reroute` (internal rewrite only). Platform files `_headers`/`_redirects` cover static assets only (Cloudflare, Netlify). Proxying an external API: a catch-all `+server` or the platform's rewrites; `server.proxy` in dev.
  - Trailing slash: page option.
  - Base path: `paths.base`.

  Source: `60-appendix/10-faq.md`, `25-build-and-deploy/60-adapter-cloudflare.md`.
- **Standalone / self-contained output**: Supported. adapter-node `build/` needs `package.json` plus prod `node_modules`; devDependencies are bundled. adapter-bun `compile` produces a **single executable** with no runtime install. Docker and LXC via adapter-node. Source: `25-build-and-deploy/40-adapter-node.md`, `25-build-and-deploy/45-adapter-bun.md`.
- **Skew protection**: Supported (built in).
  - Version-skew errors cause a hard reload.
  - `version.name` (deployment version) and `version.pollInterval` (default 1h in v3) drive `updated.current`. It is also checked on server data fetches, remote calls, and focus or visibility change. Use it to prompt a reload.
  - Vercel cookie-based skew protection is supported (routes requests to the original deployment). Multiple open tabs fall back to built-in handling. Passive detection may give false negatives under Vercel skew protection; polling still works.

  Source: `25-build-and-deploy/90-adapter-vercel.md`, `60-appendix/35-migrating-to-sveltekit-3.md`.
- **SvelteKit plugin config (`sveltekit({...})` in `vite.config.js`)**: The config reference page is a generated stub. Keys below are verified from narrative docs or the message catalog unless marked:

  | Key | Values / default | Behaviour |
  |---|---|---|
  | `adapter` | adapter object (call it) | Required for deployable output (`config_invalid_adapter`). |
  | `paths.base` | `''` \| `'/sub'` | Sub-path deployment. |
  | `paths.assets` | absolute URL, no trailing `/` | CDN for build assets. Incompatible with service worker. |
  | `paths.relative` | `true` | Relative asset paths in SSR HTML. |
  | `paths.origin` [new] | origin string | Trusted self-origin (CSRF, remote calls), `url.origin` during prerender. Must be a bare http(s) origin. |
  | `csrf.trustedOrigins` [new] | `string[]` | Allowed cross-origin form and remote submitters. |
  | `csp.mode` | `'auto'` \| `'hash'` \| `'nonce'` | `'nonce'` forbids prerendering. |
  | `csp.directives` / `csp.reportOnly` | CSP directive objects | Report-only requires `report-to`/`report-uri`. |
  | `prerender.entries` | `['*']` default (from memory) \| `'*'` \| `'/path'` | Crawl starting points. |
  | `prerender.concurrency` | positive int | Parallel prerender. |
  | `prerender.crawl` | bool (from memory, unverified) | Follow links. |
  | `prerender.handleHttpError` / `handleMissingId` / `handleEntryGeneratorMismatch` / `handleInvalidUrl` / `handleUnseenRoutes` | `'fail'` \| `'warn'` \| `'ignore'` \| fn | Prerender problem handling. |
  | `router.type` | `'pathname'` (default) \| `'hash'` | Hash router equals client-only app. |
  | `router.resolution` | `'client'` (default) \| `'server'` | Route matching location. |
  | `output.bundleStrategy` | `'split'` (default) \| `'single'` \| `'inline'` | Chunking. |
  | `output.linkHeaderPreload` [new] | bool, `false` | Use `Link` headers instead of `<link>` elements. |
  | `serviceWorker.register` | bool, `true` | Auto-register (module SW). |
  | `files.routes` / `files.appTemplate` / `files.params` / `files.serviceWorker` | paths | Override locations. `files.lib` removed. `files.hooks.*` (from memory). |
  | `appDir` | `'_app'` (from memory) | Build asset dir under base; no leading/trailing `/`. |
  | `outDir` | `'.svelte-kit'` | Generated files. |
  | `version.name` / `version.pollInterval` | string / ms (default 1h) | Version detection. |
  | `tracing.server` [new top-level] | bool, `false` | Emit OTel spans. |
  | `experimental.remoteFunctions` | bool, `false` | Enable remote functions [EXPERIMENTAL]. |
  | `alias` [deprecated] | record | Use `package.json` `imports`. |
  | `typescript.config` [deprecated] | fn | Edit `tsconfig.json` instead. |
  | `embedded`, `inlineStyleThreshold`, `moduleExtensions`, `env.*` | (from memory, unverified) | Not described in this docs checkout. |
  | vite-plugin-svelte options | `compilerOptions`, `preprocess`, `extensions`, `inspector`, … | Passed through (v3 removed `vitePlugin`). |

  - Removed in v3: `files.lib`, `experimental.handleRenderingErrors`, `experimental.instrumentation`, `experimental.tracing`, `vitePlugin`, `preloadStrategy`, `prerender.origin`, `csrf.checkOrigin`.
  - Unknown keys error with "did you mean". `one_of` options default to the first listed value.
  - SvelteKit overrides some Vite options (`vite_config_overridden`).
  - Docs inconsistency: the Netlify doc still mentions a `prerender.force` option.

  Source: `60-appendix/35-migrating-to-sveltekit-3.md`, `+assets/messages.json`, `10-getting-started/30-project-structure.md`.
- **Notable extras**:
  - `vite preview` runs in Node and doesn't emulate the adapter's `platform`, except via the adapter's `emulate()`; Cloudflare emulates bindings in dev and preview.
  - Browser target: Vite `baseline-widely-available` (Chrome/Edge 111, Firefox 114, Safari 16.4). No polyfills; use `@vitejs/plugin-legacy`.
  - Library packaging via `@sveltejs/package`.

## 12. Dev tooling & observability

- **Dev server and HMR**: Supported. `vite dev` (port 5173) with Svelte HMR via vite-plugin-svelte. HMR is disabled on `csr = false` pages. After an unexpected error, the next HMR update does a full reload. The service worker is not bundled in dev. In dev the server code runs in Vite's `ssr` environment module runner (`vite_ssr_environment_not_runnable` if replaced). Source: `10-getting-started/10-introduction.md`, `20-core-concepts/40-page-options.md`, `+assets/messages.json`.
- **Error overlay**: Not documented in SvelteKit docs (Vite's overlay; from memory, unverified). Dev errors carry a `frame` code excerpt for Svelte syntax errors. Dev-only `debugger` pause before a full reload on navigation failure. Source: `30-advanced/20-hooks.md`, `+assets/messages.json`.
- **Devtools**: Partial. Svelte inspector via the vite-plugin-svelte `inspector` option passed to `sveltekit()`. Breakpoint debugging guides: VS Code JavaScript Debug Terminal or `launch.json`, `NODE_OPTIONS="--inspect"` plus Chrome or Edge Node devtools, WebStorm, Neovim. No SvelteKit-specific in-browser devtools panel. Source: `60-appendix/35-migrating-to-sveltekit-3.md`, `60-appendix/25-debugging.md`.
- **Type generation commands**: `svelte-kit sync` (auto via `prepare`, dev and build). `svelte-check` for CLI type-checking, including omitted `$types` annotations. Source: `98-reference/52-cli.md`, `20-core-concepts/10-routing.md`.
- **CLI scaffolding / generators**:
  - `npx sv create` (templates, TypeScript, library option).
  - `npx sv add <addon>`: prettier, eslint, vitest, playwright, better-auth, tailwind, drizzle, paraglide, mdsvex, storybook, `sveltekit-adapter="adapter:node|bun|static|cloudflare|netlify|vercel"`, mcp.
  - `npx sv migrate sveltekit-3` / `app-state`.
  - No route or file generators.

  Source: `10-getting-started/20-creating-a-project.md`, `60-appendix/20-integrations.md`, `60-appendix/35-migrating-to-sveltekit-3.md`.
- **AI-agent support**: Partial. `npx sv add mcp` ("LLM tooling") is listed as an add-on. No `llms.txt`, bundled docs or app-level `AGENTS.md` scaffolding appear in these docs. The repo's own `AGENTS.md`/`CLAUDE.md` is for contributors to the monorepo, not users. Source: `60-appendix/20-integrations.md`.
- **Instrumentation / OpenTelemetry**: Supported [stable in v3; since 2.31].
  - `tracing: { server: true }` emits spans for `handle` (and `sequence` children), server loads, universal loads run on the server, form actions, `+server` handlers and remote functions.
  - **`src/instrumentation.server.js`** is auto-loaded *before* app code (no flag in v3) when the adapter declares `supports.instrumentation`; otherwise the build errors (`adapter_instrumentation_unsupported`).
  - Annotate spans with `event.tracing.root` and `event.tracing.current` (`.setAttribute`).
  - `@opentelemetry/api` is an optional peer and auto-externalized (`tracing_api_missing` if absent).
  - Bundling caveats:
    - Shared chunks can evaluate app code before interceptors run.
    - Bundlers can inline instrumented modules. Fix with `ssr.external: ['lib']`; adapter-node keeps `dependencies` external.
    - Modules imported by `src/env` can't be instrumented.
  - Example uses `@opentelemetry/sdk-node`, auto-instrumentations, OTLP exporter and `import-in-the-middle/register-hooks.mjs` (sync hooks need Node 22.22.3+/24.11.1+/25.1+/26+). Jaeger quickstart.
  - Client-side tracing is not supported (server only).

  Source: `30-advanced/68-observability.md`, `25-build-and-deploy/99-writing-adapters.md`, `+assets/messages.json`.
- **Server error reporting hooks**: Supported. `handleError` (server and client) with `kind`, `event`, `error` and `issues`. Sentry example. Source: `30-advanced/20-hooks.md`.
- **Web vitals reporting**: Not found in docs. Core Web Vitals are mentioned only as guidance; Lighthouse and PageSpeed are recommended. Source: `40-best-practices/05-performance.md`.
- **Notable extras** — extensive dev-time diagnostics, documented in `+assets/messages.json`. They include:
  - `ssr_fetch_eager`, `window_fetch_in_load`, `load_tracking_after_return`, `streaming_without_csr`;
  - cookie size and path warnings, `cache-control` and `content-type` validation, `transform_page_chunk_comments`;
  - `remote_form_issues_ignored`, `form_input_missing_value`, misspelled-file detection, `invalid_export` typo guard;
  - `app_body_unwrapped`;
  - `server_only_import` with import chains (disabled under `TEST=true`).

## Out-of-scope features seen (one line each)
- Auth: guidance only (sessions vs JWT, check cookies in `handle` → `locals`). Better Auth via `sv add better-auth`. Lucia guide. (`40-best-practices/03-auth.md`)
- Databases/ORMs: Drizzle via `sv add drizzle`. DB setup in hooks or `init`. (`60-appendix/10-faq.md`)
- i18n: Paraglide add-on. `reroute` for translated slugs. `[[lang]]` optional params. `%lang%` via `transformPageChunk`.
- Testing: Vitest and Playwright add-ons. Route-colocated `*.test.*` files ignored. Server-only import checks disabled when `TEST=true`.
- Realtime/WebSockets: no built-in WebSockets. Adapter `vite.setResponse` hook "handle WebSockets here". Bun `serverOptions` doesn't expose `websocket`. `query.live` covers server→client streams.
- KV/Durable Objects/bindings: Cloudflare `env` from `cloudflare:workers`. Durable Objects and Workflows class exports unsupported.
- Packaging component libraries: `@sveltejs/package` / `svelte-package` (`30-advanced/70-packaging.md`).
- PWA/offline: `src/service-worker/index.ts` auto-bundled and registered as `type: 'module'`.
  - Typed `self` via `$app/service-worker`.
  - `$app/manifest` (`immutable`, `assets`, `prerendered`) and `version` from `$app/env` (replace the removed `$service-worker`).
  - Manual registration via `serviceWorker.register: false`.
  - Updates checked only on full navigations, or on error recovery with version change.
  - Can't import `$app/forms|navigation|state` or `match`.
- Snapshots (UI state persistence): `snapshot({ id?, capture, restore, reset? })` from `$app/navigation`.
  - Any component; devalue plus transport serialization; stored in `sessionStorage`.
  - Captured before navigation, including shallow; restored on back/forward and reload.
  - IDs derived from the stack trace unless given; duplicates error.
  - `export const snapshot` is deprecated (JSON-only, not captured on shallow navigations).
