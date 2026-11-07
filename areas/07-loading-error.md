# 7. Loading & error states

**Versions:** Void 1.6.2 · Next.js 16.4 (App Router) · React Router 8 (framework mode) · TanStack Start 1.169 (React) · Nuxt 5.0 pre-release (4.x is stable) · SvelteKit 3.1 · SolidStart 2.0 · Astro 7.4

**Markers:** [exp] experimental, unstable or canary · [CC] Next.js with Cache Components on (the create-next-app default)

**Paths:** Void file paths are in the `voidzero-dev/void` repo. Short paths such as `pages/scan.ts` are under `packages/void/src/`; paths that start with a package name, such as `react/src/…`, are under `packages/`.

## At a glance

- **Pending state primitives are in place; route-level pending UI is not.**
  - `useNavigation()` returns `{ state: 'idle'|'loading'|'submitting', location, method }` in all four adapters.
  - React navigations run inside transitions.
  - Deferred props carry their own pending and error state: React uses `Suspense`/`use()`; Vue, Svelte and Solid get `{ loading, value, error }`.
  - Forms expose `pending`. `Link` sets `data-void-pending` while its destination loads.
  - Missing: a route-level pending component (Next.js, TanStack Start), pending delay/min-duration (TanStack Start, Nuxt) and a built-in progress bar (Nuxt).
- **Error UI is the largest gap in the area.** Void has no per-route error boundary and no error page component.
  - A loader, action, `head()` or pre-shell SSR error produces a **whole-document 500**. The page is static `public/500.html` (src, undocumented) or a built-in page. It receives no data and renders no layouts.
  - A client navigation that hits an error **falls back to a full page load** of the failing URL.
  - All 7 others render error UI with app components; 4 do so per route segment by convention.
- **404 handling is static.**
  - Unmatched URLs get a static 404 (`public/404.html`, a prerendered `/404`, or a built-in page) with `X-Void-No-Match: 1`.
  - `return c.notFound()` from a loader reaches that page. `throw new HTTPException(404)` instead yields a **plain-text** 404.
  - Void has no component-rendered 404 and no per-segment 404 UI. All 7 others render 404 UI with app components.
- **Rendered pages are always 200.** The renderer ignores `c.status()`, and returning a `Response` replaces the page. 5/7 others can set an arbitrary status while still rendering, and all 7 render error and 404 UI with the matching status.
- **Helpers are Hono's** (`c.redirect`, `c.notFound`, `HTTPException`). None is a throwable redirect or not-found that renders app UI; 5/7 others have each.
- **No error-reporting hooks.** There is no server `handleError`/`onRequestError` and no client `onError`; errors only reach `console.error`. 4/7 others have a dedicated server hook.
- **Strengths:**
  - production masking of 500 details and of deferred-prop errors, while `HTTPException` messages pass through;
  - status-based routing of action errors (call-site vs thrown);
  - status and redirect decisions always happen before streaming starts, so there is no "late 404 → 200 + noindex" pitfall;
  - a dev 500 overlay with source frames and editor links.

## Gap list for this area

| Gap in Void | Who has it (mechanism, briefly) | Prevalence | Notes for design (constraints, dependencies, adapter impact) |
|---|---|---|---|
| App-rendered error UI that keeps the app running (error component with status/message; errors during client navigation rendered in place, not a hard reload) | Next.js (`error.js`/`global-error.js`), React Router (`ErrorBoundary`), TanStack Start (`errorComponent`), Nuxt (`error.vue`), SvelteKit (`+error.svelte`), SolidStart (`ErrorBoundary`), Astro (`500.astro`) | Table stakes (7) | Needs: (1) a Pages-protocol "error page object" (status, message/digest, data) the server returns for document and JSON requests; (2) the navigation engine to commit it instead of `location.href = url`; (3) an error component convention (e.g. `pages/_error.tsx`, or per directory) rendered inside layouts by all 4 adapters. Install `app.onError` for API-only/SSR apps too. |
| Component-rendered 404 page (layouts, data, i18n) | Next.js (`not-found.js`), React Router (splat/`ErrorBoundary`), TanStack Start (`notFoundComponent`), Nuxt (`error.vue`), SvelteKit (`+error.svelte`), SolidStart (`[...404]` + `HttpStatusCode`), Astro (`404.astro`) | Table stakes (7) | Same machinery as above. The pages fallback (`createPagesFallback`) would SSR the 404 component instead of fetching `/404.html`. Keep `X-Void-No-Match` and the `/api` text behavior. |
| Status code control while rendering a page | React Router (`data(v, { status })`), TanStack Start (`setResponseStatus`), Nuxt (`setResponseStatus`), SolidStart (`<HttpStatusCode>`), Astro (`Astro.response.status`); all 7 for error statuses | Common (5) / Table stakes (7) for error statuses | Honor `c.status()` in `renderedResponse`/`pageJsonResponse`. Check that ISR (stores only 200) and the client engine handle non-200 page objects. No streaming constraint, since loaders finish before rendering. |
| Per-route/segment error boundary convention | Next.js, React Router, TanStack Start, SvelteKit | Common (4) | Depends on the first gap. Void layouts have no server companion, so boundary placement would follow the `pages/` layout tree. Per-adapter boundary components. |
| Throwable `notFound()` / `error(status)` from loaders and deep code that renders app UI | Next.js (`notFound()`), React Router (`throw data(…, 404)`), TanStack Start (`notFound()`), Nuxt (`createError`), SvelteKit (`error()`) | Common (5) | Today `HTTPException(404)` gives a text body and `c.notFound()` requires `c`. A Void-owned throwable recognized by `onError` and the protocol fixes both. |
| Throwable `redirect()` from loaders and deep code | Next.js, React Router, TanStack Start, SvelteKit, SolidStart | Common (5) | Must keep Void's action-key query handling (`redirectLocation`) and `routeUrl()` typing. Client navigation already follows fetch redirects. |
| Server error reporting hook | Next.js (`onRequestError`), React Router (`handleError`), Nuxt (Nitro `error` hook), SvelteKit (`handleError`) | Common (4) | Single hook with phase info, plus deferred and pre-shell render errors. Optionally reshape the client-visible error (SvelteKit-style). |
| Client error reporting hook | React Router (`HydratedRouter onError`), TanStack Start (`defaultOnCatch`), Nuxt (`vue:error`/`app:error`), SvelteKit (client `handleError`) | Common (4) | Shared navigation engine (fetch/commit failures) plus per-adapter render error capture. |
| Per-segment 404 UI | Next.js (`not-found.js`), React Router (nested `ErrorBoundary`), TanStack Start (fuzzy `notFoundComponent`), SvelteKit (nested `+error`), SolidStart (nested catch-alls) | Common (5) | Follows from the error-boundary convention. |
| Retry/reset of an error boundary | Next.js (`retry`/`reset`), TanStack Start (`reset` + `invalidate`), Nuxt (`clearError`), SolidStart (`ErrorBoundary` reset) | Common (4) | `retry` = re-run the loader through `router.refresh()`, which already exists. |
| Route-level pending component | Next.js (`loading.js`), TanStack Start (`pendingComponent`) | Differentiator (2) | React can use transitions and Suspense. Vue, Svelte and Solid need an engine-driven swap. Interacts with the prefetch cache (instant if prefetched). |
| Pending delay / min duration | TanStack Start (`pendingMs` 1000/`pendingMinMs` 500), Nuxt (indicator `throttle` 200) | Differentiator (2) | Engine-level timers exposed on `useNavigation()` (e.g. `showPending`). |
| Error-transform hook (reshape or change status of client-visible errors) | SvelteKit (`handleError` return/status), SolidStart (`serverFunctions.onError`) | Differentiator (2) | Could be the same hook as server reporting. |
| Built-in progress indicator | Nuxt (`<NuxtLoadingIndicator>`, `useLoadingIndicator`) | Differentiator (1) | Small component per adapter on top of `useNavigation()`. |
| Auth-specific interrupts (`forbidden()` / `unauthorized()` + UI) | Next.js (**exp.**) | Differentiator (1) | `requireAuth()` already throws 401; would map to an error page variant. |
| Documentation of custom 404/500 pages for Worker apps; consistent `/api` behavior for custom 500 | (n/a: hygiene) | — | `public/404.html`/`500.html` work in source but are documented only for static builds. A custom 500 is returned as HTML even for `/api/*` and non-GET (src: `serveCustomPage`). |

## Where Void is ahead

- **Uniform deferred-data states across adapters.** `Deferred<T>` is `{ loading, value, error }` in Vue, Svelte and Solid, and `Promise` + Suspense in React. Production masks unexpected messages while `HTTPException` messages pass, and grouped resolvers share one call. Peers rely on raw library primitives.
- **Status-based routing of action errors.** Call-site errors go to `form.errors`/`form.error` and `action()` returns `{ ok: false }`; the rest are thrown. `VoidActionError` carries `status`, `body`, `url` and `limit`, and `Form` renders an alert and blocks resubmission until a 429 retry deadline. `isVoidActionError()` (all 4 adapters) matches one at any status; `isCallSiteActionError()` matches only the statuses `action()` returns. No peer classifies by status out of the box.
- **No late-status pitfalls.** Redirects, 404s and 5xx are decided before any byte streams, because the loader completes first and deferred data can't alter status. Next.js (200 + `noindex`), SolidStart, Nuxt and SvelteKit all document constraints here.
- **`useNavigation()` with `submitting` state and `location`/`method`** is identical in React, Vue, Svelte and Solid. Nuxt, SvelteKit and SolidStart each expose a different, smaller shape.
- **Error responses negotiate HTML vs text** using `Sec-Fetch-Dest`, `Accept`, method, `/api` prefix and file extension (built-in pages). Fetch/XHR callers don't get HTML error documents. Nuxt 5 and SvelteKit do something similar by `Accept`/location.
- **Dev 500 overlay** with parsed stack frames, project-relative display paths and `vscode://` links, plus failing-page CSS injected into the error page (area 14 overlap).
- **`X-Void-No-Match: 1`** marks genuinely unmatched document requests, which helps hosts and monitoring tell "no route" from an app-level 404.

## Route-level loading UI

| Framework | Convention | Default navigation behavior | Pending delay / min duration | Initial load / SSR | Notes |
|---|---|---|---|---|---|
| **Void** | none (grepped `loading.(tsx\|vue)`) | Old page stays until the destination's page data is fetched and committed. React wraps the commit in a transition; the `resolveOn` visit option is React-only. | none | Deferred props stream after the shell: inline `<script>` chunks in HTML, NDJSON on navigation. Prefetch responses resolve deferred inline. | Section-level only: `<Suspense>` around `Deferred` (React), `{loading}` (others). |
| **Next.js** | **`loading.js`**: Suspense around page, `not-found` and nested layouts (not its own layout/template/error) | **Instant fallback.** The fallback is prefetched; navigation is interruptible and shared layouts stay interactive. | none | Streamed | [CC] treats it as an ordinary Suspense boundary. Scope it to one page with a route group. |
| **React Router** | none (`HydrateFallback` covers initial hydration with client loaders only) | Old page stays until all loaders resolve | none | `HydrateFallback` | `<Suspense>` + streamed promises per section |
| **TanStack Start** | **`pendingComponent` / `defaultPendingComponent`** | Pending UI appears once loaders exceed `pendingMs` | **`pendingMs` 1000 ms, `pendingMinMs` 500 ms.** Stale-while-revalidate reloads show no pending UI unless `staleReloadMode: 'blocking'` or `invalidate({ forcePending: true })`. | The first non-SSR route's pendingComponent is the SSR fallback; the SPA shell renders it. | `wrapInSuspense: true` |
| **Nuxt** | none | Blocking: old page stays until Suspense resolves. Optional `<NuxtLoadingIndicator>` bar. | `throttle` 200 ms (indicator) | `spa-loading-template.html` for `ssr: false` | `lazy` data with `status` for non-blocking pages |
| **SvelteKit** | none | Waits for non-streamed loads | none | — | `{#await}` for streamed promises; `<svelte:boundary>` pending (Svelte async, exp.) |
| **SolidStart** | none; `<Suspense fallback>` anywhere | Runs inside Solid transitions | none | Root `<Suspense>` required for lazy routes | — |
| **Astro** | none | MPA, or ClientRouter swap | — | — | `slot="fallback"` for server islands and `client:only` |

**Behavioral differences that matter:** Void behaves like React Router, Nuxt and SvelteKit: the old page stays until the next one is ready. Next.js and TanStack Start can show a route skeleton immediately or after a threshold. The anti-flash pending window is TanStack Start-only (`pendingMs`/`pendingMinMs`), plus Nuxt's indicator `throttle`.

**Void gap:** partial. Missing: a route-level pending component (Differentiator: Next.js, TanStack Start) and pending delay/min-duration (Differentiator: TanStack Start, Nuxt). Adapter impact: React could build this on transitions and Suspense; Vue, Svelte and Solid need a component the navigation engine shows while `state === 'loading'`.

## Navigation pending state hooks

| Framework | Global navigation state | Per-link pending | Mutation pending | Built-in progress UI |
|---|---|---|---|---|
| **Void** | `useNavigation()` → `{ state, location, method }` (React, Vue, Svelte, Solid) | **`data-void-pending`** on every link to the in-flight destination (path, query, hash and method), including during `router.refresh()` (`pages/link.ts`). Not a render prop. | `form.pending`; React `useFormStatus`; `useNavigation().state === 'submitting'` | none |
| **Next.js** | none (wrap `router.push` in `useTransition`) | **`useLinkStatus()` → `{ pending }`**: skipped if already prefetched; only the last-clicked link | `useActionState`, `useFormStatus` | none |
| **React Router** | `useNavigation()` (state, location, formData…), `useFetchers()` | **`NavLink` `isPending` / `.pending` class** | `fetcher.state` | none |
| **TanStack Start** | `useRouterState()`; `router.subscribe` events (`onBeforeNavigate` → … → `onRendered`) | **`<MatchRoute pending>`** | server-fn calls are BYO | none |
| **Nuxt** | `useLoadingIndicator({ duration, throttle, estimatedProgress })` → `isLoading`, `progress`, `error`, `start/set/finish/clear`; hooks `page:loading:start/end` | none | `useAsyncData` `status` | **`<NuxtLoadingIndicator>`** (`color`, `errorColor`, `finishColor`, `height` 3 px, `duration` 2000 ms, `throttle` 200 ms, `estimatedProgress`) |
| **SvelteKit** | `navigating` (`$app/state`: `from`, `to`, `type`); `beforeNavigate`/`afterNavigate` | none | Form actions: no flag (use `SubmitFunction` + `navigating`); remote `form.pending` [exp] | none |
| **SolidStart** | `useIsRouting()` | none | `useSubmission(s)` | none |
| **Astro** | ClientRouter events (`astro:before-preparation` / `after-preparation`, overridable `loader()`) | none | — | none |

**Void gap:** partial. Missing: a built-in progress indicator (Differentiator: Nuxt). Link pending state is `data-void-pending` in all four adapters. The global hook is at parity, so Vue, Svelte and Solid users get the React Router-shaped API their single-library peers lack.

## Section-level loading and error states (deferred/streamed data)

| Framework | Mechanism | Pending | Error | Notes |
|---|---|---|---|---|
| **Void** | `defer(fn)` / `defer('group', fn)` in the loader | React: `<Suspense>` + `use()`. Vue/Svelte/Solid: `{ loading: true }`. | React: throws to the nearest **user-supplied** error boundary (docs suggest one). Others: `error` field. **Production masks non-`HTTPException` messages as `"Internal Server Error"`** (raw in dev). | After an action, deferred props keep their last values until the next navigation. Prefetch errors go into `deferredErrors`. |
| **Next.js** | Suspense + async Server Components | fallback | Nearest `error.js` / `catchError` | — |
| **React Router** | `<Await>` / `use()` on promises from `data()` | Suspense | `<Await errorElement>` + `useAsyncError()`, else the route `ErrorBoundary` | `streamTimeout` 4950 ms |
| **TanStack Start** | Unawaited loader promises + `<Await>` / `use()` | Suspense | `errorComponent` / `CatchBoundary` | — |
| **Nuxt** | `lazy` `useAsyncData`/`useFetch`; islands `#fallback` | `status` / `pending` | `error` ref | — |
| **SvelteKit** | Streamed promises `{#await}`; remote queries `.loading` | — | `{:catch}`; remote `.error` (`App.Error`) | — |
| **SolidStart** | `createAsync` + Suspense; `deferStream` | Suspense | `<ErrorBoundary>` | — |
| **Astro** | Server islands | `slot="fallback"` | none | — |

**Void gap:** none. Void is ahead: it has a uniform pending/error state object across Vue, Svelte and Solid, with production masking built in.

## Error boundaries

| Framework | Per-route / segment convention | Component-level boundary | Root / global | What is caught | Server error during client navigation | Reset / retry |
|---|---|---|---|---|---|---|
| **Void** | **none** (grepped `ErrorBoundary`, `onErrorCaptured`, `svelte:boundary`, `+error`, `error.(tsx\|vue)` in adapters and docs) | The UI library's own: React class or third-party boundary, Vue `onErrorCaptured`, Svelte `<svelte:boundary>`, Solid `<ErrorBoundary>`. Docs: boundary-category action errors (401, 403, 405, 428, 5xx) are "thrown. Handle them with your framework's error boundary" (React rethrows from the form action; Vue/Svelte/Solid `post()` rejects). | **Whole-document 500**: `public/500.html` if present (src only), else the built-in page; dev adds an overlay. Pages apps only. API-only and custom-SSR apps get Hono's default `Internal Server Error` text (src: `app.onError` registered only in `compilePageRoutes`). | Errors thrown by loaders, actions (non-call-site statuses), `head()`, global/per-route middleware, and SSR render before the shell (React streams; Vue/Svelte/Solid render to string). React render errors after the shell are logged and client-rendered. | The JSON response lacks `X-VoidPages`, so the client does `window.location.href = url` and the server renders the 500 document (src: pages/navigation-engine.ts). **App state and layout are lost.** | none (static page; reload) |
| **Next.js** | **`error.js`** (client component) wraps `loading`, `not-found`, `page` and nested layouts, not its own layout | **`catchError(fallback)`** (stable 16.3); doesn't catch `redirect`/`notFound`; clears on navigation | **`global-error.js`**: replaces the root layout, renders its own `<html>/<body>`, no `metadata` | Render, Server Components, `startTransition`; not event handlers or async callbacks | Rendered in place under layouts | **`retry()`** re-fetches and re-renders (stable 16.3); `reset()` clears without re-fetching |
| **React Router** | **`ErrorBoundary`** export; the nearest ancestor renders in place of the route component; parents stay | `<Await errorElement>` | Root `ErrorBoundary` inside `Layout` (minimal built-in if `Layout` throws) | Loaders, actions, middleware, render, `headers`, `links`, `meta` | Rendered in the boundary (sanitized) | none (navigate / revalidate) |
| **TanStack Start** | **`errorComponent({ error, reset })`**: route → parent → router `defaultErrorComponent` | `CatchBoundary`, `CatchNotFound` | Root route `errorComponent` (inside `shellComponent`) | `validateSearch`, `params.parse`, `beforeLoad`, `loader`, render | In place | **`reset()`**; loader errors need `router.invalidate()` |
| **Nuxt** | none per route | **`<NuxtErrorBoundary>`** (client only; `#error { error, clearError }`; `@error`; auto-clears on navigation); `<NuxtClientFallback>` [exp] | **`app/error.vue`** replaces the app on a fatal error | Server errors are fatal. Client errors are non-fatal unless `fatal: true`. | `error.vue` (full-screen) | **`clearError({ redirect })`** |
| **SvelteKit** | **`+error.svelte`**: nearest walking up; `load` errors use the one *above* that layout | `<svelte:boundary>` (v3 auto-creates one per `+error.svelte`) | Root `+error.svelte`; static **`src/error.html`** fallback for root-layout load errors, error-page failures, `handle` and `+server` | `load`, actions, remote fns, **rendering (v3)** | In place (via `__data.json`) | `svelte:boundary` `failed` snippet reset (Svelte core) |
| **SolidStart** | none | Solid `<ErrorBoundary fallback>` | `StartClient`/`StartServer` wrap the app; user wraps `Router root` | `createAsync` errors, render | In place | `ErrorBoundary` reset (Solid core) |
| **Astro** | none | Islands use their framework's own | **`src/pages/500.astro`** (on-demand pages only; `error` prop; host page if it fails) | Page and middleware errors; prerender errors fail the build | MPA | none |

**Behavioral differences that matter:**
- In Void, a single failing loader takes down the whole document, layouts included. Next.js, React Router, TanStack Start and SvelteKit confine the failure to the segment and keep parent layouts interactive.
- Void's client navigation turns a server error into a **hard reload**. Every SPA-style peer renders the error inside the running app, keeping client state.
- UI-library boundaries can't help with *loader* errors in Void. Loaders run on the server before rendering, and the protocol has no "error page object": the client receives no page data, only a non-Void response. A framework boundary therefore needs a protocol change (an error page object with status and message or digest) as well as a component.

**Void gap:** missing. Per-route boundary convention: Common (4: Next.js, React Router, TanStack Start, SvelteKit). App-rendered error UI that keeps the app running: Table stakes (7). Retry/reset: Common (Next.js, TanStack Start, Nuxt, SolidStart). Adapter impact: each adapter needs its own boundary component (React class, Vue `onErrorCaptured`, Svelte `<svelte:boundary>`, Solid `<ErrorBoundary>`). The SSR path must render the error component inside layouts, and the navigation engine must commit an error page object rather than reloading.

## Error page conventions and the data they receive

| Framework | File(s) | Props / data received | Inside layouts? | Production masking |
|---|---|---|---|---|
| **Void** | `public/500.html`, `public/404.html`. In Worker apps they're served through the assets binding (src: runtime/routing-errors.ts `serveCustomPage`); documented only for static builds (docs/guide/ssg.md). Otherwise built-in pages. Platform-only `public/usage-limit.html` / `execution-limit.html` for quota 429s. | **None** (static HTML). Dev only: the 500 overlay shows name, message, stack frames, display paths and `vscode://` links. | No (the page CSS of the failing route is injected when known) | Production never includes exception details |
| **Next.js** | `error.js`, `global-error.js`, `not-found.js` | `error` (Server Component errors: generic message + **`digest`**; client-thrown values as-is), `retry`, `reset`. `not-found.js`: no props, supports `metadata`. | Yes (`error.js`) | Message masked, `digest` kept |
| **React Router** | `ErrorBoundary` export | `error` (`Route.ErrorBoundaryProps`) or `useRouteError()`. `isRouteErrorResponse` → `{ status, statusText, data }`; otherwise an `Error`. | Yes | Unexpected errors sanitized; thrown Responses/`data()` not sanitized |
| **TanStack Start** | `errorComponent`, `notFoundComponent` | `{ error (unknown), reset, info }`; not-found `data` | Yes | Server: generic 500 JSON unless the error carries HTTP metadata |
| **Nuxt** | `app/error.vue` | `error: NuxtError { status, statusText, message, data, fatal, unhandled, cause (dev only) }`; may use `<NuxtLayout name>` | Opt-in | `createError` exposes only `message` + `data`; others are `unhandled` with a generic message |
| **SvelteKit** | `+error.svelte`, `src/error.html` | `error: App.Error` (always `status` + `message`, plus typed custom fields), `page.status`. `error.html` placeholders: `%sveltekit.status%`, `%sveltekit.error.message%`. | Yes | Unknown errors become `{ status: 500, message: 'Internal Error' }` unless `handleError` says otherwise |
| **SolidStart** | none (user `ErrorBoundary`) | Fallback `(err, reset)` | Wherever placed | — |
| **Astro** | `src/pages/500.astro`, `404.astro` | 500: `error` (unknown); docs warn not to render stacks | Own layout | — |

**Behavioral differences that matter:**
- Void's static error pages can't show the status, a message, a request ID, the app's layout, i18n or the theme. Even SvelteKit's last-resort `src/error.html` gets the status and message.
- Void's HTML-vs-text negotiation for errors applies only to the **built-in** page. It serves HTML for GET/HEAD requests outside `/api` with no file extension, when `Sec-Fetch-Dest` is document or empty and `Accept` includes html or `*/*`; otherwise it sends text. A custom `public/500.html` is served for *every* failing request in a Pages app, including `/api/*` and non-GET (src: `serveCustomPage` has no such check). The 404 path does return text for `/api`, so this looks like an unintended inconsistency.

**Void gap:** missing; Table stakes (7). Also a documentation gap: custom 404/500 pages for Worker apps.

## 404 / not-found handling

| Framework | Unmatched URL | Not-found from data code | Per-segment 404 UI | Status fidelity | Extras |
|---|---|---|---|---|---|
| **Void** | Pages fallback chain: static asset → `routing.fallbacks` → trailing-slash 301 → custom/built-in 404 with **`X-Void-No-Match: 1`**. `/api/*` and non-GET get `Not Found` text (src: runtime/routing-pages.ts). `routing.notFound: 'single-page-application'\|'404-page'\|'none'` controls the asset layer. | **`return c.notFound()`** reaches the same static 404 page; documented only in a storage example. **`throw new HTTPException(404, { message })`** gives a **plain-text** 404, not the page. On client navigation either one causes a full reload. | none | Always 404, decided before rendering | A catch-all page (`pages/[...path]`) renders, but with **200** (§ Status codes) |
| **Next.js** | Root `app/not-found.js`; `global-not-found.js` (**exp.**, skips rendering) | **`notFound()`** in Server Components, Server Functions and Route Handlers; `try/catch` needs `unstable_rethrow` (unstable) | **Nearest `not-found.js`** | 404 if thrown before streaming, **else 200 + injected `noindex`** | Every `not-found.js` ships with all routes under its segment |
| **React Router** | Splat route (`$.tsx`) that throws a 404; otherwise the root `ErrorBoundary` shows 404 (from memory, unverified) | **`throw data(null, { status: 404 })`** | Nearest `ErrorBoundary` (`isRouteErrorResponse`) | Thrown status | A catch-all that doesn't throw returns 200 |
| **TanStack Start** | Automatic; **`notFoundMode: 'fuzzy'`** (default: nearest route with `notFoundComponent`, layouts kept) or `'root'` | **`throw notFound({ data, routeId, headers })`** from `beforeLoad`, `loader`, server fns and components (discouraged) | Nearest `notFoundComponent` (leaf routes can't handle path not-found) | 404 implied (mechanism undocumented) | Default fallback is a bare `<p>Not Found</p>` |
| **Nuxt** | `error.vue` with 404; `experimental.early404` (opt-in) | **`createError({ status: 404 })`** anywhere; `validate` returning `false` | none (`error.vue` is global) | 404 | `prerenderErrorPages` [exp] renders `error.vue` into `404.html` |
| **SvelteKit** | Root `+error.svelte` (`kind: 'framework'`) | **`error(404, msg)`** in load, actions, endpoints and remote fns | Nearest `+error.svelte` (via a `[...path]` route) | 404 | — |
| **SolidStart** | Catch-all `[...404].tsx` rendering **`<HttpStatusCode code={404} />`** | No throwable; render `HttpStatusCode` | Nested catch-all routes | Status must be set before the shell flushes; cleanup resets it to 200 on unmount | — |
| **Astro** | `src/pages/404.astro` (emits `404.html`) | `return Astro.rewrite('/404')`, `new Response(null, { status: 404 })`, `Astro.response.status = 404`; `notFound(state)` in `src/fetch.ts` (7.4) | none | 404 | Endpoints with no matching method fall to the 404 page |

**Behavioral differences that matter:**
- In Void, the two documented ways to signal "not found" from a loader behave differently. `c.notFound()` serves the 404 page; `HTTPException(404)` serves a text body. Neither renders app components.
- Void can't do "404 inside the layout", the TanStack Start fuzzy mode or the Next.js/SvelteKit per-segment pattern. Product pages lose navigation chrome on a missing record.
- Because loaders finish before rendering, Void never sends a 200 for a late not-found. Next.js documents exactly that fallback (200 + `noindex`).

**Void gap:** partial. Missing:
- a component-rendered 404 page: Table stakes (7);
- a throwable not-found from loaders or deep code that renders app UI with 404: Common (5: Next.js, React Router, TanStack Start, Nuxt, SvelteKit);
- per-segment 404 UI: Common (5: Next.js, React Router, TanStack Start, SvelteKit, SolidStart via nested catch-alls).

## Helpers and where they can be called

| Framework | Redirect | Not found | Generic / typed HTTP error | Auth-specific | Throw or return | Callable from |
|---|---|---|---|---|---|---|
| **Void** | `c.redirect(url \| routeUrl(...), status?)` (Hono, default 302). The location is sent unchanged; the request query is not appended. A named action still drops its action key on a GET follow-up and keeps the page's other parameters (`runtime/routing.ts`). Cross-origin → full page load. | `c.notFound()` | `throw new HTTPException(status, { message })` (`hono/http-exception`); `throw new ValidationError({ field: msg })` (actions, per-route middleware); `withValidator` 400 | `requireAuth(c)` throws `HTTPException(401)` | Redirect/notFound: **return only**. `HTTPException`: throwable anywhere, including deep code and deferred resolvers. A throwable redirect is possible only through Hono's `HTTPException({ res })` (Hono API; undocumented in Void, unverified). | Loader ✓, action ✓, middleware ✓, route ✓, deferred resolver (HTTPException) ✓. **Components ✗.** |
| **Next.js** | `redirect(path, 'replace'\|'push')`: 307, or 303 for no-JS actions. `permanentRedirect` 308. External URLs allowed. | `notFound()` | none | `forbidden()` / `unauthorized()` + `forbidden.js` / `unauthorized.js` (**exp.**, `authInterrupts`) | **Throw** (must be in the render path) | Server Components, **Client Components during render**, Server Functions, Route Handlers; not event handlers. Proxy uses `NextResponse`. |
| **React Router** | `redirect()`, `replace()`, `redirectDocument()` | `throw data(null, { status: 404 })` | `data(value, { status, headers })`; `isRouteErrorResponse` | — | Throw or return | Loaders, actions, middleware (+ client variants); not components |
| **TanStack Start** | `redirect({ to \| href, statusCode, headers, throw })`; typed `Route.redirect()`; `isRedirect` | `notFound({ data, routeId, headers, throw })`; `isNotFound` | none (throw anything; `setResponseStatus` or error metadata sets the status) | — | Throw or return | `beforeLoad`, `loader`, server fns, middleware, components (notFound discouraged); `onError` may convert errors |
| **Nuxt** | `navigateTo()` (return from middleware); server `sendRedirect(event)` | `createError({ status: 404 })` | `createError({ status, statusText, message, data, fatal })`, `showError`, `clearError`, `isNuxtError`. Nuxt 5: `NuxtError` is no longer an `HTTPError` subclass. | — | `createError` throws; `navigateTo` is returned | Route middleware, plugins, setup, server handlers |
| **SvelteKit** | `redirect(300–308, location, { external? })` (v3: external needs opt-in) | `error(404, …)` | `error(400–599, message, props)`, `fail(status, data)` (actions, returned), `invalid(...)` (remote forms); `isHttpError`, `isRedirect` | — | Throw (`fail` returns) | Load, actions, endpoints, `handle`, remote fns; not components |
| **SolidStart** | `redirect(url, init)` (302 default, optional `X-Revalidate`), `reload()`, `json()` | none | none | — | Return or throw (they're Responses) | Queries, actions, middleware, server fns. Components: `<HttpStatusCode>`, `<HttpHeader>`. |
| **Astro** | `Astro.redirect(path, status?)`, `Astro.rewrite()` | none (`rewrite('/404')`) | `ActionError` (actions) | — | **Return only** | Page frontmatter, endpoints, middleware |

**Behavioral differences that matter:**
- Void's redirect needs `c` and must be *returned* from the loader, action or middleware. A helper several calls deep, such as `assertCanEdit(post)`, can't redirect or 404. It can only `throw HTTPException`, which renders a text body.
- Next.js, React Router, TanStack Start, SvelteKit and SolidStart let that helper `throw redirect(...)`.
- Next.js is alone in allowing redirect and not-found from (client) component render, and alone in having auth-specific interrupts (experimental).

**Void gap:** partial. Missing: a throwable redirect (Common, 5: Next.js, React Router, TanStack Start, SvelteKit, SolidStart) and a throwable not-found that renders the app's 404 UI (Common, 5). `forbidden`/`unauthorized` UI is a Differentiator (1, experimental). Design: make Void's `onError` recognize framework-specific throwables (`redirect()`, `notFound()`, `error(status)`), and teach the Pages protocol to answer a client navigation with a redirect or error page object instead of forcing a reload.

## Status codes and headers from pages

| Framework | Status while still rendering the page | Response headers from page / loader | Streaming constraint |
|---|---|---|---|
| **Void** | **No.** Page HTML and page JSON are always built as 200 (src: pages/protocol.ts `renderedResponse` / `pageJsonResponse` ignore `c.status()`). A loader that returns a `Response` with status ≥300, or with a non-JSON body, replaces the page; a JSON 200 `Response` is parsed as props. Possible workaround: per-route or global middleware replaces `c.res` with a new status after `await next()` (inferred, undocumented). | **Yes:** `c.header()` in a loader or in middleware before `next()` is copied onto the page response (both HTML and JSON). Also `routing.headers` config and `x-revalidate` for ISR. | None. The loader completes before rendering and deferred props never change status or headers. |
| **Next.js** | Only through `notFound` / `redirect` / `forbidden` / `unauthorized`; no arbitrary status | Config `headers`, Proxy. `cookies().set` only in actions and handlers. | Status fixed once the shell streams. [CC] status fidelity requires checks before the shell. |
| **React Router** | **`data(value, { status })`** from loader/action; thrown → `ErrorBoundary` with that status | `headers` export (deepest route wins; `parentHeaders`, `loaderHeaders`, `actionHeaders`) | `streamTimeout` |
| **TanStack Start** | `setResponseStatus` (server fns, middleware) | Route `headers()`, `setResponseHeader(s)` | — |
| **Nuxt** | **`setResponseStatus(event, code)`**, `createError` | `useResponseHeader(name)` (writable ref) | Mutations after the shell flushes are dropped (dev warning) |
| **SvelteKit** | `error(status)` → `+error.svelte` with that status; no arbitrary 2xx for pages | **`setHeaders()`** in load (once per header; no `set-cookie`) | Fixed once streaming starts |
| **SolidStart** | **`<HttpStatusCode code text>`**, `event.response.status` | **`<HttpHeader>`**, `setResponseHeader` | Must be set before the shell flushes (`deferStream`) |
| **Astro** | **`Astro.response.status/statusText`** | `Astro.response.headers` (can't be replaced) | Before streaming (inferred) |

**Void gap:** missing. Error statuses with UI: Table stakes (7). Arbitrary status while rendering: Common (5: React Router, TanStack Start, Nuxt, SolidStart, Astro). Design: honor `c.status()` (and a `setStatus` in the request-context getter) in `renderedResponse`/`pageJsonResponse`. The client navigation engine already accepts any response that carries `X-VoidPages`, so a non-200 page object would need checking there too. ISR stores only 200s, so non-200 pages already stay uncached.

## Expected vs unexpected errors

| Framework | Expected-error mechanism | Unexpected errors | Production masking | What reaches the client |
|---|---|---|---|---|
| **Void** | `HTTPException(status, message)`, `ValidationError`, validator 400. **Action errors are routed by status** (src: pages/action-result.ts): call-site (400, 402, 404, 408, 409, 412, 413, 415, 422, 429, 499) go to `form.errors`/`form.error` and `action()` → `{ ok: false }`; boundary (401, 403, 405, 428, 5xx, others) are thrown. | `console.error` + 500 page (Pages apps) or Hono's text 500 | 500 page never shows details. Deferred: non-HTTPException messages → `"Internal Server Error"`. | Actions: `VoidActionError { status, statusText, body, url, limit }`; message = HTTPException message (4xx) or plain-text 4xx body. `isVoidActionError()` narrows any status; `isCallSiteActionError()` only the statuses returned to the caller. Loaders and routes: an HTTPException message becomes the plain-text body. |
| **Next.js** | Return values (`useActionState`), conditional render or redirect | Thrown to boundaries | Generic message + `digest` | — |
| **React Router** | Thrown `Response`/`data()`: not sanitized, not sent to `handleError` | Thrown `Error` → sanitized, `handleError` | Generic message, no stack | `isRouteErrorResponse` vs `Error` |
| **TanStack Start** | `redirect`/`notFound` control flow; errors with status ≥400 metadata are "expected" (not logged) | Logged; generic 500 JSON | Message hidden | Server-fn errors propagate with their message |
| **Nuxt** | `createError` (`message` + `data` reach the client) | `unhandled`, generic message | `cause` only in dev; API routes don't send `message` (use `statusText`/`data`) | **Nuxt 5:** page errors always HTML; server route/middleware errors always JSON |
| **SvelteKit** | `error()` → `App.Error` body (safe); `fail()` | `kind: 'unknown'` → `{ status: 500, message: 'Internal Error' }` | `handleError` decides the shape and **may change the status** (v3) | Typed `App.Error`; `kind` ∈ app/framework/validation/unknown |
| **SolidStart** | Actions return typed results | `submission.error` | **`serverFunctions.onError`** may replace the value sent (network calls only) | Serialized value |
| **Astro** | `ActionError` codes + input errors | 500 / build failure | — | `result.error` |

**Behavioral differences that matter:** Void's status-based routing of action errors is unique and well thought out. But there's no app-level *transform* hook. SvelteKit's `handleError` reshapes errors and changes status for every error kind; SolidStart's `onError` replaces values. Page loads also have no structured error object, unlike `App.Error`, `NuxtError.data` or React Router's thrown `data`.

**Void gap:** partial. Missing: an error-transform hook (Differentiator: SvelteKit, SolidStart) and a structured error payload for page errors (tied to the error-UI gap).

## Error reporting hooks

| Framework | Server hook | Client hook | Notes |
|---|---|---|---|
| **Void** | **none.** Errors are `console.error`ed in `onError` and in deferred resolution; view them with `void project logs` (Cloudflare live tail; the platform keeps history; `--level error`). Workaround: global middleware reads Hono's `c.error` after `await next()` (Hono semantics; unverified for Void, no usage in repo). | **none.** Navigation failures reload silently. | `void/log` structured JSON logger |
| **Next.js** | **`instrumentation.ts` `onRequestError(error, request { path, method, headers }, context { routerKind, routePath, routeType: render\|route\|action\|proxy, renderSource, revalidateReason, renderType })`** | `instrumentation-client.ts` (init); `instrumentationClientInject` | Correlate with `digest` |
| **React Router** | **`handleError(error, { request, params, context })`** in `entry.server` (skip `request.signal.aborted`; not called for thrown Responses; shell errors only when streaming) | **`<HydratedRouter onError={(error, { location, params, pattern, errorInfo })}>`**, once per error | Plus instrumentation (area 14) |
| **TanStack Start** | No dedicated hook: wrap the `createServerEntry` fetch and use `handleStartError`; middleware try/catch | `defaultOnCatch(error, errorInfo)`, route `onError`/`onCatch`, `router.subscribe` | OpenTelemetry recipe [exp] |
| **Nuxt** | Nitro `error(error, { event })` hook via `useNitroHooks()` in a server plugin; `defineErrorHandler` | `vue:error`, `app:error`, `app:error:cleared`, `vueApp.config.errorHandler`; `app:chunkError` (`emitRouteChunkError`) | Error guide still says no server handler exists (docs conflict) |
| **SvelteKit** | **`handleError({ error, event, status, message, kind })`** in `hooks.server`, receiving *all* errors (v3) | **`handleError`** in `hooks.client` | Sentry example; the hook's return becomes `App.Error` |
| **SolidStart** | `serverFunctions.onError` (server functions only) | none | — |
| **Astro** | Logger API destinations (`write`/`flush` per request/`close`); `@sentry/astro` | none | — |

**Void gap:** missing. Server hook: Common (4: Next.js, React Router, Nuxt, SvelteKit; TanStack Start, SolidStart and Astro are partial). Client hook: Common (4: React Router, TanStack Start, Nuxt, SvelteKit). Design: one `onError(error, { c, phase: 'route'|'loader'|'action'|'render'|'deferred'|'middleware' })` hook, for example in `void.config.ts` or `src/server.ts`. It would be called from `app.onError` (which must then be installed for API-only and SSR apps too), from deferred rejection and from pre-shell render failures. A client counterpart would plug into the shared navigation engine plus per-adapter render error capture.
