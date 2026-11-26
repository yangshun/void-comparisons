# 7. Loading & error states

**Versions:** Void 1.12.0 · Next.js 16.4 (App Router) · React Router 8 (framework mode) · TanStack Start 1.169 (React) · Nuxt 5.0 pre-release (4.x is stable) · SvelteKit 3.4 · SolidStart 2.0 · Astro 7.4

**Markers:** [exp] experimental, unstable or canary · [CC] Next.js with Cache Components on (the create-next-app default)

**Paths:** Void file paths are in the `voidzero-dev/void` repo. Short paths such as `pages/scan.ts` are under `packages/void/src/`; paths that start with a package name, such as `react/src/…`, are under `packages/`.

## At a glance

- **Pending state primitives are in place; route-level pending UI is not.**
  - `useNavigation()` returns `{ state: 'idle'|'loading'|'submitting', location, method }` in all four adapters.
  - React navigations run inside transitions.
  - Deferred props carry their own pending and error state: React uses `Suspense`/`use()`; Vue, Svelte and Solid get `{ loading, value, error }`.
  - Forms expose `pending`. `Link` sets `data-void-pending` while its destination loads.
  - Missing: a route-level pending component (Next.js, TanStack Start), pending delay/min-duration (TanStack Start, Nuxt) and a built-in progress bar (Nuxt).
- **Error and 404 UI render inside the app.** `pages/_error` and `pages/_not-found` (any directory; the nearest one wins) receive `{ status, message }` and keep the surrounding layouts, in all four adapters (`docs/guide/pages-routing/errors.md`).
  - A loader or SSR failure, and an `HTTPException` from a loader or from middleware on a page GET/HEAD, render that component. `404` selects `_not-found`. Client navigations receive a page object and commit it in place.
  - Without a matching component, Void still serves `public/500.html` or the built-in page. A custom `500.html` is HTML for every failing request, including `/api/*`.
  - Client render errors are caught by each adapter's `PageErrorBoundary`, which renders the same `_error` component. Event handlers and detached async work are not.
  - Retry is `useRouter().refresh()`. There is no reset that clears the boundary without a new request.
- **404 handling uses the same components.** `c.notFound()` and `HTTPException(404)` both render `_not-found`. An unmatched URL uses the root component, or `public/404.html` / the built-in page when there is none. A static build prerenders the root `_not-found` to `404.html`.
- **Status codes are real.** `c.status()` is the status of the rendered page, for the document and for client navigation. An `HTTPException` uses its own status on the error component. ISR still stores only 200s.
- **Helpers are still Hono's** (`c.redirect`, `c.notFound`, `HTTPException`). `HTTPException` and `c.notFound()` render app UI. Redirects must still be returned; 5/7 others have a throwable `redirect()`.
- **No error-reporting hooks.** There is no server `handleError`/`onRequestError` and no client `onError`; errors only reach `console.error`. 4/7 others have a dedicated server hook.
- **Strengths:**
  - production masking of 500 details and of deferred-prop errors, while `HTTPException` messages pass through;
  - status-based routing of action errors (call-site vs thrown);
  - status and redirect decisions always happen before streaming starts, so there is no "late 404 → 200 + noindex" pitfall;
  - a dev 500 overlay with source frames and editor links.

## Gap list

| Gap in Void | Who has it (mechanism, briefly) | Prevalence | Notes for design (constraints, dependencies, adapter impact) |
|---|---|---|---|
| Throwable `redirect()` from loaders and deep code | Next.js, React Router, TanStack Start, SvelteKit, SolidStart | Common (5) | `HTTPException` and `c.notFound()` already render app UI. Redirects are still `return c.redirect()`. Must keep action-key query handling (`redirectLocation`) and `routeUrl()` typing. Client navigation already follows fetch redirects. |
| Server error reporting hook | Next.js (`onRequestError`), React Router (`handleError`), Nuxt (Nitro `error` hook), SvelteKit (`handleError`) | Common (4) | Single hook with phase info, plus deferred and pre-shell render errors. Optionally reshape the client-visible error (SvelteKit-style). |
| Client error reporting hook | React Router (`HydratedRouter onError`), TanStack Start (`defaultOnCatch`), Nuxt (`vue:error`/`app:error`), SvelteKit (client `handleError`) | Common (4) | Shared navigation engine (fetch/commit failures) plus per-adapter render error capture. |
| Reset an error boundary without re-fetching | Next.js (`reset`), TanStack Start (`reset`), Nuxt (`clearBoundaryError`), SolidStart (`ErrorBoundary` reset) | Common (4) | Retry already exists: `useRouter().refresh()` re-runs the loader. There is no reset that only clears the boundary. |
| Route-level pending component | Next.js (`loading.js`), TanStack Start (`pendingComponent`) | Differentiator (2) | React can use transitions and Suspense. Vue, Svelte and Solid need an engine-driven swap. Interacts with the prefetch cache (instant if prefetched). |
| Pending delay / min duration | TanStack Start (`pendingMs` 1000/`pendingMinMs` 500), Nuxt (indicator `throttle` 200) | Differentiator (2) | Engine-level timers exposed on `useNavigation()` (e.g. `showPending`). |
| Error-transform hook (reshape or change status of client-visible errors) | SvelteKit (`handleError` return/status), SolidStart (`serverFunctions.onError`) | Differentiator (2) | Could be the same hook as server reporting. |
| Built-in progress indicator | Nuxt (`<NuxtLoadingIndicator>`, `useLoadingIndicator`) | Differentiator (1) | Small component per adapter on top of `useNavigation()`. |
| Auth-specific interrupts (`forbidden()` / `unauthorized()` + UI) | Next.js (**exp.**) | Differentiator (1) | `requireAuth()` already throws 401; would map to an error page variant. |
| A custom `public/500.html` is HTML for every failing request, including `/api/*` and non-GET | (n/a: hygiene) | — | Component errors are documented (`docs/guide/pages-routing/errors.md`). `serveCustomPage` in `runtime/routing/errors.ts` skips the HTML-vs-text check that the built-in page uses. |

## Where Void is ahead

- **Uniform deferred-data states across adapters.** `Deferred<T>` is `{ loading, value, error }` in Vue, Svelte and Solid, and `Promise` + Suspense in React. Production masks unexpected messages while `HTTPException` messages pass, and grouped resolvers share one call. Peers rely on raw library primitives.
- **Status-based routing of action errors.** Call-site errors go to `form.errors`/`form.error` and `action()` returns `{ ok: false }`; the rest are thrown. `VoidActionError` carries `status`, `body`, `url` and `limit`, and `Form` renders an alert and blocks resubmission until a 429 retry deadline. `isVoidActionError()` (all 4 adapters) matches one at any status; `isCallSiteActionError()` matches only the statuses `action()` returns. No peer classifies by status out of the box.
- **No late-status pitfalls.** Redirects, 404s and 5xx are decided before any byte streams, because the loader completes first and deferred data can't alter status. Next.js (200 + `noindex`), SolidStart, Nuxt and SvelteKit all document constraints here.
- **`useNavigation()` with `submitting` state and `location`/`method`** is identical in React, Vue, Svelte and Solid. Nuxt, SvelteKit and SolidStart each expose a different, smaller shape.
- **Error responses negotiate HTML vs text** using `Sec-Fetch-Dest`, `Accept`, method, `/api` prefix and file extension (built-in pages). Fetch/XHR callers don't get HTML error documents. Nuxt 5 and SvelteKit do something similar by `Accept`/location.
- **Dev 500 overlay** with parsed stack frames, project-relative display paths and `vscode://` links, plus failing-page CSS injected into the error page (area 14 overlap).
- **`X-Void-No-Match: 1`** marks genuinely unmatched document requests, which helps hosts and monitoring tell "no route" from an app-level 404.
- **One error-component convention across four UI libraries.** `_error` and `_not-found` take the same `{ status, message }` prop in React, Vue, Svelte and Solid. The nearest file wins, surrounding layouts stay, and a client navigation commits the page object instead of reloading.

## Comparison

### Route-level loading UI

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

### Navigation pending state hooks

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

### Section-level loading and error states (deferred/streamed data)

| Framework | Mechanism | Pending | Error | Notes |
|---|---|---|---|---|
| **Void** | `defer(fn)` / `defer('group', fn)` in the loader | React: `<Suspense>` + `use()`. Vue/Svelte/Solid: `{ loading: true }`. | React: throws to `PageErrorBoundary`, which renders `_error` (a boundary inside the page still catches first). Others: `error` field. **Production masks non-`HTTPException` messages as `"Internal Server Error"`** (raw in dev). | After an action, deferred props keep their last values until the next navigation. Prefetch errors go into `deferredErrors`. |
| **Next.js** | Suspense + async Server Components | fallback | Nearest `error.js` / `catchError` | — |
| **React Router** | `<Await>` / `use()` on promises from `data()` | Suspense | `<Await errorElement>` + `useAsyncError()`, else the route `ErrorBoundary` | `streamTimeout` 4950 ms |
| **TanStack Start** | Unawaited loader promises + `<Await>` / `use()` | Suspense | `errorComponent` / `CatchBoundary` | — |
| **Nuxt** | `lazy` `useAsyncData`/`useFetch`; islands `#fallback` | `status` / `pending` | `error` ref | — |
| **SvelteKit** | Streamed promises `{#await}`; remote queries `.loading` | — | `{:catch}`; remote `.error` (`App.Error`) | — |
| **SolidStart** | `createAsync` + Suspense; `deferStream` | Suspense | `<ErrorBoundary>` | — |
| **Astro** | Server islands | `slot="fallback"` | none | — |

**Void gap:** none. Void is ahead: it has a uniform pending/error state object across Vue, Svelte and Solid, with production masking built in.

### Error boundaries

| Framework | Per-route / segment convention | Component-level boundary | Root / global | What is caught | Server error during client navigation | Reset / retry |
|---|---|---|---|---|---|---|
| **Void** | **`_error` / `_not-found`** in any `pages/` directory. The nearest file wins and surrounding layouts stay. A layout failure uses a component outside that layout. A failing error component tries an outer one, then the built-in page (`docs/guide/pages-routing/errors.md`, `pages/boundary-plans.ts`). Boundaries have no `.server` companion, actions or `layout` export, and they are not routes. | Each adapter wraps the page in `PageErrorBoundary` (React class, Vue `onErrorCaptured`, Svelte `<svelte:boundary>`, Solid `<ErrorBoundary>`), which renders the same `_error` with `{ status, message }`. | Root `_error` / `_not-found`. If none match: `public/500.html` or the built-in page (dev overlay on the built-in 500). API-only and custom-SSR apps still get Hono's text 500 (`app.onError` is installed for Pages apps). | Loader and SSR render failures, `HTTPException` from a loader or from middleware on a page GET/HEAD, and client render errors. Boundary-category action errors (`VoidActionError`) are thrown into `PageErrorBoundary`. Call-site statuses stay on the form. Event handlers and detached async work are not caught. | The server returns an `X-VoidPages` page object whose component is the boundary. The client commits it in place. A response without that header still does `location.href`. | `useRouter().refresh()` re-runs the loader. No reset that skips the request. Error responses are `Cache-Control: no-store`. |
| **Next.js** | **`error.js`** (client component) wraps `loading`, `not-found`, `page` and nested layouts, not its own layout | **`catchError(fallback)`** (stable 16.3); doesn't catch `redirect`/`notFound`; clears on navigation | **`global-error.js`**: replaces the root layout, renders its own `<html>/<body>`, no `metadata` | Render, Server Components, `startTransition`; not event handlers or async callbacks | Rendered in place under layouts | **`retry()`** re-fetches and re-renders (stable 16.3); `reset()` clears without re-fetching |
| **React Router** | **`ErrorBoundary`** export; the nearest ancestor renders in place of the route component; parents stay | `<Await errorElement>` | Root `ErrorBoundary` inside `Layout` (minimal built-in if `Layout` throws) | Loaders, actions, middleware, render, `headers`, `links`, `meta` | Rendered in the boundary (sanitized) | none (navigate / revalidate) |
| **TanStack Start** | **`errorComponent({ error, reset })`**: route → parent → router `defaultErrorComponent` | `CatchBoundary`, `CatchNotFound` | Root route `errorComponent` (inside `shellComponent`) | `validateSearch`, `params.parse`, `beforeLoad`, `loader`, render | In place | **`reset()`**; loader errors need `router.invalidate()` |
| **Nuxt** | none per route | **`<NuxtErrorBoundary>`**: catches its default slot on the server too (`experimental.ssrErrorBoundary`, on by default). A server throw renders `#error` into the HTML with a 200, and the client hydrates into it. `retry-on-client` re-renders the slot in the browser. `#error { error, clearBoundaryError }`, `@error`, auto-clears on navigation. `<NuxtClientFallback>` [exp] is deprecated in its favor. | **`app/error.vue`** replaces the app on a fatal error | Server errors outside a boundary are fatal. A boundary catches even `fatal: true` errors from its slot, but not `showError`, route middleware or `useFetch` errors. Production turns a non-HTTP server error into a generic 500. | `error.vue` (full-screen) | **`clearBoundaryError`** (boundary); **`clearError({ redirect })`** (global) |
| **SvelteKit** | **`+error.svelte`**: nearest walking up; `load` errors use the one *above* that layout | `<svelte:boundary>` (v3 auto-creates one per `+error.svelte`) | Root `+error.svelte`; static **`src/error.html`** fallback for root-layout load errors, error-page failures, `handle` and `+server` | `load`, actions, remote fns, **rendering (v3)** | In place (via `__data.json`) | `svelte:boundary` `failed` snippet reset (Svelte core) |
| **SolidStart** | none | Solid `<ErrorBoundary fallback>` | `StartClient`/`StartServer` wrap the app; user wraps `Router root` | `createAsync` errors, render | In place | `ErrorBoundary` reset (Solid core) |
| **Astro** | none | Islands use their framework's own | **`src/pages/500.astro`** (on-demand pages only; `error` prop; host page if it fails) | Page and middleware errors; prerender errors fail the build | MPA | none |

**Behavioral differences that matter:**
- A failing loader renders the nearest `_error` inside the layouts outside the failed segment. Next.js, React Router, TanStack Start and SvelteKit do the same with their own conventions. Void's boundary files are not paired with a layout file: any directory can hold `_error`, and a layout's own failure uses a component outside that layout.
- Client navigation commits the error page object. The running app and the layouts outside the boundary stay.
- The error prop is only `{ status, message }`. There is no digest, custom data, or reset function on the component.

**Void gap:** partial. The component convention, in-place client navigations and per-directory boundaries are in place. Missing: a reset that does not re-fetch (Common 4: Next.js, TanStack Start, Nuxt, SolidStart) and a payload beyond `status` and `message`.

### Error page conventions and the data they receive

| Framework | File(s) | Props / data received | Inside layouts? | Production masking |
|---|---|---|---|---|
| **Void** | `pages/_error` and `pages/_not-found` (React, Vue, Svelte, Solid). Fallback: `public/500.html` / `public/404.html` via `runtime/routing/errors.ts` `serveCustomPage`, else the built-in page. A static build writes the root `_not-found` to `404.html` unless `public/404.html` exists. Platform-only `public/usage-limit.html` / `execution-limit.html` for quota 429s. | `{ error: { status, message } }` (`ErrorPageProps`). Unexpected production errors use a generic message; dev shows the error message; `HTTPException` messages pass through. The title template wraps the default error title. | Yes, inside the layouts that enclose the boundary. Shared context of the replaced page is passed through. No loader of its own. | Production never includes unexpected exception details |
| **Next.js** | `error.js`, `global-error.js`, `not-found.js` | `error` (Server Component errors: generic message + **`digest`**; client-thrown values as-is), `retry`, `reset`. `not-found.js`: no props, supports `metadata`. | Yes (`error.js`) | Message masked, `digest` kept |
| **React Router** | `ErrorBoundary` export | `error` (`Route.ErrorBoundaryProps`) or `useRouteError()`. `isRouteErrorResponse` → `{ status, statusText, data }`; otherwise an `Error`. | Yes | Unexpected errors sanitized; thrown Responses/`data()` not sanitized |
| **TanStack Start** | `errorComponent`, `notFoundComponent` | `{ error (unknown), reset, info }`; not-found `data` | Yes | Server: generic 500 JSON unless the error carries HTTP metadata |
| **Nuxt** | `app/error.vue` | `error: NuxtError { status, statusText, message, data, fatal, unhandled, cause (dev only) }`; may use `<NuxtLayout name>` | Opt-in | `createError` exposes only `message` + `data`; others are `unhandled` with a generic message |
| **SvelteKit** | `+error.svelte`, `src/error.html` | `error: App.Error` (always `status` + `message`, plus typed custom fields), `page.status`. `error.html` placeholders: `%sveltekit.status%`, `%sveltekit.error.message%`. | Yes | Unknown errors become `{ status: 500, message: 'Internal Error' }` unless `handleError` says otherwise |
| **SolidStart** | none (user `ErrorBoundary`) | Fallback `(err, reset)` | Wherever placed | — |
| **Astro** | `src/pages/500.astro`, `404.astro` | 500: `error` (unknown); docs warn not to render stacks | Own layout | — |

**Behavioral differences that matter:**
- The component receives status and message and renders inside layouts. It does not receive a request id, custom data or i18n props. The last-resort built-in page is still static HTML, apart from the dev overlay.
- HTML-vs-text negotiation applies to the **built-in** page. A custom `public/500.html` is served for every failing request in a Pages app, including `/api/*` and non-GET (`serveCustomPage` has no such check). The 404 path does return text for `/api`.

**Void gap:** partial. The app-rendered page is in place (Table stakes). The custom-`500.html` over-serving is a bug, recorded in [Bugs](bugs.md).

### 404 / not-found handling

| Framework | Unmatched URL | Not-found from data code | Per-segment 404 UI | Status fidelity | Extras |
|---|---|---|---|---|---|
| **Void** | Pages fallback: static asset → `routing.fallbacks` → trailing-slash redirect → root `_not-found` (or `public/404.html` / the built-in page) with **`X-Void-No-Match: 1`**. `/api/*` and non-GET get `Not Found` text (`runtime/routing/pages.ts`). `routing.notFound` controls the asset layer. `routing.trailingSlash` redirects to the chosen form before this. | **`return c.notFound()`** and **`throw new HTTPException(404)`** both render `_not-found` with that message. Middleware `c.notFound()` does it without running the loader. Returning `c.text(..., 404)` sends that response instead. Client navigation commits the page object. | Nearest `_not-found` in the page's directory or an ancestor. A missing record on a nested page keeps the outer layouts. | 404, decided before rendering. A catch-all page can also call `c.status(404)` and render its own props. | Static `output`: the root `_not-found` is prerendered to `404.html` with empty shared data, and the host sets the status. |
| **Next.js** | Root `app/not-found.js`; `global-not-found.js` (**exp.**, skips rendering) | **`notFound()`** in Server Components, Server Functions and Route Handlers; `try/catch` needs `unstable_rethrow` (unstable) | **Nearest `not-found.js`** | 404 if thrown before streaming, **else 200 + injected `noindex`** | Every `not-found.js` ships with all routes under its segment |
| **React Router** | Splat route (`$.tsx`) that throws a 404; otherwise the root `ErrorBoundary` shows 404 (from memory, unverified) | **`throw data(null, { status: 404 })`** | Nearest `ErrorBoundary` (`isRouteErrorResponse`) | Thrown status | A catch-all that doesn't throw returns 200 |
| **TanStack Start** | Automatic; **`notFoundMode: 'fuzzy'`** (default: nearest route with `notFoundComponent`, layouts kept) or `'root'` | **`throw notFound({ data, routeId, headers })`** from `beforeLoad`, `loader`, server fns and components (discouraged) | Nearest `notFoundComponent` (leaf routes can't handle path not-found) | 404 implied (mechanism undocumented) | Default fallback is a bare `<p>Not Found</p>` |
| **Nuxt** | `error.vue` with 404; `experimental.early404` (opt-in) | **`createError({ status: 404 })`** anywhere; `validate` returning `false` | none (`error.vue` is global) | 404 | `prerenderErrorPages` [exp] renders `error.vue` into `404.html` |
| **SvelteKit** | Root `+error.svelte` (`kind: 'framework'`) | **`error(404, msg)`** in load, actions, endpoints and remote fns | Nearest `+error.svelte` (via a `[...path]` route) | 404 | — |
| **SolidStart** | Catch-all `[...404].tsx` rendering **`<HttpStatusCode code={404} />`** | No throwable; render `HttpStatusCode` | Nested catch-all routes | Status must be set before the shell flushes; cleanup resets it to 200 on unmount | — |
| **Astro** | `src/pages/404.astro` (emits `404.html`) | `return Astro.rewrite('/404')`, `new Response(null, { status: 404 })`, `Astro.response.status = 404`; `notFound(state)` in `src/fetch.ts` (7.4) | none | 404 | Endpoints with no matching method fall to the 404 page |

**Behavioral differences that matter:**
- `c.notFound()` and `HTTPException(404)` both render `_not-found` inside the surrounding layouts. A product page can show a missing record without dropping the app chrome.
- `c.notFound()` still needs the Hono context. `HTTPException` can be thrown from deeper code. There is no separate `notFound()` helper.
- Because loaders finish before rendering, Void never sends a 200 for a late not-found. Next.js documents exactly that fallback (200 + `noindex`).

**Void gap:** none for the rendered 404. Missing a throwable redirect (see the next section) and an automatic `noindex` on 404 (Differentiator: Next.js, area 9).

### Helpers and where they can be called

| Framework | Redirect | Not found | Generic / typed HTTP error | Auth-specific | Throw or return | Callable from |
|---|---|---|---|---|---|---|
| **Void** | `c.redirect(url \| routeUrl(...), status?)` (Hono, default 302). The location is sent unchanged; the request query is not appended. Action redirects keep the URL fragment (`pages/redirect.ts`). A named action drops its action key on a GET follow-up and keeps the page's other parameters. Cross-origin → full page load. | `c.notFound()` renders `_not-found`. `HTTPException(404)` does the same. | `throw new HTTPException(status, { message })` renders the nearest `_error` on a page GET/HEAD, with that status and message. An exception that carries its own `Response` is returned as-is. `ValidationError` and `withValidator` 400 stay call-site errors. | `requireAuth(c)` throws `HTTPException(401)`, which renders `_error` on a page GET. | Redirect/notFound: **return only**. `HTTPException`: throwable anywhere, including deep code. A throwable redirect is possible only through Hono's `HTTPException({ res })` (Hono API; undocumented in Void). | Loader ✓, action ✓ (actions keep their own error routing; a boundary-category error reaches `PageErrorBoundary`), middleware ✓, route ✓ (API routes do not render `_error`), deferred resolver (HTTPException) ✓. **Components ✗.** |
| **Next.js** | `redirect(path, 'replace'\|'push')`: 307, or 303 for no-JS actions. `permanentRedirect` 308. External URLs allowed. | `notFound()` | none | `forbidden()` / `unauthorized()` + `forbidden.js` / `unauthorized.js` (**exp.**, `authInterrupts`) | **Throw** (must be in the render path) | Server Components, **Client Components during render**, Server Functions, Route Handlers; not event handlers. Proxy uses `NextResponse`. |
| **React Router** | `redirect()`, `replace()`, `redirectDocument()` | `throw data(null, { status: 404 })` | `data(value, { status, headers })`; `isRouteErrorResponse` | — | Throw or return | Loaders, actions, middleware (+ client variants); not components |
| **TanStack Start** | `redirect({ to \| href, statusCode, headers, throw })`; typed `Route.redirect()`; `isRedirect` | `notFound({ data, routeId, headers, throw })`; `isNotFound` | none (throw anything; `setResponseStatus` or error metadata sets the status) | — | Throw or return | `beforeLoad`, `loader`, server fns, middleware, components (notFound discouraged); `onError` may convert errors |
| **Nuxt** | `navigateTo()` (return from middleware); server `sendRedirect(event)` | `createError({ status: 404 })` | `createError({ status, statusText, message, data, fatal })`, `showError`, `clearError`, `isNuxtError`. Nuxt 5: `NuxtError` is no longer an `HTTPError` subclass. | — | `createError` throws; `navigateTo` is returned | Route middleware, plugins, setup, server handlers |
| **SvelteKit** | `redirect(300–308, location, { external? })` (v3: external needs opt-in) | `error(404, …)` | `error(400–599, message, props)`, `fail(status, data)` (actions, returned), `invalid(...)` (remote forms); `isHttpError`, `isRedirect` | — | Throw (`fail` returns) | Load, actions, endpoints, `handle`, remote fns; not components |
| **SolidStart** | `redirect(url, init)` (302 default, optional `X-Revalidate`), `reload()`, `json()` | none | none | — | Return or throw (they're Responses) | Queries, actions, middleware, server fns. Components: `<HttpStatusCode>`, `<HttpHeader>`. |
| **Astro** | `Astro.redirect(path, status?)`, `Astro.rewrite()` | none (`rewrite('/404')`) | `ActionError` (actions) | — | **Return only** | Page frontmatter, endpoints, middleware |

**Behavioral differences that matter:**
- A helper several calls deep can `throw new HTTPException(404)` or any other status and get the app's error UI. It still cannot redirect without `c` and a returned `c.redirect()`.
- Next.js, React Router, TanStack Start, SvelteKit and SolidStart let that helper `throw redirect(...)`.
- Next.js is alone in allowing redirect and not-found from (client) component render, and alone in having auth-specific interrupts (experimental).

**Void gap:** partial. Missing: a throwable redirect (Common, 5: Next.js, React Router, TanStack Start, SvelteKit, SolidStart). `forbidden`/`unauthorized` UI is a Differentiator (1, experimental). The not-found and error-page-object pieces of the old design note have shipped.

### Status codes and headers from pages

| Framework | Status while still rendering the page | Response headers from page / loader | Streaming constraint |
|---|---|---|---|
| **Void** | **Yes.** `renderedResponse` and `pageJsonResponse` copy `c.status()` (`c.newResponse(null).status`, because Hono's `c.res` ignores it). Document loads and client navigations both use it, including while deferred props stream. Set it before streaming starts. `HTTPException` renders `_error` instead of the page. A loader `Response` with status ≥300, or a non-JSON body, still replaces the page. | **Yes:** `c.header()` in a loader or in middleware before `next()` is copied onto the page response (both HTML and JSON). Also `routing.headers` config and `x-revalidate` for ISR. | None. The loader completes before rendering and deferred props never change status or headers. ISR stores only status 200 (`isStorableRender`). |
| **Next.js** | Only through `notFound` / `redirect` / `forbidden` / `unauthorized`; no arbitrary status | Config `headers`, Proxy. `cookies().set` only in actions and handlers. | Status fixed once the shell streams. [CC] status fidelity requires checks before the shell. |
| **React Router** | **`data(value, { status })`** from loader/action; thrown → `ErrorBoundary` with that status | `headers` export (deepest route wins; `parentHeaders`, `loaderHeaders`, `actionHeaders`) | `streamTimeout` |
| **TanStack Start** | `setResponseStatus` (server fns, middleware) | Route `headers()`, `setResponseHeader(s)` | — |
| **Nuxt** | **`setResponseStatus(event, code)`**, `createError` | `useResponseHeader(name)` (writable ref) | Mutations after the shell flushes are dropped (dev warning) |
| **SvelteKit** | `error(status)` → `+error.svelte` with that status; no arbitrary 2xx for pages | **`setHeaders()`** in load (once per header; no `set-cookie`) | Fixed once streaming starts |
| **SolidStart** | **`<HttpStatusCode code text>`**, `event.response.status` | **`<HttpHeader>`**, `setResponseHeader` | Must be set before the shell flushes (`deferStream`) |
| **Astro** | **`Astro.response.status/statusText`** | `Astro.response.headers` (can't be replaced) | Before streaming (inferred) |

**Void gap:** none. `c.status()` renders the page at that status, and `HTTPException` renders `_error` or `_not-found` at its status. Non-200 pages stay out of the ISR cache.

### Expected vs unexpected errors

| Framework | Expected-error mechanism | Unexpected errors | Production masking | What reaches the client |
|---|---|---|---|---|
| **Void** | `c.status()` renders the page. `HTTPException(status, message)` renders `_error` (or `_not-found` for 404) with that status and message. `ValidationError` and validator issues stay on the form. **Action errors are routed by status** (`pages/action-result.ts`): call-site (400, 402, 404, 408, 409, 412, 413, 415, 422, 429, 499) go to `form.errors`/`form.error` and `action()` → `{ ok: false }`; boundary statuses are thrown into `PageErrorBoundary`, which shows `_error`. | `console.error` + `_error` when a component exists, otherwise the 500 page (Pages apps) or Hono's text 500 | Unexpected 500s show a generic message. Dev shows the message. Deferred: non-HTTPException messages → `"Internal Server Error"`. | The error component gets `{ status, message }` only. Actions: `VoidActionError { status, statusText, body, url, limit }`. |
| **Next.js** | Return values (`useActionState`), conditional render or redirect | Thrown to boundaries | Generic message + `digest` | — |
| **React Router** | Thrown `Response`/`data()`: not sanitized, not sent to `handleError` | Thrown `Error` → sanitized, `handleError` | Generic message, no stack | `isRouteErrorResponse` vs `Error` |
| **TanStack Start** | `redirect`/`notFound` control flow; errors with status ≥400 metadata are "expected" (not logged) | Logged; generic 500 JSON | Message hidden | Server-fn errors propagate with their message |
| **Nuxt** | `createError` (`message` + `data` reach the client) | `unhandled`, generic message | `cause` only in dev; API routes don't send `message` (use `statusText`/`data`) | **Nuxt 5:** page errors always HTML; server route/middleware errors always JSON |
| **SvelteKit** | `error()` → `App.Error` body (safe); `fail()` | `kind: 'unknown'` → `{ status: 500, message: 'Internal Error' }` | `handleError` decides the shape and **may change the status** (v3) | Typed `App.Error`; `kind` ∈ app/framework/validation/unknown |
| **SolidStart** | Actions return typed results | `submission.error` | **`serverFunctions.onError`** may replace the value sent (network calls only) | Serialized value |
| **Astro** | `ActionError` codes + input errors | 500 / build failure | — | `result.error` |

**Behavioral differences that matter:** Void's status-based routing of action errors is unique and well thought out. Page errors now have a structured `{ status, message }`, and nothing richer: no custom fields, no digest, and no hook that reshapes them. SvelteKit's `handleError` reshapes errors and changes status; SolidStart's `onError` replaces values.

**Void gap:** partial. Missing: an error-transform hook (Differentiator: SvelteKit, SolidStart) and custom fields on the error prop.

### Error reporting hooks

| Framework | Server hook | Client hook | Notes |
|---|---|---|---|
| **Void** | **none.** Errors are `console.error`ed in `onError` and in deferred resolution; view them with `void project logs` (Cloudflare live tail; the platform keeps history; `--level error`). Workaround: global middleware reads Hono's `c.error` after `await next()` (Hono semantics; unverified for Void, no usage in repo). | **none.** Render errors reach `PageErrorBoundary` with a generic message. A fetch that is not an `X-VoidPages` response still reloads the document. | `void/log` structured JSON logger |
| **Next.js** | **`instrumentation.ts` `onRequestError(error, request { path, method, headers }, context { routerKind, routePath, routeType: render\|route\|action\|proxy, renderSource, revalidateReason, renderType })`** | `instrumentation-client.ts` (init); `instrumentationClientInject` | Correlate with `digest` |
| **React Router** | **`handleError(error, { request, params, context })`** in `entry.server` (skip `request.signal.aborted`; not called for thrown Responses; shell errors only when streaming) | **`<HydratedRouter onError={(error, { location, params, pattern, errorInfo })}>`**, once per error | Plus instrumentation (area 14) |
| **TanStack Start** | No dedicated hook: wrap the `createServerEntry` fetch and use `handleStartError`; middleware try/catch | `defaultOnCatch(error, errorInfo)`, route `onError`/`onCatch`, `router.subscribe` | OpenTelemetry recipe [exp] |
| **Nuxt** | Nitro `error(error, { event })` hook via `useNitroHooks()` in a server plugin; `defineErrorHandler` | `vue:error`, `app:error`, `app:error:cleared`, `vueApp.config.errorHandler`; `app:chunkError` (`emitRouteChunkError`) | Error guide still says no server handler exists (docs conflict) |
| **SvelteKit** | **`handleError({ error, event, status, message, kind })`** in `hooks.server`, receiving *all* errors (v3) | **`handleError`** in `hooks.client` | Sentry example; the hook's return becomes `App.Error` |
| **SolidStart** | `serverFunctions.onError` (server functions only) | none | — |
| **Astro** | Logger API destinations (`write`/`flush` per request/`close`); `@sentry/astro` | none | — |

**Void gap:** missing. Server hook: Common (4: Next.js, React Router, Nuxt, SvelteKit; TanStack Start, SolidStart and Astro are partial). Client hook: Common (4: React Router, TanStack Start, Nuxt, SvelteKit). The error UI no longer depends on this hook. A server `onError(error, { c, phase })` would still be called from `app.onError` (which must then be installed for API-only and SSR apps too), from deferred rejection and from pre-shell render failures. A client counterpart would plug into the navigation engine and `PageErrorBoundary`.
