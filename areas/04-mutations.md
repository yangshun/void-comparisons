# 4. Mutations

**Versions:** Void 1.6.2 · Next.js 16.4 (App Router) · React Router 8 (framework mode) · TanStack Start 1.169 (React) · Nuxt 5.0 pre-release (4.x is stable) · SvelteKit 3.1 · SolidStart 2.0 · Astro 7.4

**Markers:** [exp] experimental, unstable or canary

**Note:** SvelteKit *form actions* are stable; its *remote functions* (`form`, `command`, `query`) are [exp].

**Paths:** Void file paths are in the `voidzero-dev/void` repo. Short paths such as `pages/scan.ts` are under `packages/void/src/`; paths that start with a package name, such as `react/src/…`, are under `packages/`.

## At a glance

- **Model.** Void uses page actions: `action` or `actions = { name, default }` in the page's `.server.ts`, on `POST`/`PUT`/`PATCH`/`DELETE` of the page URL, with named actions addressed as `?name`. On the client, `useForm` + `Form`, `action()` and `Link method="post"` submit through the **router** as a page visit. After a successful action, the server re-runs the page loader and returns fresh props **in the same response**.
- **Biggest gap: no progressive enhancement.** Void's `Form` cannot submit without JavaScript. React renders a function `action`; Vue, Svelte and Solid render `<form>` with no `action`/`method` and call `preventDefault()`. `withValidator` also parses JSON bodies only. Next.js, React Router, SvelteKit, SolidStart and Astro all work without JS (5/7).
- **Second biggest gap: an action cannot return data to its caller.** A successful action yields only refreshed page props. A plain return value is ignored, and a non-page 2xx `Response` makes the client fall back to a **full page load**. All 7 peers can return arbitrary data.
- **Only one submission can be in flight.** Every `useForm`/`action()` submission is a router visit, and a new visit aborts the previous one client-side; the server keeps running. React Router (fetchers), SolidStart (`useSubmissions`) and SvelteKit remote functions [exp] track many concurrent, keyed submissions.
- **Revalidation is automatic but all-or-nothing.** The current page's loader always re-runs, even on validation failure. There is no targeted or opt-out revalidation (Next.js tags/paths, React Router `shouldRevalidate`, SvelteKit single-flight `refresh()`/`set()`, SolidStart `revalidate` keys), and deferred props keep stale values until the next navigation.
- **Strong form state.** `useForm` errors come typed from the validator schema, flattened from Standard Schema issues, and cleared when a field is edited. It also has `hasChanges`, `wasSuccessful`/`recentlySuccessful`, `reset(fields | {initial})`, `resetOnSuccess`, and status-based routing of errors to the call site or an error boundary. `Form` adds `aria-busy`, an alert block and 429 retry gating. Only SvelteKit's [exp] remote `form` comes close.
- **Optimistic UI** is React-only, through `useOptimistic` composed with `useForm` (integration-tested). Vue, Svelte and Solid have no helper, and `useNavigation()` does not expose the submitted data.
- **Uploads and CSRF are partial.** Uploads switch the client to multipart automatically, but nothing validates them server-side (no schema, no size limit, no streaming parser). Page actions get an always-on same-origin check, with no allow-list and no coverage for `routes/` handlers.

## Gap list for this area

| Gap in Void | Who has it (mechanism, briefly) | Prevalence | Notes for design (constraints, dependencies, adapter impact) |
|---|---|---|---|
| Returning arbitrary data from an action to its caller | Next.js (return → `useActionState`), React Router (`actionData` / `fetcher.data`), TanStack Start (fn return), Nuxt (`$fetch` result), SvelteKit (`form` / `form.result`), SolidStart (`submission.result`), Astro (`{ data }`) | Table stakes (7) | Add a typed `result` field to the page object for mutation responses (ephemeral, like SvelteKit `form`), surfaced as `form.result` / `action()` → `{ ok, pageData, result }`. Keep the "void → refresh" default. Today a 2xx non-page `Response` triggers a full page load. An undocumented workaround is `c.set()` read back by the same-request loader. |
| Progressive enhancement for `Form` | Next.js (server-action forms, queued pre-hydration), React Router (`<Form>`), SvelteKit (form actions; remote `form` [exp]), SolidStart (`<form action={action}>`), Astro (`action={actions.x}`); TanStack Start partial (`.url`) | Common (5) | The server already re-renders HTML for non-`X-VoidPages` POSTs. Needs: `Form` to render `method` + `action` URL with `?name`; urlencoded/multipart parsing into `withValidator`; a method override for PUT/PATCH/DELETE; seeding `useForm` `data` and `errors` from the server page object (Solid already reads `ErrorsContext`); a 4xx status for invalid submits; a PRG option. The React adapter must stop using a client function as the form action, or use one that degrades. |
| Schema validation of urlencoded / multipart bodies, with coercion | Astro (`accept: 'form'`), SvelteKit remote `form` [exp], TanStack Start (validator receives `FormData`) | Common (3) | Prerequisite for the two rows above and for validated uploads. Must decode Void's own client encoding (`a[b]`, `name[]`, `'1'`/`'0'`, ISO dates; pages/navigation-engine.ts `objectToFormData`). |
| Concurrent non-navigating submissions with tracked state | React Router (`useFetcher` + `key`, `useFetchers`), SolidStart (`useSubmissions`, `retry`), SvelteKit (remote `pending` counts, `form.for(id)`) [exp] | Common (3; Next.js actions are non-navigating but sequential) | Today every submission is a router visit and the next visit aborts it. Needs a separate request lane that doesn't commit history, an optional page-props refresh, and per-key state, in all 4 adapters. |
| Targeted, partial or opt-out revalidation after a mutation | Next.js (`revalidateTag`/`revalidatePath`/`refresh`), React Router (`shouldRevalidate`, `defaultShouldRevalidate`), SvelteKit (single-flight `refresh()`/`set()`, `.updates()` + `requested()`), SolidStart (`revalidate` keys via `X-Revalidate`) | Common (4) | With one loader, the natural unit is "skip the loader" or "only these props" (Inertia `only`). Consider skipping the loader re-run on `ValidationError` (React Router skips revalidation on non-2xx). |
| RPC server functions | Next.js, TanStack Start, SolidStart, Astro (stable); SvelteKit `command`/`query` [exp]; React Router RSC `"use server"` [exp] | Common (4 stable) | Void's typed `fetch` to `routes/` covers typing, but there is no client state or revalidation hook. If added, CSRF must cover it (TanStack Start auto-installs middleware for server fns). |
| GET / search forms with client-side navigation | Next.js (`<Form action="/search">`, with prefetch), React Router (`<Form method="get">`), SvelteKit (GET forms routed like links), Astro (ClientRouter) | Common (4) | `FormMethod` excludes `get` and nothing intercepts native submits. Could map to `router.visit(url, { data })`, since `Link` already serializes GET `data` to a query string. |
| Trusted-origins allow-list for page actions; opt-in protection for `routes/` | Next.js (`allowedOrigins`), React Router (`allowedActionOrigins`), SvelteKit (`csrf.trustedOrigins`), TanStack Start (`origin`; middleware attachable to routes) | Common (4) | Keep the current behaviour of allowing requests with no origin headers, or make it configurable (TanStack Start rejects them by default). |
| Configurable request body-size limit | Next.js (`serverActions.bodySizeLimit` 1 MB), SvelteKit (`BODY_SIZE_LIMIT`), Astro (`security.actionBodySizeLimit` 1 MB) | Common (3) | Hono's `bodyLimit` middleware may work (not documented by Void). Note that Cloudflare has platform caps. |
| `replace` and history `state` for React `useForm` submissions | React Router (`replace`, `state`), Next.js (`replace`), SvelteKit (`data-sveltekit-replacestate`) | Common (3) | Scroll is closed: an in-place action keeps scroll unless `preserveScroll: false` (`pages/navigation-engine.ts` `makeCommit`). React `useForm` takes `preserveScroll` as a hook option; `action()` takes it per call. Vue, Svelte and Solid still take `replace` and `viewTransition` per submit. React does not. |
| Submitted data in global navigation or submission state (optimistic and pending UI elsewhere) | React Router (`navigation.formData`, `fetcher.formData`), SolidStart (`submission.input`); Next.js (`useFormStatus().data`, React) | Common (3) | `useNavigation()` exposes `{ state, location, method }` only. |
| Framework optimistic helper (non-React) | SvelteKit `withOverride` [exp] | Differentiator (1, [exp]) | React already composes `useOptimistic` with `useForm`. Vue, Svelte and Solid would need a helper keyed to `useForm`. |
| Deferred props refreshed after a mutation | React Router (loaders re-run), SvelteKit (loads re-run), TanStack Start (`invalidate`) | Common (3) | Void strips deferred from mutation responses and keeps stale values (docs/guide/pages-routing/loaders.md). |
| Streaming multipart parsing | React Router (`@remix-run/form-data-parser` upload handler) | Differentiator (1) | `c.req.parseBody()` buffers the body. Large uploads should stream to R2. |
| File uploads from every submission helper (islands included) | All 7 accept `FormData` or files from any client-side submission path | Table stakes (7) | Void-internal parity: `useIslandForm` always sends JSON (pages/island-action.ts), while `useForm` and `action()` switch to multipart. |

## Where Void is ahead

- **Form state.** `useForm` provides: typed `data`; `errors` typed from the action's validator, flattened automatically from Standard Schema issues, and cleared when the field is edited; `error` as a structured `VoidActionError`; `hasChanges`; `wasSuccessful`/`recentlySuccessful` (2 s); `reset(...fields)` and `reset({ initial: true })`; `resetOnSuccess`; `setError` / `clearErrors` / `clearError`. Only SvelteKit's [exp] remote `form` (`issues`, `touched`, `dirty`, `submitted`) is comparable, and no stable peer is.
- **Typed action URLs.** `useForm('/users/:id?update', …)` autocompletes the URL, fills `params` at submit time, and types the body and error keys from that named action's validator.
- **Named actions on real HTTP methods.** `PUT`, `PATCH` and `DELETE` work on the page URL, with typed `?name` dispatch and per-action validators. SvelteKit form actions are POST-only; React Router allows one action per route.
- **An automatic, single-round-trip refresh of the current page** after every action, with no developer call. Next.js re-renders only when invalidation functions are called; React Router needs a second request.
- **Status-category error routing.** Expected 4xx stay with the form, and auth or 5xx errors go to boundaries. This is built in; peers leave it to convention.
- **An accessible, quota-aware `Form`.** It renders a `role="alert"` error block, a `renderError` override, and `aria-busy`, and it gates resubmission on `UsageLimit` 429 `retryAt` without auto-retrying.
- **The page-action origin check is on by default**, with `Sec-Fetch-Site` and `Referer` fallbacks. Nuxt and SolidStart have no built-in check.
- **Well-specified redirect semantics.** `c.redirect()` sends the location unchanged. A named action still drops its action key when the follow-up is a GET and keeps the page's other parameters. Config `routing.redirects` still merge the request query.
- **`Link method="post" data={…}`** for one-click mutations, plus the `action()` helper with `{ ok, pageData } | { ok: false, error }`.
- **One mutation API across React, Vue, Svelte and Solid.** React additionally integrates with `useActionState`, `useFormStatus` and `useOptimistic`.

## Action and server-function model

| Framework | Primitive | Addressed by | HTTP methods | Several per page | Callable from code (RPC) |
|---|---|---|---|---|---|
| **Void** | Page `action` or `actions = { name: handler, default? }` (`defineHandler` / `.withValidator()`, per-route middleware allowed) | Page URL; a named action is selected by the **first query key** (`/users/42?update`); an unknown name gives 404 `Unknown action: x` | POST, PUT, PATCH, DELETE | ✓ named actions, each with its own validator and types | `action(url, { data, params, method, preserveScroll })`, which is a router visit, not RPC; typed `fetch` from `void/client` to `routes/` handlers |
| **Next.js** | Server Functions (`'use server'`) | Encrypted, per-build action ID, POSTed to the current page | POST only | ✓ (`formAction` per button; actions as props) | ✓ event handlers or `startTransition`; **the client dispatches them one at a time** |
| **React Router** | Route `action` / `clientAction` (the client one takes priority; `serverAction()`) | Route URL (`?index` added for index routes) | non-GET | one per route (branch on an `intent` field, or target other routes) | `useSubmit()`, `fetcher.submit()`; RSC `"use server"` [exp] |
| **TanStack Start** | `createServerFn({ method })` + `.validator()` + `.middleware()` + `.handler()` | SHA-256 function ID; `.url` | `GET` (default) or `POST` | any number | ✓ direct call; `useServerFn` (redirects and notFound work) |
| **Nuxt** | `server/api/*.post.ts` endpoints | URL + method suffix | any | n/a | typed `$fetch` (no RPC stubs) |
| **SvelteKit** | Form actions (`default` or named `?/name`); remote `form` / `command` [exp] | page `?/name`; generated remote endpoint | POST | ✓ named actions; many remote forms; `form.for(id)` | `command(schema?, fn)` [exp], which can't redirect or run during render |
| **SolidStart** | `action(fn, name \| { name, onComplete })` wrapping `"use server"` functions | `action.url` (`actionBase` `/_server`); `.with(...args)` | POST | ✓ | `useAction(action)`; any server function is RPC |
| **Astro** | Actions: `defineAction({ input, accept, handler })` in `src/actions` | `/_actions/<name>` (groups allowed) | POST | ✓ | `actions.x(input)` → `{ data, error }`; `.orThrow()`; needs an adapter |

**Behavioral differences that matter:**
- Void is the only framework whose actions answer `PUT`, `PATCH` and `DELETE` on the page URL. SvelteKit form actions are POST-only; Next.js actions are POST-only.
- Void has no RPC. Its typed `fetch` to `routes/` is the Nuxt-style alternative, which is typed but has no submission state and no revalidation.
- A Void action is always a page visit. `action('/other/page')` therefore commits *that* page and changes the URL, which is closer to React Router's `<Form>` than to a fetcher.

**Void gap: partial.** Page actions are complete. Missing: RPC-style server functions, which 4 peers have stable (Next.js, TanStack Start, SolidStart, Astro), plus SvelteKit [exp] and React Router RSC [exp].

## Progressive enhancement

| Framework | Works without JS? | Methods without JS | What the server returns to a no-JS POST | Before hydration |
|---|---|---|---|---|
| **Void** | **No** with Void's `Form` / `useForm`. React renders `<form action={form[method]}>`, a React 19 function action with no URL (react/src/runtime/form.tsx). Vue, Svelte and Solid render `<form>` without `action`/`method` and `preventDefault()` on submit (vue/src/runtime/form.ts, svelte/src/runtime/Form.svelte, solid/src/runtime/form.tsx). `Link method="post"` renders an inert `<button>` | POST only, and only from a **hand-written** `<form method="post">` whose action parses `c.req.parseBody()` (`withValidator` rejects non-JSON with 400) | Full HTML re-render with fresh loader props (200). `ValidationError` re-renders the HTML with `errors` in the page object, still 200 (Solid's `useForm` reads it; React only via the undocumented `ErrorsContext`). A redirect passes through (pages/protocol.ts `handlePageMutation`) | React: depends on React 19's function-action behaviour (not documented by Void). Vue/Svelte/Solid: the browser GETs the current URL |
| **Next.js** | ✓ `<form action={serverAction}>` in a Server Component | POST | Re-rendered page (`useActionState` state); `redirect()` → **303** | Client-component forms are **queued until hydration** and get hydration priority |
| **React Router** | ✓ `<Form>` renders a native `<form>` | GET, POST (PUT/PATCH/DELETE lose progressive enhancement) | Document POST: the action, then loaders, then HTML with `actionData` (action and loaders share one request context); `redirect` 302 | native submit |
| **TanStack Start** | Partial: `serverFn.url` as a form `action` (one sentence in the docs); the documented progressive-enhancement patterns are GET forms or POST to a server route | POST | Whatever the server function or route returns (no page re-render) | Event-handler forms stay disabled until hydration (migration guide) |
| **Nuxt** | ✗ (not documented) | — | DIY server route + `sendRedirect`; Nuxt 5 makes server-route errors JSON | — |
| **SvelteKit** | ✓ form actions `<form method="POST" action="?/x">`; remote `form` spread (`method` + `action`) [exp] | POST (GET forms are navigations) | Page re-render with the `form` prop; `fail(status)` sets the status (v3); `redirect(303)`. Remote form re-populates values except `_`-prefixed names | native submit |
| **SolidStart** | ✓ `<form action={myAction} method="post">` (SSR needs the action `name`) | POST only | Not described in the docs | native submit |
| **Astro** | ✓ `<form method="POST" action={actions.x}>` on on-demand pages | POST (GET throws `ActionsUsedWithForGetError`) | Page re-renders; `Astro.getActionResult(actions.x)`; the result exists only in that POST response; PRG via `getActionContext()` middleware | native submit |

**Behavioral differences that matter:**
- Void's **server side is already progressive-enhancement capable.** A mutation without the `X-VoidPages` header re-renders full HTML. The gap is on the client: the form markup has no URL. On the server, `withValidator` only reads JSON, and validation errors are not shown as form state after a full-page response.
- Browsers send only GET and POST, so PUT, PATCH and DELETE actions (a Void strength) need a method-override convention (for example a hidden `_method` field) to work without JS. React Router simply documents that those methods lose progressive enhancement.

**Void gap: missing.** Option-level work needed:
- `Form` renders `method="post"` and `action="<url>?<name>"`.
- Body parsing for `application/x-www-form-urlencoded` and `multipart/form-data` that feeds `withValidator`.
- Method override.
- Seeding `useForm` `data` and `errors` from the server-rendered page object (the server already ships `errors`).
- A non-200 status for invalid submissions.
- A POST/redirect/GET (PRG) story.
- React: a URL action (or a server-function action) instead of a client function.

## Input parsing and validation

| Framework | Encodings | Built-in schema validation | Form data → typed object | Field-error shape |
|---|---|---|---|---|
| **Void** | Client: **JSON**, or `multipart/form-data` when `data` contains a `File`, `Blob` or `FileList`. Multipart keys use brackets: `a[b]`, `files[]`, `items[0]`; booleans become `'1'`/`'0'`; Dates become ISO strings (pages/navigation-engine.ts `objectToFormData`). Server: `withValidator({ body, query, params })` with body = `c.req.json()` **only** (runtime/validator.ts); otherwise `c.req.parseBody()` (Hono) by hand | ✓ any Standard Schema (Zod, Valibot, ArkType; Drizzle-derived) | ✗: nothing decodes the client's own bracket and boolean encoding, and adding a file switches the payload to multipart, which a validated action rejects (400 `Invalid JSON body`) | `{ 'path.to.field': message }` (flattened issues); `ValidationError({ field: msg })` |
| **Next.js** | `FormData` (forms) or Flight-encoded args (RPC); `.bind()` for extra args | BYO (Zod/Valibot examples) | `Object.fromEntries(formData)` (includes `$ACTION_*` keys) | whatever you return |
| **React Router** | urlencoded (default), multipart, `text/plain`; `application/json` via `useSubmit`/`fetcher.submit` `encType` | BYO | ✗ | `data({ errors }, { status: 400 })` |
| **TanStack Start** | serializer types, or `FormData` (POST only) | `.validator(fn \| schema)` | ✗ (validator gets raw `FormData`) | thrown error |
| **Nuxt** | `$fetch` JSON or `FormData`; server `readBody`, `event.req.formData()`, `readMultipartFormData` | `readValidatedBody` / `getValidatedQuery` / `defineValidatedHandler` (Standard Schema) → 400 with `data.issues` | ✗ | `data.issues` |
| **SvelteKit** | Form actions: `request.formData()`. Remote `form`: form data → object by field name (`n:`/`b:` coercion prefixes, nested `a.b` / `a[0]`) [exp]. Remote `command`/`query`: devalue args | Remote functions: Standard Schema, or `'unchecked'` [exp]; form actions BYO | ✓ remote `form` [exp] | `fields.x.issues()`, `allIssues()`; `invalid(issue.x('msg'))` |
| **SolidStart** | `FormData` for multipart, else `URLSearchParams` (the reference page; other pages say `FormData`); server-fn args via Seroval (`FormData`, `Blob` and `File` passed raw) | BYO (Valibot example) | ✗ | whatever you return |
| **Astro** | `accept: 'json'` (default) or `'form'` | ✓ Zod `input` (failure returns `BAD_REQUEST` before the handler runs) | ✓ with `accept: 'form'`: `number` → number, checkbox → boolean, `file` → `File`, repeated names → array, empty → `null` | `isInputError(e).fields[name]` |

**Behavioral differences that matter:** Void's client chooses the encoding from the *data*, not from the form. The same validated action therefore works until a user picks a file, then fails with 400. Astro and SvelteKit [exp] make the form encoding a first-class validated input.

**Void gap: partial.** Schema validation is a strength for JSON. Missing: validation of urlencoded or multipart bodies, decoding that matches the client's bracket encoding, and coercion rules (3 peers: Astro, SvelteKit [exp], TanStack Start raw `FormData`). This is a prerequisite for progressive enhancement and for validated uploads.

## Form component(s): props and options

Columns run left to right: Void `Form`/`useForm` | Next.js `<Form>` | React Router `<Form>` | SvelteKit native `<form>` + `use:enhance` / remote `form` | SolidStart native `<form action>` | Astro native `<form>` + ClientRouter. TanStack Start and Nuxt have **no form component** and are omitted.

| Capability | Void | Next.js | React Router | SvelteKit | SolidStart | Astro |
|---|---|---|---|---|---|---|
| Component | `Form` in all 4 adapters; props `form` (required), `method`, `renderError` (a snippet in Svelte), plus native attributes (React omits `action`/`onSubmit`/`method`) | `<Form>` (`next/form`) | `<Form>` | none: native form + `use:enhance`, or `{...remoteForm}` [exp] | none: native form | none: native form |
| `method` | `post` (default), `put`, `patch`, `delete`. **No `get`** | string `action` = GET search form; function = Server Action. `method` unsupported | `get` (default), `post`, `put`, `patch`, `delete` | POST (actions); GET forms go through the router | `post` (required) | GET/POST |
| Target | from `useForm(url)`, including `?name` and `:params` filled at submit | `action` (`""` = same route) | `action`, defaulting to the **closest route** in context; `relative` | `action="?/name"`, `formaction` | `action.url`; `.with()` | `actions.x` → `?_astroAction=` |
| `encType` | automatic: JSON, or multipart when files are present | unsupported | urlencoded / multipart / `text/plain` | native; `use:enhance` requires multipart when there is a file input | native | native |
| Non-navigating mode | ✗ (always a router visit) | function actions don't navigate | `navigate={false}` + `fetcherKey` | `update({ navigate: false })`; remote forms don't navigate | default (actions don't navigate) | — |
| Replace history | automatic (same URL replaces; a redirect pushes). `replace` is a per-submit option in Vue/Svelte/Solid, **not React** | `replace` (string action) | `replace` | `data-sveltekit-replacestate` (GET forms) | — | — |
| Scroll | **Keeps scroll** when the action stays on the same URL. A redirect, or `preserveScroll: false`, scrolls to the top (or the hash). React sets `preserveScroll` on `useForm()`; Vue, Svelte and Solid pass it per submit; `action()` takes it per call (`pages/navigation-engine.ts` `makeCommit`) | `scroll` (default true) | `preventScrollReset` | `data-sveltekit-reset="false"` | — | — |
| Reset fields on success | `resetOnSuccess` (data + defaults back to mount values); `reset()` | React 19 resets uncontrolled fields after an action (React behavior, not a Next.js option) | — | `update({ reset })` (default true); remote `enhance`: no auto reset | — | inputs cleared on submit (use `transition:persist`) |
| Revalidation control | ✗ (the loader always re-runs) | via the action's own calls | `defaultShouldRevalidate` | `update({ refreshAll })`; `.updates()` | `revalidate` keys in the response helper | — |
| Full-document submit | ✗ | `formMethod` etc. fall back to native | `reloadDocument` | `data-sveltekit-reload` | native | `data-astro-reload` |
| History state | ✗ | — | `state` | `goto` state | — | — |
| Prefetch target | n/a | `prefetch` (default true, string action) | `discover` (route discovery) | GET forms honour `preload-data` | — | — |
| Error rendering | Built in: `role="alert" data-void-form-error` block, `renderError`, `aria-busy`, blocks resubmission until a known 429 `retryAt` | — | — | `+error` / `form` prop | — | — |
| Per-submit hooks | React: `onSuccess`, `onError` (async; `pending` stays true until they finish). Others: `await form.post(opts)` | `onSubmit` + `preventDefault` cancels | — | `SubmitFunction` `({ formData, formElement, action, submitter, controller, cancel })` → `({ result, update })` | `onComplete` on the action | — |
| View transitions | `viewTransition` per-submit option (Vue/Svelte/Solid) | — | `viewTransition` (**deprecated**) | — | — | ClientRouter |

**Behavioral differences that matter:**
- React `useForm` submits `form.data` (client state) and **ignores the `FormData`** React passes to the action (react/src/runtime/use-form.ts). Uncontrolled inputs that have a `name` but are not bound to `form.data` are silently dropped.
- Vue, Svelte and Solid submit methods take visit options (`preserveScroll`, `preserveState`, `replace`, `viewTransition`, a `data` override). React's submit methods are native form-action callbacks. React `useForm` accepts `preserveScroll` on the hook, not per submit, and still has no `replace` or `viewTransition`. That is an adapter-parity gap.

**Void gap: partial.** Missing: GET/search forms with client-side navigation (Next.js, React Router, SvelteKit, Astro); non-navigating mode; a `replace`/`state` option for React; full-document opt-out; revalidation control.

## Non-navigating and concurrent submissions

| Framework | Non-navigating API | Concurrency | Keyed or shared state | Cancellation | Revalidation |
|---|---|---|---|---|---|
| **Void** | None for page actions: `useForm` and `action()` both run as router visits that commit a page object (pages/client.ts `submitAction` → `router.visit`). `useIslandForm` uses raw `fetch` (**JSON only**, and success does `window.location.reload()`) | **One in flight**: `prepareVisit` aborts the pending visit, so a second submission or a link click drops the first one's client handling while the server keeps running. React `useForm` treats the abort as a no-op | per `useForm` instance only | implicit (the next visit) | current page (same response) |
| **Next.js** | Server Actions from event handlers or `startTransition` | **dispatched sequentially** | — | — | only if the action invalidates |
| **React Router** | `useFetcher()`, `<fetcher.Form>`, `fetcher.submit/load`, `<Form navigate={false} fetcherKey>` | concurrent; each triggers revalidation, older in-flight revalidations are cancelled | `key` shares state; `useFetchers()` lists all in flight | resubmitting cancels that fetcher's pending request | all active loaders |
| **TanStack Start** | Server functions | unlimited | — (TanStack Query `useMutation` recommended) | `AbortSignal` mentioned | manual |
| **Nuxt** | `$fetch` | unlimited | — | — | manual |
| **SvelteKit** | Remote `command`, remote `form` (non-navigating), `use:enhance` + `navigate: false` | concurrent (`pending` is a **count**) | `form.for(id)` instances | `controller` in `SubmitFunction` | remote form: everything; command: nothing |
| **SolidStart** | `useAction()`, form submissions | concurrent | `useSubmissions(action, filter?)` (all records, each with `retry()`/`clear()`); `useSubmission` (latest) | `clear()` | all active queries, or the given keys |
| **Astro** | `actions.x()` RPC | unlimited | — | — | none |

**Void gap: missing.** Void has no fetcher-style API: no concurrent, keyed, non-committing submissions that also revalidate, and no global list of in-flight submissions. Because a later navigation silently aborts a pending submission's client-side result, a "like" button followed by a link click loses its error state.

## Pending and progress state

| Framework | Per-form pending | Global pending | Submitted data visible while pending | Upload progress |
|---|---|---|---|---|
| **Void** | `form.pending` (all adapters); React also `useFormStatus()` (the form is a native React action) | `useNavigation()` → `{ state: 'idle' \| 'loading' \| 'submitting', location, method }` | `form.data` (local only); `useNavigation()` has **no form data** | ✗ |
| **Next.js** | `useActionState` `pending`, `useFormStatus()` (`pending`, `data`, `method`, `action`) | `useLinkStatus` (navigation) | `useFormStatus().data` | ✗ |
| **React Router** | `fetcher.state` / `formData` | `useNavigation()` → `state`, `formMethod`, `formAction`, `formEncType`, `formData`, `json`, `text` | ✓ in both | ✗ |
| **TanStack Start** | ✗ (use Query `isPending`) | — | — | ✗ |
| **Nuxt** | via `useAsyncData(..., { immediate: false })` `status` | `<NuxtLoadingIndicator>` (navigation) | — | ✗ |
| **SvelteKit** | Remote `form.pending` / `command.pending` (counts) [exp]; form actions: none (SubmitFunction callbacks) | `navigating` (`$app/state`) | remote `fields.value()` [exp] | ✗ |
| **SolidStart** | `useSubmission().pending`, `useSubmissions().pending` | — | `submission.input` | ✗ |
| **Astro** | only React `withState` + `useActionState` | — | — | ✗ |

**Void gap: partial.** The per-form state is strong. Missing: submitted data in the global navigation state (React Router, Next.js `useFormStatus`, SolidStart `input`), which other components need for optimistic or pending UI. No framework documents upload progress.

## Validation errors and returned data

| Framework | Expected-error channel | Status of an invalid submission | Arbitrary data returned on success | Lifetime |
|---|---|---|---|---|
| **Void** | `ValidationError({ field: msg })` or `withValidator` 400 issues → `form.errors` (typed keys; editing a field clears its error). Other "call-site" 4xx → `form.error` (`VoidActionError`: `status`, `statusText`, `body`, `url`, `limit`, `message`) / `action()` → `{ ok: false, error }` | page JSON **200** with `errors` (the client reports it as 422); island pages 422 `{ errors }`; no-JS HTML 200 | **✗.** A void return refreshes props; plain non-`Response` returns are **ignored**; a non-page 2xx `Response` (including JSON from `withValidator`) makes the client do a **full page load** (pages/navigation-engine.ts). `action()` success returns `{ ok: true, pageData }` | `errors` until the next submit or edit |
| **Next.js** | Returned value as `useActionState` state; thrown → `error.js` | 200 | ✓ return value | component state |
| **React Router** | `return data({ errors }, { status: 400 })` → `actionData` / `fetcher.data`; thrown → `ErrorBoundary` | any status (non-2xx **skips revalidation**) | ✓ | `useActionData` = the last POST navigation |
| **TanStack Start** | the call rejects with whatever was thrown (`Response` included) | middleware status is preserved | ✓ | promise |
| **Nuxt** | `createError({ status, data })` → `FetchError.data`; validated handlers → 400 `data.issues` | as set | ✓ | — |
| **SvelteKit** | Actions: `return fail(status, data)` → `form` / `page.form`, `page.status`. Remote `form`: `invalid(...)` → `issues()` [exp] | `fail` status (v3); `undefined` → 204 | ✓ `form` prop / `form.result` | "until the next update" (ephemeral) |
| **SolidStart** | Return `{ ok: false, errors }` (typed `result`); throw → `error` | 200 | ✓ `submission.result` | the latest submission; returning `undefined` removes it (stale-error pitfall) |
| **Astro** | `ActionError({ code })` → status; `isInputError(e).fields` | from `code` | ✓ `{ data }` / `getActionResult()` | the POST response only |

**Behavioral differences that matter:**
- Void is the only framework where a successful action cannot hand a value (a created ID, a token, a message) back to the caller.
- There is an undocumented workaround, verified in pages/protocol.ts: the loader re-runs **in the same request with the same Hono `c`**, so an action can `c.set(...)` (or set `shared`) and the loader can return that value as a prop.
- On failure, a 4xx JSON body does reach `form.error.body`.

**Void gap: missing** for returned data (7/7 peers have it). Void's error-side handling is better than most peers.

## Optimistic UI

| Framework | Mechanism | Rollback | Across components |
|---|---|---|---|
| **Void** | **React:** React 19 `useOptimistic` composes with `useForm` (react/test/integration/react-pages-client.test.ts). **Vue/Svelte/Solid:** manual (`form.pending` + `form.data`) | manual / implicit when props refresh | ✗ (no global list of submissions) |
| **Next.js** | React `useOptimistic` (the docs show a reducer shared with the server) | React | via props or context |
| **React Router** | Read `fetcher.formData` / `navigation.formData`; `useFetchers()`; React `useOptimistic` via `useTransitions` | reverts when the fetcher goes idle with revalidated data | ✓ `useFetchers()` |
| **TanStack Start** | none (TanStack Query `setQueryData`) | Query | Query |
| **Nuxt** | Recipe: write to the `useNuxtData(key)` ref in `onRequest`, roll back in `onResponseError` | manual | keyed cache |
| **SvelteKit** | `submit().updates(query.withOverride(fn))` [exp]; form actions manual | automatic: replaced by the server value in the same response | query-level |
| **SolidStart** | Derive from `submission.input` while `pending`; `useSubmissions` for lists | automatic when `pending` ends | ✓ `useSubmissions` |
| **Astro** | not documented | — | — |

**Void gap: partial.** React relies on the library. Missing: framework-level optimistic primitives for Vue, Svelte and Solid, and exposure of in-flight submission input (React Router, SolidStart stable; SvelteKit [exp]).

## Revalidation after a mutation

| Framework | Default after success | Round trips | Targeting | Opt-out | After a failed submission |
|---|---|---|---|---|---|
| **Void** | **The current page's loader re-runs on the server and the new props return in the same response** (single-flight for the current page). The prefetch cache is flushed entirely. Global middleware does not run again, so `shared` is whatever the action request already set. Deferred props are **stripped and keep their last values** until the next navigation | 1 (a redirect is followed in the same `fetch`, and the destination JSON is used as the GET result) | ✗ | ✗ (only by redirecting or returning a `Response`) | The loader **also re-runs** on `ValidationError` (the page is returned with `errors`) |
| **Next.js** | Re-renders the current route in the same response **only if** the action called `updateTag`, `revalidatePath` or `refresh()`, mutated cookies, or redirected; otherwise only the return value comes back. Any revalidation clears the whole client cache | 1 | tags / paths | default is "nothing" | — |
| **React Router** | **All active loaders** (2xx), including after fetcher and resource-route submissions | 2 for client submissions (POST, then `.data` GET); 1 for a document POST | — | `shouldRevalidate`, `defaultShouldRevalidate` | non-2xx: **no** revalidation |
| **TanStack Start** | none (`router.invalidate()` by hand; does not purge CDN or DB caches) | 2 | `filter` | — | — |
| **Nuxt** | none (`refresh()`, `refreshNuxtData(keys)`) | 2 | keys | — | — |
| **SvelteKit** | Form actions: the page's loads re-run (`use:enhance`: `refreshAll` on success). Remote `form` [exp]: all queries and loads by default, or **single-flight** targeted updates via `query(arg).refresh()` / `.set(v)` / `.reconnect()` inside the handler, or client-requested `.updates(...)` that the server must accept with `requested(query, limit)`. `command`: nothing | 1 (single-flight) or 2 | query and arg level | `update({ refreshAll: false })`; `.updates()` with no args | `refreshAll` defaults to false on failure |
| **SolidStart** | All active queries; **single-flight** when the affected queries are preloaded by the (destination) route's `preload` (`singleFlight` default true) | 1 or 2 | `json(...)` / `reload(...)` / `redirect(..., { revalidate: keys })` → `X-Revalidate` header | `revalidate: []` | — |
| **Astro** | Form submissions re-render the page (fresh); RPC refreshes nothing | 1 | — | — | — |

**Behavioral differences that matter:**
- Void's automatic one-round-trip refresh is the best default in this group. Only SvelteKit and SolidStart match it, and both need extra setup.
- Void cannot say "this mutation doesn't affect the page", so a like-counter still pays for the full loader.
- Void cannot refresh one prop (Inertia `only`) or other pages' data. Since Void keeps no visited-page cache, other pages are fresh on the next visit anyway.

**Void gap: partial.** Missing: targeted or partial refresh and opt-out (Next.js, React Router, SvelteKit, SolidStart); re-resolving deferred props; skipping the loader re-run on validation failure (React Router skips revalidation on non-2xx). Server HTML-cache purge exists (`revalidate({ paths })` from `void/isr`, area 5).

## Redirects after a mutation

| Framework | API | Default status | Client handling | Notes |
|---|---|---|---|---|
| **Void** | `return c.redirect(url \| routeUrl(...), status?)` | 302, Hono's default (per Hono, not Void docs) | `fetch` follows the redirect; the destination page JSON is used as the GET result; a cross-origin target gets a full page load | `c.redirect()` sends the location unchanged and does not append the request query (`runtime/routing.ts`). A named action still drops its action key when the follow-up is a GET and keeps the page's other parameters. Config `routing.redirects` still merge the request query (the destination wins). No external-URL guard |
| **Next.js** | `redirect(path, type?)` (throws; call it outside `try`) | 303 without JS | In actions it defaults to `push`; the destination RSC is streamed in the same response | Revalidate before redirecting |
| **React Router** | `redirect` / `replace` / `redirectDocument` (return or throw) | 302 | `replace` → `replaceState`; `redirectDocument` → full reload | Docs warn about open redirects |
| **TanStack Start** | `throw redirect({ to \| href, params, search, statusCode, replace, resetScroll, … })` | — | handled by route lifecycles or `useServerFn`; a returned `Response` with `Location` is followed by the browser before the caller sees it | |
| **Nuxt** | client `navigateTo()` after `$fetch`; server `sendRedirect` | — | manual | |
| **SvelteKit** | `redirect(303, url)` (throws) | 300–308 required | enhanced forms call `goto` | v3: external redirects need `{ external: true \| [origins] }`; `command` cannot redirect |
| **SolidStart** | `redirect(url, init)` (throw or return; `never` type) | 302 | `Location` → client navigation; can carry `revalidate` keys; single-flight to the destination's preload | |
| **Astro** | Page code: `if (result && !result.error) return Astro.redirect(...)`; actions **cannot** redirect | — | `navigate()` | PRG is DIY |

**Void gap: none** at the capability level. Option-level: no `replace` vs `push` choice for redirects (React Router `replace()`, TanStack Start `replace`), no "full document" redirect (React Router `redirectDocument`), and no open-redirect guard (SvelteKit v3).

## File uploads

| Framework | Client | Server parsing | Size limit | Streaming | Validation |
|---|---|---|---|---|---|
| **Void** | `useForm` / `action()`: automatic multipart when `data` holds a `File`, `Blob` or `FileList`. `useIslandForm` is JSON-only (no files) | `await c.req.parseBody()` (Hono; buffers the whole body) | **none** in the framework (platform limits only) | ✗ (`file.stream()` to R2 only after the buffered parse) | ✗ for schemas (`withValidator` is JSON-only); manual `instanceof File` + `ValidationError` (the docs show a type allow-list and server-chosen keys) |
| **Next.js** | `FormData` | `formData()` | `serverActions.bodySizeLimit`, **1 MB** default (raw multipart) | ✗ | BYO; a string `<Form>` sends only the file name |
| **React Router** | `encType="multipart/form-data"` | `@remix-run/form-data-parser` `parseFormData(request, uploadHandler)` | not documented | ✓ per-file upload handler | BYO |
| **TanStack Start** | `FormData` to a POST server fn | validator gets `FormData`; server routes use `request.formData()` | not documented | ✗ | manual |
| **Nuxt** | `FormData` body | `event.req.formData()`, `readMultipartFormData` | not documented | ✗ | — |
| **SvelteKit** | native multipart; remote form `.as('file' \| 'file multiple')` [exp]; commands accept `File` | `request.formData()` | `BODY_SIZE_LIMIT` (adapter-node/bun, 512K default) → 413 | limit enforced while streaming | remote form schema (`v.file()`) [exp] |
| **SolidStart** | `enctype` multipart; `File`/`Blob` passed raw to server fns | `FormData` | not documented | ✗ | BYO |
| **Astro** | `enctype` multipart | Actions `z.instanceof(File)` | `security.actionBodySizeLimit` **1 MB**; Node adapter `bodySizeLimit` 1 GB | ✗ | Zod |

**Void gap: partial.** Missing: a configurable body-size limit (Next.js, SvelteKit, Astro); schema validation of file fields (SvelteKit [exp], Astro); file support in `useIslandForm`; streaming multipart. No framework documents upload progress.

## CSRF and origin checks

| Framework | Built in | Check | Requests with no origin headers | Scope | Allow-list |
|---|---|---|---|---|---|
| **Void** | ✓ for page actions, always on | `Origin` must equal the request URL's origin. Otherwise `Sec-Fetch-Site` must be `same-origin` or `none`. Otherwise `Referer` must have the same origin | **allowed** (non-browser clients) | **page actions only**; `routes/` handlers are unprotected (docs suggest Hono `csrf()`); Void auth ignores the session on cross-origin non-GET unless `trustedOrigins` allows it | **none** for page actions | 
| **Next.js** | ✓ | `Origin` host vs `X-Forwarded-Host` / `Host` | allowed with a warning | Server Actions (POST only) | `serverActions.allowedOrigins` (`*`, `**` wildcards) |
| **React Router** | ✓ | origin validation | not documented | actions on UI routes (not resource routes) | `allowedActionOrigins` (globs) |
| **TanStack Start** | ✓ for server functions (auto-installed only when there is no custom `src/start.ts`) | `Sec-Fetch-Site`, `Origin` or `Referer` same-origin | **rejected** unless `allowRequestsWithoutOriginCheck` | server functions; attachable to server routes | `origin` override |
| **Nuxt** | ✗ (not documented) | — | — | — | — |
| **SvelteKit** | ✓, always on (v3) | origin vs app origin / `paths.origin` | cross-origin mutative requests **without `Content-Type`** are rejected | form submissions + remote calls | `csrf.trustedOrigins` |
| **SolidStart** | ✗ (a middleware recipe; double-submit cookie recommended) | — | — | — | — |
| **Astro** | ✓ `security.checkOrigin` (default true) | `Sec-Fetch-Site`, falling back to `Origin` | not documented | on-demand pages; unsafe methods with form-like or missing content types | `security.allowedDomains` (for `X-Forwarded-Host`) |

**Behavioral differences that matter:** Void compares `Origin` with the request URL's own origin. Behind a proxy that rewrites the host, or on a multi-domain app, there is no allow-list to fix legitimate cross-origin posts. Next.js, React Router, SvelteKit and TanStack Start all have one. Void returns 403 `Cross-origin page actions are not allowed.` (pages/protocol.ts `isSameOriginAction`).

**Void gap: partial.** Missing: a trusted-origins allow-list for page actions (4 peers) and opt-in protection for `routes/` handlers.

## Error handling and status codes

| Framework | Expected vs unexpected | Where unexpected errors go | Notes |
|---|---|---|---|
| **Void** | Fixed status routing (pages/action-result.ts). **Call-site** (`form.error`, `action()` `ok: false`): 400, 402, 404, 408, 409, 412, 413, 415, 422, 429, 499. **Boundary** (thrown): 401, 403, 405, 428, 5xx, everything else | framework error handling / error boundary (area 7) | Message: the `HTTPException` message for 4xx, a plain-text 4xx body, or `Action failed with <status> <text>`. `UsageLimit` → structured 429 with `retryAt`, which `Form` honours |
| **Next.js** | Return expected errors; throw unexpected ones | nearest `error.js` / `catchError` | `forbidden()` / `unauthorized()` from actions [exp] |
| **React Router** | `data(..., { status })` vs `throw` | route `ErrorBoundary` | non-2xx skips revalidation |
| **TanStack Start** | Rejects with the thrown value; serialized message | caller | middleware errors keep their status |
| **Nuxt** | `createError` → `FetchError` | caller | Nuxt 5: server-route errors are always JSON |
| **SvelteKit** | `fail()` vs `error()`; remote `invalid()` | nearest `+error.svelte` | invalid remote args → generic 400 + `handleError({ kind: 'validation' })` |
| **SolidStart** | return vs throw (`submission.error`) | `<ErrorBoundary>` for queries | `serverFunctions.onError` sanitizes |
| **Astro** | `ActionError({ code })` → HTTP status; `SafeResult` | caller | `isActionError`, `isInputError` |

**Void gap: none.** Void's status-category routing is more opinionated than any peer and should be kept.
