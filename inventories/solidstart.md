# SolidStart — feature inventory
Version documented: **SolidStart 2.0 (`@solidjs/start@2.0.0`) + Solid Router v1 ("latest")**. How determined: (a) docs-site config `vite.config.ts` lists SolidStart versions `v2` and `v1` and overrides the v1 label to **"v1 (legacy)"**; (b) every v2 page has frontmatter `version: "2.0"`; (c) `S2/(2)migrating-from-v1.mdx` installs `@solidjs/start@2.0.0` and describes 2.0.0 behavior vs. "earlier prereleases"; (d) the root Quick start (`src/routes/(1)quick-start.mdx`) links to `/solid-start/v2`; (e) the docs site is itself a SolidStart app pinned to `@solidjs/start` `2.0.0`; (f) `S2/(2)guides/(5)deployment-plugins.mdx` links a Netlify changelog dated 2026-08-06 announcing "SolidStart 2". Caveats: one leftover sentence in the migration guide still says "the RC setup", and the recommended deployment layer, **Nitro v3, is still a beta** (`nitro@3.0.260610-beta`). So the framework is stable, but its default deployment plugin is pre-release. · Docs commit: 2026-10-29 (`9a9d77a`, solidjs/solid-docs).
Context: Solid 1.x (solid-js 1.9; v2 overview says it builds on "Solid v1") · Vite 8 or 9, using Vite's Environment API for client and server builds · H3 v2 (Web-standard Request/Response) through a deployment Vite plugin: Nitro v3 (portable presets), the Netlify Vite plugin or the Cloudflare Vite plugin · Node.js ≥ 24 required for v2 tooling; the production runtime depends on the deployment preset. Router-agnostic: official Solid Router v1 or TanStack Solid Router v1.

**Path legend** (all relative to repo root): `S2/` = `src/routes/solid-start/v2/`, `S1/` = `src/routes/solid-start/v1/`, `R/` = `src/routes/solid-router/`.
**Scope notes:**
- The v2 docs are shorter than v1 for some topics. The v2 overview says v2 "is mainly a tooling and stability upgrade" (`S2/(0)index.mdx`). Where v2 omits a file convention that v1 documents (route groups, layout files, `(name)` index renaming, layout escaping), I cite v1 and tag it **[v1 doc, presumed unchanged]**.
- This sparse clone has no Solid Meta docs and no Solid core docs (Suspense, ErrorBoundary, lazy, getRequestEvent reference pages). Claims about those come only from mentions in the Start and Router docs, or are tagged "(from memory, unverified)".
- SolidStart deliberately delegates routing, data and mutations to Solid Router. Router APIs are inventoried here because they are the framework's data layer.

---

## 1. Routing

- **Route definition (file-based + code-based)**: **Supported (both)**. `FileRoutes` from `@solidjs/start/router` turns files in `src/routes` into route definitions. You render it as the children of Solid Router's `<Router>` in `src/app.tsx`. A file with a **default export** becomes a UI route. A file exporting **HTTP method names** (`GET`, `POST`, …) becomes an API route. Source: `S2/(0)building-your-application/(0)routing.mdx`.
  - `FileRoutes` (type `() => any[]`, takes no args): on the server it returns the request event's routes; on the client it builds routes from the generated page-route config and caches them in module scope. Generated route info includes `filesystem: true` [v1 ref]. Because it returns a plain route-config array, it can feed "the router of your choice". Source: `S2/reference/routing/file-routes.mdx`, `S1/reference/routing/file-routes.mdx`, `S1/(0)building-your-application/(0)routing.mdx`.
  - Code-based routing (Solid Router): JSX `<Route path component preload matchFilters info children>` or config objects (`RouteDefinition` / arrays with `children`) passed to `<Router>`. Docs say the two have "the same capabilities". Source: `R/(0)getting-started/(1)component.mdx`, `R/(0)getting-started/(2)config.mdx`, `R/reference/components/route.mdx`.
  - Directory config (`solidStart()`): `appRoot` (default `"./src"`, the folder containing `app.tsx`/`app.jsx`), `routeDir` (default `"./routes"`, relative to `appRoot`), `extensions` (default `[]`: extra file extensions that both the filesystem router and the Solid compiler process; in v1 the default was `["js","jsx","ts","tsx"]`). Source: `S2/reference/config/solid-start.mdx`, `S1/reference/config/define-config.mdx`.
  - `.mdx` files in `src/routes` are also page routes. Source: `S2/(0)building-your-application/(0)routing.mdx`.
  - **File-name → URL table** (v2 rows from `S2/.../(0)routing.mdx`; rows marked † from `S1/.../(0)routing.mdx` [v1 doc, presumed unchanged]):

    | File | URL / effect |
    |---|---|
    | `routes/index.tsx` | `/` |
    | `routes/about.tsx` | `/about` |
    | `routes/blog/index.tsx` | `/blog` |
    | `routes/blog/post.tsx` | `/blog/post` |
    | `routes/users/[id].tsx` | `/users/:id` |
    | `routes/users/[[id]].tsx` | `/users/:id?` (matches `/users`, `/users/1`) |
    | `routes/docs/[...slug].tsx` | `/docs/*slug` |
    | `routes/blog.tsx` + `routes/blog/*` † | `blog.tsx` is the **layout** for everything in `blog/` |
    | `routes/socials/(socials).tsx` † | `/socials` ("renamed index", avoids many `index.tsx` files) |
    | `routes/(static)/about-us/index.tsx` † | `/about-us` (route group: no URL segment) |
    | `routes/users(details)/[id].tsx` † | `/users/:id`, **escaping** the `users.tsx` layout |
    | `routes/users(details).tsx` † | separate layout for the escaped `users(details)/` subtree |
    | `routes/api/ping.ts` exporting `GET` | API endpoint `/api/ping` |

- **Route module exports**: default export = page component. A named `export const route = { preload } satisfies RouteDefinition` attaches route-level config "while still default-exporting UI". Only `preload` appears in the docs. Whether `matchFilters` or `info` are honored when exported from a file route is **not documented**. v1 describes `route` as the hook for configuring "the router of your choice". Source: `S2/(0)building-your-application/(0)routing.mdx`, `S1/(0)building-your-application/(0)routing.mdx`.
- **Nested layouts**: **Supported**.
  - File routing [v1 doc]: a file named like a folder (`blog.tsx` beside `blog/`) wraps that folder's routes and renders the child via `props.children` (`RouteSectionProps`). `blog/index.tsx` and `blog/(blogIndex).tsx` are *not* layouts; they render only for the index URL.
  - Root layout: the `<Router root={...}>` prop in `app.tsx`. Docs say to wrap `props.children` in `<Suspense>`, "since each component will be lazy-loaded automatically. Without this, you could see some unexpected hydration errors."
  - Code routing: a parent `<Route component={Layout}>` with child `<Route>`s; the layout renders `props.children`. Limitation: only the **innermost** nested `<Route>` becomes a matchable route. To make the parent path itself match, define it separately or add a child with `path=""`.
  - Re-render behavior: "Routes that share the same path match will be treated as the same route." For example, `/users/1` → `/users/2` reuses the component instance and params update reactively. To force a remount, wrap the content in a keyed `<Show when={params.x} keyed>`. A `<Route path={["login","register"]}>` keeps one component mounted across several URLs.
  - Sources: `S1/(0)building-your-application/(0)routing.mdx`, `R/(1)concepts/(5)nesting.mdx`, `R/(1)concepts/(6)layouts.mdx`, `R/(1)concepts/(4)dynamic-routes.mdx`, `R/(1)concepts/(1)path-parameters.mdx`.
- **Dynamic segments**: **Supported**. `[id]` in files, `:id` in code. Read params with `useParams()` (a reactive object `Record<string, string | undefined>` merged across all current matches; property reads are tracked) or `props.params` on route components. Source: `S2/.../(0)routing.mdx`, `R/reference/primitives/use-params.mdx`.
- **Optional segments**: **Supported**. `[[id]]` in files, `:id?` in code. Caveat: `?` makes the parameter optional only as the **last segment**, so `/users/:id?` does not match `/users/123/contact`. `useMatch` "expands optional path segments before creating matchers". Source: `R/(1)concepts/(1)path-parameters.mdx`, `R/reference/primitives/use-match.mdx`.
- **Catch-all / splat**: **Supported**. `[...slug]` in files, `*slug` or bare `*` in code.
  - The param value is a slash-delimited string of the remaining segments: `[...post]` at `/post/foo/baz` gives `post/foo/baz`.
  - `/users/*` also matches `/users` itself (zero segments).
  - The wildcard must be last: `/users/*rest/:id` creates no routes.
  - Not-found pages use a catch-all at the end. Code routing: `path="*404"`. File routing: a root `[...404].tsx`; v1 shows `[...missing].tsx`, and the docs repo itself uses `src/routes/[...404].tsx`.
  - Sources: `S1/.../(0)routing.mdx`, `R/(1)concepts/(3)catch-all.mdx`, `R/(1)concepts/(4)dynamic-routes.mdx`.
- **Param validation (match filters)**: **Supported (code routing)**. `matchFilters` on `<Route>` (and on `useMatch`) maps each param name to an array of allowed strings, a `RegExp` or a predicate `(s: string) => boolean`. If validation fails, the route does not match and later routes are tried. The type `MatchFilters<P>` is keyed by params parsed from the literal path string. For file routes, no documented way exists to attach filters. Source: `R/(1)concepts/(1)path-parameters.mdx`, `R/reference/components/route.mdx`, `R/reference/primitives/use-match.mdx`.
- **Route groups / pathless layouts**: **Supported** [v1 doc, presumed unchanged]. `(folder)` groups routes without a URL segment. `name(group).tsx` plus `name(group)/` creates a sibling layout tree that "escapes" the parent layout while sharing its URL prefix. Code routing gets the same effect with a `<Route component={Layout}>` that has no `path` (`R/(1)concepts/(6)layouts.mdx`). Source: `S1/.../(0)routing.mdx`.
- **Parallel routes / intercepting (modal) routes**: **Not found in docs**.
- **Typed links & typed route params**: **Not supported** in the docs. `<A href: string>` and `navigate(to: string)` are untyped. `useParams<T extends Params>()` takes a manual generic. There is no route codegen. `Route` is generic over the path literal `S`, but only `matchFilters` keys use it. TanStack Solid Router is the documented alternative router (`S2/(0)index.mdx`); its typed-route features are not described in these docs. Source: `R/reference/components/a.mdx`, `R/reference/primitives/use-params.mdx`.
- **Search-param handling**: **Partial** (reactive, untyped, unvalidated). `useSearchParams<T extends SearchParams>()` returns `[params, setParams]`. Source: `R/reference/primitives/use-search-params.mdx`, `R/(1)concepts/(2)search-parameters.mdx`, `R/reference/primitives/use-location.mdx`.
  - `params`: a reactive `Partial<T>`, where `SearchParams = Record<string, string | string[] | undefined>`.
  - `setParams(values: Record<string, string|string[]|number|number[]|boolean|boolean[]|null|undefined>, options?: Partial<NavigateOptions>)`:
    - It **merges** into the current `location.search`, then navigates.
    - It deletes keys whose value is `null`, `undefined`, `""` or `[]`.
    - Array values append one entry per item; other values are set with `String(value)`.
    - It preserves the current hash.
    - Defaults are `scroll: false` and `resolve: false`; both can be overridden.
  - `useLocation().query` is the reactive parsed object derived from `search`; `useLocation().search` is the raw string.
  - No schema validation or typed parsing exists.
- **Programmatic navigation**: **Supported**. Sources: `R/reference/primitives/use-navigate.mdx`, `R/reference/components/navigate.mdx`, `R/reference/primitives/use-before-leave.mdx`, `R/reference/primitives/use-is-routing.mdx`, `R/reference/primitives/use-location.mdx`, `R/reference/primitives/use-match.mdx`, `R/reference/primitives/use-current-matches.mdx`, `R/reference/primitives/use-resolved-path.mdx`.
  - `useNavigate()` returns `navigate(to: string | number, options?)`:

    | Option | Values / default | Behavior |
    |---|---|---|
    | `resolve` | boolean; **true** for paths, **false** for query-only strings | resolve `to` relative to the current route |
    | `replace` | boolean; false | `history.replaceState` instead of push |
    | `scroll` | boolean; true | scroll after the route changes |
    | `state` | unknown; undefined | stored on the next location (`useLocation().state`) |

    Numeric `to` is a history delta; `0` does nothing. Query-only strings resolve against the current pathname. **On the server**, path navigation sets a `302` and a `Location` header when a request event exists.
  - `<Navigate href state>`: a redirect component that calls `navigate` during render with `{ replace: true, state }` and renders `null`. `href` can be a function `({ navigate, location }) => string`.
  - `useBeforeLeave(listener)` (navigation blocking). The event has `from` (Location), `to` (string | number), `options`, `defaultPrevented`, `preventDefault()` and `retry(force?)`; `retry(true)` skips the leave handlers. The subscription is owner-scoped.
  - `useIsRouting()`: an accessor that is true while a route transition is in progress.
  - `useLocation()`: `{ pathname, search, hash (includes #), query, state, key }`.
  - `useMatch(() => path, matchFilters?)`: a memo of `{ params, path } | undefined` tested against `useLocation().pathname`.
  - `useCurrentMatches()`: `() => RouteMatch[]`, where each match carries `route.info` (example: breadcrumbs). It is computed after `transformUrl`.
  - `useResolvedPath(() => path)`: resolves against the active route; returns `undefined` if the path cannot be resolved.
- **Links (`<A>`)**: **Supported, with the note "`A` will be deprecated in favor of the native `<a>` element."** Native `<a>` tags already get soft navigation: the router delegates anchor clicks unless `explicitLinks` is set. Source: `R/reference/components/a.mdx`, `R/(1)concepts/(0)navigation.mdx`, `R/reference/components/router.mdx`.

  | `<A>` prop | Type / default | Behavior |
  |---|---|---|
  | `href` | string (required) | resolved against the current route (relative paths allowed); the router base is applied |
  | `replace` | boolean | forwarded to the anchor for router handling (replace history entry) |
  | `noScroll` | boolean | forwarded; suppresses the post-navigation scroll |
  | `state` | unknown | `JSON.stringify`'d onto the anchor, then becomes location state |
  | `activeClass` | string, `"active"` | applied when the href matches the current location |
  | `inactiveClass` | string, `"inactive"` | applied otherwise |
  | `end` | boolean | exact-match only; without it, descendants also match (`/dashboard` is active on `/dashboard/users/1`) |
  | other `<a>` attributes | — | spread onto the native `a`, plus a router `link` attribute |

  Other behavior: an exact match sets `aria-current="page"`. Matching compares normalized pathnames. `<A>` requires router context.
- **Prefetching**: **Supported (intent-based; fetches code and data)**. Source: `R/(4)advanced-concepts/(0)preloading.mdx`, `R/reference/primitives/use-preload-route.mdx`, `R/reference/preload-functions/preload.mdx`, `R/(3)data-fetching/how-to/(0)preload-data.mdx`.
  - Router prop `preload` (boolean, default `true`) turns router-managed anchor preloading on or off.
  - Triggers: **hover**, debounced about **20 ms**, and **focus**, which fires immediately. When triggered, the router "loads the route module and runs its preload routine", i.e. the route's `preload` function with `intent: "preload"`. Results go into the short-lived query cache, reused for **5 s** (see area 3).
  - The second built-in trigger is the start of route rendering: preload runs in parallel with rendering ("render-as-you-fetch").
  - Imperative: `usePreloadRoute()` returns `(url: string | URL, { preloadData?: boolean = false })`. By default it preloads **only the route (code)**. Data `preload` runs "only when `preloadData` is truthy".
  - Nested `lazy()` components outside the route hierarchy are **not** warmed automatically. Call `lazy(...).preload()` yourself.
  - No viewport, "render" or "always" strategies are documented, and there is no per-link prefetch prop.
- **Scroll restoration**: **Partial**. After navigation the router scrolls by default (`scroll: true`; `<A noScroll>` opts out). "Hash scrolling uses the decoded hash target when one is present." `setSearchParams` defaults to `scroll: false`. Saving and restoring scroll position on back/forward is **not documented**. Source: `R/reference/primitives/use-navigate.mdx`, `R/reference/components/router.mdx`, `R/reference/components/a.mdx`.
- **View transitions**: **Not found in docs**.
- **Route-level code splitting**: **Supported**. File-routed components are "lazy-loaded automatically" (hence the root `<Suspense>` requirement). In code routing, use Solid's `lazy(() => import(...))`, which the docs call "best practice". The router loads the module when the route matches or is preloaded. v2 also server-renders CSS from lazy components without FOUC (area 10). Source: `S1/.../(0)routing.mdx`, `R/(4)advanced-concepts/(1)lazy-loading.mdx`, `R/(0)getting-started/(2)config.mdx`.
- **Base path**: **Supported (router-level)**. `<Router base>` (string, default `""`) sets the base used when creating route branches, and `<A>` applies it automatically. `actionBase` (default `"/_server"`) is the base for native form-action handling. A SolidStart- or Vite-level base path is **not documented**. Source: `R/reference/components/router.mdx`.
- **Notable extras**:
  - `transformUrl(url) => string` on Router rewrites the pathname before matching (useful for i18n prefixes or custom normalization).
  - `info: Record<string, any>` on routes stores metadata, exposed via `useCurrentMatches()`.
  - `rootPreload` is a preload for the root route context (`rootLoad` is a deprecated alias). `load` is a deprecated alias for `preload`.
  - `explicitLinks` (default false) intercepts only anchors with the `link` attribute.
  - `HashRouter` reads `window.location.hash.slice(1)`, writes `#`-prefixed paths and listens to `hashchange`.
  - `MemoryRouter` with `createMemoryHistory()` (`get/set/go/listen/back/forward`; starts at `/`; `go` clamps) suits tests and embedded use.
  - `<Router url>` gives the initial URL for the server static router. On the server, `Router` delegates to `StaticRouter`.
  - Since router v0.10 the outlet is `props.children`, not `<Outlet>`, a design choice "to support … Islands/Partial Hydration".
  - Sources: `R/reference/components/*.mdx`, `R/(5)guides/(0)migration.mdx`.

## 2. Rendering modes

- **SSR**: **Supported (default)**. `solidStart({ ssr: true })` is the default. Source: `S2/reference/config/solid-start.mdx`, `S2/reference/server/create-handler.mdx`, `S2/reference/server/start-server.mdx`, `S2/reference/entrypoints/entry-server.mdx`.
  - The server entry `src/entry-server.tsx` default-exports `createHandler(fn, options?, routerLoad?)`. `fn(PageEvent)` returns `<StartServer document={Document} />`.
  - `createHandler` options (an object, or a function of the `PageEvent` returning an object or a Promise of one):

    | Option | Values / default | Behavior |
    |---|---|---|
    | `mode` | `"sync" \| "async" \| "stream"`; **`"stream"`** | `sync` (and `ssr:false`): `renderToString` returns an HTML string. `async`: per docs "returns the `renderToStream` result". `stream`: returns a ReadableStream |
    | `nonce` | string | assigned to the page event (CSP nonces on inline scripts) |
    | `renderId` | string | passed to the render context |
    | `onCompleteShell` | `({ write }) => void` | called when the shell is ready; `write` injects into the stream |
    | `onCompleteAll` | `({ write }) => void` | called when all streamed content is ready |

  - `routerLoad(event: FetchEvent) => Promise<void>` runs before the page event is created. It exists so routers such as TanStack can load server routing state.
  - Request-handling order: **matching API routes run first**; `HEAD` uses the `HEAD` export or falls back to `GET`. Matched UI routes get a page event and render. If rendering sets a `Location` header, the handler "sends or writes a redirect response depending on the render phase". `createHandler` returns a `StartHandler`, which extends H3's `H3` app.
  - `StartServer` reads the request event as a `PageEvent` and registers page assets (`useAssets`). It emits `<!DOCTYPE html>`, then calls the `document` component with `{ assets?, scripts, children }`, and wraps the app in error boundaries. The document is user-authored JSX: html, head with `{assets}`, `<div id="app">{children}</div>` and `{scripts}`.
- **Streaming SSR**: **Supported (default; Suspense-driven out-of-order streaming)**. Source: `R/(3)data-fetching/(1)streaming.mdx`, `S1/(0)building-your-application/(3)data-fetching.mdx`, `S2/(1)advanced/(5)auth.mdx`, `R/reference/data-apis/create-async.mdx`.
  - Reading a query during SSR suspends. Without a `<Suspense>` boundary, "this suspension affects the entire page".
  - Each `<Suspense fallback>` is an independent boundary: the shell and the fallback stream immediately, and "the server streams the final HTML for that section, replacing the fallback" when its data resolves.
  - Opt-out per resource: `createAsync(fn, { deferStream: true })` (also on `createAsyncStore`) makes the server wait for that resource before flushing. Use it for SEO-critical content such as titles, and for anything that must set headers.
  - Hard constraint: once streaming begins, status, headers and cookies are sent and "cannot be changed". Redirects or `useSession` cookie writes after that point raise `Cannot set headers after they are sent to the client.`, and "server-side redirects cannot occur after streaming has started". Fix: `deferStream: true` on that query.
- **Static pre-rendering**: **Supported (via Nitro, build-time crawl or list)**. Source: `S2/(0)building-your-application/(6)route-prerendering.mdx`, `vite.config.ts` (docs site).
  - Configure it in the top-level `nitro.prerender` key of `vite.config.ts`. HTML is generated during `vite build` into `.output/public`.

    | Key | Behavior |
    |---|---|
    | `routes: string[]` | explicit list of paths |
    | `crawlLinks: true` | start at `/` and follow links in the rendered HTML; `routes` adds entry points |
    | `failOnError` | fail the build on a prerender error |
    | retry / concurrency / `ignore` / output-path | Nitro options (links to Nitro docs) |

  - **Dynamic params**: there is no `getStaticPaths`-style API. Dynamic URLs "must be listed explicitly or discovered from another entry route" by the crawler.
  - No per-route `prerender` export is documented. The docs site itself uses `crawlLinks`, `autoSubfolderIndex: false` and regex `ignore`.
  - Other deployment plugins (Netlify, Cloudflare) have no documented prerender path.
- **Client-only / SPA**: **Supported**. Source: `S2/reference/config/solid-start.mdx`, `S2/reference/client/client-only.mdx`, `S1/reference/client/client-only.mdx`, `R/(2)rendering-modes/(0)spa.mdx`, `S2/(2)guides/(1)data-fetching.mdx`.
  - Whole-app SPA: `solidStart({ ssr: false })`. SolidStart "swaps its server and client entrypoints to their SPA implementations while retaining file routing and server functions", so a server is still needed if you use server functions or API routes. With SSR disabled, `createHandler` renders with `renderToString` (the shell).
  - SPA hosting needs a catch-all rewrite to `index.html`: Netlify `_redirects` `/* /index.html 200`, or Vercel `rewrites`.
  - Component-level: `clientOnly(fn, options?)` from `@solidjs/start`:

    | Parameter | Values / default | Behavior |
    |---|---|---|
    | `fn` | `() => Promise<{ default: Component }>` | the component import |
    | `options.lazy` | boolean; falsy | falsy: the client loads `fn` "immediately"; truthy: "defers the import to the returned component" (loads when it renders) |
    | prop `fallback` | JSX | rendered on the server (and until loaded); stripped from the props passed to the loaded component |

    During hydration, rendering waits until mount [v1 ref].
  - Client-only data: Solid `createResource` in a component.
  - There is no per-route `ssr: false` (see below).
- **Partial hydration (islands / server components)**: **Not supported in v2**. `experimental.islands` has type `false`, default `false`, and is "reserved … Islands are not currently supported, so this option only accepts `false`". In v1, `experimental.islands: boolean` existed (experimental): the client `mount` hydrated `solid-island[data-hk]` elements instead of the whole app, loaded per-island CSS from `data-css`, and hydrated `data-when="idle"` islands via `requestIdleCallback`. Server components and server islands: **not found**. Source: `S2/reference/config/solid-start.mdx`, `S1/reference/config/define-config.mdx`, `S1/reference/client/mount.mdx`.
- **Static shell with dynamic holes (PPR-like)**: **Not found in docs**. Closest: the streaming shell plus Suspense holes per request, or a prerendered page plus client-side `createResource` or `clientOnly` holes.
- **Per-route rendering-mode control**: **Not supported as a route-level setting**. `ssr` is global. Prerendering is chosen per path in Nitro config. `createHandler` accepts `options` as a per-request function of the `PageEvent`, which in principle lets `mode` vary per request or path (inference; docs only demonstrate `nonce` this way). `deferStream` adjusts per resource and `clientOnly` per component. Source: `S2/reference/server/create-handler.mdx`.
- **Hydration strategies**: **Full hydration only (v2)**. `src/entry-client.tsx` calls `mount(() => <StartClient />, document.getElementById("app")!)`. `mount` "is Solid's `hydrate` re-exported". `StartClient` renders the generated `solid-start:app` module inside the shared `ErrorBoundary`. Hydration reuses serialized query results: "a matching serialized value from Solid's shared config is loaded instead of calling `fn`". While `createAsync` or `createAsyncStore` runs during hydration, `window.fetch` and `Promise` are temporarily replaced with mocks. Route `preload` functions run during SSR and "resume … on the client during hydration", so keep them pure. No lazy, visible or idle hydration in v2. Source: `S2/reference/client/mount.mdx`, `S2/reference/client/start-client.mdx`, `R/reference/data-apis/query.mdx`, `R/reference/data-apis/create-async.mdx`, `R/(4)advanced-concepts/(0)preloading.mdx`.
- **Notable extras**: the HTML document is fully user-owned JSX in `entry-server`. `onCompleteShell`/`onCompleteAll` can write arbitrary content into the stream. Per-request `nonce` supports strict CSP (area 6). The `// @refresh reload` pragma appears at the top of entry files in examples. v1 also listed SSG/CSR/SSR "sync, async and streaming" as features (`S1/(0)index.mdx`).

## 3. Data loading

- **Where data is fetched**: in components, through `query()`-wrapped fetchers read with `createAsync` / `createAsyncStore`. A route-module `preload` warms them. If the fetcher body contains `"use server"`, it runs only on the server and the client calls it over RPC; otherwise it is isomorphic (runs on the server during SSR and on the client during navigation). There is no separate loader or server-component concept. API routes and Nitro server routes are alternatives for non-UI consumers. Source: `S2/(0)building-your-application/(3)data-fetching.mdx`, `S2/(2)guides/(1)data-fetching.mdx`, `S1/(0)building-your-application/(3)data-fetching.mdx`, `R/(3)data-fetching/(0)queries.mdx`.
- **`query(fn, name)`** (Solid Router; `cache` is a **deprecated alias**). Source: `R/reference/data-apis/query.mdx`, `R/reference/data-apis/cache.mdx`, `R/(3)data-fetching/(0)queries.mdx`.

  | Aspect | Behavior |
  |---|---|
  | `fn` | any function; its args become part of the key and "should serialize consistently with `JSON.stringify`" |
  | `name` | **required** base key; same name + same serialized args = same entry |
  | key format | `name` + `JSON.stringify(args)`, with plain-object keys **sorted** |
  | `.key` | base key, targets every arg set |
  | `.keyFor(...args)` | key for one arg list |
  | `fn.GET` | if `fn` has a `GET` property, `fn.GET` is wrapped instead (GET-method server functions, area 5) |
  | statics | `query.get(key)` (resolved value), `query.set(key, nonPromiseValue)`, `query.delete(key) => boolean`, `query.clear()` act on the *active* cache |
  | reuse: preload | preloaded results reused for **5000 ms** |
  | reuse: subscribers | entries stay reusable while any subscriber is active (dedupe across components) |
  | reuse: back/forward | native history navigation reuses entries without calling `fn` |
  | reuse: SSR | repeated calls with the same key reuse one **request-scoped** entry |
  | reuse: hydration | serialized server value used instead of calling `fn` |
  | storage | server: request event's router cache; client: module-level `Map` |
  | GC | client entries with no subscribers deletable after **180000 ms** (3 min) |
  | Response returns | headers of a returned `Response` are **copied onto the SSR response**; a `Location` header gives client navigation, or a **302** during SSR |
  | errors | a thrown error goes to the nearest `<ErrorBoundary>` |
  | types | `CachedFunction<T>`: Response-typed returns are narrowed (`NarrowResponse`) |

- **`createAsync(fn, options?)`**: wraps `createResource`. Returns `AccessorWithLatest<T>`: `value()` suspends, `.latest` returns the latest value. Source: `R/reference/data-apis/create-async.mdx`.

  | Option | Type / default | Behavior |
  |---|---|---|
  | `name` | string | debug name |
  | `initialValue` | T | returned before the first resolve; also narrows the type to non-undefined |
  | `deferStream` | boolean; **false** | SSR waits for this resource before flushing (area 2) |

  `fn(prev)` receives the previous latest value (read untracked). **Synchronous reactive reads inside `fn` are tracked**, so changing a signal or param re-runs it. The resource integrates with Suspense (pending) and ErrorBoundary (errors).
- **`createAsyncStore(fn, options?)`**: same as `createAsync`, plus `reconcile?: ReconcileOptions`. The value lives in a Solid store: initial value via `structuredClone(initialValue)`, and each resolve is `structuredClone`d and merged with `reconcile`, so updates are fine-grained for large arrays and objects. `fn` receives `unwrap(resource.latest)`. Source: `R/reference/data-apis/create-async-store.mdx`.
- **Loader execution model**: Source: `R/reference/preload-functions/preload.mdx`, `R/(2)rendering-modes/(1)ssr.mdx`, `R/(4)advanced-concepts/(0)preloading.mdx`, `S2/.../(3)data-fetching.mdx`.
  - Route `preload({ params, location, intent })` is called during route-context creation. `intent` is one of `"initial" | "native" | "navigate" | "preload"`.
  - Its return value is passed to the route component as `props.data`.
  - It "loads in parallel to the routes" (render-as-you-fetch).
  - A route component's static `preload` method runs **before** the route-level `preload`.
  - On the server, preload runs in the initial render; on the client it resumes during hydration.
  - Without a `preload`, fetches start when the component first reads the query, so nested lazy routes can waterfall (inference from the preloading rationale).
  - Server vs client loaders: no distinct API. `"use server"` inside the fetcher decides where the body runs. The `query` wrapper itself always runs on both sides.
  - Warning: put `"use server"` **inside** the query function, not at file level. A file-level directive "turns the whole module, including the `query` wrapper that also runs on the client, into a server reference". Source: `S2/reference/server/use-server.mdx`.
- **Request deduplication**: **Supported**. It is keyed by query name and args, and covers concurrent component calls, preload vs. render, and SSR within a request. Source: `R/(3)data-fetching/(0)queries.mdx`, `R/reference/data-apis/query.mdx`.
- **Passing server data to the client**: **Supported (automatic serialization)**. Source: `S2/(1)advanced/(4)serialization.mdx`, `S1/(1)advanced/(4)serialization.mdx`, `S2/reference/config/solid-start.mdx`, `S2/(1)advanced/(3)return-responses.mdx`.
  - SSR query results are embedded for hydration. Server function args and returns are serialized with **Seroval**.
  - `serialization.mode`: `"json"` (**v2 default**; client uses `JSON.parse`, no `eval`, CSP-safe) or `"js"` (smaller and faster; requires `unsafe-eval`; v1's default).
  - Supported by default: Seroval types plus the web plugins `AbortSignal`, `CustomEvent`, `DOMException`, `Event`, `FormData`, `Headers`, `ReadableStream`, `Request`, `Response`, `URL`, `URLSearchParams` [v1 doc].
  - **Temporal** values are preserved in v2. No polyfill is installed; a global `Temporal` must exist on both client and server (Node ≥ 26, Deno ≥ 2.7, Bun no stable release). Use `import "temporal-polyfill/global"` in both entries.
  - Limits: `RegExp` disabled by default; JSON mode max depth **64** [v1 doc].
  - Custom types: `serialization.plugins` is a module path whose default export is an array of plugins built with `createPlugin` (also exported: `OpaqueReference` and plugin types) from `@solidjs/start/serialization`. The module is bundled into **both** builds, so it must not import server-only code. Built-in plugins run first. Custom plugins **do not affect** the `solid-js/web` hydration payload, only server-function and action payloads.
  - **Raw transfer bypass**: `FormData`, `URLSearchParams`, `Uint8Array`, `ArrayBuffer`, `Blob`, `File` and `string` skip Seroval in both directions, giving smaller payloads.
  - Promises nested in returned objects stream: e.g. `json({ hello: new Promise(...) })`. v1 says payloads are streamed "to keep responses responsive".
- **Client-side data cache**: **Supported (router query cache)**: a module-level map with the 5 s preload window, back/forward reuse and 3-minute GC described above. Manual writes via `query.set`. The docs recommend TanStack Query for "automatic background re-fetching or infinite queries". Source: `R/reference/data-apis/query.mdx`, `S2/(2)guides/(1)data-fetching.mdx`.
- **Deferred / streamed data**: **Supported**. Unawaited `createAsync` reads inside `<Suspense>` stream (area 2). Promises inside server-function return values stream. Blocking is opt-in with `deferStream`. Source: `R/(3)data-fetching/(1)streaming.mdx`, `S2/(1)advanced/(3)return-responses.mdx`.
- **Dependency tracking & invalidation**: **Supported**. Source: `R/(3)data-fetching/(2)revalidation.mdx`, `R/reference/data-apis/revalidate.mdx`, `R/(1)concepts/(8)actions.mdx`.
  - Reactive: `createAsync` re-runs when the signals it read change.
  - Manual: `revalidate(key?, force = true)` from `@solidjs/router`. It runs inside `startTransition`. With no key, everything matches. String or array keys match by **prefix** (`q.key` = all arg sets; `q.keyFor(a)` = one). `force: true` marks entries as misses before retriggering; `false` retriggers without touching timestamps. Entries **without active subscribers are not refetched**. Returns a Promise that resolves when the transition completes.
  - After actions: automatic (area 4).
- **Access to request context**: **Supported**. Source: `S2/(1)advanced/(2)request-events.mdx`, `S2/(2)migrating-from-v1.mdx`, `S1/(1)advanced/(2)request-events.mdx`.
  - `getRequestEvent()` (from `solid-js/web`) works in SSR, API, middleware, query and action code; it returns `undefined` outside a request. It exposes `event.request`, `event.response`, `event.locals` and `event.nativeEvent` (an H3 v2 event with Web `req`/`res`).
  - Context-aware helpers in `@solidjs/start/http` (server-only) need no event argument: `getCookie`, `setCookie`, `readBody`, `getQuery`, `getRequestHeader`, `setResponseHeader`, `useSession` and related helpers. In v1 they came from `vinxi/http` and took `event.nativeEvent`.
  - Async-local-storage-based. v1 needed `nodejs_compat` on Cloudflare (`S1/reference/config/define-config.mdx`).
- **Notable extras**: `getServerFunctionMeta()` from `@solidjs/start` returns `{ id }` (`locals.serverFunctionMeta`) for the executing server function, or `undefined` outside a request (`S2/reference/server/get-server-function-meta.mdx`). The `preload` `intent` argument lets code tell hover-preloads from real navigations. `props.data` gives the old "route data" pattern; turning preload off with `<Router preload={false}>` plus a Context reproduces v0.9 `data` functions (`R/(5)guides/(0)migration.mdx`).

## 4. Mutations

- **Progressive enhancement (no-JS forms)**: **Supported**. Source: `R/(1)concepts/(8)actions.mdx`, `R/reference/data-apis/action.mdx`, `R/reference/components/router.mdx`, `S2/(2)guides/(2)data-mutation.mdx`.
  - Render `<form action={myAction} method="post">`. Requirements: `method="post"` is **mandatory**, and for SSR the action **must have a unique name** (second argument), which is used "to identify and serialize the action across the client and server". The action's `.url` is the form's action URL. Native form handling uses the Router's `actionBase` (default `"/_server"`).
  - Argument type: the action receives **`FormData` for `multipart/form-data` forms and `URLSearchParams` otherwise** (reference page). The concept and guide pages simply say `FormData`, so the docs are inconsistent here.
  - How the server responds to a no-JS POST (redirect-back vs. render) is **not described**.
- **Server functions / RPC / actions**: **Supported**. Source: `S2/reference/server/use-server.mdx`, `S2/reference/config/solid-start.mdx`, `R/reference/data-apis/action.mdx`, `S2/(1)advanced/(5)auth.mdx`.
  - `"use server"` works as a **function-level** directive (first statement in the body) or a **file-level** directive (every export becomes a server function). The compiler transforms references with a client runtime in client builds and a server runtime in SSR and server-function builds, and adds valid modules to a **server function manifest**.
  - Any server function is a plain async function callable from client code as RPC. It does not need to be in an action or query.
  - `serverFunctions.filter: { include?, exclude? }` (FilterPattern) controls which files the compiler scans. Default: source JS/TS under `src`, excluding `node_modules`. Use it for monorepo packages, for example.
  - `action(fn, name?)` or `action(fn, { name?, onComplete? })` returns an `Action<T, U>` with:

    | Member / option | Behavior |
    |---|---|
    | `name` | stable string used to build `.url` (required for SSR forms) |
    | `onComplete(submission)` | called with a submission snapshot after the response is handled |
    | `.url` | form `action` value and the key that submissions match on; stringifying an action with no URL **throws** |
    | `.with(...args)` | new action with **leading args prefilled**; form data is appended last; works in no-JS forms |
    | calling | adds a submission (`input`, `url`, `result`, `error`, `pending`, `clear`, `retry`) to the router's submissions signal |
    | client registration | actions register by URL in an action map and are removed on owner cleanup |

  - `useAction(action)` returns a router-bound caller `(...args) => Promise<NarrowResponse<U>>` for non-form triggers. It "depend[s] on client-side JavaScript" and is not progressively enhanced.
- **Pending, error and validation-error state**: **Supported**. Source: `R/reference/data-apis/use-submission.mdx`, `R/reference/data-apis/use-submissions.mdx`, `R/(1)concepts/(8)actions.mdx`, `S2/(2)guides/(2)data-mutation.mdx`.
  - `useSubmission(action, filter?)` returns a proxy over the **latest** matching submission:

    | Field | Behavior |
    |---|---|
    | `input` | args array (`input[0]` is the FormData) |
    | `result` | typed return value |
    | `error` | thrown or rejected value (`any`) |
    | `pending` | boolean or undefined |
    | `url` | action URL |
    | `clear()` | clears the latest submission (no-op if none) |
    | `retry()` | **always a no-op** on this proxy |

  - `useSubmissions(action, filter?)` returns an array-like proxy of all matching records plus `.pending`, which is true while any record lacks a result. Each record has a working `retry()` (re-runs the same call) and `clear()` (removes it). `filter(input)` selects records by input.
  - Expected errors: **return** objects such as `{ ok: false, errors: {...} }`, giving a typed `result`. Unexpected errors: **throw**; they arrive untyped in `error`. Schema validation is user-land; the guide shows Valibot `safeParse`.
  - **Pitfall**: if an action returns `undefined` or `null`, its submission is removed from the list on completion. A later success can therefore leave a *stale previous error* showing. "Always return a value" (e.g. `{ ok: true }`).
- **Optimistic UI**: **Partial (manual)**. While `submission.pending`, derive UI from `submission.input`. On failure `pending` turns false and the derived UI reverts; on success the auto-revalidated query replaces it. Use `useSubmissions` for several concurrent optimistic items. There is no cache-level optimistic API; TanStack Query is suggested for that. Source: `R/(1)concepts/(8)actions.mdx`, `S2/(2)guides/(2)data-mutation.mdx`.
- **Data refresh after mutation**: **Automatic, configurable**. Source: `R/(1)concepts/(8)actions.mdx`, `R/reference/data-apis/action.mdx`, `R/reference/response-helpers/*.mdx`, `R/reference/data-apis/revalidate.mdx`.
  - After a successful action, Solid Router "automatically revalidates all queries used in the same page" (all active queries).
  - Control it by returning or throwing response helpers:
    - `reload({ revalidate, headers, status (200), statusText })`
    - `json(data, { revalidate, headers, status (200), statusText })`, which also returns data
    - `redirect(url, { revalidate, … })`
  - `revalidate: string | string[]` of query keys; `[]` **disables** revalidation. Helpers serialize it into an **`X-Revalidate`** response header. Without the header, the action passes `undefined`, which revalidates everything.
  - Manual: `revalidate(keys)` anywhere.
- **Single-flight mutations**: **Supported (SolidStart-specific)**. Source: `S1/(0)building-your-application/(4)data-mutation.mdx`, `R/reference/components/router.mdx`.
  - When the action is a server function and the affected queries are **preloaded** by the route's `preload` (on the redirect destination's route if the action redirects), one POST both runs the mutation and returns the revalidated query data. "SolidStart can trigger the revalidation on the server and stream the result back to the client in the same response."
  - Router prop `singleFlight` (boolean, default `true`) controls it.
  - Queries not covered by `preload` refetch in a second round trip (inference).
- **Redirects after mutation**: **Supported**. `throw redirect(url)` or `return redirect(url)`. `init` may be a number (status) or an object; the default status is **302**. Sets `Location`; it can carry `revalidate` keys for the destination; the return type is `never`, so it does not pollute the action's result type. A `Location` header on an action response triggers client navigation. Source: `R/reference/response-helpers/redirect.mdx`, `S2/(1)advanced/(3)return-responses.mdx`.
- **File uploads**: **Supported (basic)**. Use `<form enctype="multipart/form-data">`. `File`, `Blob`, `FormData`, `ArrayBuffer` and `Uint8Array` pass to and from server functions **without Seroval**. No upload size limits, progress or streaming-upload helpers are documented. Source: `R/(1)concepts/(8)actions.mdx`, `S2/(1)advanced/(4)serialization.mdx`.
- **Multiple actions per page**: **Supported**. Each action is identified by its URL or name. `.with()` variants are separate bound actions. `useSubmission(action, filter)` tells instances apart by input. Source: `R/reference/data-apis/action.mdx`, `R/reference/data-apis/use-submissions.mdx`.
- **CSRF protection built in**: **Not supported**. The Security guide gives a *recipe*: middleware that blocks unsafe methods (anything but `GET`, `HEAD`, `OPTIONS`, `TRACE`) whose `Origin` (or, over TLS without Origin, `Referer`) is not same-origin or allow-listed, returning 403. It notes "both of these headers can be forged" and recommends the double-submit-cookie pattern. Source: `S2/(2)guides/(0)security.mdx`.
- **Notable extras**: `serverFunctions.onError` sanitizes and reports thrown server-function values (area 7). `submission.retry()` re-runs a call. Action `onComplete` hook. Actions and queries are usable without SolidStart (client-only), and `"use server"` upgrades them to RPC.

## 5. Caching & revalidation

- **Page/HTML caching**: **Not supported as a framework feature**. Prerendered HTML (area 2) is the only built-in static cache. Per-response cache headers can be set from components with `<HttpHeader name="cache-control" value=...>`, from middleware via `event.res.headers`, from queries (returned Response headers are copied onto the SSR response) and with `setResponseHeader`. Nitro `routeRules` (cache/swr/isr) are **not mentioned** in these docs (from memory, unverified: Nitro supports them). Source: `S2/reference/server/http-header.mdx`, `R/reference/data-apis/query.mdx`, `S2/(1)advanced/(0)middleware.mdx`.
- **Time-based revalidation (ISR)**: **Not found in docs**.
- **On-demand revalidation (path / tag)**: **Server-side: not supported** (there is no server data or page cache). **Client-side: supported by key**. `revalidate(key | key[])` does prefix matching on query keys, so the `query` name acts like a tag and `keyFor` like a single entry. Actions can also target keys via `X-Revalidate`. Source: `R/reference/data-apis/revalidate.mdx`.
- **Data-level / function-level caching**: **Partial**. `query()` memoizes per request on the server (request-scoped dedupe) and per client session (module map). There is **no cross-request server cache** and no TTL config. The fixed 5 s preload reuse and 180 s GC values are documented constants, not options. Source: `R/reference/data-apis/query.mdx`.
- **Client navigation cache**: **Supported** (query cache; back/forward reuse without refetch; intent preloads reused for 5 s). Route modules are cached by the bundler or loader. Source: `R/reference/data-apis/query.mdx`.
- **HTTP cache-header helpers**: **Partial**.
  - `HttpHeader` (from `@solidjs/start`):

    | Prop | Type | Behavior |
    |---|---|---|
    | `name` | string (required) | header name |
    | `value` | string (required) | header value |
    | `append` | boolean | true → `appendHeader(name, value)`; else `setHeader` |

    Server-only; renders `null` on the client. On **cleanup**, for example when the component unmounts during SSR, it removes its own header value unless the event has completed or been handled.
  - `json(data, { headers })` and `GET()` server functions. `GET(fn)` returns `fn.GET`, so a `"use server"` function is callable via **HTTP GET**; the docs' example sets `cache-control: max-age=60` on it, making CDN or browser caching of RPC possible.
  - No dedicated cache-control API.
  - Source: `S2/reference/server/get.mdx`, `S2/(1)advanced/(3)return-responses.mdx`.
- **Preview / draft mode**: **Not found in docs**.
- **Notable extras**: `revalidate(…, force=false)` retriggers subscribers without invalidating timestamps. `query.set/get/delete/clear` allow manual cache seeding (e.g. after a mutation). Cache entries without subscribers are not refetched by `revalidate`.

## 6. Server & API

- **API routes / endpoints (per HTTP method)**: **Supported**. Source: `S2/(0)building-your-application/(1)api-routes.mdx`, `S1/(0)building-your-application/(1)api-routes.mdx`, `S2/reference/server/create-handler.mdx`.
  - Files in `src/routes` (any folder; `api/` is just a convention) that export named method handlers: `GET`, `POST`, `PATCH`, `DELETE`, `HEAD`, etc. They follow the same path rules as UI routes (`[id]`, `[...slug]`, …).
  - Handlers receive an `APIEvent` (from `@solidjs/start/server`):

    | Field | Meaning |
    |---|---|
    | `request` | Web `Request` |
    | `params` | dynamic params |
    | `response` | mutable response stub |
    | `locals` | request-scoped locals |
    | `nativeEvent` | H3 v2 event |

    v1 also documented `fetch`, an internal fetch for calling other API routes without an origin; it is not listed in v2.
  - Return value: v2 examples return a `Response` / `Response.json`. v1 said "JSON or a `Response`" and that returning nothing from `GET` "will fallback to UI route handling".
  - **HEAD falls back to GET** when no `HEAD` export exists.
  - **Precedence**: "API routes are prioritized over UI route alternatives". To overlap at one path, use `Accept` headers [v1]. API routes are matched before page rendering in `createHandler`.
  - One handler can serve several methods (`export const POST = handler`).
  - No `ALL`/catch-all-method export and no automatic `OPTIONS`/405 handling is documented.
  - Recipes: GraphQL (`graphql()`), tRPC (`fetchRequestHandler` in `api/trpc/[trpc].ts`) [v1].
- **Middleware**: **Supported (global only)**. Source: `S2/(1)advanced/(0)middleware.mdx`, `S2/reference/server/create-middleware.mdx`, `S1/(1)advanced/(0)middleware.mdx`, `S1/reference/server/create-middleware.mdx`.
  - Registration: `solidStart({ middleware: "./src/middleware/index.ts" })`, a module that default-exports `createMiddleware(...)` from `@solidjs/start/middleware` (server-only entry).
  - **v2 (preferred) form**: `createMiddleware(Middleware[])`, an array of **H3 v2 middleware** `(event, next) => Response | Promise<Response> | …`.
    - **Onion model**: code before `await next()` runs in declaration order; code after it runs in reverse order as the response unwinds.
    - **Returning a `Response` short-circuits** the chain; `redirect()` from Solid Router works here.
    - Access `event.req` (Web Request) and `event.res.headers`.
    - SolidStart "decorates configured middleware with its request context", so `getRequestEvent()` (and `locals`) work inside.
  - **Deprecated v1 form** `createMiddleware({ onRequest?, onBeforeResponse? })`, each a function or array, still works:
    - `onRequest(event: FetchEvent)` runs before the route handler. Use it to set `locals`, modify request headers or redirect early. Returning a `Response` ends processing; "only `Response` objects can be returned … any other value will result in an error".
    - `onBeforeResponse(event, response: { body? })` runs after the handler. Use it to set or modify response headers or body.
    - Arrays run sequentially in declared order. In 2.0.0, `onBeforeResponse` arrays run in **declared** order; earlier prereleases reversed them, so remove manual workarounds.
  - **Scope**: global; there is **no per-route middleware** file or config, so branch on `pathname` yourself.
  - **Coverage caveat**: v1 says middleware "does *not* run on every request, especially during client-side navigations". v2 says "client-side navigation can reuse data and server functions independently of a page request". Either way, do not rely on it for authorization; enforce checks in each query, action and API route.
  - Experimental: `decorateHandler(fn)` / `decorateMiddleware(fn)` from `@solidjs/start/server` give Solid's request context (`getRequestEvent()`) to custom H3 or Nitro handlers that run outside the configured chain.
  - Documented uses: logging and timing, redirects (e.g. a 301 map), CSP nonce headers, CORS (preflight `OPTIONS` handling + `Vary`), CSRF origin checks, cookies.
- **Request context (cookies, headers, locals)**: **Supported**. Source: `S2/(1)advanced/(2)request-events.mdx`, `S2/(1)advanced/(0)middleware.mdx`, `S2/(1)advanced/(1)session.mdx`, `S2/(2)migrating-from-v1.mdx`.
  - `getRequestEvent()` returns `{ request, response, locals, nativeEvent, … }`.
  - `locals` is typed by augmenting `declare namespace App { interface RequestEventLocals {...} }`, with `"types": ["@solidjs/start/env"]` in tsconfig.
  - `@solidjs/start/http` (server-only; client imports fail in dev or build): cookies (`getCookie`, `setCookie(name, value, { httpOnly, secure, sameSite, maxAge… })`), headers (`getRequestHeader`, `setResponseHeader`), body and query (`readBody`, `getQuery`), and encrypted cookie sessions (`useSession({ name, password ≥32 chars, cookie })` → `{ data, update(), clear() }`; also `getSession`, `updateSession`, `clearSession`, `sealSession`, `unsealSession`).
  - Nitro v3 / H3 v2 means Web-standard `Request`/`Response`/`Headers`. Code using H3 v1 `event.node`/`event.web`/`send*` helpers must migrate.
- **Streaming responses and SSE**: **Partial / not documented as a feature**. API routes return Web `Response`, so `ReadableStream` bodies follow from the standard (inference). Server functions can return `ReadableStream`, which the default Seroval plugins support [v1 serialization doc], and nested promises stream. There is no SSE helper. Source: `S1/(1)advanced/(4)serialization.mdx`, `S2/(1)advanced/(3)return-responses.mdx`.
- **Running work after the response (waitUntil / after)**: **Not found for request handlers**. Only Nitro tasks show `context.waitUntil?.(promise)` inside `defineTask().run` (experimental; area "Out-of-scope"). Source: `S2/(2)guides/(4)background-tasks.mdx`.
- **Server-only code boundaries**: **Supported (several mechanisms)**. Source: `S2/reference/config/solid-start.mdx`, `S2/reference/server/use-server.mdx`, `S2/(1)advanced/(4)serialization.mdx`.
  - `"use server"` (function- or file-level) for RPC boundaries.
  - **Marker imports** `import "server-only"` / `import "client-only"`: "an accidental import from the wrong Vite environment" fails **during development or build**. `@solidjs/start/http` and `@solidjs/start/middleware` are already marked server-only.
  - **Env virtual modules** (`solidStart({ env })`):

    | Module | Default exposure | Notes |
    |---|---|---|
    | `env:server` | build-time vars prefixed `SERVER_` | **fails if imported by client code** |
    | `env:client` | build-time vars prefixed `CLIENT_` | available in both environments |
    | `env:server/runtime` | runtime `process.env` | server-only |

    Options: `env.server.prefix`, `env.client.prefix`, `env.server.runtime` (`"node" | "cloudflare-workers" | "netlify-edge" | custom loader source code`), and `env.server.load` / `env.client.load` for custom build-time values in the current mode.
  - Bundling rules: the `serverFunctions.onError` module is bundled **only into the server**; `serialization.plugins` is bundled into **both**.
- **Notable extras**:
  - Two server-routing systems coexist. SolidStart API routes live in `src/routes`. **Nitro file routes** live in `server/routes` (set `nitro.serverDir: "./server"`) and use `defineHandler` / `defineWebSocketHandler` from `nitro`. Source: `S2/(1)advanced/(6)websocket.mdx`.
  - The server entry is an H3 app (`StartHandler extends H3`).
  - `routerLoad` hook for custom routers.
  - CORS recipe in `S2/(2)guides/(0)security.mdx`.

## 7. Loading & error states

- **Route-level loading UI**: **Supported via Suspense (no file convention)**. Place `<Suspense fallback>` anywhere. The root `<Suspense>` in `Router root` is required for lazy file routes. `useIsRouting()` gives a global "navigating" flag. Navigation and `revalidate` run inside Solid **transitions** (the router "has Solid's transitions included"). There is **no `loading.tsx`-style convention**. Source: `S2/(2)guides/(1)data-fetching.mdx`, `R/(2)rendering-modes/(1)ssr.mdx`, `R/reference/primitives/use-is-routing.mdx`, `R/reference/data-apis/revalidate.mdx`.
- **Error boundaries**: **Supported via Solid `<ErrorBoundary fallback>` (no file convention)**. `createAsync` propagates errors to the nearest boundary. Framework-level boundaries: `StartClient` wraps the app in a shared `ErrorBoundary`, and `StartServer` "wraps the app with error boundaries". Per-segment `error.tsx`-style files: **not found**. Root or global error page customization: not documented beyond wrapping `Router root` in your own `ErrorBoundary`. Source: `R/(3)data-fetching/how-to/(1)handle-error-and-loading-states.mdx`, `S2/reference/client/start-client.mdx`, `S2/reference/server/start-server.mdx`.
- **404 / not-found handling**: **Supported (by convention)**. Use a catch-all route (`[...404].tsx` or code `*404`) that renders `<HttpStatusCode code={404} />` to set the HTTP status during SSR. `HttpStatusCode` (from `@solidjs/start`): Source: `S2/reference/server/http-status-code.mdx`, `R/(1)concepts/(3)catch-all.mdx`.

  | Prop | Type | Behavior |
  |---|---|---|
  | `code` | number (required) | sets `event.response.status` |
  | `text` | string | sets `event.response.statusText` |

  Cleanup resets the status to `200` if the event has not completed, so a 404 component that unmounts during SSR does not leak its status. It renders `null` on the client. With streaming, the status must be set before the shell flushes; use `deferStream` or put the status component outside Suspense (inference from area 2 header rules).
- **Helpers (redirect / notFound / error)**: **Partial**. `redirect(url, init)` (default 302, `Location`, optional `X-Revalidate`), `reload(init)`, `json(data, init)` (`Content-Type: application/json`, `JSON.stringify`, `customBody()` returns the raw data, `X-Revalidate`). These are Response objects you can **return or throw** from queries, actions, middleware and server functions. `HttpStatusCode` and `HttpHeader` are components. **No `notFound()` or `error(status)` helper** is documented. Source: `R/reference/response-helpers/*.mdx`, `S2/(1)advanced/(3)return-responses.mdx`.
  - Query redirect during SSR: sets **302**. Redirect after streaming has started: impossible, so use `deferStream`. `createHandler` turns a `Location` header set during render into a redirect "depending on the render phase".
- **Expected vs unexpected errors**: **Supported (convention + hook)**. Actions: return typed result objects for expected failures; thrown values become `submission.error` (`any`). Server functions: `serverFunctions.onError` (module path) handles **values thrown by server functions before serialization**. Source: `R/(1)concepts/(8)actions.mdx`, `S2/reference/config/solid-start.mdx`.

  | Handler return | Effect |
  |---|---|
  | `undefined` / `null` | original thrown value sent |
  | a `Response` | passed through unchanged (keeps a thrown `redirect()` working) |
  | any other value | sent **instead** of the original, serialized with its own properties (e.g. a generic `Error`) |
  | handler throws or rejects | original value sent, as if no handler existed |

  It may be `async`; it is awaited, so you can flush to a monitoring service. **Only network-originated calls** reach it (direct server-side calls do not). Typed as `ServerFunctionErrorHandler` from `@solidjs/start/server`.
- **Error reporting hooks**: **Partial**. `serverFunctions.onError` covers server functions. No documented global hook exists for SSR render errors, API route errors or client errors; middleware could wrap `next()` (inference). The dev toolbar shows "application errors" in development (area 12).
- **Notable extras**: `useSubmission().clear()` resets error state. `useBeforeLeave` can block navigation away from dirty forms.

## 8. Type safety

- **Typed links and params**: **Not supported**. `href` and `navigate` take strings. `useParams<T>()` / `RouteSectionProps<T>` use manual generics, and params are `string | undefined`. `MatchFilters<P>` keys are inferred from a literal path in code routing only. Source: `R/reference/components/a.mdx`, `R/reference/primitives/use-params.mdx`, `R/reference/primitives/use-match.mdx`.
- **Typed loader/server data to components**: **Supported (inferred)**. `createAsync(() => getPosts())` infers from the query's return type. `query` returns `CachedFunction<T>`, whose return is `Promise<NarrowResponse<P>>`: `json<T>()` contributes `T`, while `redirect()`/`reload()` return `CustomResponse<never>` and so "will not impact the return value" type. `initialValue` removes `undefined`. Route `preload` return type flows to `props.data` via `RouteSectionProps<T>` (manual generic). Source: `R/reference/data-apis/query.mdx`, `R/reference/data-apis/create-async.mdx`, `S2/(1)advanced/(3)return-responses.mdx`, `R/reference/preload-functions/preload.mdx`.
- **Typed server calls**: **Supported (inferred end-to-end)**. `"use server"` functions are ordinary TS functions, so args and returns are checked at call sites. `Action<T, U>` keeps arg types (`.with` prefill). `useAction` returns `Promise<NarrowResponse<U>>`. `submission.result` is typed while `submission.error` is `any`, which is why the docs recommend returning errors. The serialization round-trip (e.g. Temporal, custom classes via plugins) is not reflected in types beyond what TS infers. Source: `R/reference/data-apis/action.mdx`, `R/reference/data-apis/use-action.mdx`, `R/(1)concepts/(8)actions.mdx`.
- **Generated types**: **None (no codegen step)**. Types ship in `@solidjs/start/env` (add to `compilerOptions.types`). Augment `App.RequestEventLocals` for locals. `RouteDefinition` is used with `satisfies` for the `route` export. Source: `S2/(1)getting-started.mdx`, `S2/(1)advanced/(2)request-events.mdx`.
- **Typed search params**: **Partial**. Only the generic `useSearchParams<T extends SearchParams>()`, where values are strings or string arrays; setters accept primitives and stringify them. No validation or coercion. Source: `R/reference/primitives/use-search-params.mdx`.
- **Notable extras**: `useLocation<S>()` types `location.state`. `ServerFunctionErrorHandler` type. `APIEvent` type. `createPlugin<T, Node>` typed Seroval plugins.

## 9. Metadata & SEO

- **Head/meta management per route**: **Supported via the separate `@solidjs/meta` package** ("SolidStart does not bundle a metadata API"). Source: `S2/(0)building-your-application/(5)head-and-metadata.mdx`, `S1/(0)building-your-application/(5)head-and-metadata.mdx`.
  - Put `<MetaProvider>` in `Router root`. It collects tags during SSR and updates them on client navigation.
  - Components named in the docs: `Title`, `Meta` (`name`/`property`/`content`), `Link` (e.g. `rel="stylesheet"`), `Style`.
  - Tags rendered by a route are **removed or updated when the route changes**.
  - A route-level `Meta` **overrides** the same tag set higher up (v1 says route `Meta` overrides `Meta` in the root `Head`).
  - Composition: wrap `Title` in your own component to add a site suffix.
  - Full component list and props: **not in this sparse clone** (Solid Meta docs live in `src/routes/solid-meta`, not checked out). From memory, unverified: `Base`, `Stylesheet` and a `useHead` primitive also exist.
- **Metadata from loaded data**: **Supported**. Render `<Title>{data().name}</Title>` inside `Show`/`Suspense` using the same query as the page. For crawler-visible values in the initial HTML, use `deferStream: true` on that query ("Some search engine crawlers may not wait for streamed content"). Source: `S2/.../(5)head-and-metadata.mdx`, `R/(3)data-fetching/(1)streaming.mdx`.
- **Sitemap / robots / manifest generation**: **Not supported by SolidStart**. The docs suggest putting `robots.txt`, sitemaps and manifest files in `public/`. The solid-docs site itself gets `sitemap`, `robots` and `llms` output from the third-party SolidBase plugin, which is not a SolidStart feature. Source: `S2/(0)building-your-application/(7)static-assets.mdx`, `vite.config.ts`.
- **Open Graph image generation**: **Not found in docs** (OG tags via `<Meta property="og:image">` only).
- **Canonical, etc.**: **Not specifically documented**. Achievable with `<Link rel="canonical">` from `@solidjs/meta` (from memory, unverified). `lang` and other `<html>` attributes are set in the user-owned `entry-server` document.
- **Notable extras**: the whole HTML document (`<html>`, static `<head>` tags, favicon) lives in `entry-server.tsx` JSX, so per-site static head content needs no API.

## 10. Assets & styling

- **Image optimization**: **Not supported / not found**. Only Vite asset imports (`import logo from "./solid.png"` gives a hashed URL such as `/assets/solid.2d8efhg.png`) and `public/` files at stable URLs. No image component, formats, responsive or remote images. Source: `S2/(0)building-your-application/(7)static-assets.mdx`.
- **Font optimization**: **Not found** (fonts as public or static assets).
- **Third-party script loading**: **Not supported as an API**. Add `<script>` tags in the `entry-server` document (the docs site adds `<script src="/scripts/browser-specific.js" type="module">`), or register a service worker in `entry-client` (`navigator.serviceWorker.register("/sw.js")` guarded by `import.meta.env.PROD`). CSP nonces: `createHandler` `nonce` option. Source: `src/entry-server.tsx` (docs site), `S2/(2)guides/(3)service-workers.mdx`, `S2/(2)guides/(0)security.mdx`.
- **CSS support**: **Supported (Vite-native)**. Source: `S2/(0)building-your-application/(2)css-and-styling.mdx`, `S1/(0)building-your-application/(2)css-and-styling.mdx`, `S1/(1)getting-started.mdx`.
  - Global CSS via ESM import anywhere in the tree.
  - **CSS Modules** with `.module.css`, `.module.scss` and `.module.sass` (use `styles.card`; hard-coded `class="card"` will not match).
  - Preprocessors: Sass via Vite.
  - Tailwind: `@import "tailwindcss"` example; `with-tailwindcss` template; the docs site uses `@tailwindcss/vite`.
  - CSS-in-JS and other approaches: deferred to Solid's styling guide; templates include `with-solid-styled` and `ts-unocss`.
  - **v2 CSS pipeline changes**:
    - SSR CSS dedup works "more consistently".
    - Route CSS HMR is managed by Vite.
    - **CSS of `lazy()` components is server-rendered, with no FOUC.**
    - Client navigation mounts new CSS via Vite.
    - Server HTML no longer embeds the whole assets manifest.
    - Client navigation **no longer unmounts old CSS**, matching Vite's native behavior.
  - **Consequence**: route-specific global styles **accumulate and overlap** after navigation. Documented workarounds: scope with `body:has(main[data-route="about"])`, or import `./about.css?url` and mount it with `<Link rel="stylesheet" href={url}>` from `@solidjs/meta`, so it is removed with the route.
  - Scoped styles: CSS Modules only; no SFC-style scoping.
- **MDX/Markdown as pages**: **Partial**. "An `.mdx` file in `src/routes` is also treated as a page route". The compiler plugin is not specified; v1 lists a `with-mdx` template. `extensions` adds file types for the router and compiler. SolidBase (separate project) is recommended for Markdown/MDX-heavy static sites. Source: `S2/.../(0)routing.mdx`, `S2/reference/config/solid-start.mdx`, `S1/(0)building-your-application/(6)route-prerendering.mdx`.
- **Static assets**: `public/` is served at the root path (`public/images/logo.png` → `/images/logo.png`). Use it for stable, human-readable URLs, documents, service workers, manifests, robots and favicons. Imports are hashed for cache-busting. Source: `S2/.../(7)static-assets.mdx`.
- **Notable extras**: built-in `~` alias → `appRoot` (`~/lib/db` → `src/lib/db`). `solid` option forwards `Partial<SolidOptions>` to `vite-plugin-solid`. Source: `S2/(1)getting-started.mdx`, `S2/reference/config/solid-start.mdx`.

## 11. Build output & deployment

- **Output modes**: Source: `S2/(2)guides/(5)deployment-plugins.mdx`, `S2/(0)building-your-application/(6)route-prerendering.mdx`, `S2/reference/config/solid-start.mdx`, `S2/reference/entrypoints/(0)vite-config.mdx`.
  - **Server**: the deployment plugin's output, e.g. Nitro `.output/` per preset.
  - **Static**: Nitro prerender into `.output/public`, with full-site crawl via `crawlLinks`.
  - **SPA**: `ssr: false`; still has server functions and API routes when used.
  - A dedicated "static export with no server" mode or command is **not documented** (Nitro static presets: from memory, unverified).
  - Scripts: `vite dev`, `vite build`, `vite preview` (local check of the production build only; "run or deploy Nitro's generated output according to the selected preset").
- **Supported runtimes**: whatever the deployment plugin targets. Source: `S2/(2)migrating-from-v1.mdx`, `S1/reference/config/define-config.mdx`, `S2/(2)guides/(4)background-tasks.mdx`, `S2/(1)advanced/(4)serialization.mdx`.
  - Documented v2 example presets: `node_server`, `cloudflare_module`.
  - The v1 preset list (Nitro v2 names): `node` (default), `deno_server`, `bun`, `netlify`, `netlify-edge` (the example config spells it `netlify_edge`), `vercel`, `vercel-edge`, `aws_lambda`, `cloudflare`, `cloudflare_pages`, `cloudflare_module`, `deno_deploy`.
  - v2 warns that Nitro v3 **renamed** presets, "especially Cloudflare, Vercel Edge, Firebase, and the old Node middleware preset".
  - Node, Bun and Deno are referenced in the task and Temporal docs.
  - SolidStart relies on **AsyncLocalStorage**. v1 needed `nodejs_compat` plus externals on Cloudflare; in v2 the Cloudflare Vite plugin runs the server build in workerd.
  - **Per-route runtime choice: not supported / not found.**
- **Adapters / presets**: **Supported via deployment Vite plugins, no SolidStart adapter API**. "Choose one deployment plugin." Source: `S2/(2)guides/(5)deployment-plugins.mdx`, `S2/(0)index.mdx`, `S2/reference/entrypoints/(0)vite-config.mdx`.

  | Plugin | Setup | Notes |
  |---|---|---|
  | **Nitro v3** (`nitro/vite`, currently beta) | `plugins: [solidStart(), nitro()]`; options in the top-level `nitro` key (`preset`, `prerender`, `serverDir`, `features.websocket`, `experimental.tasks`, `scheduledTasks`, …) | portable presets; Nitro settings "do not belong inside `solidStart()`" |
  | **Netlify** (`@netlify/vite-plugin`) | `netlify({ build: { enabled: true } })` after `solidStart()` | builds Netlify Functions, emulates platform features in dev; Netlify auto-detects the build command and publish dir; "No SolidStart-specific adapter is required" |
  | **Cloudflare** (`@cloudflare/vite-plugin` + `wrangler`) | `cloudflare({ viteEnvironment: { name: "ssr" } })` **before** `solidStart()` | runs SSR in workerd during dev; needs Wrangler config and bindings |

  Any plugin built on Vite's Environment API can integrate (that is the "adapter API"). v1 used Vinxi and Nitro v2 (`server` key in `app.config.ts`); `@solidjs/vite-plugin-nitro-2` is **deprecated**.
- **Config-level headers, redirects, rewrites, trailing slash**: **Not provided by SolidStart**. Redirects and headers go in middleware. SPA rewrites are host config (Netlify `_redirects`, `vercel.json`). Nitro `routeRules`: not mentioned (from memory, unverified). Trailing-slash policy: **not found** (the docs site's Nitro prerender sets `autoSubfolderIndex: false`, a Nitro option). Source: `R/(2)rendering-modes/(0)spa.mdx`, `S2/(1)advanced/(0)middleware.mdx`.
- **Base path**: router `base` only (area 1). A Vite `base` interplay is **not documented**.
- **Standalone / self-contained output**: **Not documented explicitly**. Nitro output is self-contained per preset (from memory, unverified: `.output/server/index.mjs` for `node_server`).
- **Skew protection**: **Not found in docs**.
- **Notable extras**:
  - Requirements: **Node ≥ 24** (`engines`, CI and deploy runtimes) and **Vite 8 or 9**.
  - `vite.config.ts` replaces v1's `app.config.ts`. v1's `vite` option, which could be a function per Vinxi router (`server` | `client` | `server-function`), is gone; v2 uses Vite environments.
  - Entry resolution: `src/app.tsx` (or `.jsx`) is resolved as the virtual `solid-start:app`, and its extension selects `entry-client`/`entry-server` `.tsx` vs `.jsx`.
  - Source: `S2/(2)migrating-from-v1.mdx`, `S2/reference/entrypoints/app.mdx`, `S1/reference/config/define-config.mdx`.

## 12. Dev tooling & observability

- **Dev server and HMR**: **Supported (Vite)**. `vite dev` (the tasks example uses `localhost:5173`; v1 with Vinxi defaulted to port 3000). HMR is Vite's, including route CSS in v2. Entry files carry a `// @refresh reload` pragma in examples. Cloudflare and Netlify plugins emulate their runtimes in dev. Source: `S2/(1)getting-started.mdx`, `S2/(2)guides/(4)background-tasks.mdx`, `S2/.../(2)css-and-styling.mdx`, `S1/(1)getting-started.mdx`.
- **Error overlay**: **Supported**. The dev toolbar/overlay (`devOverlay`, default `true`) is "for inspecting application errors and server function calls". It is excluded from production builds; `devOverlay: false` hides it. Source: `S2/(1)getting-started.mdx`, `S2/reference/config/solid-start.mdx`.
- **Devtools**: **Partial**. The dev toolbar above includes a server-function call inspector. Solid DevTools are not mentioned in these docs. `createAsync({ name })` names exist "for development debugging". Source: same as above, `R/reference/data-apis/create-async.mdx`.
- **Type generation commands**: **None needed / not found** (types are inferred; `@solidjs/start/env` is static).
- **CLI scaffolding / generators**: **Partial**. `npm create solid` (create-solid) offers interactive prompts: SolidStart or not, template or "official example", TypeScript. The v1 template list includes `basic`, `bare`, `with-solidbase`, `with-auth`, `with-authjs`, `with-drizzle`, `with-mdx`, `with-prisma`, `with-solid-styled`, `with-tailwindcss`, …. No route or code generators. Source: `S2/(1)getting-started.mdx`, `S1/(1)getting-started.mdx`, `src/routes/(1)quick-start.mdx`.
- **AI-agent support**: **Not found as a framework feature**. Docs pages carry `use_cases` and `tags` frontmatter, and the docs site is built with SolidBase `llms: true` (so docs.solidjs.com likely serves llms.txt; inference from `vite.config.ts`). No AGENTS.md, MCP server or bundled docs in the package are documented.
- **Instrumentation / OpenTelemetry**: **Not found**. Middleware timing (`Date.now()` around `await next()`) is the only pattern shown.
- **Server error reporting hooks**: **Partial**. `serverFunctions.onError` (async-capable, can flush to e.g. Sentry via `captureException`) covers server functions only (area 7).
- **Web vitals reporting**: **Not found**.
- **Notable extras**: Nitro dev endpoint `/_nitro/tasks/<name>` for running tasks during dev (with a warning not to expose an equivalent in prod). `getServerFunctionMeta()` gives the server-function `id` for logging.

---

## Out-of-scope features seen
- Sessions: encrypted cookie sessions via `useSession`/`getSession`/`updateSession`/`clearSession`/`sealSession`/`unsealSession` (H3 v2) in `@solidjs/start/http` (`S2/(1)advanced/(1)session.mdx`).
- Auth: a guide showing protected queries plus `throw redirect("/login")` and `deferStream` (`S2/(1)advanced/(5)auth.mdx`).
- WebSockets: Nitro v3 cross-platform `defineWebSocketHandler` in `server/routes/*.ts` with `nitro.features.websocket: true`. Nitro also offers peers, topics and pub/sub (`S2/(1)advanced/(6)websocket.mdx`). v1 marked it experimental.
- Background or scheduled tasks: Nitro **experimental** Tasks API (`server/tasks/**`, `defineTask`, `scheduledTasks` cron map, native Cloudflare and Vercel cron) (`S2/(2)guides/(4)background-tasks.mdx`).
- Security guide: XSS guidance and CSP with or without nonce via middleware (`S2/(2)guides/(0)security.mdx`).
- Service workers: a manual registration recipe (`S2/(2)guides/(3)service-workers.mdx`).

## v1 → v2 delta (for readers comparing against older SolidStart material)
- Toolchain: Vinxi + Nitro v2 + `app.config.ts`/`defineConfig` became Vite 8/9 Environment API + `vite.config.ts`/`solidStart()` + any deployment Vite plugin (Nitro v3 beta, Netlify, Cloudflare).
- HTTP helpers: `vinxi/http` (event-arg) became the context-aware `@solidjs/start/http`.
- Middleware: `{ onRequest, onBeforeResponse }` became an onion-model H3 middleware array (the old form is deprecated but works).
- Serialization: the default changed from `js` (needs `unsafe-eval`) to `json`. v2 adds Temporal support, custom Seroval plugins and raw binary/FormData bypass.
- Islands: experimental in v1; removed in v2 (option reserved and only accepts `false`).
- CSS: rewritten pipeline (no FOUC for lazy components; old CSS no longer unmounted on navigation).
- New in v2: `serverFunctions.filter` / `serverFunctions.onError`, `env:` virtual modules, `server-only` / `client-only` markers, experimental `decorateHandler`/`decorateMiddleware`, `routerLoad` for TanStack Router, Node ≥ 24 requirement.
- Sources: `S2/(2)migrating-from-v1.mdx`, `S1/reference/config/define-config.mdx`, `S1/reference/client/mount.mdx`, `S2/.../(2)css-and-styling.mdx`.
