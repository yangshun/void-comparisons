# Nuxt — feature inventory
Version documented: **5.0 (pre-release, "still in development")**. Determined from `docs/package.json` (`"version": "5.0.0-0"`), the upgrade guide's "Migrating to Nuxt 5 … Nuxt 5 is still in development, so this page changes" (`docs/1.getting-started/18.upgrade.md`), the roadmap table (5.x "scheduled", initial release "Q4 2026 (estimated)"; 4.x is the current stable line, `docs/5.community/6.roadmap.md`), the StackBlitz starter pointing at the `v5-nightly` branch (`docs/1.getting-started/02.installation.md`), and `future.compatibilityVersion` "always resolves to `5` in Nuxt 5" (`docs/3.guide/6.going-further/1.features.md`). Version badges in the docs run up to `v4.6`, so most APIs are already shipped in 4.x and Nuxt 5 mainly changes defaults and the server engine. A web search found no stable Nuxt 5 release. · Docs commit: 2026-11-03 (`9496b7e`, nuxt/nuxt main).
Context: Vue 3 (vue-router, Unhead for head) · Vite 8 / Rolldown by default (`@nuxt/vite-builder`; webpack and Rspack builders are also official) · Nitro v3 on h3 v2 + srvx through the `@nuxt/nitro-server` server builder (`@nuxt/vite-server` is an experimental alternative) · Node ≥ 22.22 / 24.11 (`node-server` preset by default). Deno, Bun, workers and edge targets go through Nitro presets.

Path convention: "Source:" paths are relative to the repo root. `exp.md` = `docs/3.guide/6.going-further/1.experimental-features.md`; `upgrade.md` = `docs/1.getting-started/18.upgrade.md`.

### Notable Nuxt 5 changes (from `upgrade.md` unless noted)
- **Nitro v3** (h3 v2, srvx, Web `Request`/`Response`). A `nitroLegacy` compat layer keeps unmigrated server code running. `nitropack` becomes `nitro`, and `h3` imports become `nitro/h3`. `useStorage` becomes `useKV` (`nitro/kv`) and `nitro.storage` becomes `nitro.kv`. Errors use `status`/`statusText` in place of `statusCode`/`statusMessage`. `useRuntimeConfig()` no longer takes an event. Nitro runtime hooks `beforeResponse`/`afterResponse` become `response`. Route-rule redirect `statusCode` becomes `status`.
- **`nuxt/server`**: a new builder-agnostic server import surface (introduced in 4.6). It includes sealed-cookie sessions (`useSession`, cookie `nuxt-session`) keyed from a new `runtimeConfig.appSecret` / `NUXT_APP_SECRET`.
- **Server auto-imports off by default** (`experimental.nitroAutoImports` turns them back on). Only top-level `server/utils/` files are scanned.
- **Vite Environment API always on, Vite 8 (Rolldown)**. Nitro is built as a Vite environment (`experimental.nitroViteEnvironment` defaults to true), so client and server come from one Vite build.
- **Typed `$fetch`/`useFetch` rebuilt** on generated route types. They are method-aware and type the body, query and headers of validated handlers. The `params` option is dropped (use `query`). The browser no longer gets a `globalThis.$fetch`.
- **Routing defaults**: case-sensitive routing (`router.options.sensitive: true`, settable only in nuxt.config), `typedPages` on by default, `normalizePageNames` on, `extractSerializablePageMeta` on, and `navigateToEarlyReturn` on (a top-level `await navigateTo()` in `<script setup>` returns early).
- **Route rules**: patterns follow URLPattern/rou3, and `*` now matches nested segments. Cached rules (`cache`/`swr`/`isr`) **ignore the query string** unless `allowQuery` is set. Regex constraints may not match percent-encoded characters.
- **Error format**: page errors always return the HTML error page, and server route or server middleware errors always return JSON, whatever the `Accept` header says. `experimental.parseErrorData` is forced on.
- **Payload extraction default `'client'`**: the payload is inlined in the HTML for the first render, and `_payload.json` is used for client navigation.
- **Bundle trims**: the Options API is compiled out of the client (`__VUE_OPTIONS_API__: false`). Client-only placeholders are comment nodes. `jiti` is gone, so config and modules load through Node's native TypeScript stripping. `autoprefixer`/`cssnano`, `@vitejs/plugin-vue-jsx` and `giget` are now optional. Server-only head composables are no longer auto-imported.

---

## 1. Routing

- **Route definition (file-based and code-based)**: **Supported (both)**. Each file in `app/pages/` becomes a vue-router route through a dynamic import. The `pages/` directory is optional: without it vue-router is not bundled and only `app.vue` renders. `pages: true` forces routing on, and `pages: { pattern: [...] }` restricts the scanned globs. Page extensions are `.vue .js .jsx .mjs .ts .tsx` (the `extensions` option). Code and config hooks: `app/router.options.ts` → `routes: (scannedRoutes) => routes` (returning null falls back to the scanned routes; **definePageMeta is not applied to routes returned this way**); the build hooks `pages:extend` (mutate a `NuxtPage[]` of `{name, path, file, meta, children}`), `pages:resolved` and `pages:routerOptions` (add extra router-options files; later ones win); Kit `extendPages()` and `extendRouteRules()`; and runtime `router.addRoute()`, which is incompatible with `early404`. A page can override its matcher with `definePageMeta({ path: '/:postId(\\d+)-:postSlug' })` using vue-router regex syntax. Since Nuxt 5, routes are **case-sensitive** by default. Turning that off with `router.options.sensitive: false` also lower-cases route-rule matching and is only allowed in `nuxt.config`. Other vue-router options settable in nuxt.config (JSON-serializable only): `linkActiveClass`, `linkExactActiveClass`, `end`, `sensitive`, `strict`, `hashMode`, `scrollBehaviorType`. Files whose names start with `-` (`ignorePrefix`) and files matching `ignore` globs (`*.spec`, `*.stories`, etc.) are skipped. Pages can also come from layers ("multiple pages directories"). Source: docs/2.directory-structure/1.app/1.pages.md, docs/3.guide/5.recipes/1.custom-routing.md, docs/4.api/6.nuxt-config.md
  - File conventions: `index.vue` maps to the directory path; `[id].vue` is a param; `[[slug]].vue` is an optional param; `[...slug].vue` is a catch-all (the param is an array, e.g. `["hello","world"]`); `users-[group]/[id].vue` mixes static text and params in one segment; `(group)/` is a route group; `name@view.vue` is a named view; `*.client.vue` is a client-only page and `*.server.vue` a server-only (island) page. Generated route names join segments with dashes (`posts-id`, `parent-child`). **Priority**: a named parent beats a nested dynamic route (`pages/foo.vue` wins over `pages/foo/[slug].vue` for `/foo/hello`; use `foo/index.vue` to separate them). Pages must have a **single root element** (comments count as elements), or client-side transitions and navigation fail to render. Source: docs/2.directory-structure/1.app/1.pages.md
- **Nested layouts**: **Supported (two separate mechanisms)**.
  1. **Nested routes**: `pages/parent.vue` plus `pages/parent/child.vue`; the parent renders `<NuxtPage>`. Extra props on `<NuxtPage :foobar>` are passed down to the child page (as props or `attrs`). Error E4016 fires if a parent fails to render `<NuxtPage>`.
  2. **Layouts** (`app/layouts/*.vue`, enabled by wrapping `<NuxtPage>` in `<NuxtLayout>` in `app.vue`): one layout per page, not one per segment. Layouts **do not nest** automatically; nesting comes from nested routes or from a page rendering `<NuxtLayout>` itself with `layout: false`. If none is chosen, `default.vue` applies. Names are kebab-cased (`someLayout` → `some-layout`) and duplicated directory segments are removed (`layouts/desktop/default.vue` → `desktop-default`). A layout needs one root element, which **cannot be `<slot />`**. Layouts are loaded asynchronously.
     Layout selection, in order of documentation: `definePageMeta({ layout })`, where `layout` is `string | false | Ref | ComputedRef | { name, props }` and props are typed from the layout's `defineProps`; the `name` prop of `<NuxtLayout>`; `setPageLayout(name, props?)` at runtime (E2007 if called on the server inside a component); and the `appLayout` route rule (v4.3), a string or `false`, which also covers catch-all pages.
     `<NuxtLayout>` props: `name` (`string | false`, default `'default'`); `fallback` (layout rendered when `name` is invalid, otherwise nothing renders); extra props are passed through as `$attrs`. `ref.value.layoutRef` exposes the layout instance. If `<NuxtLayout>` is used inside a page, it must not be the page's root element (because of transitions).
  Source: docs/2.directory-structure/1.app/1.layouts.md, docs/4.api/1.components/3.nuxt-layout.md, docs/4.api/3.utils/set-page-layout.md
- **Dynamic, optional and catch-all segments**: **Supported**: `[id]`, `[[slug]]` (optional) and `[...slug]` (catch-all). An **optional catch-all** (`[[...slug]]`) was not found in the docs. Custom regex params go through `definePageMeta({ path })`. **Route validation**: `definePageMeta({ validate(route) })` returns `boolean | Promise<boolean> | Partial<NuxtError>`. `false` makes the router try other matches and returns a 404 if none match. Returning an object `{ status, statusText }` responds immediately with that error and skips other matches. `validate` runs after plugins and before route middleware, on both server and client. Source: docs/1.getting-started/07.routing.md, docs/4.api/3.utils/define-page-meta.md, docs/3.guide/1.concepts/2.nuxt-lifecycle.md
- **Route groups / pathless layouts**: **Supported (groups); Partial (pathless layouts)**. A folder named `(marketing)/` is left out of the URL. Since v4.3, groups are exposed as `route.meta.groups: string[]` and as the auto-populated `groups` key in page meta. A group does not attach a layout component by itself. To get a "pathless layout", combine it with a parent page file or with `appLayout` route rules. Source: docs/2.directory-structure/1.app/1.pages.md
- **Parallel routes / intercepting routes**: **Partial / Not found**. Named views (v4.5): a sibling file `child@sidebar.vue` renders into `<NuxtPage name="sidebar" />` in the parent. Outlets with no matching view stay empty, and `definePageMeta` is read **only from the default file**. **Intercepting routes and modal routes were not found in the docs**. Source: docs/2.directory-structure/1.app/1.pages.md, docs/4.api/1.components/2.nuxt-page.md
- **Typed links and typed route params**: **Supported (on by default in Nuxt 5)**. `experimental.typedPages` (now enabled by default) generates route names, paths and params from `pages/`. `useRoute('route-name')` returns typed params, and `<NuxtLink>`, `navigateTo` and `router.push` are type-checked. The `templateDiagnostics` check (on by default) warns at build time with `NUXT_B4025` when a `<NuxtLink>` has a static `to` that matches no page. It cannot see `router.addRoute()` routes or routes changed through a custom `router.options`. See §8. Source: upgrade.md, exp.md
- **Search-param handling**: **Partial (untyped, unvalidated)**. Query params are read from `useRoute().query` (vue-router `LocationQuery`) and set through `navigateTo({ path, query })` or `<NuxtLink :to="{ query }">`, which encode keys and values automatically. `useFetch({ query })` accepts reactive query objects. **No typed or validated search-param API was found.** Source: docs/4.api/2.composables/use-route.md, docs/4.api/1.components/4.nuxt-link.md
- **Programmatic navigation**: **Supported**. `navigateTo(to, options)` works on server and client and must be awaited or returned. `to` is a string or route object; `undefined`/`null` mean `'/'`.

  | option | values / default | behavior |
  |---|---|---|
  | `replace` | bool, `false` | replace instead of push (client) |
  | `redirectCode` | number, `302` | status code when the redirect happens on the server |
  | `external` | bool, `false` | without it, an external URL **throws** (E2001); with it, internal URLs do a full reload |
  | `open` | `{ target='_blank', windowFeatures: {popup, width/innerWidth, height/innerHeight, left/screenX, top/screenY, noopener, noreferrer} }` | client-only `window.open`; ignored on the server |

  Behavior: a server-side `navigateTo` sends a `Location` header and app state resets unless it is kept in a cookie. It **cannot be used in Nitro routes**; use `sendRedirect` there. Dangerous protocols are rejected (E2002). In Nuxt 5 a top-level `await navigateTo()` in `<script setup>` returns early from `setup()` when it succeeds: nothing after it runs, including `defineExpose` and hooks registered later. The early return does not apply when the result is used, when `open` is passed, or when the navigation was aborted or failed. Note that `docs/4.api/3.utils/navigate-to.md` still calls this opt-in, which is out of date. Also available: `abortNavigation(err?)`, usable only inside middleware (E2003); vue-router's `useRouter()` (`push/replace/back/forward/go/resolve/addRoute/removeRoute/hasRoute/getRoutes/beforeEach/afterEach/isReady/onError`, with `navigateTo` recommended over `push`); `onBeforeRouteLeave/Update`; `reloadNuxtApp({ path, ttl, force, persistState })`; and `experimental.serverPathFallback` (on by default), which turns a client navigation that matches no page into a full document load, so `<NuxtLink to="/file.pdf">` reaches `public/` or a server route. Source: docs/4.api/3.utils/navigate-to.md, exp.md, docs/4.api/2.composables/use-router.md
- **Prefetching (strategies)**: **Supported**. `<NuxtLink>` prefetches when a link is **visible** (IntersectionObserver, the default) and/or on **interaction** (`pointerenter`/`focus`). It only does so while the browser is idle, and **skips** prefetching when offline, on 2G, or with data-saver on. **What is fetched**: the page's component chunks, plus its middleware and layouts, plus its **payload `_payload.json` when payload extraction applies** (prerendered and ISR/SWR routes). Data from `useFetch` on a normal SSR route is **not** prefetched. For a `.server.vue` page, the island response is prefetched and cached by name, props and context. Separately, preload/modulepreload hints cover the current page's chunks, while `rel=prefetch` hints for lazy chunks are written with `data-href` and activated on `onNuxtReady` (`experimental.deferPrefetchHints`, default on; not activated at all on data-saver or 2G). The `build:manifest` hook can set `chunk.prefetch = false` per chunk. Manual helpers: `preloadRouteComponents(to)`, `preloadComponents(names)` and `prefetchComponents(names)` (currently behaves like preload); all three do nothing on the server. The `link:prefetch` runtime hook fires on prefetch. Experimental extras: `crossOriginPrefetch` (Speculation Rules API) and `prefetchPreloadTags` (forwards the destination's `useHead` preload links as `rel=prefetch`; images keep `preload`; off by default). `noScripts` pages emit speculation rules (prefetch plus prerender) scoped to page routes. Source: docs/4.api/1.components/4.nuxt-link.md, docs/3.guide/2.best-practices/performance.md, exp.md, docs/3.guide/1.concepts/6.server-components.md

  `<NuxtLink>` props (plus every vue-router `RouterLink` prop: `to`, `custom`, `activeClass`, `exactActiveClass`, `replace`, `ariaCurrentValue`):

  | prop | values / default | behavior |
  |---|---|---|
  | `href` | alias of `to` | ignored when `to` is also set |
  | `external` | bool | forces a plain `<a>`, bypassing the router (needed for `public/` files or another app on the same domain) |
  | `target` / `rel` | – / `"noopener noreferrer"` for external or `target` links | the default `rel` is applied to absolute URLs (`http(s)://`, `//`) and links with a `target` |
  | `noRel` | bool | removes the default rel; `rel` is ignored when both are set |
  | `prefetch` / `noPrefetch` | `true` | turns prefetching on or off |
  | `prefetchOn` | `'visibility'` (default) \| `'interaction'` \| `{visibility, interaction}` | trigger(s) |
  | `prefetchedClass` | string | class added once the link has been prefetched |
  | `custom` slot | `{ href, navigate, prefetch, prefetched, shouldPrefetch }` | since v4.5 no handlers are attached automatically; you call `prefetch()` yourself |

  Global defaults go in `experimental.defaults.nuxtLink`: `{componentName, externalRelAttribute, activeClass, exactActiveClass, prefetchedClass, trailingSlash: 'append'|'remove', prefetch, prefetchOn}`. Alternatively, `defineNuxtLink(options)` in a component file creates a custom link component.
- **Scroll restoration**: **Supported**. By default Nuxt scrolls to the top on a new route, restores the previous position on back navigation, and scrolls to hash targets. `definePageMeta({ scrollToTop: boolean | (to, from) => boolean })` controls this per page. Scrolling happens even when the page does not re-render (for example with a fixed `key`). `router.options.scrollBehaviorType: 'auto' | 'smooth'` (default `'auto'`) applies to hash links, and a fully custom `scrollBehavior` can go in `app/router.options.ts`. Source: docs/3.guide/2.best-practices/accessibility.md, docs/4.api/3.utils/define-page-meta.md, docs/3.guide/5.recipes/1.custom-routing.md
- **View transitions**: **Supported (experimental)**. `experimental.viewTransition` accepts `false | true | 'always' | { enabled, types: string[] }`. `true` skips the transition under `prefers-reduced-motion: reduce`, while `'always'` ignores it. The default can be set in `app.viewTransition`. Per page: `definePageMeta({ viewTransition: boolean | 'always' | { enabled, types, toTypes, fromTypes } })`. The types fields accept functions `(to, from) => string[]` **only in page meta**; nuxt.config takes static arrays only. Types are added to `ViewTransition.types` (v4.4) and can be targeted in CSS with `:active-view-transition-type()`. The runtime hook `page:view-transition:start(transition)` lets you read or change the types. **Known issue**: DOM updates freeze for the whole transition, which includes async data fetching in page setup. `noScripts` pages use declarative cross-document view transitions. Vue `<Transition>`-based **page and layout transitions** also exist: `app.pageTransition` and `app.layoutTransition` (`boolean | TransitionProps`, default `false`, JSON-serializable only), overridable per page through definePageMeta, with JS hooks (`onBeforeEnter`, etc.). The page transition does **not** run when the layout changes too; set a layout transition instead. `<NuxtPage :transition>` sets a global transition that **cannot** be overridden per page. Both kinds need a single root element. Source: docs/1.getting-started/09.transitions.md, exp.md
- **Route-level code splitting**: **Supported (automatic)**. Every page is a dynamic import. Layouts and named middleware load asynchronously, and components prefixed `Lazy` are split. Code splitting can be disabled with `vite.$client.build.rolldownOptions.output.codeSplitting: false` (not recommended). Pages under `ssr: false` route rules are dropped from the server bundle, and pages under `noScripts` rules are dropped from the client bundle, whenever those rules can be resolved at build time. `experimental.extractAsyncDataHandlers` moves `useAsyncData` handlers into their own chunks (recommended only for static builds). The `entryImportMap` option (on by default) keeps chunk hashes stable across entry changes. Source: docs/1.getting-started/07.routing.md, docs/3.guide/1.concepts/1.rendering.md, exp.md
- **Base path**: **Supported**. `app.baseURL` (default `'/'`) can be overridden at runtime with `NUXT_APP_BASE_URL`. Relative bases (`./`) are not allowed in nuxt.config; set them through the env var at build time or through `runtimeConfig.app.baseURL`. `app.buildAssetsDir` defaults to `'/_nuxt/'` and is fixed at build time. `app.cdnURL` (production only, `NUXT_APP_CDN_URL`) serves `public/` and build assets from a CDN. Static literal `src` paths get the base prefix at runtime, but runtime-built `:src` values do **not**; prefix those with `useRuntimeConfig().app.baseURL`. Source: docs/4.api/6.nuxt-config.md, docs/1.getting-started/05.assets.md
- **Notable extras**:
  - **`definePageMeta`**, a compiler macro that works in `<script>` and `<script setup>`. It can reference imports and pure local functions but **not** component state; a ref would be hoisted out. Meta from nested routes is merged. Keys:

    | key | type | behavior |
    |---|---|---|
    | `name` / `path` / `alias` / `redirect` / `props` | vue-router record fields | custom route name, regex path, extra paths (they must share params), redirect before guards, params as props |
    | `groups` | `string[]` (auto) | the route groups the page sits in |
    | `key` | `false \| string \| (route) => string` | controls when `<NuxtPage>` re-renders |
    | `keepalive` | `boolean \| KeepAliveProps` | wraps the page in `<KeepAlive>`; default from `app.keepalive` |
    | `layout` | see above | |
    | `layoutTransition` / `pageTransition` / `viewTransition` | see above | |
    | `middleware` | name \| inline fn \| array | merged with the middleware of parent and child routes |
    | `validate` | fn | see above |
    | `scrollToTop` | bool \| fn | |
    | custom keys | any | typed by augmenting `PageMeta` in `#app` |

    Build-time extraction: in Nuxt 5 every JSON-serializable value is written into the route record (`extractSerializablePageMeta`). `scanPageMeta` exposes `alias/name/path/redirect/props/middleware` to modules, and `extraPageMetaExtractionKeys` adds more keys. Values that cannot be serialized are resolved at runtime from a per-page meta module. Source: docs/4.api/3.utils/define-page-meta.md, exp.md
  - **Route middleware** (Vue side; server middleware is in §6). There are three kinds: **inline** (a function inside `definePageMeta`), **named** (`app/middleware/auth.ts`, loaded on demand and referenced by its kebab-case name; only top-level files or `dir/index.ts` are registered) and **global** (`*.global.ts`, runs on every route change). **Order**: global middleware runs first, sorted alphabetically by filename (use `01.`/`02.` prefixes to control it), then the page's middleware in array order. Signature: `defineNuxtRouteMiddleware((to, from) => …)` with no `next()`. Return nothing to continue, `navigateTo()` to redirect (302 by default, `redirectCode` to change it, as a real HTTP redirect on the server), or `abortNavigation(err?)` to stop. **Runs on the server for the initial render and again on the client during hydration.** To skip a side, check `import.meta.server`/`import.meta.client`, or `nuxtApp.isHydrating && nuxtApp.payload.serverRendered`. It also re-runs when the error page renders; `useError()` tells you an error is being handled. Use `to`/`from`, **not** `useRoute()` (that triggers a warning, E2005). Middleware can also be added with `addRouteMiddleware(name, fn, { global })` (for example from a plugin), assigned at build time through `pages:extend`, or switched per path with the **`appMiddleware` route rule** (`string | string[] | Record<string, boolean>`, where false disables). Route middleware **does not run** for server routes or islands. Source: docs/2.directory-structure/1.app/1.middleware.md, docs/1.getting-started/07.routing.md, docs/3.guide/1.concepts/1.rendering.md
  - **`<NuxtPage>`** wraps `<RouterView>` with `<Suspense>`, `<Transition>` and `<KeepAlive>`. Props: `name` (named view), `route`, `pageKey` (string or function), `transition`, `keepalive`, plus any custom props, which are passed to the page. Because of Suspense, the **new page mounts before the old one unmounts**. `ref.value.pageRef` exposes the page instance. Source: docs/4.api/1.components/2.nuxt-page.md
  - Nuxt's `useRoute()` only updates **after the new page content has rendered**, whereas vue-router's updates immediately. `experimental.templateRouteInjection` (on by default) keeps `$route` in sync with it. Reading `route.fullPath` in a template risks hydration mismatches because the hash is never sent to the server. Source: docs/4.api/2.composables/use-route.md, exp.md
  - `experimental.early404` (opt-in): a build-time matcher answers requests that cannot match any page with a 404 **before the Vue app loads**, and a `cache` rule's `maxAge` is sent as `Cache-Control` on those misses. It is turned off automatically in dev, in hashMode, when a root catch-all exists, or when `router.options` changes the routes. Source: exp.md
  - SPA `hashMode` (`ssr: false` only); custom history through `router.options.ts` `history: base => …`; `<NuxtRouteAnnouncer>` (since 3.12) and `<NuxtAnnouncer>`/`useAnnouncer` (since 4.4) for screen-reader announcements. Source: docs/3.guide/5.recipes/1.custom-routing.md, docs/4.api/1.components/12.nuxt-route-announcer.md

## 2. Rendering modes

- **SSR**: **Supported (default, `ssr: true`)**. Universal rendering runs pages, middleware and plugins on the server, then hydrates on the client, re-running page setup. By default the response is **buffered**: `<Suspense>` and `onServerPrefetch` wait for every awaited `useFetch`/`useAsyncData` before the HTML is serialized, whether or not the call is `await`ed. Vue `onBeforeMount`, `onMounted` and later hooks do not run during SSR. `experimental.noVueServer` disables the Vue renderer endpoint inside Nitro. `experimental.writeEarlyHints` sends 103 Early Hints on the node server. Source: docs/3.guide/1.concepts/1.rendering.md, docs/3.guide/1.concepts/2.nuxt-lifecycle.md, docs/1.getting-started/10.data-fetching.md
- **Streaming SSR**: **Supported (experimental, opt-in)**. `experimental.ssrStreaming: true | { botRegex }` renders through Vue `renderToWebStream`. The **shell** (`<head>`, entry styles, preload hints, entry scripts) is flushed **after the first render pass**, and the body then streams progressively, including nested `<Suspense>` boundaries. The streaming mechanism is Vue Suspense; there is no separate primitive for deferred or promise data.
  - **Bots are not streamed.** A request whose `user-agent` matches `botRegex` gets buffered HTML. The default list covers indexing crawlers only, so Lighthouse is streamed. Setting `botRegex` replaces the default list rather than adding to it.
  - **Per route**: `routeRules: { '/x/**': { streaming: false } }`. **Per request**: the `render:route` server hook exposes `ctx.canStream`, and setting `ctx.prefersStream = false` opts out. A response streams only when `canStream && prefersStream`.
  - **Automatic buffered fallback** for: routes with `noScripts`, `cache`, `isr`, `swr`, `redirect` or `streaming: false`; `ssr: false` routes; bots; prerendering; server-side `navigateTo()` redirects; and fatal errors thrown before the shell flushes.
  - **Response mutations after the shell flushes are dropped**: `setResponseStatus`, `useResponseHeader`, cookie writes from `useCookie`, and h3 header setters called during component rendering, including after an `await` in middleware or setup. Dev mode logs a warning. Make those changes in plugins instead, which run to completion before rendering starts.
  - **Errors after the flush**: `payload.error` is set and the document still closes cleanly, so `error.vue` renders on the client. If that recovery itself fails, the diagnostic is NUXT_E8009.
  - **Head tags registered after the shell** (after an `await`, or inside nested Suspense) are sent as inline patch scripts. Clients without JS and crawlers that `botRegex` misses never see them, except JSON-LD, `noscript` and body-positioned tags, which are rendered before `</body>`.
  - Route and layout CSS streams straight after the shell. Route JS chunks are **not** preloaded from the shell. Nested async components can flash unstyled in production, and SFC styles can flash in dev.
  - **Islands are compatible**: their teleports are emitted as `<template>` elements and moved into place by an inline script. Apps that combine `features.noScripts` with islands fall back to buffered rendering.
  - CSP nonces found on head scripts are reused on the inline scripts the stream emits.
  - Module hooks: `render:html` (with `streaming: true`; changes to `body`/`bodyAppend` are dropped), `render:html:chunk` (`ctx.chunk: Uint8Array`, `ctx.index`) and `render:html:close` (`ctx.bodyAppend`).

  Source: exp.md (`ssrStreaming`), docs/errors/e8009.md
- **Static pre-rendering incl. dynamic params**: **Supported**.
  - `nuxt generate` (equivalent to `nuxt build --prerender` or `nitro.static: true`) runs the crawler. It starts from `/`, every non-dynamic page and the `prerender.routes` list, writes HTML plus `_payload.json` to `.output/public`, then follows every `<a href>` it finds, recursively.
  - Config: top-level `prerender: { routes, ignore, crawlLinks }` works with any `server.builder`; Nitro-specific settings (`concurrency`, `failOnError`) go in `nitro.prerender`. The route rule `prerender: true | false` accepts globs (`'/blog/**'`). Pages can declare `defineRouteRules({ prerender: true })` (needs the experimental `inlineRouteRules`).
  - **Dynamic params** are discovered by crawling links, listed in `prerender.routes`, added in the `prerender:routes` build hook (`ctx.routes.add()`), or added at runtime with `prerenderRoutes(path | path[])` called inside the Nuxt context. Individual routes can be skipped from the Nitro `prerender:generate` hook (`route.skip = true`).
  - `experimental.sharedPrerenderData` (on by default) reuses payload data across pages that share a key during prerendering, so keys must uniquely identify the data.
  - Static builds also emit `200.html` (SPA fallback) and `404.html`. `experimental.prerenderErrorPages: true | number[]` server-renders `error.vue` into 404.html, or into extra status pages from 400–599. `import.meta.prerender` is true only while generating.
  - Prerendered API routes may be served with the wrong headers depending on the host. **"Hybrid rendering is not available with `nuxt generate`."**

  Source: docs/1.getting-started/15.prerendering.md, docs/3.guide/1.concepts/1.rendering.md, docs/4.api/3.utils/prerender-routes.md
- **Client-only / SPA routes and full SPA mode**: **Supported**.
  - **Full SPA**: `ssr: false` produces an empty `<div id="__nuxt">` plus an optional loading screen from `app/spa-loading-template.html`. The `spaLoadingTemplate` option is `null` (auto-detect), `false`, `true` (falls back to Nuxt's default image) or a path. `experimental.spaLoadingTemplateLocation` is `'body'` (default; a sibling `#__nuxt-loader` removed once the first page is ready, so no white flash) or `'within'` (removed on mount). The loader element is customised with `app.spaLoaderTag`/`spaLoaderAttrs`. Payload extraction is forced off in this mode.
  - **Per route**: `routeRules: { '/admin/**': { ssr: false } }`. The page component is removed from the server bundle unless a more specific rule re-enables SSR, an alias or absolute-path child falls outside the client-only region, or a server-rendered child uses the page as its shell. A page can also be client-only through a `.client.vue` filename.
  - Deploying an SPA to a static host: `nuxt generate` with `ssr: false`. Clearing all routes in `prerender:routes` leaves only `index.html`, `200.html` and `404.html`.

  Source: docs/3.guide/1.concepts/1.rendering.md, docs/4.api/6.nuxt-config.md, exp.md, docs/1.getting-started/16.deployment.md
- **Partial hydration (islands / server components)**: **Supported (experimental)**.
  - **Server components**: `Foo.server.vue`, components in `components/islands/`, and `.server.vue` **pages** (server-only pages that can still be reached by client navigation).
  - `experimental.componentIslands` defaults to `'auto'`, which switches on when a server component exists. Other values: `true`, `false`, `'local+remote'`, or `{ selectiveClient: true | 'deep', remoteIsland: boolean }`. A `.server.vue` paired with a `.client.vue` of the same name is **not** an island; the client half hydrates normally.
  - **How islands render**: each island renders in a request to an island endpoint, in a **new, isolated Vue app**. Plugins run again unless the object-syntax plugin sets `env: { islands: false }`. **Route middleware does not run**, and `useRoute()` reflects the island's own request. provide/inject, `useState` and Pinia **do not cross** the island boundary; inside the island, use `nuxtApp.ssrContext.islandContext`.
  - **Props** are sent as GET query parameters, which keeps responses cacheable. Consequences: props must be JSON-serializable, are limited by URL length, and are visible in logs and `Referer`. Treat them as untrusted input: an undeclared top-level `as` prop is rejected, `template` is rejected under `runtimeCompiler`, numeric `v-for` is capped at 10,000, and allowlists are recommended for `<component :is>`.
  - Changing props re-fetches and re-renders the island in place.
  - **On the first SSR load** islands are rendered inline. **On client navigation**, each island costs a network round trip and blocks navigation unless it is marked `lazy` with a `#fallback`.
  - **Selective hydration**: a `nuxt-client` attribute on a child (local SFCs only; not on built-ins like `<NuxtLink>`) hydrates just that component through the main app. `'deep'` also allows slots, which are rendered on the server and **not** interactive. Slots passed into islands from the parent **are** interactive (wrapped in `display: contents`).
  - **Caching**: identical islands (same name, props and context) render once during prerendering, and two identical instances share one render and one payload entry. Endpoint responses are cacheable by a CDN.
  - **Limitations**: most features are SFC-only; islands increase chunk count; webpack and Rspack can produce `:slotted` scope-ID mismatches; no template refs into islands; the auto wrapper exposes no load or error events; `useId` collides across islands (workaround: an `idPrefix` from the island context id; identical islands still share ids, and `useId` in `nuxt-client` components mismatches). Build diagnostics: B3014 (`v-on`/`v-model` on a server component) and B3015 (a non-serializable prop).

  `<NuxtIsland>` props:

  | prop | type / default | behavior |
  |---|---|---|
  | `name` | string, required | the island component name |
  | `lazy` | bool, `false` | non-blocking; `#fallback` renders until it loads |
  | `props` | `Record<string, any>` | sent as query parameters |
  | `context` | object | extra context, readable in `islandContext` |
  | `source` | string | **remote island** URL (needs `'local+remote'`; trusts the remote HTML completely) |
  | `dangerouslyLoadClientComponents` | bool, `false` | also downloads and runs client components from the remote source |

  `<NuxtIsland>` also has a `#fallback` slot (shown while loading or on fetch failure), `@error`, and `ref.refresh()`.

  Source: docs/3.guide/1.concepts/6.server-components.md, docs/4.api/1.components/8.nuxt-island.md, docs/2.directory-structure/1.app/1.components.md, exp.md
- **Static shell with dynamic holes (PPR-like)**: **Not supported as a feature (not found in docs).** Closest approximations: a prerendered or SWR-cached page with client-only holes (`<ClientOnly>`, `.client.vue`, `useFetch({ server: false, lazy: true })`); islands, which render inline on the first load and are fetched separately only on client navigation; and the `ssrStreaming` shell flush, which is not cached separately. Source: inferred from docs/3.guide/1.concepts/1.rendering.md and docs/3.guide/1.concepts/6.server-components.md
- **Per-route rendering-mode control**: **Supported**, through `routeRules` in nuxt.config (also `nitro.routeRules`). The Vue-side rules are `ssr`, `noScripts`, `appMiddleware`, `appLayout` and `streaming`; the server-side rules are `prerender`, `swr`, `isr`, `cache`, `redirect`, `proxy`, `headers` and `cors` (full table in §5). `defineRouteRules()` sets rules from inside a page (experimental `inlineRouteRules`; `[id]` pages become `/foo/*`; finite alternatives such as `/:locale(en|fr)` expand to one rule each; params that cannot be converted, like regex, partial or repeatable params, are skipped with a warning). Rule patterns follow URLPattern-style rou3 syntax: `*` matches **any depth** in Nuxt 5, `**` also works, `:param` matches one segment, and **only one** `*`/`**` is allowed per pattern. The client respects route rules through `experimental.appManifest` (on by default). The `appMiddleware`, `redirect` and `prerender` rules also change client behavior. Rules are mapped onto the native config of Netlify and Vercel. In nuxt-config.md, `routeRules` is still labelled "Experimental: API may change". Source: docs/3.guide/1.concepts/1.rendering.md, docs/1.getting-started/13.server.md, docs/4.api/3.utils/define-route-rules.md, upgrade.md
- **Hydration strategies**: **Supported**. **Lazy (delayed) hydration** (`experimental.lazyHydration`, on by default; since 3.16) is set with attributes on `Lazy`-prefixed components, **one strategy per component**:

  | attribute | value | trigger |
  |---|---|---|
  | `hydrate-on-visible` | IntersectionObserver options (e.g. `{ rootMargin: '100px' }`) | element enters the viewport |
  | `hydrate-on-idle` | max timeout (ms) | `requestIdleCallback` |
  | `hydrate-on-interaction` | event name or array; default `pointerenter`, `click`, `focus` | user interaction |
  | `hydrate-on-media-query` | media query | media query matches |
  | `hydrate-after` | ms | after a delay |
  | `hydrate-when` | boolean (reactive) | condition becomes true |
  | `hydrate-never` | – | never (no JS executes, but **any prop change forces hydration**) |

  These components emit `@hydrated`. They only work in SFC templates with literal props: not through `v-bind` spreads and not with direct `#components` imports. `defineLazyHydrationComponent('visible'|'idle'|'interaction'|'mediaQuery'|'if'|'time'|'never', () => import(...))` is the macro form; its arguments must be literal. `experimental.stripNeverHydratedData` (opt-in) defaults `serialize: false` for data fetched inside `hydrate-never` components.

  Other controls:
  - `<ClientOnly>`: `placeholder`/`fallback` content, `placeholderTag`/`fallbackTag`, and a `#fallback` slot. The default slot is **tree-shaken from the server build**, so its CSS may not be inlined.
  - `.client.vue` components render after mount. In Nuxt 5 their SSR placeholder is a comment, so `class`/`style` passed to them is not in the SSR HTML.
  - `<NuxtClientFallback>` (experimental `clientFallback`) re-renders on the client if SSR throws. Props: `fallbackTag` (default `div`), `fallback` (raw HTML, so an XSS risk), `keepFallback`; event `@ssr-error`.
  - `onPrehydrate(cb)` inlines a serialized callback that runs before hydration.
  - `useHydration` gives manual control of the hydration payload.
  - `noScripts` routes never hydrate.

  Source: docs/2.directory-structure/1.app/1.components.md, docs/4.api/3.utils/define-lazy-hydration-component.md, docs/4.api/1.components/1.client-only.md, docs/4.api/1.components/1.nuxt-client-fallback.md, docs/4.api/2.composables/on-prehydrate.md, exp.md
- **Notable extras**:
  - **`noScripts`** (zero-JS pages): `features.noScripts: false | 'production' (= true) | 'all'` app-wide, or the `noScripts: true` route rule. It drops the entry scripts, import map, inline payload and JS resource hints but keeps CSS. A client navigation to a `noScripts` route becomes a full document load. These pages emit speculation-rules prefetch/prerender (scoped to page routes, so `/logout` is never prefetched) and, with view transitions on, cross-document view transitions. Their pages are excluded from the client bundle. `nuxt-client` islands do not hydrate there. NUXT_E8007 warns when a route relies on client JS but will be stripped. The "mostly-static sites" recipe combines `prerender` + `noScripts` + islands + lazy hydration. Source: docs/3.guide/6.going-further/1.features.md, docs/3.guide/5.recipes/5.mostly-static-sites.md
  - **Edge-side rendering** is a deploy target (Cloudflare Pages, `vercel-edge`, `netlify-edge`), and hybrid rules still apply there. Source: docs/3.guide/1.concepts/1.rendering.md
  - **Server builder `@nuxt/vite-server`** (experimental; `server.builder: 'vite'`): with `ssr: false` it emits a static SPA; with SSR it emits a web `{ fetch }` entry bundled with all dependencies. It has **no** server routes, no route rules except `prerender`, no inlined styles and no server components. Source: docs/4.api/6.nuxt-config.md
  - `features.inlineStyles` (Vite only; default `(id) => id.includes('.vue')`) inlines component CSS into the SSR HTML. Source: docs/3.guide/6.going-further/1.features.md

## 3. Data loading

- **Where data is fetched**: **Composables inside component, page, layout, plugin or middleware setup.** There are no route loaders and no React-style server components that fetch. The three primitives are `useFetch(url, opts)` (sugar for `useAsyncData(key, () => event.$fetch(url))`), `useAsyncData(key?, handler, opts)` for any async source (CMS SDKs and so on), and `$fetch` (ofetch), which **does not** transfer state to the client, so data fetched with it in setup is fetched twice. `useLazyFetch`/`useLazyAsyncData` are `lazy: true` aliases. Calls must happen in the Nuxt context (setup, plugin or middleware); outside it you get E1001. Other options: Options API `defineNuxtComponent({ fetchKey, asyncData() })` (the Options API itself is off in the Nuxt 5 client by default); `callOnce(key?, fn, { mode: 'navigation' })` for side effects that should run once, on SSR or on navigation; `useState(key, init)` for SSR-shared state; and server islands (§2) as a way to keep data-fetching code server-side. Source: docs/1.getting-started/10.data-fetching.md, docs/4.api/2.composables/use-async-data.md, docs/4.api/2.composables/use-fetch.md, docs/4.api/3.utils/call-once.md
- **Loader execution model (parallel vs waterfall; server vs client)**: **Partial / component-driven.**
  - On SSR every composable runs on the server and the result goes into the payload, so **hydration does not refetch**.
  - On client navigation they run in the browser. Awaited calls **block navigation** through `<Suspense>`, which Nuxt uses to keep the user on the old page until all async setup resolves (show `<NuxtLoadingIndicator>` meanwhile).
  - Sequential `await`s within one component **waterfall**. For parallel requests, either use `Promise.all` inside one `useAsyncData` (with `signal`) or leave calls un-awaited. Parent and child pages/layouts resolve under the same Suspense tree. Route middleware and `validate` run **before** page setup.
  - `server: false` makes a call client-only: on the first load it runs **after hydration** (`data` stays undefined in setup even when awaited), but on later client navigations it is awaited before the page renders.
  - `lazy: true` does not block client navigation, though it still blocks SSR. `await`ing a lazy call on the client resolves immediately, so check `status`. Leaving a call un-awaited starts the request during setup without blocking; `lazy` defers it until mount and is the explicit way to opt in.

  Source: docs/1.getting-started/10.data-fetching.md
- **Request deduplication**: **Supported (key-based)**.
  - `useAsyncData` uses its first argument (a string, ref, computed or getter) as the key. Without one it auto-generates a key from file and line through a compiler transform (`optimization.keyedComposables` covers `useFetch`, `useAsyncData`, the lazy variants, `useState`, `callOnce` and `defineNuxtComponent`). `useFetch` builds its key from the **URL, the fetch options and the call site**, so the same URL called from two components gives **two requests** unless both pass the same `key`. Instances of one component share a key.
  - Calls with the same key **share `data`/`error`/`status`/`pending` refs**. These options must match across them (otherwise dev warns): handler, `deep`, `transform`, `pick`, `getCachedData`, `default` and `middleware`. These may differ: `server`, `lazy`, `immediate`, `dedupe`, `watch`, `enabled` and `serialize`.
  - Concurrent executions follow `dedupe: 'cancel'` (default; aborts the earlier handler's `signal`) or `'defer'` (returns the in-flight promise).
  - **Server-side** `$fetch('/api/x')` to your own routes calls the handler **in-process**, with no HTTP hop. Calling the same key twice during one SSR pass is deduped. The handler must return a value that is neither `undefined` nor `null`, or the client may fetch it again.
  - Errors E3008/E3009 flag an empty key or a non-function handler.

  Source: docs/4.api/2.composables/use-async-data.md, docs/4.api/2.composables/use-fetch.md, docs/4.api/6.nuxt-config.md (`keyedComposables`), docs/4.api/3.utils/$fetch.md
- **Passing server data to client components**: **Supported (payload)**. Results of `useAsyncData`/`useFetch` and `useState` state are serialized into `__NUXT_DATA__` with **devalue**, which keeps Date, Map, Set, RegExp, refs, `shallowRef`/`reactive` and `NuxtError`. Custom classes need `definePayloadPlugin` with `definePayloadReducer`/`definePayloadReviver`. Responses from server routes reaching `$fetch`/`useFetch` are `JSON.stringify`'d (`toJSON` is respected and types are mapped). Ways to trim the payload: `pick: string[]`, `transform(fn)` (neither stops the over-fetch itself), `serialize: false` (v4.6; data stays out of the payload and the client refetches if it renders the data), and `experimental.stripNeverHydratedData`. **Payload extraction** (`experimental.payloadExtraction`): `'client'` (Nuxt 5 default) inlines the payload in the HTML and writes `_payload.json` for client navigation; `true` always uses a separate `_payload.json`, which is CDN-cacheable but costs an extra request; `false` always inlines. It applies to prerendered and ISR/SWR routes and is forced off with `ssr: false`. Private `runtimeConfig` stays server-only; `runtimeConfig.public` is added to the payload. Source: docs/1.getting-started/10.data-fetching.md, docs/1.getting-started/15.prerendering.md, docs/4.api/2.composables/use-nuxt-app.md, docs/3.guide/6.going-further/10.runtime-config.md
- **Client-side data cache**: **Supported (keyed, per app instance)**. Cached data lives in `nuxtApp.payload.data` and `nuxtApp.static.data`. The default `getCachedData(key, nuxtApp, ctx)` returns `payload.data[key]` while hydrating and `static.data[key]` otherwise; the latter is filled from prefetched or extracted `_payload.json`. A custom `getCachedData` can return cached data, which skips the fetch, or `undefined` to fetch. Its `ctx.cause` is one of `'initial' | 'refresh:manual' | 'refresh:hook' | 'watch'`, and `experimental.granularCachedData` (on by default) also calls it on refreshes. `experimental.purgeCachedData` (on by default) clears `useAsyncData` and static caches during navigation to prevent memory leaks. `useNuxtData(key)` reads (and can write) the cached ref. `<KeepAlive>` (`keepalive`) keeps page instances, and their data, alive. Source: docs/4.api/2.composables/use-async-data.md, exp.md, docs/4.api/2.composables/use-nuxt-data.md
- **Deferred / streamed data**: **Partial**. Deferring is done with `lazy: true`, un-awaited calls, `server: false`, `immediate: false` + `execute()`, or `enabled: false`; the UI then reads `status`. **There is no promise-streaming to the client**: on SSR every started request is awaited before the response, or before the relevant Suspense chunk under `ssrStreaming`. Under `ssrStreaming`, async setup inside nested `<Suspense>` boundaries streams as HTML after the shell. Source: docs/1.getting-started/10.data-fetching.md, exp.md
- **Dependency tracking & invalidation**: **Supported (explicit and reactive)**.
  - **Reactive keys**: a new key fetches again (and, with `alwaysRunFetchOnKeyChange`, even when not immediate).
  - **Reactive fetch options**: a ref or computed `query`, `body`, `headers`, `baseURL`, `method` or URL getter is **auto-watched** and refetches on change; `watch: false` opts out.
  - **`watch: [sources]`** re-runs the handler. Watching does **not** rebuild a URL string built at call time; use a getter URL for that.
  - `refresh()`/`execute()` accept `{ dedupe, timeout, signal }`; `clear()` resets data to `default()`, sets status to `idle` and cancels.
  - Global helpers: `refreshNuxtData(keys?)` (no argument refreshes everything; fires `app:data:refresh`; also refreshes deactivated `<KeepAlive>` components until they unmount) and `clearNuxtData(keys? | (key) => boolean)` (no argument clears everything, e.g. to invalidate another page).
  - `enabled` (v4.5) is a barrier: while false, every execution is blocked and switching true→false cancels an in-flight request. Turning it back on does **not** refetch.
  - There is **no automatic invalidation tied to mutations** (see §4).

  Source: docs/1.getting-started/10.data-fetching.md, docs/4.api/3.utils/refresh-nuxt-data.md, docs/4.api/3.utils/clear-nuxt-data.md
- **Access to request context**: **Supported**. Helpers: `useRequestEvent()` (the h3/Nitro event, or the web `RequestEvent` shape, on the server; `undefined` in the browser), `useRequestHeaders(['cookie'])`, `useRequestHeader(name)`, `useRequestURL()`, `useCookie()` (isomorphic), `useRequestFetch()` (a `$fetch` that forwards the incoming request's headers and cookies, minus hop-by-hop headers such as `host`, `accept`, `connection` and `transfer-encoding`; plain `$fetch` during SSR **does not** forward cookies, by design, to avoid SSRF), `useRuntimeConfig()` and `useNuxtApp().ssrContext`. `useFetch` with a relative URL on the server forwards headers automatically. Cookies from internal API calls are **not** passed back to the browser automatically; the documented recipe appends `set-cookie` from `$fetch.raw` to `event.res.headers`. Source: docs/1.getting-started/10.data-fetching.md, docs/4.api/2.composables/use-request-fetch.md, docs/4.api/2.composables/use-request-event.md
- **`useAsyncData` / `useFetch` options** (all accept refs or computeds; ref values are watched):

  | option | type / default | behavior |
  |---|---|---|
  | `key` (useFetch) | `MaybeRefOrGetter<string>` / auto | dedupe and share key |
  | `server` | `true` | run on the server |
  | `lazy` | `false` | don't block client navigation |
  | `immediate` | `true` | `false` keeps `status: 'idle'` until `execute()` |
  | `default` | `() => T` | initial `data` and the value `clear()` resets to |
  | `transform` | `(input) => T \| Promise<T>` | post-process (also limits the payload) |
  | `pick` | `string[]` | keep only these keys |
  | `getCachedData` | `(key, nuxtApp, ctx) => T \| undefined` | custom cache |
  | `watch` | sources \| `false` (useFetch) | extra re-run triggers |
  | `deep` | `false` | `data` is a shallowRef by default |
  | `dedupe` | `'cancel'` \| `'defer'` | concurrent policy |
  | `timeout` (v4.2) | ms | aborts the handler's signal |
  | `enabled` (v4.5) | `true` | execution barrier |
  | `serialize` (v4.6) | `true` | include in the payload |
  | `middleware` (v4.6) | `(next, {signal}) => Promise` array | wraps the handler; first entry is outermost; throw to abort |
  | useFetch only | `method`, `query`, `body`, `headers`, `baseURL`, `cache`, `$fetch` (custom instance), ofetch interceptors `onRequest`/`onRequestError`/`onResponse`/`onResponseError` | |

  Returns: `data`, `status` (`'idle'|'pending'|'success'|'error'`), `pending` (true only while in flight; with `experimental.pendingWhenIdle` also while idle with no data), `error` (`NuxtError` for useFetch), `refresh`/`execute`, and `clear`. The return value is also awaitable (`then`/`catch`/`finally` can be destructured). The handler signature is `(nuxtApp, { signal })`; the signal aborts on `dedupe: 'cancel'`, on `clear()` and on timeout. `useFetch` and `useAsyncData` are reserved names because the compiler transforms them. Source: docs/4.api/2.composables/use-async-data.md, docs/4.api/2.composables/use-fetch.md
- **Notable extras**:
  - **`createUseFetch(defaults | (callerOpts) => overrides)` / `createUseAsyncData`** (since 4.4): a compiler macro that must be **exported** from `composables/`, which then gets keys injected automatically. A plain object sets defaults the caller can override; a function enforces overrides and is needed when it calls `useNuxtApp()`. `routes: {} as Routes` types a third-party API (fetchdts `Endpoint`/`DynamicParam` shape, which can be generated from OpenAPI). Source: docs/4.api/2.composables/create-use-fetch.md
  - **Addons** (`defineUseFetchAddon`/`defineUseAsyncDataAddon`, since 4.6): typed custom call-site options (`UseFetchAddonOptions<{…}>`), a `setup` that runs on every call, middleware, and interceptor arrays. The function returned from `setup` can extend the returned object, a `key` resolver can contribute to the auto key, and `then`/`catch`/`finally` can be wrapped. Addons run in array order and duplicates run once. Source: docs/4.api/3.utils/define-use-fetch-addon.md
  - `useHydration`, `onPrehydrate`, and `callOnce` with `mode: 'navigation'` (v3.15). Source: docs/4.api/3.utils/call-once.md

## 4. Mutations

- **Form handling without JS (progressive enhancement)**: **Not supported / not found in docs.** There is no `<Form>` component, no action convention, and no documented integration for a native `<form method="post">` that falls back cleanly. Forms in the docs are `@submit.prevent` handlers calling `$fetch`. A plain HTML form *can* post to a `server/routes` or `server/api` handler, which reads `readBody` or `event.req.formData()` and replies with `sendRedirect`, but the docs present no pattern for it, and Nuxt 5 makes server route errors return JSON. (Separately, the `noScripts` pages of §2 are read-only zero-JS pages.) Source: docs/1.getting-started/10.data-fetching.md, docs/3.guide/5.recipes/4.sessions-and-authentication.md
- **Server functions / RPC / actions**: **Not supported as a primitive.** Mutations go to HTTP endpoints in `server/api/*.post.ts` (method suffixes) and are called with `$fetch(url, { method: 'POST', body })`. The calls are typed from the generated route types, including validated bodies (§8). There are no `'use server'` functions and no generated RPC stubs; community modules exist but are not in the docs. Source: docs/2.directory-structure/1.server.md, docs/1.getting-started/10.data-fetching.md
- **Pending, error and validation-error state**: **Partial (manual or composable)**.
  - **Pending**: track a local ref around `$fetch`, or wrap the mutation in `useAsyncData(..., { immediate: false })` and call `execute()` to get `status`/`error`.
  - **Errors**: `$fetch` throws `FetchError` on non-2xx (`error.data` holds the response body). On the server side, `createError({ status, statusText, data })`; with useFetch the custom data lands at `error.value.data.data`.
  - **Validation**: `readValidatedBody`/`getValidatedQuery` take any Standard Schema or a function. Invalid input gets a **400 whose `data.issues` lists the failures**; pass `onError` to change the error. `defineValidatedHandler({ validate: { body, query, headers }, handler })` also types the request on the client.
  - There are no form-field-level error helpers.

  Source: docs/3.guide/6.going-further/5.server-imports.md, docs/4.api/3.utils/create-error.md, docs/1.getting-started/10.data-fetching.md
- **Optimistic UI**: **Partial (recipe)**. The documented pattern uses `useNuxtData('todos')` and writes to the cached ref: snapshot the old value in `onRequest`, update it optimistically, roll back in `onResponseError`, and call `refreshNuxtData('todos')` in `onResponse`. There is no dedicated API. Source: docs/4.api/2.composables/use-nuxt-data.md
- **Data refresh after a mutation**: **Manual.** Use `refresh()` on the instance, `refreshNuxtData(keys?)` (all keys by default), `clearNuxtData`, or a reactive key or option that triggers a refetch. Nothing is revalidated automatically. Source: docs/4.api/3.utils/refresh-nuxt-data.md
- **Redirect after mutation**: **Partial.** On the client, call `await navigateTo(path)` after the `$fetch` resolves. On the server, `sendRedirect(event, location, status)`; in `nuxt/server` it returns a response that you must `return`. Source: docs/4.api/3.utils/navigate-to.md, upgrade.md
- **File uploads**: **Partial (low-level).** Server side: `await event.req.formData()` (Web standard) or `readMultipartFormData` / `readFormData` / `readRawBody` from `nitro/h3`. Client side: pass a `FormData` body to `$fetch`. There are no size limits, streaming-upload helpers or upload components in the docs. Source: upgrade.md (h3 v1 → v2 table), docs/3.guide/6.going-further/5.server-imports.md
- **Multiple actions per page**: **N/A.** Each mutation is a separate endpoint or method file; there is no action routing concept. Source: docs/2.directory-structure/1.server.md
- **CSRF protection built in**: **Not found in docs.** Related facts: sessions from `nuxt/server` default to `sameSite: 'lax'`, `httpOnly` and `secure` cookies, and `useCookie({ sameSite })` is configurable. Community modules such as `nuxt-csurf` and `nuxt-security` provide CSRF protection (from memory, unverified). Source: docs/3.guide/6.going-further/5.server-imports.md
- **Notable extras**: `handleCors(event, options)` and the `cors` route rule; `createUseFetch` addons for auth headers; `deriveSecret(purpose)` for signing tokens; and `useSession`/`getSession`/`updateSession`/`clearSession` sealed-cookie sessions (iron-webcrypto; the cookie must stay under 4096 bytes; `maxAge`, `name`, `cookie` and `password` (32+ chars) options). Sessions are auth-adjacent and described further in §6. Source: docs/3.guide/6.going-further/5.server-imports.md

## 5. Caching & revalidation

- **Page/HTML caching**: **Supported (route rules on the Nitro cache layer)**. Nuxt registers middleware and wraps the matching routes in Nitro cache handlers.

  | rule | values | behavior |
  |---|---|---|
  | `swr` | `number` (s) \| `true` | adds cache headers and caches the response on the server or reverse proxy for the TTL. After expiry it serves stale and regenerates in the background. `true` sends `stale-while-revalidate` without a max-age. The `node-server` preset caches the full response. |
  | `isr` | `number` \| `true` | like `swr`, but also stores the response in the **CDN cache** on supporting platforms ("currently Netlify or Vercel"). `true` keeps it until the next deploy. |
  | `cache` | Nitro cache options object | e.g. `{ cache: { swr: true, maxAge: 60, allowQuery: ['page'] } }` or `{ cache: { maxAge: 3600 } }`. Docs name `maxAge`, `swr` and `allowQuery`; Nitro also has `staleMaxAge`, `varies`, `name`, `group`, `getKey`, `base`, `shouldBypassCache`, `shouldInvalidateCache` and `integrity` (from memory, unverified). |
  | `prerender` | bool | build-time HTML file (§2) |
  | `headers` | object | static response headers (e.g. `cache-control` for assets) |

  Behaviors:
  - **Nuxt 5: cached routes (`cache`/`swr`/`isr`) key on the path only.** The query string is **removed before the handler runs** unless `allowQuery: true | string[]` is set.
  - ISR/SWR routes also write a `_payload.json` the first time they render; CDNs can cache it, and client navigation reuses it.
  - Cached routes are never streamed.
  - Rules are mapped to Netlify/Vercel native config where possible.
  - With `early404`, a `cache` rule's `maxAge` is also sent as `Cache-Control` on 404 misses.

  Source: docs/3.guide/1.concepts/1.rendering.md, upgrade.md ("Cached Route Rules Ignore Query Parameters"), docs/1.getting-started/15.prerendering.md, exp.md
- **Time-based revalidation (ISR)**: **Supported**. `swr: N`, `isr: N`, or `cache: { maxAge, swr: true }`. Regeneration is stale-while-revalidate (background). Source: docs/3.guide/1.concepts/1.rendering.md
- **On-demand revalidation (by path or tag)**: **Not found in docs.** There is no `revalidatePath`/`revalidateTag` equivalent and no cache-tag API. Possible workarounds (from memory, unverified): purge the Nitro cache storage mount, or use the host's ISR bypass/purge mechanism (e.g. a Vercel bypass token).
- **Data-level / function-level caching**: **Supported via Nitro (server side) and keys (client side).** `defineCachedFunction()` and `defineCachedHandler()` (formerly `cachedEventHandler`) come from **`nitro/cache`**. The docs name them and say they are not portable across server builders (`@nuxt/vite-server` lacks them); their options are not documented in this clone (from memory: `maxAge`, `swr`, `staleMaxAge`, `getKey`, `name`, `group`, `varies`, `shouldBypassCache`, `shouldInvalidateCache`; unverified). In the app layer: `useAsyncData` keys and `getCachedData`, `sharedPrerenderData`, and `callOnce`. Source: docs/3.guide/6.going-further/5.server-imports.md ("What Isn't Portable"), docs/3.guide/4.modules/9.server-compatibility.md
- **Client navigation cache**: **Supported (payload-level)**. Prefetched or extracted `_payload.json` goes into `nuxtApp.static.data`, and the default `getCachedData` reuses it, so prerendered and ISR pages skip refetching on client navigation. **On a fully static site this data can be stale until the next rebuild.** `purgeCachedData` (on by default) clears the caches on navigation. Other mechanisms: `<KeepAlive>` page caching (`keepalive`), and a custom `getCachedData` for a time-based client cache. There is no router-level "stale time" setting. Source: docs/1.getting-started/15.prerendering.md, docs/4.api/2.composables/use-async-data.md, exp.md
- **HTTP cache-header helpers**: **Partial.** The `headers` route rule; `swr`/`isr` set cache headers automatically; `useResponseHeader(name)` returns a writable ref for the server response header from pages, middleware or plugins (since 3.14); in handlers, `event.res.headers.set()`. There is no dedicated cache-control builder. Under `ssrStreaming`, headers written after the shell is flushed are lost. Source: docs/4.api/2.composables/use-response-header.md, exp.md
- **Preview / draft mode bypass**: **Supported (client-driven)**. `usePreviewMode({ shouldEnable?, getState?, onEnable?, onDisable? })` returns `{ enabled, state }`.
  - It turns on by default when the URL has `?preview=true`, and stores a `token` query param in `state`. `getState` merges extra state into it.
  - On enable it calls `refreshNuxtData()`, refetching everything so preview content replaces static or extracted payloads. On disable it schedules the refresh after the next navigation.
  - `useAsyncData`/`useFetch` are forced to re-render with preview content.
  - The docs say to test it with `nuxt generate` + `nuxt preview`, not `nuxt dev`.
  - Whether it bypasses **server-side** SWR/ISR caches is **not documented**.

  Source: docs/4.api/2.composables/use-preview-mode.md
- **Notable extras**: `experimental.payloadExtraction` modes (§3); island responses are cacheable at the endpoint because props travel as GET query (§2); `granularCachedData`.

## 6. Server & API

- **API routes / endpoints (per HTTP method)**: **Supported (file-based in `server/`)**.
  - `server/api/**` is served under `/api/**`; `server/routes/**` is served with no prefix (e.g. a dynamic `sitemap.xml.ts`).
  - **Method suffixes**: `.get`, `.post`, `.put`, `.delete`, `.patch`, etc. Other methods get **405**. `index.post.ts` works inside directories. In Nuxt 5 an unknown dotted suffix (`hello.world.ts`) **fails the build** unless it is a known extension (`feed.json.ts`) or listed in `nitro.scanSuffixes`.
  - **Params**: `[name].ts` is read with `getRouterParam(event, 'name')` or `event.context.params`. From `nuxt/server` it returns the raw URL value; pass `{ decode: true }` to decode. `[...].ts` / `[...slug].ts` are catch-alls.
  - The docs warn that server routes do not yet support everything page dynamic routes do.
  - The handler is the default export of `defineEventHandler` from **`nuxt/server`**. A bare function, or h3's `defineEventHandler`, receives the runtime's own event instead.
  - **Return values**:
    - a JSON-serializable value, sent as JSON with `event.res` status and headers;
    - a `Response`, with `event.res.headers` merged in, same-name headers replaced except `set-cookie`, which is appended;
    - a `ReadableStream` (or a Node stream);
    - text or HTML.
  - Uncaught errors return 500; `createError({ status, statusText, data })` sets a custom status; `setResponseStatus(event, 202)` sets success codes.
  - Registration alternatives: the `serverHandlers` config (`{ route (rou3 syntax), handler, method, middleware: bool, lazy: bool }`), `devServerHandlers`, and Kit `addServerHandler` (typed automatically).
  - Legacy routing: h3's `createRouter`/`useBase` for nested routers and `fromNodeMiddleware` for Node-style middleware (discouraged).

  Source: docs/2.directory-structure/1.server.md, docs/3.guide/6.going-further/5.server-imports.md, docs/4.api/6.nuxt-config.md, upgrade.md
- **Middleware (global, per-route, ordering, capabilities)**: **Supported (two separate systems)**.
  - **Server middleware** (`server/middleware/*.ts`) runs **on every request, before any server route** and before page rendering. It inspects or extends the request (`event.context.auth = …`), checks headers, logs, or throws. It "should not return anything"; if it does return a value, that value **ends the request and becomes the response** (discouraged). **Nuxt 5 change**: an error thrown in server middleware returns **JSON even for a browser page navigation**, so the docs move auth checks that should show the HTML error page into route middleware.
  - **Per-route server middleware**: no file convention. Check `getRequestURL(event).pathname` inside the handler, or register a `serverHandlers` entry with `route` and `middleware: true`. Declarative per-path behavior comes from route rules (`headers`, `cors`, `redirect`, `proxy`). The `basicAuth` route rule is removed in Nitro v3 and replaced by middleware.
  - **Ordering** of server middleware files is not documented in this clone (alphabetical by filename, from memory, unverified).
  - **Route middleware** (Vue side) is covered in §1.

  Source: docs/2.directory-structure/1.server.md, docs/3.guide/1.concepts/2.nuxt-lifecycle.md, upgrade.md ("Error Format Depends on Where the Error Is Thrown")
- **Request context (cookies, headers, locals)**: **Supported**.
  - **The event**: `RequestEvent = { req: Request, url: URL, res: { status, statusText, headers: Headers }, context }`. `event.context` holds per-request locals (middleware → handler) and `params`. `NuxtRequestEvent` is h3's `H3Event` under Nitro, which adds `event.node`, `event.runtime` and `event.waitUntil`.
  - **`nuxt/server` helpers**:
    - URL and request: `getRequestURL`/`getRequestHost`/`getRequestProtocol` (forwarded headers trusted only with `{ xForwardedHost, xForwardedProto }`), `getRequestHeader(s)`, `getRouterParam(s)`.
    - Client IP: `getRequestIP` (no forwarded header trusted by default; `{ xForwardedFor: true }` reads the first XFF entry).
    - Input: `getQuery`/`getValidatedQuery`, `readBody`/`readValidatedBody` (Standard Schema; 400 with `data.issues`). `readBody` on a GET throws 405.
    - Cookies and response: `getCookie`/`parseCookies`/`setCookie`/`deleteCookie`, `setResponseStatus`, `handleCors` (returns a preflight `Response` or `false`), `sendRedirect` (returns a value you must return).
    - In-process calls: `serverFetch(event, path)` fetches the app in-process, forwarding `cookie`/`authorization` unless `forwardHeaders` is set.
    - Secrets and config: `useSession`/`getSession`/`updateSession`/`clearSession`, `deriveSecret`, `getRouteRules`/`matchRouteRules`, `useRuntimeConfig()` (no event argument), `useServerHooks`, `useAppConfig(event)`.
  - **Forwarding**: `event.$fetch(path)` forwards context and headers (minus hop-by-hop headers).
  - **Escape hatch**: anything else comes from `nitro/h3` (`proxyRequest`, `readMultipartFormData`, `writeEarlyHints`, …). Handlers that need the runtime event import `defineEventHandler` from `nitro/h3`.
  - **On the app side**: `useRequestEvent()`, `useRequestHeaders()`, `useCookie()` (options below).

  `useCookie(name, opts)` options:

  | option | default | notes |
  |---|---|---|
  | `decode` / `encode` | `destr`+decodeURIComponent / `JSON.stringify`+encodeURIComponent | values are serialized as JSON |
  | `default` | `undefined` | `() => T \| Ref<T>` |
  | `watch` | `true` | `true` (deep) \| `'shallow'` \| `false` |
  | `refresh` (v4.4) | `false` | renew the expiry on every explicit write |
  | `readonly` | `false` | |
  | `maxAge` / `expires` | – | `expires` may be a getter, re-evaluated on each write |
  | `httpOnly`, `secure`, `partitioned`, `domain`, `path` (`'/'`), `sameSite` (`true` = Strict, `'lax'`, …) | | |

  `refreshCookie(name)` re-reads a cookie. `experimental.cookieStore` (on by default) listens to CookieStore changes.

  Source: docs/3.guide/6.going-further/5.server-imports.md, docs/2.directory-structure/1.server.md, docs/4.api/2.composables/use-cookie.md
- **Streaming responses & SSE**: **Partial.** A handler can return a `ReadableStream` or a Node stream (labelled "experimental" but available on every runtime). **SSE production helpers are not documented** in this clone; h3's `createEventStream` from `nitro/h3` exists (from memory, unverified). Consuming SSE over POST is a documented recipe: `$fetch(url, { method: 'POST', responseType: 'stream' })` piped through `TextDecoderStream`; for GET, use `EventSource`. Source: docs/2.directory-structure/1.server.md, docs/1.getting-started/10.data-fetching.md
- **Running work after the response (waitUntil/after)**: **Supported (Nitro event)**. `event.waitUntil(promise)` waits for background work without delaying the response, using the platform's native mechanism where one exists. It is **not** on the portable `RequestEvent`; it belongs to the Nitro/h3 event, so the handler needs h3's `defineEventHandler`. Source: docs/2.directory-structure/1.server.md, docs/3.guide/6.going-further/5.server-imports.md
- **Server-only code boundaries**: **Supported (directory and bundle separation plus build errors)**.
  - `app/` and `server/` are separate bundles. The docs say not to import Vue app code into server code or the reverse.
  - `shared/` may import **neither** Vue nor Nitro code. Only `shared/utils` and `shared/types` are auto-imported (top level only); everything else is reached through `#shared/...`.
  - **Build errors**: importing `nuxt/server` from a Vue component, a plugin or `shared/` **fails the build**. The `#server` alias (v4.3) errors in client code. `nuxt/server` also must not be used in `nuxt.config` or module setup, where `useRuntimeConfig()` returns empty.
  - **File and value boundaries**: `.server.vue` components and pages keep their code (and dependencies) out of the client bundle. `.server.ts`/`.client.ts` plugins. `import.meta.server`/`import.meta.client` are replaced at build time so the dead branch is tree-shaken. Private `runtimeConfig` keys exist only on the server (the client sees `public` and `app`, which are writable and reactive there; the server copy is read-only).
  - **Types**: separate tsconfigs (`app`/`server`/`shared`/`node`), with `server/types` scoped to the server and `app/types` to the app.
  - A `server-only` marker package or `"use server"` directive was **not found**.

  Source: docs/2.directory-structure/1.shared.md, docs/2.directory-structure/1.server.md, docs/3.guide/6.going-further/5.server-imports.md, docs/3.guide/6.going-further/10.runtime-config.md, docs/4.api/6.advanced/2.import-meta.md
- **Notable extras**:
  - **Server plugins** (`server/plugins/*.ts`, `definePlugin` from `'nitro'`) run once at server start, or on every boot in serverless, without being awaited. Nitro runtime hooks `request`/`response`/`error`/`close` come from `useNitroHooks()` (`nitro/app`); renderer hooks `render:html`/`render:response`/`render:island`/`render:route` come from `useServerHooks()`.
  - Lazy handlers (`lazyEventHandler`, from `nitro/h3`).
  - The **builder-agnostic server surface** `nuxt/server`, so one file runs on Nitro v2 (Nuxt 4.6), Nitro v3 or `@nuxt/vite-server`.
  - The **Nitro v2 compatibility layer** (`nitroLegacy`, applied to modules automatically).
  - `$fetch` called on the server invokes your own handlers in-process.
  - `proxy` route rule.
  - The handler return type flows into `$fetch` types (§8).

  Source: docs/2.directory-structure/1.server.md, docs/3.guide/6.going-further/5.server-imports.md, docs/4.api/6.advanced/1.hooks.md, upgrade.md

## 7. Loading & error states

- **Route-level loading UI**: **Partial (no per-route loading file).** Awaited data **blocks navigation**: the old page stays until the new page's Suspense resolves, and `<NuxtLoadingIndicator>` (put in `app.vue` or a layout) shows a top progress bar meanwhile:

  | prop | default | behavior |
  |---|---|---|
  | `color` | built-in styling; `false` = no inline color | bar color |
  | `errorColor` | – | color when `error` is set |
  | `finishColor` | = `color` | color on finish |
  | `height` | `3` px | |
  | `duration` | `2000` ms | expected duration |
  | `throttle` | `200` ms | delay before showing and hiding |
  | `estimatedProgress` | built-in back-off | `(duration, elapsed) => 0..100` |

  The default slot allows custom markup. `useLoadingIndicator({ duration, throttle, estimatedProgress })` exposes `isLoading`, `error`, `progress` (readonly shallow refs) and `start({ force })`, `set(n, { force })`, `finish({ force, error })` and `clear()`. It listens to `page:loading:start`/`page:loading:end`; with a static `key` the start hook can fire without setup re-running. For non-blocking pages, use `lazy` data with `status`. The first load of an `ssr: false` app uses `spa-loading-template.html`. Islands use `lazy` plus `#fallback`; `<ClientOnly>` uses `#fallback`. Source: docs/4.api/1.components/5.nuxt-loading-indicator.md, docs/4.api/2.composables/use-loading-indicator.md, docs/1.getting-started/10.data-fetching.md, docs/4.api/6.advanced/1.hooks.md
- **Error boundaries (per route/segment, root/global)**: **Partial.**
  - **Global**: `app/error.vue`, which replaces the whole app on a **fatal** error. It is **not a route**, so no `definePageMeta`, though it can use `<NuxtLayout name>`. Its only prop is `error: NuxtError` (`status`, `statusText`, `fatal`, `unhandled`, `message`, `data`, `cause`).
  - **Local, client only**: `<NuxtErrorBoundary>` uses `onErrorCaptured` and renders the `#error` slot with `{ error, clearError }`. It emits `@error`. Setting `error = null` re-renders the default slot. Errors are **cleared automatically when navigating**. `error` and `clearError` are also available through a template ref.
  - `<NuxtClientFallback>` (experimental) re-renders on the client when SSR fails.
  - **There is no per-route-segment error file.**

  Source: docs/2.directory-structure/1.app/3.error.md, docs/4.api/1.components/6.nuxt-error-boundary.md, docs/1.getting-started/12.error-handling.md
- **404 / not-found handling**: **Supported.**
  - A URL matching no page renders the error page with a 404. `validate` returning `false` also gives 404 if nothing else matches, and `createError({ status: 404 })` is available anywhere.
  - `experimental.early404` (opt-in) short-circuits unknown paths before the Vue app loads.
  - Static hosting: `404.html` is emitted, and `experimental.prerenderErrorPages` server-renders `error.vue` into it.
  - Client links to non-page paths fall back to a full load (`serverPathFallback`).
  - There is no `notFound()` helper or `not-found.vue` file; `error.vue` handles every status.

  Source: docs/1.getting-started/07.routing.md, exp.md, docs/3.guide/1.concepts/1.rendering.md
- **Helpers (redirect / notFound / error)**: **Supported.**
  - `createError(string | { status, statusText, message, data, cause, fatal, name, stack })`: a string becomes `message` with status 500. Thrown on the server, it triggers the **full-screen error page**. Thrown on the client it is **non-fatal** unless `fatal: true`.
  - `showError(err)` sets the shared `useError()` state and calls `app:error`; usable in middleware, plugins and setup.
  - `clearError({ redirect? })` clears the error. Plugins that threw are **not re-run** until it is called.
  - Also: `useError()`, `navigateTo()`, `abortNavigation()`, `setResponseStatus(event, code, text?)` (no effect in the browser), `isNuxtError()`.
  - In server routes, `createError` from `nuxt/server` or `HTTPError` from `nitro/h3`. In Nuxt 5, `NuxtError` is no longer an `HTTPError` subclass; use `HTTPError.isError()`.
  - `statusText` should be short ASCII; put detail in `message`.

  Source: docs/1.getting-started/12.error-handling.md, docs/4.api/3.utils/create-error.md, docs/4.api/3.utils/show-error.md, upgrade.md
- **Expected vs unexpected errors**: **Partial (via createError plus redaction).** In production SSR, the error page and payload receive **only `message` and `data`** for errors made with `createError`. Any other thrown error (a failed `$fetch`, for example) is marked `unhandled` and gets a **generic message**. Custom fields are lost unless placed in `data`, which Nuxt 5 always passes unstringified. `cause` chains are exposed **in dev only**. In API routes, `message` does **not** reach the client; use `statusText` or `data` (with useFetch, the data is at `error.value.data.data`). **Nuxt 5 response format**: page errors always return HTML with the error status (including for `fetch` and `Accept: application/json`), server route and server middleware errors always return JSON, and payload errors return JSON. Source: docs/2.directory-structure/1.app/3.error.md, docs/4.api/3.utils/create-error.md, upgrade.md
- **Error reporting hooks**: **Supported (client and app); Partial (server).**
  - `vue:error(err, instance, info)` fires for errors that propagate to the root (it is `onErrorCaptured`-based).
  - `nuxtApp.vueApp.config.errorHandler` receives **all** Vue errors, including handled ones, and is the recommended place to wire a reporting service.
  - `app:error` covers startup and fatal errors: plugins, `app:created`, `app:beforeMount`, SSR render, mount and `app:mounted`. `app:error:cleared` fires when the error is cleared.
  - Chunk-load errors: `experimental.emitRouteChunkError` is `'automatic'` (default; reloads the new route on navigation), `'automatic-immediate'`, `'manual'` (emits `app:chunkError` for you to handle) or `false`.
  - **Server**: the Nitro `error(error, { event })` runtime hook, registered in a server plugin through `useNitroHooks()`, plus Nitro's `defineErrorHandler`. Note that the error-handling guide still says "You cannot currently define a server-side handler for these errors", which conflicts with the hooks reference.

  Source: docs/1.getting-started/12.error-handling.md, docs/4.api/6.advanced/1.hooks.md, docs/3.guide/6.going-further/5.server-imports.md, exp.md
- **Notable extras**: middleware re-runs during error-page rendering (check `useError()`). In dev, warnings from template diagnostics reach the error page and overlays. Under streaming, errors after the shell flush are recovered on the client (E8009). Every documented NUXT_ diagnostic code has its own docs page (`docs/errors/*`).

## 8. Type safety

- **Typed links and params**: **Supported (Nuxt 5 default)**.
  - `typedPages`, now native to vue-router, generates route names and paths: `useRoute('posts-id').params.id` is typed, and `NuxtLink :to`, `navigateTo` and `router.push` are checked.
  - Routes added at runtime need manual augmentation of the generated types.
  - Layout names (`LayoutKey`/`NuxtLayouts`), layout **props** (from the layout's `defineProps`, through `definePageMeta({ layout: { name, props } })` and `setPageLayout`) and middleware names (`MiddlewareKey`) are typed. Custom page meta is typed by augmenting `PageMeta` in `#app`.
  - Build-time check: `NUXT_B4025` (unknown route in a static `to`).

  Source: upgrade.md ("Typed Pages Enabled by Default"), exp.md, docs/4.api/3.utils/define-page-meta.md, docs/2.directory-structure/1.app/1.layouts.md
- **Typed loader/server data flowing to components**: **Supported (inferred)**. `useAsyncData` infers `data` from the handler's return type, after `transform`/`pick`, and `default` widens it. `useFetch` infers it from the **server handler's return type** (`defineEventHandler` keeps it; annotate the returned value, not the handler). The error type of `useFetch` is `NuxtError<unknown>`. Server-route JSON serialization is reflected in the types: Nuxt "does its best" to map them (a `Date` becomes a string, and `toJSON` is respected). Payload data is devalue-serialized, so rich types survive. Source: docs/1.getting-started/10.data-fetching.md, docs/3.guide/6.going-further/5.server-imports.md
- **Typed server calls (RPC / fetch)**: **Supported, and rebuilt in Nuxt 5.**
  - `$fetch` and `useFetch` are typed from **generated route types** reported by the server builder (fetchdts format). Checking cost stays flat however many routes there are; the old `InternalApi` approach did not scale past about 300 routes.
  - The method decides which handler supplies the type (GET vs `.post.ts`).
  - Request `body`, `query` and `headers` are **enforced** when the handler validates them with a Standard Schema (Zod, Valibot, ArkType) through `defineValidatedHandler({ validate: { body, query, headers }, handler })` or `readValidatedBody`.
  - `experimental.strictRouteTypes` is `false` (default: unknown paths are `unknown`, no method is rejected), `true` (only reported routes and methods are allowed; `public/` files become errors) or `'isomorphic'` (pages are added as `GET → string`).
  - Always `unknown`: runtime-built paths, absolute URLs and `Request` objects. An explicit generic `$fetch<T>()` opts a call out.
  - **`baseURL` is resolved into the path** before matching, and passing a path that already contains the base is a type error. A runtime or ref base, or another origin, gives `unknown`.
  - Routes Nuxt cannot see are declared by augmenting `ServerRoutes` with `[Endpoint]: { GET: { response, query, body } }`. `createUseFetch({ routes: {} as Routes })` types a third-party API. `$Fetch` is the type of a fetch instance.
  - Routes added through `addServerHandler` are typed automatically. `serverFetch(...).json()` is typed too.

  Source: docs/1.getting-started/10.data-fetching.md ("Typed Routes"), exp.md (`strictRouteTypes`), upgrade.md ("Typed `$fetch` Rebuilt"), docs/4.api/2.composables/create-use-fetch.md
- **Generated types (codegen or inferred)**: **Codegen.**
  - `.nuxt/` types and the tsconfig files are generated by `nuxt dev`, `nuxt build` and **`nuxt prepare`**. They cover auto-imports, components, route types, aliases (`#imports`, `#app`, `#build`, `#shared`, `#server`, `#layers/name`), runtime config and app config.
  - Project references: `.nuxt/tsconfig.app.json`, `tsconfig.server.json`, `tsconfig.node.json` and `tsconfig.shared.json`. The legacy `.nuxt/tsconfig.json` is deprecated. Extend them with `typescript.{tsConfig, appTsConfig, serverTsConfig, nodeTsConfig, sharedTsConfig}`, not by editing the generated files.
  - Type-checking: `nuxt typecheck` (vue-tsc), or `typescript.typeCheck: true | 'build'`. `typescript.strict` defaults to true.
  - Nuxt 5 tsconfig changes: `noUncheckedSideEffectImports` on; `baseUrl` removed; the node tsconfig uses `nodenext` with `erasableSyntaxOnly`.
  - `experimental.typescriptPlugin` enables the @dxup/nuxt language-service enhancements.
  - Module augmentation points: `NuxtServerHooks`, `RouteRuleConfig`/`RouteRules` (in `h3/rules`), and `NitroRuntimeConfig` (`nitro/types`).

  Source: docs/3.guide/1.concepts/8.typescript.md, docs/4.api/6.nuxt-config.md, upgrade.md
- **Typed search params**: **Not supported / not found.** `route.query` is untyped `LocationQuery`, with no schema-validated search params. Source: docs/4.api/2.composables/use-route.md
- **Notable extras**: plugin `provide` helpers are typed automatically on `useNuxtApp()` and in templates. `useState<T>`. Typed runtime config and app config (app config has full types support, runtime config "partial"). Standard Schema validation shares one schema between runtime checking and client types. Source: docs/2.directory-structure/1.app/1.plugins.md, docs/1.getting-started/03.configuration.md

## 9. Metadata & SEO

- **Head/meta management per route**: **Supported (Unhead).**
  - `useHead(input)` takes `title`, `titleTemplate` (string with `%s`, or a function; **a function cannot be set in nuxt.config**), `templateParams` (e.g. `%siteName`, `%separator`), `base`, `link[]`, `meta[]`, `style[]`, `script[]`, `noscript[]`, `htmlAttrs` and `bodyAttrs`. Every property accepts a ref, computed or getter, or the whole input can be a function.
  - Tag options include `tagPosition: 'bodyClose'` (and other positions), and `key` for dedupe.
  - The return value is documented both as `ActiveHeadEntry { patch, dispose }` and as "does not return any value" (the docs contradict themselves).
  - Calls are made in page, layout, component or `app.vue` setup, and entries are disposed with the component.
  - `useSeoMeta({...})` takes 100+ flat typed keys (`title`, `description`, `ogTitle`, `ogImage`, `twitterCard`, …). It is XSS-safe and the recommended API; use getter syntax for reactivity.
  - `useHeadSafe` whitelists attributes per tag: `htmlAttrs` class/style/lang/dir; `bodyAttrs` class/style; `meta` name/property/charset/content/media; `script` type/textContent/nonce/blocking; `link` href/rel/media/… It drops `innerHTML` and `http-equiv`.
  - Template components: `<Title> <Base> <NoScript> <Style> <Meta> <Link> <Body> <Html> <Head>`.
  - **Server-only meta**: wrap the call in `if (import.meta.server)`. `useServerSeoMeta`, `useServerHead` and `useServerHeadSafe` are deprecated and no longer auto-imported in Nuxt 5 (still exported from `#app`).
  - **Global defaults**: `app.head` (static, not reactive; defaults are `charset: utf-8` and `viewport: width=device-width, initial-scale=1`, which can be overridden with the `charset`/`viewport` shortcuts). A static `app.head` link is not rewritten for `cdnURL`.
  - Unhead options: `unhead.renderSSRHeadOptions.omitLineBreaks`. Capo.js tag sorting is always on in Nuxt 5 (`headNext` on by default); the `unhead.legacy` option is ignored.

  Source: docs/1.getting-started/08.seo-meta.md, docs/4.api/2.composables/use-head.md, docs/4.api/2.composables/use-seo-meta.md, docs/4.api/2.composables/use-head-safe.md, upgrade.md, docs/4.api/6.nuxt-config.md
- **Metadata derived from loaded data**: **Supported.** Call `useHead`/`useSeoMeta` with computed values or getters built on `useFetch` data in the same setup. On SSR the awaited data is ready before the head is serialized. **With `ssrStreaming`, head tags registered after an `await` are sent as client-side patch scripts**, so crawlers outside `botRegex` miss them (JSON-LD, noscript and body tags excepted); keep SEO-critical tags synchronous or set `streaming: false` for the route. `definePageMeta({ title })` combined with a layout reading `route.meta.title` is a static (build-time) option. Source: docs/1.getting-started/08.seo-meta.md, exp.md
- **Sitemap / robots / manifest generation**: **Not in core (not found).** Options in core: a static `public/robots.txt`; dynamic `server/routes/sitemap.xml.ts` or `robots.txt.ts` handlers; adding these to `prerender.routes`. A "SEO & PWA" milestone for built-in SEO utilities is on the roadmap (2025) but not shipped according to the docs. The ecosystem has `@nuxtjs/robots` (named in the docs) and `@nuxtjs/sitemap` / the "Nuxt SEO" collection (from memory, unverified). No web manifest generation was found. Source: docs/2.directory-structure/1.public.md, docs/1.getting-started/15.prerendering.md, docs/5.community/6.roadmap.md, docs/3.guide/4.modules/9.server-compatibility.md
- **Open Graph image generation**: **Not in core (not found).** The community `nuxt-og-image` module provides it (from memory, unverified). Source: (none in docs)
- **Canonical, etc.**: **Manual.** Add `useHead({ link: [{ rel: 'canonical', href }] })` and the `hreflang` links yourself; there is no canonical helper. Source: docs/4.api/2.composables/use-head.md
- **Notable extras**: `<NuxtRouteAnnouncer>` reads the page title for screen readers. `htmlAttrs.lang`. The `render:html` Nitro hook can rewrite the final head (it is also the place to inject CSP nonces). `prefetchPreloadTags` forwards the destination's preload hints. `noScripts` pages keep full meta. Source: docs/4.api/1.components/12.nuxt-route-announcer.md, exp.md

## 10. Assets & styling

- **Image optimization**: **Official module `@nuxt/image`** (`npx nuxt module add image`), described as a "core Nuxt module". `<NuxtImg>` outputs a plain `<img>` with no wrapper. It optimizes **local and remote** images through a built-in provider or image CDN providers, rewrites `src` to provider URLs in modern formats (WebP/AVIF), resizes from `width`/`height`, generates responsive output from `sizes`, and supports native lazy loading. Documented props include `format`, `preload: { fetchPriority }`, `loading`, `fetchpriority`, `width` and `height`. `<NuxtPicture>` renders `<picture>` with modern-format sources. Further props (from memory, unverified): `densities`, `quality`, `fit`, `modifiers`, `provider`, `preset`, `placeholder`, `custom`, `nonce`, and `legacyFormat`/`imgAttrs` on NuxtPicture; IPX is the default local provider, with 20+ CDN providers. `compatibilityDate` also governs Nuxt Image behavior. `<NuxtImg preload>` hints can be forwarded by `prefetchPreloadTags`. Core alone only offers `public/` and Vite asset handling, with no image component. Source: docs/4.api/1.components/9.nuxt-img.md, docs/4.api/1.components/10.nuxt-picture.md, docs/3.guide/2.best-practices/performance.md, docs/4.api/6.nuxt-config.md
- **Font optimization**: **Official module `@nuxt/fonts`.** For any `font-family` it finds in your CSS, it (1) resolves the font from `public/`, then from web providers (Google, Bunny, Fontshare; providers are pluggable); (2) generates `@font-face` rules; (3) proxies and caches the files under `/_fonts`; (4) generates metric-adjusted fallbacks with fontaine to reduce CLS; and (5) bundles the fonts with hashed names and long-lived cache headers. Without the module: put local fonts in `public/fonts` and reference them with `url()`; the `fontaine` and Google Fonts community modules also exist. Source: docs/3.guide/2.best-practices/performance.md, docs/1.getting-started/06.styling.md
- **Third-party script loading**: **Official module `@nuxt/scripts`.** It is an abstraction over third-party scripts with SSR support and type safety, plus registry composables. The documented example is `useScriptGoogleAnalytics({ id, scriptOptions: { trigger: 'manual' } })`, which returns `{ onLoaded, proxy }` (a proxy that queues calls until the script loads). From memory, unverified: generic `useScript(src, { trigger })`, where the trigger is `'onNuxtReady'` (default), `'client'`, `'server'`, `'manual'`, a promise, `useScriptTriggerElement` or `useScriptTriggerConsent`; `bundle: true` self-hosts the script; `warmupStrategy`; and facade components such as `<ScriptYouTubePlayer>` and `<ScriptGoogleMaps>`. Core alone offers `useHead({ script: [{ src, async/defer, tagPosition: 'bodyClose' }] })` and `app.head.script`. Source: docs/3.guide/2.best-practices/performance.md, docs/1.getting-started/08.seo-meta.md
- **CSS support**: **Supported (through Vite).**
  - **SFC styles**: `<style scoped>`, CSS Modules (`<style module>` → `$style`), `v-bind()` inside CSS for dynamic values, and `lang="scss|sass|less|styl|stylus|postcss"` (install the preprocessor first).
  - **Global CSS**: the `css: []` option (project files, or npm packages such as `'bulma'`), JS/`@import` imports inside components, or external stylesheets through `app.head.link`/`useHead`.
  - **Inlining**: stylesheets are **inlined in the SSR HTML** (`features.inlineStyles`, Vite only; default `(id) => id.includes('.vue')`). A `build:manifest` hook recipe drops external CSS links entirely.
  - **Preprocessor options**: `vite.css.preprocessorOptions` (e.g. injecting Sass partials with `additionalData`); `vite.css.preprocessorMaxWorkers` (experimental).
  - **PostCSS**: built in, configured with `postcss.plugins` and `postcss.order`. **Nuxt 5 + Vite configures no PostCSS plugins** (autoprefixer and cssnano are opt-in); webpack still adds postcss-import, postcss-url, autoprefixer and cssnano.
  - **Tailwind and UnoCSS** come through modules (`@nuxtjs/tailwindcss` is a community module, as is UnoCSS). **CSS-in-JS** only through third parties (Panda CSS, Pinceau). Layouts can carry per-section styles.
  - Caveats: `<ClientOnly>` content may lose inlined CSS. SFC styles flash unstyled in dev under streaming; put paint-critical CSS in global `css`.

  Source: docs/1.getting-started/06.styling.md, docs/3.guide/6.going-further/1.features.md, upgrade.md, exp.md
- **MDX/Markdown as pages**: **Not in core; official module `@nuxt/content`.** It reads `content/` and parses `.md`, `.yml`, `.csv` and `.json` into collections, queried with a MongoDB-like API (`queryCollection('content').path(route.path).first()`, wrapped in `useAsyncData`). Vue components are used inside Markdown through **MDC** syntax, rendered by `<ContentRenderer :value>`, and navigation is generated automatically. Markdown files are **not** pages by themselves; a catch-all page renders them. JSX-based MDX is not applicable (Vue). Source: docs/2.directory-structure/1.content.md
- **Notable extras**:
  - Assets: `app/assets/` files are processed by the bundler (`~/assets/...`, never served at `/assets/`), and `public/` is served as-is.
  - Static literal `src` values are rewritten with `baseURL` and hashed. Dynamic ones should use Vite `?url` dynamic imports or `import.meta.glob` (`eager: true` for synchronous use). Vite's `new URL(…, import.meta.url)` pattern does not work under SSR.
  - `vue.transformAssetUrls`; `app.cdnURL`.
  - `<NuxtTime>` (since 3.17) formats dates consistently between server and client.
  - Vue compile flags: Options API off in Nuxt 5 (`vue.config`/`__VUE_OPTIONS_API__`), `vue.propsDestructure`, `vue.runtimeCompiler`.

  Source: docs/1.getting-started/05.assets.md, docs/4.api/6.nuxt-config.md, docs/4.api/1.components/13.nuxt-time.md

## 11. Build output & deployment

- **Output modes (server, static export, SPA)**: **Supported.**
  - `nuxt build` produces `.output/server/index.mjs` plus `.output/public`.
  - `nuxt generate` (or `build --prerender`) produces static `.output/public` with 200/404 fallbacks.
  - SPA: `ssr: false`, then generate, giving `index.html` plus the JS.
  - Hybrid: route rules, with some routes prerendered inside a server build.
  - `nuxt preview` runs the built output locally.
  - With `@nuxt/vite-server`: a static SPA, or a web `{ fetch }` server whose `nuxt generate` crawls that server.

  Source: docs/1.getting-started/16.deployment.md, docs/1.getting-started/15.prerendering.md, docs/4.api/6.nuxt-config.md
- **Supported runtimes; per-route runtime choice**: **Supported runtimes, no per-route choice.**
  - **Node** (default `node-server` preset): env `NITRO_PORT`/`PORT` (3000), `NITRO_HOST`/`HOST` (`0.0.0.0`) and `NITRO_SSL_CERT`/`NITRO_SSL_KEY`. Run with `NODE_ENV=production`. A `node_cluster` preset (round-robin workers) and PM2 also work.
  - Deno and Bun.
  - Edge and serverless: Cloudflare Workers and Pages (zero-config), Vercel (and `vercel-edge`), Netlify Functions and Edge (`netlify-edge`), plus "experimental browser service workers".
  - **Per-route runtime selection: not found.** There is one preset per build.

  Source: docs/1.getting-started/16.deployment.md, docs/3.guide/1.concepts/1.rendering.md, docs/1.getting-started/13.server.md, docs/3.guide/1.concepts/4.server-engine.md
- **Adapters / presets (count, official vs community, API)**: **Supported (Nitro presets).**
  - Presets are set with `nitro.preset` or `NITRO_PRESET`, and many providers are auto-detected with zero config. The docs say "more than 15 presets", and the full list is at nitro.build/deploy (Nitro has well over 30, from memory, unverified). All presets are maintained in Nitro, i.e. official. `compatibilityDate` pins preset behavior.
  - **Adapter API, two layers**:
    1. Custom Nitro presets (Nitro API, not documented here).
    2. Nuxt's new **server-builder contract** (experimental, `@nuxt/kit/internal`): a server builder (`@nuxt/nitro-server` by default, `@nuxt/vite-server` experimental) calls `getServerRuntime()` to get the renderer modules (with `defines` and `overrides`), creates the renderer with `createNuxtRenderer()`, and describes its output with `setServerBuild()`/`useServerBuild()` (`output.root/dir/publicDir`, `input.serverEntry/clientManifest…`). It can expose `runtime.handler`, a module exporting web `fetch`, for deploy targets (workers); `#server-entry` lets a worker entry wrap the render.
  - **App builders**: `builder: 'vite' | 'webpack' | 'rspack' | { bundle(nuxt) }`. They work through the **build output contract** (`serverEntry`, `ssrStyles`, `clientManifest`, `clientPrecomputed`, `entryChunkName`, `entryIds`, set with `setBuildOutput`).

  Source: docs/1.getting-started/16.deployment.md, docs/1.getting-started/13.server.md, docs/3.guide/6.going-further/8.builders.md
- **Config-level headers, redirects, rewrites, trailing slash, base path**: **Partial.**
  - `routeRules.headers`.
  - `routeRules.redirect`: `'/new'` or `{ to, status }` (`statusCode` is accepted with a warning in Nuxt 5). It is also applied on the client through the app manifest.
  - `routeRules.proxy`: a string or `{ to, ...h3 proxy options }`. This is the **rewrite** mechanism; there is no `rewrite` key.
  - `routeRules.cors: true`. Redirects and headers are mapped to Netlify/Vercel native rules where possible.
  - **Trailing slash**: no global redirect policy was found. vue-router's `strict` option makes matching strict, and `<NuxtLink>`'s `trailingSlash: 'append' | 'remove'` (through `defineNuxtLink` or `experimental.defaults.nuxtLink`) only rewrites generated hrefs.
  - **Base path**: `app.baseURL` (§1).
  - Page `alias`/`redirect` in `definePageMeta`.

  Source: docs/3.guide/1.concepts/1.rendering.md, upgrade.md, docs/4.api/1.components/4.nuxt-link.md, docs/3.guide/5.recipes/1.custom-routing.md
- **Standalone / self-contained output**: **Supported.** `.output/` is self-contained and does not need `node_modules`. Nitro v3 **bundles every dependency** by default, unlike v2, which externalized them. The Vue compiler packages are mocked out of the server bundle unless `vue.runtimeCompiler` is set, saving about 860 KB (~59%). `@nuxt/vite-server` output is also fully bundled. Source: docs/3.guide/1.concepts/4.server-engine.md, upgrade.md, docs/4.api/6.nuxt-config.md
- **Skew protection**: **Partial.**
  - `experimental.appManifest` (on by default) with `checkOutdatedBuildInterval` (default 3600000 ms, `false` to disable) polls for a newer build and fires the `app:manifest:update({ id, timestamp })` hook.
  - When a chunk fails to load, `emitRouteChunkError: 'automatic'` performs a **hard reload of the target route**. `experimental.restoreState` can restore `useState` from sessionStorage after the reload (opt-in; may flicker).
  - `entryImportMap` (on by default) keeps chunk hashes stable when only the entry changes.
  - `buildId` namespaces the runtime context.
  - **No retention of old assets or version pinning was found.**

  Source: exp.md, docs/1.getting-started/12.error-handling.md, docs/4.api/3.utils/reload-nuxt-app.md
- **Notable extras**:
  - Build engine: **Vite 8 / Rolldown** (`vite.oxc`, `build.rolldownOptions`), one combined client+server Vite build (`nitroViteEnvironment`), and `vite.$client`/`vite.$server` for per-environment settings.
  - Build tooling: `sourcemap: { server: true, client: false }` (also `'hidden'`/`'nosource'`); `build.analyze` / `nuxt analyze`; `experimental.buildCache` (keeps the last 10 tarballs); `compileHints` (V8 eager compile for the entry, layout and page chunks).
  - Environments: `$development`/`$production`/`$env.<name>` config overrides selected with `--envName`. `.env` is read by the CLI during dev, build and generate but **not** by the production server. `NUXT_*` env variables override `runtimeConfig` at runtime (cast with destr).
  - **Layers**: `extends` (local path, npm, `github:` with `auth`; remote layers need `giget` in Nuxt 5) and an auto-scanned `layers/` directory. Priority runs project > `layers/` (alphabetical, Z wins) > `extends` (first wins). Each layer gets a `#layers/name` alias, and modules can be disabled per layer (v4.3).
  - Other: `asyncEntry` for module federation; `future.multiApp`; serving one build at several paths (remove `payload.path` in a plugin); Cloudflare Rocket Loader and email obfuscation must be turned off.

  Source: upgrade.md, docs/4.api/6.nuxt-config.md, exp.md, docs/1.getting-started/03.configuration.md, docs/3.guide/6.going-further/10.runtime-config.md, docs/3.guide/6.going-further/7.layers.md, docs/1.getting-started/16.deployment.md

## 12. Dev tooling & observability

- **Dev server and HMR**: **Supported.** `nuxt dev` runs the Vite dev server with HMR for the app, and server routes also hot-reload. `devServer` options: `port` (3000), `host`, `https: { key, cert }`, `cors.origin`, `loadingTemplate`. Flags: `--dotenv`, `--inspect` (Node inspector; VS Code and JetBrains configs are documented), `-o`. `experimental.watcher` defaults to `'builder'` in Nuxt 5, reusing Vite's watcher; the alternatives are `'chokidar-granular'`, `'chokidar'` and `'parcel'`. `devServerHandlers` add dev-only server handlers. With `@nuxt/vite-server`, worker targets run under their own runtime (e.g. workerd) during `nuxt dev`. Source: docs/4.api/6.nuxt-config.md, exp.md, docs/3.guide/6.going-further/9.debugging.md, docs/3.guide/6.going-further/8.builders.md
- **Error overlay**: **Partial.** The dev error page shows the `cause` chain, and template-diagnostic warnings are "sent to open error pages and overlays". Errors raised in a deploy-target environment show in the "development error overlay". There is no dedicated overlay page in the docs. Source: exp.md, docs/4.api/3.utils/create-error.md, docs/3.guide/6.going-further/8.builders.md
- **Devtools**: **Supported (official `@nuxt/devtools`, enabled with the `devtools` option).** An in-browser panel; the docs mention its Pages tab (route names and params), Payload, Virtual Files, Hooks, Timeline, Assets, Render Tree and Inspect, plus a Vitest integration through `@nuxt/test-utils`. Its breaking changes are not tied to Nuxt's version. Also available:
  - `experimental.browserDevtoolsTiming` (on in dev) adds performance marks for Nuxt hooks to Chrome's Performance panel.
  - `debug: true | {...}` prints hook names and timings; `debugModuleMutation` records config changes made by modules.
  - `features.devLogs: true | 'silent'` streams server logs to the browser console (`dev:ssr-logs` hook).
  - `@nuxt/a11y` (public alpha) gives accessibility feedback while developing.

  Source: docs/4.api/6.nuxt-config.md, docs/3.guide/2.best-practices/performance.md, docs/1.getting-started/10.data-fetching.md, docs/3.guide/6.going-further/1.features.md, exp.md, docs/3.guide/2.best-practices/accessibility.md
- **Type generation commands**: **Supported.** `nuxt prepare` generates `.nuxt` types (also done automatically by dev and build), and `nuxt typecheck` runs vue-tsc. The `prepare:types` hook extends them. Source: docs/3.guide/1.concepts/8.typescript.md, docs/4.api/6.advanced/1.hooks.md
- **CLI scaffolding / generators**: **Supported.**
  - Project creation: `npm|pnpm|bun create nuxt@latest` and `deno -A npm:create-nuxt@latest`; `nuxt init`.
  - Modules: `nuxt module add <name>` (e.g. `image`, `content`, `eslint`, `pinia`).
  - Other commands: `nuxt upgrade`, `nuxt analyze`, `nuxt generate`, `nuxt preview`.
  - The `nuxt add` generator is linked from the docs, but **CLI command reference pages live in the nuxt/cli repo and are not in this clone** (`docs/4.api/4.commands/README.md`). From memory, unverified: `nuxt add` can create component, composable, layout, plugin, page, middleware, api, layer, etc.

  Source: docs/1.getting-started/02.installation.md, docs/2.directory-structure/1.content.md, docs/4.api/4.commands/README.md
- **AI-agent support**: **Supported (hosted).**
  - A **hosted Nuxt MCP server** over HTTP. Resources: documentation pages, blog posts, deploy providers. Tools: `list-documentation-pages` (filterable by 3.x/4.x/5.x), `get-documentation-page`, `get-getting-started-guide`, `list-blog-posts`/`get-blog-post`, `list-deploy-providers`/`get-deploy-provider`, `list-modules`/`get-module`, `get-changelog`. Prompts: `find-documentation-for-topic`, `deployment-guide`, `migration-help`. The `X-MCP-Tools` header restricts the exposed tools. Setup is documented for ChatGPT, Claude Code/Desktop, Cursor, Gemini CLI and others.
  - **llms.txt**: `nuxt.com/llms.txt` (~5K tokens) and `/llms-full.txt` (~1M+ tokens).
  - The docs are published as the npm package **`@nuxt/docs`** ("Documentation for Nuxt in raw markdown").
  - **Not found**: a project-local, app-aware MCP server, or generated `AGENTS.md` files for apps. The repo's own `AGENTS.md` is a contributor policy that bans AI-authored PRs and comments.

  Source: docs/3.guide/3.ai/1.mcp.md, docs/3.guide/3.ai/2.llms-txt.md, docs/package.json, AGENTS.md
- **Instrumentation / OpenTelemetry hooks**: **Not found in docs.** The closest building blocks are the Nitro `request`/`response`/`error` hooks and the app lifecycle hooks (`page:start`/`page:finish`, `app:rendered`, `render:route`). Source: docs/4.api/6.advanced/1.hooks.md
- **Server error reporting hooks**: **Partial.** The Nitro `error(error, { event })` hook from a server plugin, Nitro's `defineErrorHandler`, and the `app:error`/`vue:error` hooks that also fire during SSR. The error-handling guide contradicts this by saying server-side handlers for Nitro errors are not yet possible. Source: docs/4.api/6.advanced/1.hooks.md, docs/3.guide/6.going-further/5.server-imports.md, docs/1.getting-started/12.error-handling.md
- **Web vitals reporting**: **Not found.** The docs only give guidance (Chrome DevTools, Lighthouse, PSI, WebPageTest). Related on-by-default optimizations: `navigationRepaint` (waits one frame before navigating to improve INP) and `compileHints`. Source: docs/3.guide/2.best-practices/performance.md, exp.md
- **Notable extras**:
  - **Coded diagnostics** (most with their own page under `docs/errors/`): build-time B3014/B3015 (server-component misuse), B4025 (unknown link), B5001 (missing `compatibilityDate`), B5003 (reserved `runtimeConfig.app`), B5004 (external config file), B9003/B9005/B9006/B9007 (Nitro v2 compat and auto-import notices); runtime E1001 (composable outside context), E2001–E2007 (navigation misuse), E3001/E3008/E3009 (fetch misuse), E4012/E4016, E5001, E6001, E7001–E7010, E8007 (`noScripts` vs client JS), E8009 (streaming error recovery).
  - `templateDiagnostics` (on by default).
  - `enforceModuleCompatibility`.
  - Telemetry opt-out (`telemetry`).
  - Nightly release channel.
  - Nuxt Kit for modules (hooks for pages, components, imports, nitro, vite, schema).

  Source: docs/errors/*.md, exp.md, upgrade.md, docs/4.api/6.advanced/1.hooks.md

## Out-of-scope features seen (one line each)
- Auth and sessions: sealed-cookie `useSession` in `nuxt/server`, `deriveSecret`/`appSecret`, a sessions-and-authentication recipe; `nuxt-auth-utils` is planned as an official module.
- KV storage: `useKV()` / `nitro.kv` (formerly `useStorage`); Nitro `useDatabase()`.
- Server tasks: `defineTask`/`runTask` (`nitro/task`).
- State management: `useState`, `callOnce`, Pinia recipe, `clearNuxtState({ reset })`.
- Testing: `@nuxt/test-utils`, Vitest, Playwright.
- i18n: modules only.
- Accessibility: `@nuxt/a11y` alpha, `<NuxtAnnouncer>`/`useAnnouncer`.
- App config: `app.config.ts`, reactive, HMR, per-request copy on the server.
- Plugins system: `defineNuxtPlugin` with `enforce` / `parallel` / `dependsOn` / `env.islands` / object syntax; `provide` helpers.
- Modules and Kit: module authoring, server-compatibility variants (`nitro2`/`nitro3`/`nuxt`), layers publishing.
