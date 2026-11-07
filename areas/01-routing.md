# 1. Routing

**Versions:** Void 1.6.2 · Next.js 16.4 (App Router) · React Router 8 (framework mode) · TanStack Start 1.169 (React) · Nuxt 5.0 pre-release (4.x is stable) · SvelteKit 3.1 · SolidStart 2.0 · Astro 7.4

**Markers:** [exp] experimental, unstable or canary · [CC] Next.js with Cache Components on (the create-next-app default) · [N5] new or changed in Nuxt 5 · (unverified) not confirmed in docs or source

**Paths:** Void file paths are in the `voidzero-dev/void` repo. Short paths such as `pages/scan.ts` are under `packages/void/src/`; paths that start with a package name, such as `react/src/…`, are under `packages/`.

## At a glance

- **Model.** Void routing is file-based only. Two trees (`routes/` for HTTP handlers, `pages/` for UI) share one filename parser. Pages mode follows the Inertia pattern: every client navigation is a server round-trip for the page's JSON object, unless it is served from the prefetch cache or from `/_void/pages/*.json` in static output. That covers search-param-only changes and back/forward too. As a result, guards, redirects and rewrites live in server middleware and loaders, and there is no client-side route middleware.
- **Strengths.** One `Link` and router API is shared across React, Vue, Svelte and Solid. Prefetch has 4 triggers, combinable arrays, a per-link TTL with a stale-while-revalidate pair, code + data loading, and a skip when the browser reports Save-Data or a 2G connection. Other strengths: built-in active-link marking (a link with a query must match those params) and `data-void-pending` while that destination loads, view transitions in all four adapters, automatic window scroll restoration that survives reload, in-place actions that keep scroll, typed URL building (`routeUrl`, `RouteDestination`, opt-in `typedRoutes`), named layouts with innermost/whole-chain replacement, `.dev`/`.prod` environment-only routes, an abort-safe navigation engine that never lets a stale visit commit, and non-GET `Link`s.
- **Table-stakes gaps (6–7 of 7 others):**
  - **base path** (7/7);
  - **layout-level data loading** (7/7; layouts get only `useShared()` from middleware; cross-listed with Area 3);
  - **current-route introspection** (6/7 plus Next.js partial: no route id, pattern or matches API);
  - **navigation lifecycle hooks** (6/7: only `useNavigation()` state exists).
- **Common gaps (3–5):**
  - Segments and layouts: optional segments, zero-length catch-all, param matchers, partial-segment params, layout escape/reset.
  - Navigation behavior: blocking that covers back/forward and programmatic navigation, history `state`, modal routes (intercept/mask/shallow), URL/search updates that skip the loader.
  - Prefetch: code-only prefetch.
  - Accessibility and view transitions: a route announcer with focus management, and view-transition types/direction.
  - URL handling: a trailing-slash policy, hash/memory routing, programmatic route injection, route metadata, a search-param setter, and client URL rewriting.
- **Differentiators Void lacks:** parallel routes, typed and validated search params (TanStack), lazy route discovery (React Router, SvelteKit), element-level scroll restoration (TanStack), and keep-alive of departed pages (Next.js [CC], Nuxt).
- **Adapter differences inside Void:**
  - `preserveState` is honored only by Vue, which remounts the page on every GET navigation (query-only changes included) unless it is set, and by Solid, which re-creates the page on GET navigation and on param change.
  - React and Svelte ignore `preserveState`. The same page component keeps its instance by reconciliation, and there is no remount key (no `preserveState` reference in `react/src/runtime/pages-client.ts` or in `svelte/src/plugin-pages.ts` `applyUpdate`).
  - `resolveOn` exists only in React.
  - All four adapters stream deferred props over NDJSON during client navigation. SSR streaming is React-only (Area 2).

## Gap list for this area

| Gap in Void | Who has it (mechanism, briefly) | Prevalence | Notes for design (constraints, dependencies, adapter impact) |
|---|---|---|---|
| Base path | Next.js `basePath`; React Router `basename`; TanStack `basepath`; Nuxt `app.baseURL`; SvelteKit `paths.base`; Solid `<Router base>`; Astro `base` | Table stakes (7) | Touches Link rendering, active matching, `routeUrl` types, prefetch/static JSON URLs, Hono registration, redirects/rewrites, `_redirects`; same in all adapters (core) |
| Layout-level data loading | Next.js (server-component layouts); React Router/TanStack/Solid layout route loaders; SvelteKit `+layout(.server).js`; Nuxt composables in layouts; Astro frontmatter | Table stakes (7) | Cross-listed with Area 3. Needs page-object protocol changes (per-layout props), a prefetch cache shape change, and a layout-props API in all 4 adapters |
| Current-route introspection (route id/pattern, matched chain) | React Router `useMatches`; TanStack `useMatch*`; Nuxt `useRoute`; SvelteKit `page.route.id`; Solid `useCurrentMatches`; Astro `routePattern`; Next.js partial | Table stakes (6, +Next.js partial) | Page id and pattern are already known client-side (manifest + page object); expose them via `useRouter()` in all adapters |
| Navigation lifecycle hooks (before/after navigate, router events) | SvelteKit `before/on/afterNavigate`; TanStack `router.subscribe`; Nuxt `afterEach` + hooks; Solid `useBeforeLeave`; Astro `astro:*` events; Next.js `onRouterTransitionStart` | Table stakes (6) | Add to the core router (`createVoidRouter`) with adapter wrappers; must cover popstate and non-GET visits |
| Router-level navigation blocking (programmatic + back/forward), tab-close prompt | React Router `useBlocker`/`useBeforeUnload`; TanStack `useBlocker`; Nuxt guards; SvelteKit `beforeNavigate.cancel()` (+`leave`); Solid `useBeforeLeave` | Common (5) | Blocking popstate requires history re-push; Next.js matches Void's link-only level |
| Optional segments | React Router `:x?`; TanStack `{-$x}`; Nuxt/SvelteKit/Solid `[[x]]` | Common (5) | Parser (`router/parse-filename.ts`), client regex matcher, Hono patterns, `routeUrl` types; i18n use case |
| History `state` per entry | React Router, TanStack, SvelteKit (`page.state`), Solid, Astro | Common (5) | `history.state` already carries `__voidScrollKey`; merge user state; expose read API per adapter |
| Code-only prefetch | SvelteKit `preload-code`; TanStack `loadRouteChunk`; Solid `usePreloadRoute`; Next.js `auto`; Nuxt (code + payload only for prerendered) | Common (5) | New strategy flag (e.g. `prefetch={{ data: false }}`); components already loadable separately |
| Programmatic route definition / injection | React Router config; TanStack code/virtual; Nuxt `pages:extend`/`extendPages`/`addRoute`; Solid config; Astro `injectRoute` | Common (5) | Needed for Void plugins to contribute pages; must feed codegen (typed routes) and the eager manifest |
| Param types inferred from the component file, and typed `c.req.param()` without a cast | React Router `+types`; TanStack inferred; SvelteKit `$types` | Common (3) | `useParams<'/users/:id'>()` and `PageParams<'/posts/:slug'>` shipped (`codegen/route-types.ts`). A wrong pattern or param name is a type error. The pattern is not inferred from the file, and `c.req.param()` still needs `as PageParams<…>`. Next.js and Nuxt also require a route literal. |
| Zero-length / optional catch-all | Next.js `[[...x]]`; SvelteKit `[...rest]`; Solid `*`; Astro `[...rest]` | Common (4) | Pattern `:p{.+}` → allow empty; decide the param value (`''` vs `undefined`) |
| Param matchers affecting matching | SvelteKit `[id=matcher]`; TanStack `params.parse`; Nuxt regex path / `validate`; Solid `matchFilters` | Common (4) | Must run identically in the client matcher and Hono; Standard Schema reuse from `withValidator` |
| Partial-segment params (`post-[id]`, `[a]-[b]`) | SvelteKit, TanStack, Nuxt, Astro | Common (4) | Parser + regex generation |
| Modal routes: intercept / mask / shallow | Next.js intercepting; React Router & TanStack `mask`; SvelteKit shallow routing | Common (4) | Shallow + state fits the Inertia model (`prefetch()` already returns the page object) |
| Layout escape/reset to an ancestor | SvelteKit `@`; React Router & TanStack `_` suffix; Solid `name(group)` | Common (4) | Void has `'!name'`/`false` only; extend `layout-resolution.ts` |
| URL/search changes without a full loader re-run | React Router `shouldRevalidate`; TanStack `loaderDeps`; SvelteKit per-key tracking + shallow; Next.js native `pushState` | Common (4) | Today every query change refetches and (Vue) remounts; needs a client-only URL-state API or loader dependency declaration |
| Client route guards/middleware | Nuxt route middleware; TanStack `beforeLoad`; React Router `clientMiddleware`; SvelteKit universal `load` | Common (4) | Server middleware already runs per navigation except prefetch-cache and static-output hits; a client guard mainly matters for static output |
| Route announcer + focus management | Next.js, SvelteKit, Astro built in; Nuxt opt-in component | Common (4) | Core + all adapters; accessibility |
| View-transition types / direction | Next.js `transitionTypes`; TanStack `types`; Nuxt `types/toTypes/fromTypes`; Astro direction-aware animations | Common (4) | Pass `types` to `startViewTransition({ types })`; popstate direction |
| Trailing-slash policy option | Next.js, TanStack, SvelteKit, Astro (Nuxt partial) | Common (4) | Today a fixed 301 for Pages only; interacts with base path, static output file layout and active-link matching |
| Hash / memory routing | Nuxt `hashMode`; SvelteKit hash router; TanStack history types; Solid `HashRouter`/`MemoryRouter` | Common (4) | Needs Pages mode without a server (static JSON already exists) |
| Static route metadata (handle/staticData/meta) | React Router `handle`; TanStack `staticData`; Nuxt page meta; Solid `info` | Common (4) | AST-extracted static export like `layout`; pairs with the introspection gap |
| Custom restoration key | React Router `getKey`; TanStack `getScrollRestorationKey`; Nuxt `scrollBehavior` | Common (3) | `scroll-restoration.ts` keys per entry today |
| Search-param setter (merge/updater) | React Router `setSearchParams`; TanStack `search: prev => next`; Solid `setParams` | Common (3) | Build on `mergeDataIntoHref` |
| Client URL rewrite/reroute | SvelteKit `reroute`; TanStack `rewrite`; Solid `transformUrl` | Common (3) | Would fix the documented rewrite vs `Link` mismatch |
| `beforeunload` integration | React Router, TanStack, SvelteKit | Common (3) | Part of blocking API |
| Remount-key hook (consistent across adapters) | Next.js `template`; TanStack `remountDeps`; Nuxt `key` | Common (3) | React/Svelte ignore `preserveState`; Vue remounts by default; unify semantics |
| Documented custom-link builder | TanStack `createLink`; Nuxt `defineNuxtLink`; React Router `useLinkClickHandler` | Common (3) | `void/pages-client` helpers exist but are undocumented |
| Relative links under typed routes | React Router `relative`; TanStack `from`; Solid `<A>` | Common (3) | `typedRoutes` currently rejects `../x` |
| Plain `<a>` client navigation | SvelteKit; Solid; Astro ClientRouter | Common (3) | Design choice; matters for Markdown/CMS HTML in Pages mode |
| Parallel routes / named outlets | Next.js `@slot` (stable); Nuxt named views | Differentiator (2) | One page component per URL today; large protocol change |
| Lazy route discovery / server route resolution | React Router `routeDiscovery`; SvelteKit `router.resolution: 'server'` | Differentiator (2) | Manifest grows with page count (`pages/manifest.ts` comment) |
| Keep-alive of departed pages | Next.js [CC] Activity; Nuxt `keepalive` | Differentiator (2) | Adapter-specific (React Activity, Vue KeepAlive) |
| Built-in reduced-motion for transitions | Nuxt, Astro | Differentiator (2) | — |
| Case-sensitivity option | TanStack `caseSensitive`; Nuxt `sensitive` | Differentiator (2) | Hono + client regex flag |
| Speculation Rules prefetch/prerender | Nuxt [exp]; Astro [exp] | Differentiator (2, experimental only) | — |
| URL mask | React Router, TanStack | Differentiator (2) | See modal routes |
| Typed + validated search params | TanStack `validateSearch` + middlewares | Differentiator (1) | Server `withValidator({ query })` could be reused client-side |
| Element/container scroll restoration | TanStack `useElementScrollRestoration` | Differentiator (1) | — |

## Where Void is ahead

- **One router API across four UI libraries**: `Link`, `useRouter`, `useNavigation`, prefetch, active links, view transitions and scroll restoration are identical in React, Vue, Svelte and Solid. The nearest competitor is TanStack Router, which covers two UI libraries (React and Solid). Astro's ClientRouter works with any UI library, but it swaps whole HTML documents.
- **Prefetch control:** four triggers, combinable arrays (first wins), per-link `cacheFor` with a `[fresh, expire]` stale-while-revalidate pair and single-use `0`, an app-wide `defaultStrategy`/`hoverDelay`/`cacheFor`, an awaitable `router.prefetch()` that returns the page object, and `flush`/`flushAll`. No other framework has a per-link TTL. `Link` prefetch also skips Save-Data and 2G connections, and a `visible` link waits 300 ms in view. `router.prefetch()` is not connection-gated.
- **Non-GET `Link`** (`method` + `data` renders a button that performs an action visit), and `router.visit` doubles as a typed mutation client with multipart detection.
- **Built-in active-link marking** with `aria-current` and `data-void-active`, exact or prefix, consistent with server matching. A link that sets a query is active only when the current URL has each of those params. Next.js, SvelteKit and Astro have nothing built in. **`data-void-pending`** marks every link to the destination that is loading (path, query, hash and method).
- **Navigation engine robustness:** AbortController-based cancellation, monotonic visit ids so stale visits never commit, transparent same-origin redirect following, a full-load fallback for non-Void responses, deferred props streamed over NDJSON during client navigation in all four adapters, rollback if the history write fails, unsafe schemes rejected (Next.js lets `javascript:` execute), and `capacitor:` support.
- **Scroll restoration out of the box,** including across reloads (sessionStorage) and new fragment entries, with no component to mount (React Router needs `<ScrollRestoration>`, TanStack needs `scrollRestoration: true`).
- **Named layouts with chain semantics** (`'name'` replaces the innermost layout, `'!name'` replaces all, `false` removes all). These are selected statically and validated at build time (a missing name fails the build).
- **Environment-only routes and pages** (`.dev`/`.prod`), with dev-only resources excluded from deploys. No competitor has a filename convention for this.
- **Typed URL building over pages, HTTP and WebSocket routes together** (`routeUrl`, `RouteDestination` accepted by `visit`/`prefetch`/`flush`/`c.rewrite()`), plus `typedRoutes` string checking that accepts query/hash suffixes, same-page `?x`/`#x`, `mailto:` and `tel:`.
- **React `resolveOn: 'data' | 'commit'`** gives explicit control over when an awaited navigation resolves inside Actions/transitions. No competitor documents an equivalent.
- **Static output keeps SPA navigation** through prebuilt `/_void/pages/*.json` page objects (fast path when no redirects/rewrites/fallbacks exist).

## Route definition model, file conventions and route manifests

| Framework | Definition model | Route files and special files | Ignore / colocation | Programmatic routes / manifest tooling |
|---|---|---|---|---|
| **Void** | File-based only | `pages/`: `.tsx .jsx .vue .svelte .md` pages, `<page>.server.{ts,tsx,js,jsx,mts,mjs}` companion (loader/actions/`ssr`/`prerender`/`revalidate`), `layout.*`, `_layouts/<name>.*`, `*.island.*`. `routes/`: method-export handlers (`GET POST PUT PATCH DELETE OPTIONS`; `HEAD` export = build error; no exports → `app.all(default)`). `.dev`/`.prod` suffix = environment-only route. `sourceDir` moves all trees | `_`-prefixed segment ignored (except `_layouts`); in `routes/`, `.`-segments ignored except `.well-known` | None: no config routes, no plugin `injectRoute`/`addRoute` (grepped `packages/void/src`). `void gen route` scaffolds files. The client route table is generated and **shipped eagerly in the client entry** ("grows with every page", `pages/manifest.ts`). `X-Void-Routing` dev header explains rewrite matches |
| **Next.js** | File-based only (`app/`) | `page`, `layout`, `template`, `loading`, `error`, `global-error`, `not-found`, `route`, `default`; [exp] `global-not-found`, `forbidden`/`unauthorized`, `route.go` | Non-special files are never routed; `_folder` private; `%5F` escape | None (only config `rewrites` or a custom server) |
| **React Router** | **Config-first**: required `app/routes.ts` (`route`, `index`, `layout`, `prefix`, `relative`; `{ id }` option); opt-in fs `flatRoutes()` mixable | Required `root.tsx`; route module exports (`loader`, `action`, `middleware`, `clientLoader`, `handle`, …) | fs-routes: `folder/route.tsx` + colocated files, `ignoredRouteFiles` | `react-router routes [--json]` prints the tree |
| **TanStack Start** | File-based default, plus code-based and "virtual file routes" (mixable) | `__root.tsx`, `createFileRoute(path)` (path auto-maintained), generated `routeTree.gen.ts`, `*.lazy.tsx` | `-` prefix (`routeFileIgnorePrefix`), `routeFileIgnorePattern`; tokens `routeToken`/`indexToken` configurable | Virtual routes API (`rootRoute`, `route`, `index`, `layout`, `physical`); generator options |
| **Nuxt** | File-based + code/config | `app/pages/*.vue` (`.vue .js .jsx .mjs .ts .tsx`), `name@view.vue`, `*.client.vue`, `*.server.vue`; `definePageMeta` | `-` prefix (`ignorePrefix`), `ignore` globs; layers add page dirs | `router.options.ts routes()`, `pages:extend`/`pages:resolved` hooks, Kit `extendPages()`, runtime `router.addRoute()` |
| **SvelteKit** | File-based only (directories) | `+page.svelte`, `+page(.server).js`, `+layout*`, `+error.svelte`, `+server.js`; strict validation (`route_file_reserved`, `invalid_export`, misspelling warnings) | Non-`+` files ignored; `.test/.spec/.stories` ignored | None; `reroute` hook remaps URL → route |
| **SolidStart** | File (`FileRoutes`) + code (JSX `<Route>` or config arrays) | Default export = page; `export const route = { preload }`; method exports = API route; `.mdx` pages | Not documented beyond `(group)` | Config/JSX routes; `FileRoutes` returns a plain route-config array |
| **Astro** | File-based + integration injection | `src/pages/*.astro .md .mdx .html`, `.js/.ts` endpoints; `getStaticPaths` | `_` prefix excluded | `injectRoute({ pattern, entrypoint, prerender })` (integrations); `src/fetch.ts` can wrap the pipeline |

**Behavioral differences that matter**
- Void, Next.js and SvelteKit have **no programmatic route injection**. Nuxt (`pages:extend`, `extendPages`), Astro (`injectRoute`), React Router (code config), TanStack (virtual/code routes) and Solid (config routes) let code or integrations add routes. This matters if Void plugins (auth, admin, docs) are to contribute pages.
- Void puts **UI and server code in separate files** (`x.tsx` + `x.server.ts`). React Router, TanStack and Solid colocate them in one route module and strip server exports. SvelteKit separates them the way Void does (`+page.svelte` / `+page.server.js`).
- Void validates route files lightly compared with SvelteKit (reserved `+` names, invalid exports, misspellings, `route_conflict`). Duplicate routes or duplicate page ids are build errors. Fully shadowed dynamic pages only warn. Exporting `HEAD` is an error. Unknown exports are not rejected.

**Void gap:** partial. Missing: a programmatic route definition or injection API for plugins (5/7 have one), a route-tree inspection CLI, and configurable ignore/route tokens (TanStack, Nuxt).

## Route matching and ranking

| Framework | Ranking rules | Conflict handling |
|---|---|---|
| **Void** (`pages/`, `routes/`, WebSocket routes) | One shared comparator (`router/route-order.ts` `compareRouteSpecificity`): catch-all routes last, fully static routes first, then the first differing segment decides (static, then `[param]`, then catch-all); parameter names never decide. The client matcher uses an exact map for the static prefix, then regexes in this order (`pages/manifest.ts`) | Same pattern or same page id → build error. Identical-regex dynamic pages (`[id]` vs `[slug]`) → warning "is never used". **Partial overlaps are silent** |
| **Next.js** | Static > dynamic > catch-all > optional catch-all (from memory, unverified; not in inventory) | Groups resolving to the same URL → error; `page` + `route` in one segment → error |
| **React Router** | Optional segments match eagerly (`/x` matches `/:lang` before `/:productId`); full ranking algorithm not in inventory. [exp] `unstable_routePatternMatching` (data mode only) | — |
| **TanStack Start** | Automatic, independent of definition order: index → static (most specific first) → dynamic (longest → shortest) → splat; optional ranks below exact. `params.priority` orders competing `params.parse` candidates | Experimental: `params.parse` returning `false` skips to the next candidate |
| **Nuxt** | vue-router ranking; documented quirk: a named parent `foo.vue` beats `foo/[slug].vue` for `/foo/hello` | `validate()` returning `false` → try other matches → 404 |
| **SvelteKit** | Fewer params wins → matcher params beat plain → optional/rest lowest when final → alphabetical | Overlapping pathnames (`/(a)/about` vs `/(b)/about`) → build error `route_conflict` |
| **SolidStart** | Not documented in inventory | Code routing: `matchFilters` failure → next route |
| **Astro** | Reserved routes → more segments → static > dynamic → named > rest → prerendered > on-demand → endpoints > pages → file > redirects → alphabetical | `prerenderConflictBehavior: 'error' \| 'warn' \| 'ignore'` |

**Behavioral differences that matter**
- Every framework with documented rules (SvelteKit, TanStack, Astro and Void) ranks **per segment**: at the first segment where two routes differ, a static segment beats a parameter. Void uses one comparator for pages, HTTP routes and WebSocket routes.
- Server and client use the same page order in Void (one source list), so at least the two sides never disagree.

**Void gap:** partial. Missing: detection of partially overlapping dynamic pages (SvelteKit-style `route_conflict`).

## Nested layouts (state persistence, opt-out/reset, named layouts, layout data)

| Framework | Layout mechanism | Persists across navigation | Layout data | Opt-out / reset / escape | Named / selectable layouts | Remount control |
|---|---|---|---|---|---|---|
| **Void** | `layout.{tsx,jsx,vue,svelte}` per directory: root + one per ancestor directory, innermost last; children via `children`/snippet or Vue default slot | Yes, all adapters (no key on layouts) | **No loader or companion.** Only `useShared()`, fed by middleware `c.set('shared', …)` on every page response | `export const layout = false` (no layouts); `'!name'` replaces the whole chain with one named layout. No "inherit from ancestor X" | `_layouts/<name>.*` (closest ancestor dir; static literal; missing name = build error; Markdown via frontmatter `layout:`). `'name'` replaces the **innermost** layout and keeps outer ones | Per-visit `preserveState` (Vue/Solid only). Vue remounts the page on every GET navigation by default; Solid re-creates it on GET/param change; React/Svelte keep same-component instances |
| **Next.js** | `layout.js` per segment (root layout required; multiple root layouts via groups) | Yes, and layouts do not re-render. [CC] `<Activity>` keeps recently left routes mounted but hidden | Layouts are Server Components that fetch their own data (no `searchParams`) | Route groups / multiple root layouts; crossing root layouts = full reload | — | `template.js` remounts when its own segment or params change |
| **React Router** | Route modules + `<Outlet context>` | Yes | Per-layout `loader`/`clientLoader`; parent loaders re-run each navigation by default (`shouldRevalidate`) | fs-routes trailing `_` (`concerts_.mine.tsx`) escapes nesting | — | — |
| **TanStack Start** | Any parent route; `<Outlet/>`; root `shellComponent` | Yes (not remounted by default) | `loader`, `beforeLoad`, context, search validation per layout | `name_` suffix "break-out" route | — | `remountDeps` / `defaultRemountDeps`; `onEnter`/`onStay`/`onLeave` |
| **Nuxt** | Two mechanisms: nested routes (`<NuxtPage>`) and `layouts/` (one per page, no automatic nesting) | Yes; optional `keepalive` per page | Layouts can call data composables | `layout: false`; `appLayout` route rule (v4.3) | `definePageMeta({ layout: name \| false \| Ref \| { name, props } })`, `<NuxtLayout name fallback>`, `setPageLayout()`; layout props typed | `key` page meta / `<NuxtPage :pageKey>` |
| **SvelteKit** | `+layout.svelte` per directory | Yes (only `data` updates; `onMount` does not re-run) | `+layout.js` / `+layout.server.js` `load` | `+page@[id].svelte`, `+page@(app).svelte`, `+page@.svelte`, `+layout@.svelte` choose which ancestor to inherit | — | `{#key}`; `snapshot` export for ephemeral DOM state |
| **SolidStart** | `blog.tsx` beside `blog/` wraps it; `<Router root>` | Yes (same-path routes reuse the instance) | Layout routes can export `route = { preload }` | `users(details)/` escapes `users.tsx` | — | Keyed `<Show>` |
| **Astro** | Component composition (`<slot/>`), MD `layout` frontmatter | **No**: full document render per navigation. With `<ClientRouter/>`, the `<body>` is swapped; only `transition:persist` elements/islands survive | Layout components fetch in frontmatter (server) | n/a | MD/MDX `layout` frontmatter | n/a |

**Behavioral differences that matter**
- Void layouts persist like everyone else's (except Astro), but they **cannot load data**. In Next.js, React Router, TanStack, SvelteKit, Solid, Nuxt and Astro a layout can fetch its own data. Void layout data must come from global middleware, which runs for every request, and there is no per-subtree data. Design note: this ties to Area 3. Adding layout loaders changes the page-object protocol (`props` would need per-layout slots) and the prefetch cache shape.
- Void's **named layouts** with innermost vs whole-chain replacement have no direct equivalent. Nuxt has named layouts but no directory nesting; SvelteKit's `@` reset is the closest. Void cannot say "skip the `docs/` layout but keep root" without defining a named layout that re-implements the root.
- **Remount semantics differ by adapter.** In Vue, a GET navigation to the same page with a different query string remounts the page (losing local state) unless `preserveState` is passed. In React it never remounts. Other frameworks give one explicit rule plus a key hook (`template.js`, `remountDeps`, `key`).
- Void has no keep-alive of departed pages (Next.js [CC] Activity, Nuxt `keepalive`).

**Void gap:** partial. Missing:
- layout loaders/companions (7/7);
- a layout escape/reset to an arbitrary ancestor (SvelteKit `@`, React Router/TanStack `_` suffix, Solid `(name)`: 4/7);
- a remount-key hook that behaves the same across adapters (Next.js `template`, TanStack `remountDeps`, Nuxt `key`: 3/7);
- keep-alive (2/7).

## Dynamic, optional and catch-all segments; param matchers

| Framework | Dynamic | Optional segment | Catch-all (zero segments? value type) | Optional catch-all | Partial-segment params | Param matching / validation | Escaping special chars |
|---|---|---|---|---|---|---|---|
| **Void** | `[id]` → `:id` | **No** (`[[x]]` is not parsed; grepped parser and pages) | `[...p]` → `:p{.+}`, **≥1 char**, string `"a/b"`; bare `[...]` → unnamed `*` | No | **No**: a segment is a param only if the whole segment is `[x]`, so `post-[id]` stays literal | None in matching. `defineHandler.withValidator({ params })` validates **after** the match and fails with 400 JSON (no fall-through, no 404) | No |
| **Next.js** | `[slug]` (Promise `params`) | No single optional | `[...slug]` → `string[]` | `[[...slug]]` → `undefined` at root | No | No; `next/root-params` getters (16.3) for params above the root layout | `%5F` for leading `_` |
| **React Router** | `:id` / `$id` | `:lang?`, also static `edit?`; fs `($lang)` | `*` / `$` → `params["*"]` | — | — | None stable ([exp] route-pattern matcher, data mode) | fs `[...]` escapes (`sitemap[.]xml`) |
| **TanStack Start** | `$id` | `{-$id}` | `$` → `_splat` | — | `pre{$id}suf`, `{$file}[.]txt`, with splats | `params.parse`/`stringify` (throw = error state; [exp] `false` = skip route), `params.priority`, `pathParamsAllowedCharacters` | `[x]` |
| **Nuxt** | `[id]` | `[[slug]]` | `[...slug]` → array | Not documented | `users-[group]` | `definePageMeta({ path: '/:id(\\d+)' })` regex; `validate(route)` → `false` falls through to 404, or an error object | — |
| **SvelteKit** | `[param]`, multiple per segment (`[a]-[b]`) | `[[lang]]` (two routes; can conflict) | `[...rest]` matches **zero or more**, string | Built in (rest is optional) | `foo-[c]` | `[id=matcher]` from `src/params.ts` `defineParams` (function or Standard Schema; sync; transforms and types the value, e.g. `number`); failure → next route → 404 | `[x+2e]`, `[u+nnnn]` |
| **SolidStart** | `[id]` / `:id` | `[[id]]` / `:id?` (last segment only) | `[...slug]` / `*slug`; `/users/*` matches `/users` | Effectively (zero-segment) | — | `matchFilters` (array / RegExp / predicate) on code routes only | — |
| **Astro** | `[param]` (`getStaticPaths` for static) | No (rest may be `undefined`) | `[...rest]` any depth, may be `undefined` | Effectively | `[lang]-[version]` | None (static: `getStaticPaths`) | — |

**Behavioral differences that matter**
- Void cannot express `/:lang?/docs`, `/files/[...path]` that also matches `/files`, or `/v[version]`. These are the common i18n and versioned-docs patterns. TanStack documents `{-$locale}` for i18n.
- Matchers in SvelteKit, TanStack and Nuxt **affect matching** (fall through to the next route) and in SvelteKit/TanStack also **type and transform** the param. Void validates params only after matching, and a failure is a 400 rather than "try the next route" or a 404.
- Void's typed URL helpers encode catch-all values keeping `/` (`routeUrl('/files/:path{.+}', …)`). SvelteKit `resolve()` throws for params with leading/trailing `/`.

**Void gap:** missing:
- optional segments (5/7);
- zero-length or optional catch-all (4/7);
- param matchers that take part in matching (4/7);
- partial-segment params (4/7);
- a filename escape syntax (3/7).

Design note: optional segments double the route patterns that the eager client manifest and `routeUrl` types carry. Matchers must run identically in the client regex matcher (`pages/manifest.ts`) and in Hono.

## Route groups and pathless layouts

| Framework | Groups | Pathless layout | Extras |
|---|---|---|---|
| **Void** | `(group)/` stripped from URLs in both trees | **Works but undocumented**: `(group)/layout.tsx` wraps only that group, because the layout chain follows file directories (`pages/layout-resolution.ts`) | No group metadata; no multiple-root-layout concept (a root `pages/layout.*` wraps everything unless `layout = false` or `'!name'`) |
| **Next.js** | `(folder)` | Yes (group layout) | Multiple root layouts (`/` must live in a group); crossing them = full reload |
| **React Router** | `layout()` / `prefix()` / fs `_leading` | Yes | `prefix()` adds a path prefix without a route |
| **TanStack Start** | `(folder)` | `_pathless.tsx` (can attach middleware in server routes) | Relative nav from pathless resolves from the parent |
| **Nuxt** | `(group)/` | Partial (needs a parent page or `appLayout` rule) | `route.meta.groups` (v4.3) |
| **SvelteKit** | `(group)` | Yes | `@(group)` layout reset target |
| **SolidStart** | `(folder)` | `<Route component>` without `path` | `name(group).tsx` sibling layout trees |
| **Astro** | **No** | No | `_` folders are excluded, not grouped |

**Void gap:** none functionally (6/7 have groups; Void matches). Documenting group layouts and exposing group membership (Nuxt `meta.groups`) would close the remaining distance.

## Parallel routes, intercepting/modal routes, URL masking and shallow routing

| Framework | Parallel / named outlets | Intercepting / modal | URL masking | Shallow routing (URL/history without navigation) |
|---|---|---|---|---|
| **Void** | No | No | No | No. `history.state` holds only `__voidScrollKey`. A manual `pushState` is unknown to the router, and popstate to such an entry triggers a server fetch |
| **Next.js** | `@slot` folders, `default.js`, per-slot `loading`/`error`, soft vs hard navigation semantics | `(.)` `(..)` `(..)(..)` `(...)`; relies on the `next-url` header (CDN must forward it); not with static export | — | Native `history.pushState/replaceState` sync with `usePathname`/`useSearchParams` |
| **React Router** | No | Via masking | `<Link mask>` / `useLinkClickHandler({ mask })`; `history.state` based; SSR ignores it | — |
| **TanStack Start** | No (stub page) | Via masking | `mask` on Link/navigate or `routeMasks` + `createRouteMask({ unmaskOnReload })` | — |
| **Nuxt** | Named views `child@sidebar.vue` → `<NuxtPage name>` (v4.5); meta only from the default file | Not documented | — | — |
| **SvelteKit** | No | Via shallow routing | — | `goto(url, { shallow: true, state })` + `preloadData()` → render the target `+page` inside a modal from `page.state`; reload lands on the real URL |
| **SolidStart** | No | No | — | — |
| **Astro** | No (page partials, server islands) | No | — | — |

**Behavioral differences that matter**
- Four frameworks offer a deep-linkable modal pattern: Next.js (file-convention interception), React Router and TanStack (masking), and SvelteKit (shallow). They differ on reload: Next.js shows the full page, TanStack keeps the mask by default, React Router/SvelteKit land on the real URL. Void apps today need a client-only modal plus manual `history.pushState`, which the Void router will then treat as a full navigation on back.

**Void gap:** missing:
- one of: intercept, mask, or shallow-with-state (4/7);
- parallel routes / named outlets (Next.js stable; Nuxt named views: 2/7).

Design note: Void's server-driven model (one page object per URL) fits SvelteKit's shallow routing best: `router.prefetch()` already returns the target page object, so `visit(url, { shallow: true, state })` plus a typed `page.state` is a small extension. Masking would also need SSR to ignore the mask.

## Link component

Normalized by capability. Cells give each framework's mechanism; "—" means not available.

| Capability | Void | Next.js | React Router | TanStack Start | Nuxt | SvelteKit | SolidStart | Astro |
|---|---|---|---|---|---|---|---|---|
| Component | `Link` in all 4 adapters (`<a>` for GET, `<button type="button">` for non-GET; sets `touch-action: manipulation`) | `next/link` | `Link`, `NavLink` | `Link` | `<NuxtLink>` | none (plain `<a>`) | `<A>` ("will be deprecated" for native `<a>`) | none (plain `<a>`) |
| Plain `<a>` gets client navigation | **No**: full document load (no global click delegation) | No | No | No | Not documented | **Yes** (every `<a>`) | **Yes** (router delegates; `explicitLinks` limits it to `link`-attr anchors) | Yes with `<ClientRouter/>` |
| Destination forms | String `Href` only (build with `routeUrl()`; destination objects only on `router.*`) | string or URL object | string or `{pathname, search, hash}` | `to` + `params` / `search` / `hash` (value, updater fn or `true`) | string or route object | string | string (relative resolved) | string |
| Relative paths | Resolved like `<a>` at runtime; `typedRoutes` **rejects** `../x` | — | `relative="route" \| "path"` | `from` + `.`/`..` | — | native | yes | native |
| Query from object | `data={…}`: arrays → repeated keys, Date → ISO, `null`/`undefined` omitted, nested objects throw | URL object `query` | — | `search` (JSON-first serializer, validated) | `to.query` | — | — | — |
| Replace history | `replace` | `replace` | `replace` | `replace` | `replace` | `data-sveltekit-replacestate` | `replace` | `data-astro-history="replace"` |
| History state | — | — | `state` | `state` | — | — (`goto` only) | `state` | — (`navigate({state})` only) |
| Scroll control | `preserveScroll` | `scroll={false}` | `preventScrollReset` | `resetScroll`, `hashScrollIntoView` | — (page meta `scrollToTop`) | `data-sveltekit-reset="false"` (scroll + focus) | `noScroll` | — |
| Keep page state | `preserveState` (Vue/Solid only) | — | — | — | — | — | — | `transition:persist` (element-level) |
| Prefetch trigger | `prefetch`: `true`=`'hover'`, `'click'`, `'mount'`, `'visible'`, `false`, or an **array** (first wins); default from plugin `defaultStrategy` (`false`) | `prefetch`: `auto`/`null` (default, viewport), `true`, `false` | `none` (default), `intent`, `render`, `viewport` | `preload`: `false` (default), `intent`, `viewport`, `render` + `preloadDelay` | `prefetch`/`noPrefetch`, `prefetchOn: 'visibility'` (default) \| `'interaction'` \| both | `preload-data` hover/tap/false; `preload-code` eager/viewport/hover/tap/false (ancestor-inherited) | router-wide only | `data-astro-prefetch` hover/tap/viewport/load |
| Per-link prefetch TTL | **`cacheFor`**: ms, `'30s'`, or `[fresh, expire]` SWR pair; `0` = single use | — | — | — (route `preloadStaleTime`) | — | — | — | — |
| Full document navigation | `reloadDocument` (GET only; disables prefetch) | — (use `<a>`) | `reloadDocument` | `reloadDocument` | `external` | `data-sveltekit-reload`, `rel="external"` | — | `data-astro-reload` |
| View transition | `viewTransition` (bool override) | `transitionTypes` | `viewTransition` (**deprecated**; use React `<ViewTransition>`) | `viewTransition: bool \| { types }` | — (page meta) | — | — | `transition:*` directives |
| Active styling | `activeMatch: 'exact'` (default) \| `'prefix'` → `aria-current="page"` (exact only) + `data-void-active`; case- and trailing-slash-sensitive; hash ignored; a link with a query is active only when the current URL has each of those params (extra params allowed; GET `data` counts); prefix matching compares the path only; `/` never a prefix (`pages/link.ts` `linkActiveAttributes`) | none (use `usePathname`) | `NavLink`: `end`, `caseSensitive`, `className`/`style`/`children` fns with `{isActive, isPending, isTransitioning}`, `aria-current` | `activeOptions {exact, includeHash, includeSearch, explicitUndefined}`, `activeProps`/`inactiveProps`, children fn, `data-status` | `activeClass`/`exactActiveClass`, `ariaCurrentValue` | none | `activeClass`/`inactiveClass`/`end`, `aria-current` | none |
| Pending state on link | `data-void-pending` on every link whose method, path, query and hash match the in-flight visit, including during `router.refresh()` (`pages/link.ts` `linkPendingAttributes`). A user-supplied attribute wins. No render prop | `useLinkStatus()` | `NavLink` `isPending` | — | `prefetchedClass` (prefetched, not pending) | — | — | — |
| Cancel per click | `onNavigate(e)` → `e.preventDefault()` | `onNavigate` | — (use `useBlocker`) | `ignoreBlocker` (bypass) | — | — | — | — |
| URL mask | — | — | `mask` | `mask` | — | — | — | — |
| Non-GET link | **`method` + `data`** → action visit (button) | — | — (`<Form>`) | — | — | — | — | — (ClientRouter intercepts forms) |
| Route discovery | n/a (eager manifest) | — | `discover="render" \| "none"` | — | — | — | — | — |
| Disabled | — | — | — | `disabled` | — | — | — | — |
| Custom link builder | Undocumented `void/pages-client` helpers (`resolveLink`, `handleLinkClick`, `linkActiveAttributes`) | — | `useLinkClickHandler` | `createLink`, `linkOptions` | `defineNuxtLink`, `custom` slot | n/a | n/a | n/a |
| Typed `href` | `routing.typedRoutes` (off by default; on in `void init`) | `typedRoutes` | — (use `href()`) | inferred | `typedPages` [N5 default on] | — (use `resolve()`) | — | — |

Void click handling (`pages/link.ts`, `pages/adapter-helpers.ts`): modified clicks (ctrl/meta/shift/alt, non-left), `target` ≠ `_self`, `download`, `defaultPrevented` and cross-origin links are left to the browser. `onNavigate` runs after the user's `onClick`. User-supplied `aria-current`/`data-void-active`/`data-void-pending` win.

**Behavioral differences that matter**
- Void's `Link` is **required** for SPA navigation, as in Next.js/React Router/TanStack/Nuxt. SvelteKit, Solid and Astro upgrade every `<a>`, which matters for Markdown/CMS content. In Void, Markdown pages are island pages anyway, so their links are always full loads.
- A Void `Link` from a Pages page **to an island page** first fetches the URL with `X-VoidPages`. It receives HTML, discards it and sets `location.href`, so the browser issues **two requests** (`pages/navigation-engine.ts` `loadNavigationShell`; no early island check before the fetch).
- Void has the richest per-link prefetch control: a trigger array plus a per-link SWR TTL. It lacks link-level history `state`, masking, relative-path support under `typedRoutes`, and object destinations on `Link` itself.

**Void gap:** partial. Missing:
- link `state` (5/7);
- a documented custom-link builder (3/7);
- object destinations / `RouteDestination` on `Link.href` (Next.js, React Router, TanStack, Nuxt: 4/7);
- relative links under `typedRoutes` (3/7);
- `mask` (2/7).

## Programmatic navigation

| Framework | API | Options | Completion / return | Abort and race behavior | Server use |
|---|---|---|---|---|---|
| **Void** | `useRouter()` → `visit(dest, opts)`, `refresh(opts)`, `prefetch`, `flush`, `flushAll`; read-only `url`, `path`, `query`, `params`. No `back`/`forward` wrappers | `method` (GET default; `POST/PUT/PATCH/DELETE`), `data` (JSON, or multipart if it contains File/Blob/FileList), `preserveScroll` (default: keep scroll when a non-GET visit stays on the same URL; `false` resets; `true` also keeps it after a redirect), `preserveState` (default `false` GET / `true` non-GET), `replace`, `viewTransition`, React-only `resolveOn: 'commit'` (default) \| `'data'` | Promise of the page object. Aborted GET visit resolves `undefined`; aborted non-GET rejects `AbortError` (`pages/client.ts`) | A new visit aborts the pending fetch (AbortController) and disposes its deferred props. Visit ids ensure an older visit never commits over a newer URL, and back/forward wins over a pending visit. Same-origin server redirects are followed in place (history gets the final URL); cross-origin → full load. A non-Void response → full-load fallback. `javascript:`/`data:` rejected; `capacitor:` allowed | Throws during SSR. Redirect from loaders/middleware via `c.redirect()` |
| **Next.js** | `useRouter()` `push`, `replace`, `refresh`, `prefetch`, `back`, `forward`, `bfcacheId` | `scroll`, `transitionTypes`; `prefetch({ kind: 'auto' \| 'full' [16.5 canary], onInvalidate })` | Not documented as a promise (use `useLinkStatus` / transitions) | Not documented; `javascript:` executes (XSS warning) | `redirect()`/`permanentRedirect()` |
| **React Router** | `useNavigate()` → `navigate(to \| delta, opts)`; `<Navigate>` | `replace`, `state`, `relative`, `preventScrollReset`, `flushSync`, `defaultShouldRevalidate`, `viewTransition` (deprecated) | `Promise<void>` on completion; stable identity | Interrupted navigations/submissions cancel in-flight requests; stale revalidations discarded | `redirect()` in loaders/actions |
| **TanStack Start** | `useNavigate({ from })`, `router.navigate()` (outside React too), `<Navigate>`, `useMatchRoute`, `useCanGoBack` | All `Link` options (`to/params/search/hash/state/mask/replace/resetScroll/hashScrollIntoView/viewTransition/ignoreBlocker/reloadDocument/href`) | `router.navigate`: `Promise<void>` | Preload lane returns `undefined` on cancel; navigation re-runs its own `beforeLoad` | No-op on server; `throw redirect()` |
| **Nuxt** | `navigateTo(to, opts)` (server + client), `abortNavigation()`, vue-router `useRouter()` (`push/replace/back/forward/go/resolve/addRoute/…`), `reloadNuxtApp()` | `replace`, `redirectCode` (302), `external` (otherwise external URLs throw), `open: { target, windowFeatures }` | Must be awaited/returned; [N5] top-level `await navigateTo()` returns early from `setup()` | — | Server call sends `Location`; not usable in Nitro routes |
| **SvelteKit** | `goto(url, opts)`, `refreshAll`, `invalidate`, `preloadData`, `preloadCode` | `replace`, `reset` (scroll + focus), `refreshAll`, `invalidate` (array; in types, not inventory), `state`, `shallow`, `persistState` | Promise; **rejects** for external URLs and unmatched same-origin URLs (v3) | `navigation.complete` rejects when aborted; >20 redirects → `redirect_loop` | — |
| **SolidStart** | `useNavigate()` → `navigate(to \| delta, opts)`, `<Navigate>` | `resolve`, `replace`, `scroll`, `state` | — | — | On server: 302 + `Location` |
| **Astro** | `navigate(href, opts)` (`astro:transitions/client`) | `history: 'auto' \| 'push' \| 'replace'`, `formData` (POST), `info`, `state`, `sourceElement` | — | — | `Astro.redirect()`; does not sanitize `href` |

**Behavioral differences that matter**
- Void's `visit` doubles as a **mutation client** (method + body + action-key handling) and returns the destination page object. Only Astro's `navigate({ formData })` is comparable.
- Void's race handling is explicit in source (`pages/navigation-engine.ts`, `pages/client.ts`): abort plus monotonic visit ids, and a rollback of the rendered page if the history write fails. React Router documents similar guarantees. Others leave them unstated.
- **Back/forward always refetches** the page JSON unless a prefetch entry is still usable. There is no history-entry cache. An internal `cacheVisitedPageData` option (SWR reuse of visited pages) and a React `navigationFallback` exist in `navigation-engine.ts` / `react/src/runtime/pages-client.ts`, but `generateClientEntry` never passes them, so users cannot enable them.

**Void gap:** partial. Missing:
- `state` (5/7);
- `back`/`forward`/`canGoBack` helpers (Next.js, TanStack, Nuxt);
- relative `from` resolution;
- a non-subscribing `matchRoute(dest)` (TanStack);
- a history-entry / visited-page cache for back/forward (latent internal option).

## Navigation blocking, client guards and lifecycle events

| Framework | Confirm-leave / blocking | Covers back/forward and programmatic? | Tab close (`beforeunload`) | Client-side route guards / middleware | Lifecycle events / hooks | Pending state |
|---|---|---|---|---|---|---|
| **Void** | `Link onNavigate` → `preventDefault()` only | **No** (not `router.visit`, not popstate) | No | **None.** Server middleware (`middleware/`, `defineHandler(mw…, loader)`) runs on each navigation's JSON fetch, but **not** for prefetch-cache hits or static-output JSON (`/_void/pages/*.json`) | **None** | `useNavigation()` → `{ state: 'idle' \| 'loading' \| 'submitting', location, method }` |
| **Next.js** | `Link onNavigate` only (docs pattern for unsaved forms) | No | No | None (Proxy is server-side) | `onRouterTransitionStart` (`instrumentation-client`) | `useLinkStatus` |
| **React Router** | `useBlocker(bool \| fn)` → `{ state, proceed, reset }`; [exp] `unstable_usePrompt` | Yes (in-app) | `useBeforeUnload` | `clientMiddleware`, `clientLoader` | (instrumentations, Area 14) | `useNavigation`, `NavLink isPending`, [exp] `unstable_useRouterState` |
| **TanStack Start** | `useBlocker({ shouldBlockFn, enableBeforeUnload, withResolver })`, `<Block>` (new API [exp]) | Yes (receives `action`) | `enableBeforeUnload` | `beforeLoad` per route (also on preload, `cause: 'preload'`) | `router.subscribe`: `onBeforeNavigate` → `onBeforeLoad` → `onLoad` → `onBeforeRouteMount` → `onResolved` → `onRendered`; route `onEnter/onStay/onLeave` | `useRouterState` |
| **Nuxt** | `onBeforeRouteLeave/Update`, `router.beforeEach`, middleware `abortNavigation()` | Yes (vue-router guards) | — | Route middleware: inline / named / `*.global.ts`, ordered; server + client; `addRouteMiddleware`, `appMiddleware` rule; `validate` | `router.afterEach`, `page:view-transition:start`, `link:prefetch` hooks | — |
| **SvelteKit** | `beforeNavigate(nav => nav.cancel())` | Yes (`type: 'popstate'`) | `type: 'leave'` + `cancel()` → native unload dialog (verified in `types/index.d.ts`) | Universal `load` (client + server) can `redirect` | `beforeNavigate`, `onNavigate` (can delay the DOM update), `afterNavigate` | `navigating` |
| **SolidStart** | `useBeforeLeave(e => e.preventDefault())` with `retry(force)` | Yes (`to` may be a delta) | — | None | `useBeforeLeave` | `useIsRouting()` |
| **Astro** | Not documented | — | — | None (server middleware) | `astro:before-preparation` → `after-preparation` → `before-swap` → `after-swap` → `page-load` | via events |

**Behavioral differences that matter**
- Void's only guard is per-link, which covers the "link in a nav bar" case and nothing else. React Router, TanStack, Nuxt, SvelteKit and Solid block router-level navigation, including back/forward, and three of them handle tab close.
- Void apps cannot run code before or after a navigation (analytics page views, closing menus, focus management) except by watching `useNavigation()` / router URL reactivity per adapter.
- Server middleware acting as the guard is consistent for SSR responses. It is **bypassed** by the prefetch cache (TTL up to `cacheFor`) and by static output, so auth-sensitive pages must also check in loaders.

**Void gap:** missing:
- router-level blocking (5/7; Next.js matches Void's link-only level);
- `beforeunload` integration (3/7);
- before/after-navigate hooks or router events (6/7);
- client route guards (4/7).

Design note: the hooks must exist in all four adapters. A framework-agnostic event API on the core router (`router.on('before'|'after', fn)`) plus adapter wrappers fits the existing `void/pages-client` layering.

## Prefetching

| Framework | Triggers (default) | Delay | What is fetched | Cache / TTL | Manual API | Skips / conditions |
|---|---|---|---|---|---|---|
| **Void** | `hover` (pointer rest; **focus** and `touchstart` immediate), `click` (`mousedown`/`touchstart`), `mount`, `visible` (IntersectionObserver; prefetches after 300 ms in view, `LINK_VISIBLE_PREFETCH_DELAY`; leaving resets the wait), arrays. App default `defaultStrategy: false` | `hoverDelay` 75 ms | **Code + data**: dynamic-imports the page and layout chunks and requests the page JSON (`X-VoidPages`, `Purpose: prefetch`); **runs the loader** (docs: keep loaders side-effect free). Deferred props resolved inline (no stream). Island targets → `<link rel="prefetch" as="document">`. Production static output reads `/_void/pages/<path>.json` | Per-URL+method entry; `cacheFor` default `'30s'`; `[fresh, expire]` = serve stale and refresh in the background; `0` = single use. **Any non-GET visit flushes the whole cache** | `router.prefetch(dest, { cacheFor })` (awaitable, returns the page object), `flush(dest)`, `flushAll()` | Other origins, the current URL, non-GET (throws). `Link` prefetch skips `saveData` and `2g`/`slow-2g` (`pages/link.ts` `prefetchLink`; Chromium `navigator.connection` only). `router.prefetch()` is not gated. Dev never reads `/_void/pages/*.json`; production skips that file when `prerender: false` (`pages/plugin.ts`, `matchStaticPageId`) |
| **Next.js** | Viewport (default `auto`); hover re-prefetches expired data | Scheduler queue (viewport > hover; offscreen discarded) | `auto`: static route full; dynamic down to nearest `loading.js`. `true`: full. Partial Prefetching (`partialPrefetching`, needs CC): shared per-route App Shell + per-link prefetch. Segment `prefetch = 'partial' \| 'force-disabled'`; `prefetch()`/`navigation()` stage deferral; segment dedupe + inlining | Client cache; invalidations refresh prefetches; `onInvalidate` | `router.prefetch(href, { kind, onInvalidate })` | **Production only**; only after hydration |
| **React Router** | `none` (default), `intent` (hover/focus), `render`, `viewport` | — | Route modules **and** loader data via `<link rel=prefetch/modulepreload>` (bypasses `unstable_fetch` headers) | Browser HTTP cache | `<PrefetchPageLinks page>` | Lazy discovery batches manifest requests for rendered links |
| **TanStack Start** | `false` (default), `intent` (touch immediate), `viewport`, `render` | `defaultPreloadDelay` 50 ms | Route chunk + every matched `beforeLoad` (`cause: 'preload'`) + `loader` (unless route `preload: false`) | `preloadStaleTime` 30 s, `preloadGcTime` 5 min; navigation re-runs `beforeLoad` and may reuse loader data | `router.preloadRoute()`, `router.loadRouteChunk()` (code only) | — |
| **Nuxt** | `visibility` (default) and/or `interaction` (`pointerenter`/`focus`) | Browser idle | Page chunks + middleware + layouts + `_payload.json` **only for prerendered/ISR/SWR routes**; SSR `useFetch` data not prefetched; island responses | — | `preloadRouteComponents`, `preloadComponents`, `prefetchComponents` | Skips offline, 2G, data-saver; [exp] `crossOriginPrefetch` (Speculation Rules) |
| **SvelteKit** | `preload-data` hover (template default on `<body>`) / tap; `preload-code` eager/viewport/hover/tap | — | Data attr: code **and** `load`; code attr: code only | Not documented | `preloadData(href)` → `{type, status, data \| location \| error}`; `preloadCode(routeId)` | `saveData`; `eager`/`viewport` only for links present after navigation |
| **SolidStart** | Router-wide `preload` (default true): hover (~20 ms) / focus | ~20 ms | Route module + route `preload` fn (`intent: 'preload'`) | Query cache ~5 s | `usePreloadRoute()(url, { preloadData = false })` (code only by default) | No viewport/render strategies |
| **Astro** | Opt-in config: `hover` (default), `tap`, `viewport`, `load`; `prefetchAll` (true with ClientRouter) | — | **Whole HTML document** via `<link rel=prefetch>` or `fetch()` | HTTP cache headers | `prefetch(url, { ignoreSlowConnection, eagerness })` | Data-saver/slow → `tap`; [exp] `clientPrerender` (Speculation Rules) |

**Behavioral differences that matter**
- Void always prefetches **code and data together**, so every prefetch executes the loader. TanStack, SvelteKit, Solid and Next.js can prefetch code only (or a static shell) for links whose data is expensive or user-specific.
- Void's per-link **SWR TTL** (`['30s', '5m']`) is unique. TanStack's 30 s/5 min split is router- or route-level.
- Void invalidation is blunt: any mutation flushes everything. Next.js refreshes affected prefetches on tag/path invalidation; TanStack has per-route stale times.
- `Link` prefetch skips Save-Data and 2G, which Nuxt, SvelteKit and Astro also do. Void does not skip offline, and the check only runs where `navigator.connection` exists. There are no Speculation Rules (Nuxt [exp], Astro [exp]).
- Void prefetch does not run in a speculative lane. A prefetched redirect becomes a `null` entry, which makes the later click do a full load. TanStack explicitly never promotes preload `beforeLoad` results.

**Void gap:** partial. Missing:
- a code-only prefetch mode (5/7);
- targeted invalidation of prefetched entries on mutation;
- Speculation Rules (2/7, both [exp]).

## Search params

| Framework | Read | Write | Typed / validated | Serialization | Loader re-run semantics |
|---|---|---|---|---|---|
| **Void** | `useRouter().query` (`URLSearchParams`); server `c.req.query()` | `Link data`, `routeUrl({ query })`, `router.visit('?page=2')` (relative query resolves against the current page). No setter / merge helper | Client: no. Server: `withValidator({ query })` (Standard Schema; multi-value → arrays); on a page loader, failure → raw 400 JSON | Flat: primitives via `String()`, Date → ISO, arrays → repeated keys, nested objects throw | **Every change is a full server loader fetch** (no key-level dependency, no shallow update); Vue also remounts the page unless `preserveState` |
| **Next.js** | `searchParams` Promise (page only), `useSearchParams()` (read-only; needs `<Suspense>` or the build fails on static pages) | `Link`, `router.push`, `<Form>` GET, native `pushState` | No | `?a=1&a=2` → `{a: ['1','2']}` | Request-time API (dynamic) |
| **React Router** | `useSearchParams()`, `request.url` | `setSearchParams(obj \| fn)` (causes navigation; callback doesn't queue), `<Form method="get">` | No | `URLSearchParams` | Revalidates unless `defaultShouldRevalidate: false` / `shouldRevalidate` |
| **TanStack Start** | `useSearch({ from, select, strict })` | `search` object or updater on Link/navigate | **Yes**: `validateSearch` (function / `.parse` / Standard Schema), separate input/output types, inherited by children; `search.middlewares` (`retainSearchParams`, `stripSearchParams`); `search.strict` | JSON-first, structural sharing; custom `parseSearch`/`stringifySearch` | Loaders see search only via `loaderDeps` (deep-compared cache key) |
| **Nuxt** | `useRoute().query` | `navigateTo({ query })`, `NuxtLink :to` | No | vue-router `LocationQuery` | — |
| **SvelteKit** | `url.searchParams`, `page.url.searchParams` (`ReadonlyURL` in v3) | `goto` | No | `URLSearchParams` | Per-key tracking: `get/getAll/has('x')` re-runs only when `x` changes; unavailable in prerender |
| **SolidStart** | `useSearchParams()` (reactive), `useLocation().query` | `setParams(values, opts)`: **merges**, deletes on `null/undefined/''/[]`, keeps hash, default `scroll: false` | No | `string \| string[]` | — |
| **Astro** | `Astro.url.searchParams` | plain links | No | — | Prerendered pages never see search params |

**Behavioral differences that matter**
- Void has **no client-only search state**. A filter or tab change in the URL costs a loader round-trip and, in Vue, a page remount. React Router (`shouldRevalidate`), TanStack (`loaderDeps`) and SvelteKit (per-key tracking, `shallow`) let URL state change without re-running unrelated data. Next.js lets native `pushState` update it.
- Void's server-side Standard Schema validation is a solid base. It is not connected to `Link`, `routeUrl` query typing (`RouteQuery` keys are not route-specific) or a page-level error UI.

**Void gap:** missing:
- a setter with merge/updater semantics (3/7);
- URL-state changes that skip or partially run the loader (4/7: React Router, TanStack, SvelteKit, Next.js);
- route-scoped typed and validated search params flowing to links and `useRouter().query` (TanStack only, 1/7);
- retain/strip middleware (TanStack).

## Typed links and route params (summary; detail in Area 8)

| Framework | Typed hrefs | Typed params in components | Mechanism |
|---|---|---|---|
| **Void** | `routeUrl(pattern, { params, query, hash })`, `RouteDestination`; `routing.typedRoutes` checks strings in `Link`/`visit`/`prefetch`/`flush`/`c.rewrite()` (a dynamic segment accepts any text, including empty) | `useParams<'/users/:id'>()` → `{ id: string }` in all 4 adapters. A wrong pattern or param name is a type error. Without a pattern, `Record<string, string>`. Not inferred from the file. `c.req.param()` needs `as PageParams<'/…'>` | Codegen (`void prepare` / dev server; `PagePathMap` in `codegen/route-types.ts`) |
| **Next.js** | `typedRoutes` (Link, push/replace/prefetch) | `PageProps<'/x/[y]'>`, `LayoutProps`, `RouteContext` | Codegen (`next typegen`) |
| **React Router** | `href(path, params)` (Link `to` is untyped) | `Route.*Args` per route via `+types` | Codegen |
| **TanStack Start** | Link/navigate `to/params/search/hash` | `Route.useParams()` | Inferred (`Register`) |
| **Nuxt** | `typedPages` [N5 default on]; `NUXT_B4025` warning for unknown static `to` | `useRoute('name')` | Codegen |
| **SvelteKit** | `resolve('/blog/[slug]', { slug })` (hrefs unchecked) | `./$types`, incl. matcher output types | Codegen |
| **SolidStart** | No | Manual generic | — |
| **Astro** | No | Static routes via `InferGetStaticParamsType` | Inference |

**Void gap:** partial. Missing: param types inferred from the component file (React Router, TanStack, SvelteKit: 3/7), and a loader `c.req.param()` that does not need a cast. `useParams<'/users/:id'>()` already types the names when the pattern is passed. Void's string-level `href` checking under `typedRoutes` is on par with Next.js and Nuxt and ahead of React Router, SvelteKit, Solid and Astro.

## Scroll restoration, focus management and route announcements

| Framework | New navigation | Back/forward | Reload | Hash | Opt-out | Custom key / containers | Focus & announcements |
|---|---|---|---|---|---|---|---|
| **Void** | GET navigations scroll to top (in `requestAnimationFrame` after commit). An action or form that stays on the same URL keeps scroll unless `preserveScroll: false`; a redirect scrolls like a navigation (`pages/navigation-engine.ts` `makeCommit`) | Restored (positions keyed by a random `history.state.__voidScrollKey`, kept in memory + `sessionStorage` `void:scroll:*`) | Restored after hydration | `scrollIntoView()` on the target; same-page `#x` skips the fetch | `preserveScroll` (Link/visit/`action()`; React `useForm` hook option; Vue/Svelte/Solid per submit); `refresh()` preserves scroll | **Window only**; no custom key; no scroll-behavior option | **None** (no announcer, no focus reset) |
| **Next.js** | `scroll` default: keep position if the new page is visible, else scroll to the first element (skips sticky/fixed) | Preserved; [CC] Activity keeps routes mounted | — | Yes | `scroll={false}` | `<html data-scroll-behavior="smooth">` | **Route announcer built in** (`docs/03-architecture/accessibility.mdx`; not in inventory) |
| **React Router** | Top | Restored | `sessionStorage` (`storageKey`) + inline script to prevent flash | Not documented | `preventScrollReset` | `getKey(location, matches)` | Not automatic (docs) |
| **TanStack Start** | Top (and `scrollToTopSelectors`) | Restored **before paint** | — | `hashScrollIntoView` (default on) | `resetScroll: false` | `getScrollRestorationKey`, `scrollRestorationBehavior`, `useElementScrollRestoration` + `data-scroll-restoration-id` (element/virtualized) | Not documented |
| **Nuxt** | Top | Restored | — | Yes (`scrollBehaviorType: 'smooth'`) | `scrollToTop: bool \| fn` per page | Fully custom `scrollBehavior` in `router.options.ts` | `<NuxtRouteAnnouncer>`, `useAnnouncer` (opt-in) |
| **SvelteKit** | Top or `#id`, then **focus reset** | Restored (history stores scroll + snapshots + `page.state`) | — | Yes | `data-sveltekit-reset="false"`, `goto({ reset: false })`, `disableScrollHandling()` | `snapshot` export | **Built in**: live region announces `<title>`, focus → `<body>`/`[autofocus]` |
| **SolidStart** | Scroll after navigation | Not documented | — | Decoded hash target | `noScroll`, `scroll: false` | — | Not documented |
| **Astro** | ClientRouter swap | "Restored if necessary" | — | — | override in `astro:after-swap` | — | **Built in** (ClientRouter announcer: title → h1 → path); `saveFocus` for persisted elements |

**Void gap:** partial. Missing:
- a route announcer and focus management (4/7);
- a custom restoration key (3/7);
- element/container restoration (TanStack, 1/7; SvelteKit snapshots are generic);
- a scroll-behavior option (Next.js, TanStack, Nuxt).

Void's reload restoration and fragment-entry handling are on par with React Router and TanStack.

## View transitions

| Framework | Enable | Per-navigation override | Types / direction | Reduced motion | Back/forward | Notes |
|---|---|---|---|---|---|---|
| **Void** | Adapter option `viewTransitions: true` (all four adapters) | `Link viewTransition`, `visit({ viewTransition })` | **None** | Not handled (user CSS) | Yes | `document.startViewTransition` wraps the adapter update; React wraps a `startTransition` reveal; default cross-fade; unsupported browsers fall back silently; island/full loads get nothing built in |
| **Next.js** | Always available (React `<ViewTransition>`, React 19.3 canary) | `Link transitionTypes`, `push/replace({ transitionTypes })` | `addTransitionType` | — | No type on back/forward | Shared-element morph only if the destination renders in the same commit (prefetched) |
| **React Router** | React `<ViewTransition>` around the outlet (19.3+) | — | via React | — | May not animate (sync popstate) | Legacy `viewTransition` / `useViewTransitionState` **deprecated** |
| **TanStack Start** | Router `defaultViewTransition: bool \| { types }` | `viewTransition` | `types: string[] \| (info) => string[] \| false` (`fromLocation`, `toLocation`, `pathChanged`, …) | — | — | Falls back to plain `startViewTransition` when types are unsupported |
| **Nuxt** [exp] | `experimental.viewTransition: bool \| 'always' \| { enabled, types }` | `definePageMeta({ viewTransition })` | `types`, `toTypes`, `fromTypes` (functions in page meta) | `true` skips under `prefers-reduced-motion`; `'always'` ignores it | — | Known issue: DOM frozen during async page setup; plus Vue `<Transition>` page/layout transitions |
| **SvelteKit** | Manual recipe (`onNavigate` + `startViewTransition`) | — | — | — | — | — |
| **SolidStart** | Not found | — | — | — | — | — |
| **Astro** | Native MPA CSS transitions, or `<ClientRouter />` | `data-astro-reload`; `transition:animate` per element | `slide` reverses on back; custom forwards/backwards animations | Built-in reduced-motion media query | Yes | `transition:name`, `transition:persist(-props)`; `fallback: 'animate' \| 'swap' \| 'none'`; not compatible with CSP |

**Behavioral differences that matter**
- Void (adapter option), TanStack (`defaultViewTransition`) and Astro (`<ClientRouter/>`) turn transitions on app-wide with one switch. Void's switch covers back/forward too. Void offers no way to vary the animation by direction or route. Next.js, TanStack, Nuxt and Astro all pass types or direction.
- For React, Next.js and React Router moved to React's `<ViewTransition>`. Void's React adapter uses the DOM API directly, and how it composes with React `<ViewTransition>` is not documented.

**Void gap:** partial. Missing:
- transition types/direction (4/7);
- built-in reduced-motion handling (2/7);
- element persistence across navigation (Astro);
- documented React `<ViewTransition>` interop.

## Route-level code splitting and route discovery

| Framework | Splitting | Client route manifest / discovery | Notes |
|---|---|---|---|
| **Void** | Automatic: each page and layout is a `() => import()`; on a GET visit the matched page and layout chunks import **in parallel** with the data request (reused only if the response selects the same page). Server route modules are lazily imported and cached per isolate | **Full table shipped eagerly** in the client entry (static map + regex list + layout chains) | No pages-client bundle if every page is an island page |
| **Next.js** | Per segment automatic; `next/dynamic`, `React.lazy` | Server-driven (RSC); not described in inventory | [exp] `turbopackLazyDynamicImports` (dev) |
| **React Router** | Per route module; `splitRouteModules` (default on; `"enforce"`) splits `clientLoader`/`clientAction`/`clientMiddleware`/`HydrateFallback` | **Lazy route discovery** default (`/__manifest?paths=…`, batched for rendered links); `mode: 'initial'` | CDN must key on `version` + `paths` |
| **TanStack Start** | `autoCodeSplitting` (groupings; `codeSplitGroupings`, `splitBehavior`); `*.lazy.tsx` | Static route tree ("Fog of War 🛑") | Start's default for `autoCodeSplitting` not stated (unverified) |
| **Nuxt** | Every page is a dynamic import; layouts/middleware async; `ssr: false` / `noScripts` pages dropped from the server/client bundle | `early404` [exp] build-time matcher | — |
| **SvelteKit** | Per route + modulepreload; `bundleStrategy: 'split' \| 'single' \| 'inline'` | `router.resolution: 'server'` (opt-in) asks the server instead of shipping the manifest | — |
| **SolidStart** | File routes lazy (root `<Suspense>` required) | — | — |
| **Astro** | Per island/page; CSS chunks | n/a (MPA) | — |

**Void gap:** partial. Missing:
- lazy route discovery or server-side route resolution (2/7). This matters because Void's manifest grows linearly with page count and regex matching is linear in dynamic routes.
- a single-bundle option for Capacitor/HTTP/1 targets (SvelteKit). Void already supports `capacitor:` URLs.

## Base path, trailing slash, case sensitivity, URL rewriting and history modes

| Framework | Base path | Trailing slash | Case sensitivity | Client-side URL rewrite | Hash / memory history |
|---|---|---|---|---|---|
| **Void** | **None** (`RoutingConfig` has no base; Vite `base` only affects assets) | Fixed: strict matching; Pages apps 301 `/x/` → `/x` on the not-found fallback (GET/HEAD, after the asset lookup, not `/api/*`; `runtime/routing-pages.ts`); `routes/`-only apps get no redirect. No option | Case-sensitive (Hono; regex without `i`); not configurable | None. Server `routing.rewrites`/`fallbacks`/`c.rewrite()`; docs warn that client `Link` navigation may load data for the unrewritten path (`docs/guide/edge/rewrites.md`) | None (Pages need a server or static JSON) |
| **Next.js** | `basePath` (build time; prefixes Link/router/config rules) + `assetPrefix` | `trailingSlash` config + `skipTrailingSlashRedirect` | (unverified) | Config rewrites (server) | — |
| **React Router** | `basename` | No policy option | `NavLink caseSensitive` only | — | Not in framework mode inventory |
| **TanStack Start** | `basepath` (implemented as a rewrite) | `trailingSlash: 'always' \| 'never' \| 'preserve'` | `caseSensitive` (default false) | `rewrite: { input, output }`, `composeRewrites` (applies on the server too) | Browser/hash/memory/server history |
| **Nuxt** | `app.baseURL` (runtime `NUXT_APP_BASE_URL`), `cdnURL` | Partial: vue-router `strict`; NuxtLink `trailingSlash: 'append' \| 'remove'` | `router.options.sensitive` [N5 default true] | — | `hashMode` (SPA) |
| **SvelteKit** | `paths.base` (+ `paths.assets`, `paths.relative`) | `trailingSlash: 'never' \| 'always' \| 'ignore'` page option | (unverified) | `reroute` hook (universal, cached per URL) | `router.type: 'hash'` |
| **SolidStart** | `<Router base>` | Not found | (unverified) | `transformUrl` | `HashRouter`, `MemoryRouter` |
| **Astro** | `base` (manual prefixing of links) | `trailingSlash: 'ignore' \| 'always' \| 'never'`; `build.format` | (unverified) | — (server `Astro.rewrite`) | n/a |

**Void gap:** missing:
- base path (7/7, table stakes);
- a trailing-slash policy option (4/7; Nuxt partial);
- client-side URL rewrite/reroute that the router honors for matching (3/7). This would also fix the documented rewrite/`Link` mismatch;
- hash/memory routing (4/7);
- a case-sensitivity option (2/7).

Design note: a base path touches `Link` href rendering and active matching, `routeUrl`/typed routes, the prefetch and static JSON paths (`/_void/pages/…`), Hono route registration, redirects/rewrites config and `_redirects` output.

## Route metadata and current-route introspection

| Framework | Static per-route metadata | Current route identity / matches |
|---|---|---|
| **Void** | None (page exports limited to `layout`; companion `ssr`/`prerender`/`revalidate`) | **None beyond** `url`, `path`, `query`, `params` (`VoidRouter` type, `pages/client.ts`); the page id is in the page object but not exposed |
| **Next.js** | Segment config only | `useSelectedLayoutSegment(s)`, `usePathname`, `useParams` (partial) |
| **React Router** | `handle` export | `useMatches()` (ids, params, loaderData, handle) |
| **TanStack Start** | `staticData` (typed via declaration merging) | `useMatch`, `useMatches`, `useParentMatches`, `useChildMatches`, `useMatchRoute` |
| **Nuxt** | `definePageMeta` custom keys (typed via `PageMeta`), `route.meta.groups` | `useRoute()` (name, matched, meta) |
| **SvelteKit** | — | `page.route.id`, `match(url)` |
| **SolidStart** | Route `info` | `useCurrentMatches()`, `useMatch()` |
| **Astro** | `RouteData` (integrations) | `Astro.routePattern`, `Astro.originPathname` |

**Void gap:** missing:
- current route id/pattern and matched layout chain (6/7, plus Next.js partial). This is needed for breadcrumbs, analytics, and nav highlighting by route rather than URL;
- static route metadata readable by layouts (4/7).
