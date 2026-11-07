# 6. Server & API

**Versions:** Void 1.6.2 · Next.js 16.4 (App Router) · React Router 8 (framework mode) · TanStack Start 1.169 (React) · Nuxt 5.0 pre-release (4.x is stable) · SvelteKit 3.1 · SolidStart 2.0 · Astro 7.4

**Markers:** [exp] experimental, unstable or canary · [CC] Next.js with Cache Components on (the create-next-app default) · (src) found in Void's source but not in its docs

**Paths:** Void file paths are in the `voidzero-dev/void` repo. Short paths such as `pages/scan.ts` are under `packages/void/src/`; paths that start with a package name, such as `react/src/…`, are under `packages/`.

## At a glance

- **Void's server layer is Hono.** Every route handler, page loader, action, `head()` and middleware gets a Hono `Context`, so any `hono/*` or `@hono/*` middleware/helper (cors, csrf, bearer-auth, etag, cache, cookie, streaming, rate limiters) works without an adapter. None of the other seven has a third-party middleware ecosystem that plugs in this directly (Astro 7 comes closest with `astro/hono` inside `src/fetch.ts`).
- **Endpoints are ergonomic.** `routes/` uses per-method exports and converts plain return values (object→JSON, string→HTML, null→204). `defineHandler.withValidator({ body, query, params })` takes any Standard Schema validator and feeds the typed `fetch` client. `.dev`/`.prod` suffixes limit a route to one environment. Only Nuxt 5 has comparable endpoint-level validation with client type flow.
- **SSE is best in class.** `void/sse` provides `eventStream` (keepalive, Last-Event-ID, closed-stream errors) and `void/sse/client` provides typed `connectEventStream`. No other framework ships first-party SSE helpers.
- **Middleware is global plus per-route.** Global middleware comes from numerically ordered files. Per-route middleware is `defineHandler(mw…, handler)`, and it also wraps page loaders/actions *and the rendered page*. Server middleware runs on every client navigation, because each one is a server request. Void lacks directory-scoped middleware (React Router, TanStack Start), client-side middleware (React Router, TanStack Start, Nuxt) and per-chain inferred context types (TanStack Start, React Router).
- **Biggest gaps:**
  1. **Server-only code isn't enforced at build time.** Nothing stops a client import of a `.server.ts` page companion, and there is no `server-only` marker. 6/7 others enforce this.
  2. **No user-owned server entry.** User middleware always runs after Void's redirect, header and auth stages, and the Worker `fetch` can't be wrapped. 6/7 others offer an entry.
  3. **No public request-scoped getter.** Deep code has no `getRequestEvent()`- or `cookies()`-style access to the request (5/7 have one). Cookies are undocumented and only available through `hono/cookie`; 7/7 others document a cookie API.
  4. **No portable `after()`/`waitUntil`.** It works only on Cloudflare, through `c.executionCtx`, and is unavailable on Node/Bun/Deno. 2/7 others have a portable API.
- **HTTP-method gaps:**
  - An unexported method returns 404, not 405.
  - `OPTIONS`/`Allow` is not auto-generated.
  - An explicit `HEAD` export fails the build.
  - The "catch-all method" mechanism (a `default` export) is undocumented.
- **Env leak protection is ahead of most.** Reading a server key from `void/env` in client code fails the client build *per key*, and `env.ts` is schema-validated.

## Gap list for this area

| Gap in Void | Who has it (mechanism, briefly) | Prevalence | Notes for design (constraints, dependencies, adapter impact) |
|---|---|---|---|
| Build-time enforcement of server-only modules (`.server.*` files, `server-only` marker) | Next.js (`server-only` pkg), React Router (`.server` files/dirs), TanStack Start (import protection), Nuxt (`nuxt/server`/`#server`), SvelteKit (`server` segment/dirs), SolidStart (`server-only`) | Table stakes (6) | Highest-risk gap: `.server.ts` is Void's loader/DB home *and* exports `Props`. Add a client-environment resolve check with an import trace; allow `import type`. Also turn silent `void/db`/`kv`/`ai`/`queues`/`storage`/`isr` stubs into errors. Must cover `.vue`/`.svelte` script blocks (all 4 adapters). |
| User-owned server entry / control over pipeline stages | Astro (`src/fetch.ts` stages, Hono), TanStack Start (`src/server.ts`), React Router (custom server, `entry.server`), SvelteKit (`handle` first + adapter-node handler), SolidStart (H3 entry), Next.js (custom server) | Table stakes (6) | Today user middleware runs after redirects/rewrites/headers/auth. Expose stages as Hono middleware a user entry can compose. Keep the managed-dispatch path (platform applies rules first) consistent. |
| Documented cookie helpers with secure defaults (and optionally isomorphic/signed/sealed) | All 7 (Next.js `cookies()`, React Router `createCookie` signed+rotation, TanStack Start/SolidStart/Nuxt get/setCookie, SvelteKit `event.cookies` secure defaults, Astro `cookies`) | Table stakes (7) | Cheapest gap: `hono/cookie` already works. Document it, or wrap it with secure defaults (`httpOnly`, `secure` outside dev, `sameSite: 'lax'`, `path: '/'`). Cookies interact with ISR (any `Set-Cookie` makes a response private) and with typed `fetch` cookie forwarding. |
| Public request-scoped getter for deep code (request, cookies, response headers) | Next.js (`cookies()`/`headers()`), TanStack Start (`getRequest()`…), SvelteKit/SolidStart (`getRequestEvent()`), Nuxt (`useRequestEvent()`; native ALS exp.) | Common (5) | The ALS `requestContext` already exists on all targets. Response-header setters must land before the page response is built. |
| Client-side middleware / navigation guards | React Router (`clientMiddleware`), TanStack Start (`beforeLoad`, function mw `.client`), Nuxt (route middleware) | Common (3) | Less critical in Void because every navigation hits server middleware. Would need a hook in the shared navigation engine (adapter-agnostic) plus prefetch-cache semantics. |
| Documented catch-all method handler | SvelteKit (`fallback`), Astro (`ALL`), Nuxt (unsuffixed file), React Router (one `action` for all mutations) | Common (4) | Already implemented (src: a file with no method exports routes all methods to `default`). Document it, type it, and error at build time when `default` is missing. |
| Proxy-aware client-IP helper | Nuxt (`getRequestIP({ xForwardedFor })`), SvelteKit (`getClientAddress` + `XFF_DEPTH`), Astro (`clientAddress`) | Common (3) | Must differ per target: `cf-connecting-ip` on Cloudflare, socket address or XFF on Node. |
| 405 + `Allow` for unexported methods; auto-`OPTIONS` | Next.js (405 + auto OPTIONS/`Allow`), Nuxt (405) | Differentiator (2) | Hono 404s on method mismatch. Needs a per-pattern method table (already known at compile time). Keep `hono/cors` preflight working. |
| Portable work-after-response (`after`/`waitUntil`) | Next.js (`after()`), Nuxt (`event.waitUntil`) | Differentiator (2) | Cloudflare: forward to `executionCtx.waitUntil`. Node/Bun/Deno: track pending promises and drain on shutdown. Document the Cloudflare path today. |
| Directory-scoped (nested) middleware | React Router (route `middleware` nesting), TanStack Start (pathless-layout middleware) | Differentiator (2) | Could follow Void's layout tree (`pages/`) and `routes/` dirs, e.g. `_middleware.ts`. Note that layouts have no server companion today. |
| Context types inferred from the middleware chain | TanStack Start (chain inference), React Router (typed `createContext` keys) | Differentiator (2) | `defineHandler(mw…, handler)` could thread Hono `Env` generics from typed middleware into the handler. Global middleware would still need augmentation. |
| External proxy rewrites | Next.js (`rewrites()` external), Nuxt (`proxy` rule, `proxyRequest`) | Differentiator (2) | Could allow external destinations in `routing.rewrites` (managed dispatch impact) or document `hono/proxy`. |
| Form/multipart body validation | Astro (actions `accept: 'form'`), SvelteKit (remote `form`, exp.) | Differentiator (2) | Also blocks no-JS forms (area 4). Extend `withValidator` to urlencoded/multipart with field coercion. |
| Header validation slot | Nuxt (`defineValidatedHandler({ validate: { headers } })`) | Differentiator (1) | Small extension of `withValidator` slots; typed-`fetch` impact. |
| Explicit `HEAD` override | Next.js, SvelteKit | Differentiator (2) | Currently a build error because Hono can't register HEAD. Would need a GET-handler wrapper that checks for a HEAD export. |
| Server-function middleware | TanStack Start (function middleware) | Differentiator (1) | Only relevant if Void adds RPC/server functions. |

## Where Void is ahead

- **First-party SSE, server and client.** `eventStream` provides keepalive, Last-Event-ID, closed-stream errors and anti-buffering headers. `connectEventStream` is typed, and `fetchStream()` covers streamed `fetch`. No other framework ships SSE helpers.
- **Schema validation on plain HTTP endpoints.** It covers `body/query/params`, works with any Standard Schema library, and flows into the typed client and `useForm`. Only Nuxt 5 matches it; the rest validate RPCs or actions only.
- **Hono-native composition.** Any Hono middleware works in global, per-route and per-page positions, and `basicAuth` is built in. Only Astro 7 offers comparable interop, and only inside `src/fetch.ts`.
- **Per-route middleware wraps page loaders, actions and the rendered page.** For example, `etag()` on pages returns 304s. Only React Router offers comparable route-scoped page middleware.
- **Server middleware covers every client navigation** without tricks, because each navigation is a server request. React Router covers navigations only when a server loader runs, and SolidStart doesn't guarantee coverage.
- **Return-value conversion** (object→JSON, string→HTML, null→204). Only Nuxt does this too.
- **Typed internal rewrites.** `c.rewrite()` takes typed destinations, re-runs middleware, and offers `c.originalUrl()`/`c.isRewritten()`. Dev builds expose an `X-Void-Routing` trace header.
- **Per-key env leak detection at build time** plus startup schema validation. Only SvelteKit's `src/env.ts` matches it on validation.
- **`.dev`/`.prod` environment-only routes** and the `void gen route` scaffolder. Not seen elsewhere.
- **Server-side typed `fetch`** to the app's own routes skips HTTP and forwards `cookie`/`authorization`. Nuxt's in-process `$fetch`/`serverFetch` is the only analogue.

## API route definition

| Framework | Convention | Method exports | HEAD | Unhandled method / OPTIONS | Catch-all method | Page + endpoint at same URL | Return value handling |
|---|---|---|---|---|---|---|---|
| **Void** | `routes/**` (`.ts/.tsx/.js/.jsx/.mts/.mjs`). Supports `[id]`, `[...slug]` and `(group)`; `_`/`.` prefixes are excluded. `.dev`/`.prod` suffixes limit a route to one environment. Generator: `void gen route --methods`. | Named `GET POST PUT PATCH DELETE OPTIONS` (`defineHandler`). | `GET` answers `HEAD` (Hono). **Exporting `HEAD` fails the build** ("HEAD requests are answered by the GET handler; remove the HEAD export"; packages/void/src/router/scan.ts). | Returns **404**: Pages apps send plain-text `Not Found`. Other apps get Hono's default `404 Not Found`, or `Not Found` after the asset/fallback check (src: router/compile.ts `notFound` selection). No 405, no `Allow` header, no auto-`OPTIONS`; preflight is handled by `hono/cors`. | **Undocumented (src):** a file with no recognized method export is registered with `app.all()` and dispatches to its `default` export (router/compile.ts). | `routes/` handlers are registered before pages, so they win for the same method and path (src: compile.ts order). | Object/array/number/boolean → JSON. `string` → `text/html; charset=utf-8`. `null`/`undefined` → 204. `Response` passes through. All Hono helpers are available (`c.json/text/html/body`, `c.status`, `c.header`, `hono/streaming`). `.tsx` handlers: React and Solid render JSX to a string themselves; Vue, Svelte and API-only apps configure Hono JSX. |
| **Next.js** | `app/**/route.ts` | `GET POST PUT PATCH DELETE HEAD OPTIONS` | Explicit `HEAD` export allowed. | Unsupported methods get **405**. **`OPTIONS` is auto-implemented with an `Allow` header** when not exported (FC/route.mdx). | none | **Cannot coexist** with `page` in the same segment. | Must return `Response`/`NextResponse`; no conversion. [CC] GET is prerendered unless it reads request data. |
| **React Router** | Resource route: a route module with `loader`/`action` and **no default export** | `loader` (GET) plus a single `action` (branch on `request.method`) | via `loader` (inferred) | not documented | `action` covers every non-GET method | A module is either a UI route or a resource route. | `Response` or `data()`. A thrown non-Response gives 500 and goes to `handleError`. |
| **TanStack Start** | `server.handlers` on `createFileRoute` in `src/routes`. Splat `$.ts`, escaped `[.]json`. | Object `{GET, POST, …}`, or `createHandlers({ GET: { middleware, handler } })` | not documented | not documented | none | **Yes**: the same file can export `component` and `server.handlers`. | Must return `Response`. |
| **Nuxt** | `server/api/**` (served under `/api`), `server/routes/**` (no prefix). Also `serverHandlers` config and Kit `addServerHandler`. | Filename suffix `.get/.post/.put/.delete/.patch` | (h3) | **405** for methods not matching the suffix. `readBody` on a GET throws 405. | An unsuffixed file serves any method (implied by docs). | Separate trees. | JSON-serializable → JSON. `Response` is merged with `event.res.headers` (set-cookie appended). Streams and text/HTML are also accepted. Nuxt 5: an unknown dotted suffix fails the build. |
| **SvelteKit** | `+server.js` | `GET POST PUT PATCH DELETE OPTIONS HEAD QUERY` | `GET` answers `HEAD` with `content-length`; GET beats `fallback`. | 405 not documented. Vite injects CORS headers on OPTIONS **in dev only**. | **`fallback` export** (e.g. `MOVE`) | **Yes**: `+server` and `+page` can share a directory. GET/POST/HEAD with `Accept: text/html` go to the page. | Must return `Response` (`json()`/`text()` deprecated). v3: empty 2xx responses have no body. |
| **SolidStart** | Files in `src/routes` that export method handlers | `GET POST PATCH DELETE HEAD …` | Falls back to GET when there is no `HEAD` export. | No auto-OPTIONS/405 documented. | none | API routes take priority over UI routes (v1: split by `Accept`). | `Response`/`Response.json`. v1: a `GET` returning nothing fell through to the UI route. |
| **Astro** | `.js/.ts` in `src/pages` | Any method name | Derived from GET (body stripped) | An unmatched method falls through to the **404 page**. | **`ALL`** | One file per path. | Must return `Response`. Static mode runs endpoints at build and emits files (`rss.xml.js`). |

**Behavioral differences that matter:**
- Only Void and Nuxt convert plain return values. Everyone else requires a `Response`. Because Void serves a returned plain string as `text/html`, a handler that returns unescaped user input is an XSS sink. Worth a doc warning.
- Void answers a wrong method with **404**, while Next.js and Nuxt answer with **405**. Clients and monitoring can't tell "wrong verb" from "missing route", and there is no `Allow` header. Next.js also auto-answers `OPTIONS`.
- Void *forbids* an explicit `HEAD` handler because Hono can't register one. Next.js and SvelteKit let you override HEAD, for example to skip computing the body.
- Void's catch-all-method path exists in source but is undocumented. With no `default` export the call would throw at runtime, giving a 500 (inferred). SvelteKit (`fallback`) and Astro (`ALL`) name and document theirs.
- Content negotiation between a page and an endpoint at the same URL is built into SvelteKit and SolidStart. TanStack Start allows both in one file. In Void, the `routes/` handler silently shadows the page.

**Void gap:** partial. Missing: 405 with `Allow`, auto-`OPTIONS`, a HEAD override, and a *documented* catch-all method export.

## Request & response API

| Framework | Handler input | Request / params / body | Cookies | Response status & headers | Per-request locals |
|---|---|---|---|---|---|
| **Void** | Hono `Context` (`CloudContext`) everywhere: routes, loaders, actions, `head()`, middleware. | `c.req.raw` (Web `Request`), `c.req.param/query/header/json/parseBody`. `c.env` holds typed bindings; `c.executionCtx` is Cloudflare-only. | **No Void API and not documented.** Use Hono's `hono/cookie` (`getCookie/setCookie/deleteCookie`, signed variants; Hono feature, not Void-documented). No secure-by-default options, no isomorphic `useCookie`. | `c.status()`, `c.header()`, or any `Response`. Headers set in a loader or in middleware before `next()` are copied onto the rendered page response (packages/void/test/unit/routing-runtime.test.ts). The page status cannot be set (§7). | `c.set/get`, typed through `declare module 'void' { interface CloudContextVariables }`. `c.set('shared', …)` reaches `useShared()`; `c.set('headDefaults', …)` sets head defaults. |
| **Next.js** | Route Handlers receive `(NextRequest, { params: Promise })`. Elsewhere use async `cookies()`, `headers()`, `connection()`. | `NextRequest.nextUrl`, `.cookies`. `ip`/`geo` removed in v15. `userAgent()`. | `cookies()`: `get/getAll/has/set/delete/toString`. Options: `expires maxAge domain path('/') secure httpOnly sameSite priority partitioned`. **`set` works only in Server Functions/Route Handlers.** | Route Handlers set them on the `Response`. `headers()` is read-only. Pages: see §7. | **None.** Pass data from Proxy as request headers (`NextResponse.next({ request: { headers } })`). |
| **React Router** | `{ request, params, context }` | Web `Request`; `url` arg is the normalized URL. | `createCookie(name, { secrets, …attrs })` → `parse/serialize`. **Signed, with secret rotation**; `isCookie`. | `data(value, { status, headers })`, plus the route `headers` export. | `RouterContextProvider` with `createContext<T>()` keys, seeded by `getLoadContext`. |
| **TanStack Start** | `{ request, params, context }`, plus context-free helpers | `getRequest()`, `getRequestHeader()` (`''` vs `undefined` semantics). Invalid percent-encoding → 400 before middleware. | `getCookie`, `setCookie(name, value, { httpOnly, secure, sameSite, path, maxAge })`, `deleteCookie`. | `setResponseStatus` (200–599), `setResponseHeader(s)`, `appendResponseHeader`. These **override** the returned Response. Using `setResponseHeader('set-cookie')` replaces all cookies. | Middleware `context` and a typed server `requestContext`. |
| **Nuxt** | `RequestEvent { req, url, res, context }` (Nitro `H3Event` adds `waitUntil`, `node`, `runtime`). | `getRequestURL/Host/Protocol` (forwarded headers trusted only when opted in), `getRequestIP({ xForwardedFor })`, `getRouterParam(s)` (raw unless `{ decode: true }`), `readBody`, `getQuery`, h3 `readMultipartFormData`. | `getCookie/parseCookies/setCookie/deleteCookie`. Isomorphic `useCookie` (options: decode/encode, default, watch, refresh, readonly, maxAge/expires…). Sealed `useSession` (`appSecret`). | `event.res.status/headers`, `setResponseStatus`. | `event.context` |
| **SvelteKit** | `RequestEvent` | `request`, `url`, `route`, `getClientAddress()` (adapter-node `ADDRESS_HEADER`/`XFF_DEPTH`), `isDataRequest`/`isSubRequest`/`isRemoteRequest`. | `cookies.get/getAll/set/delete/serialize`. **Defaults: `httpOnly: true`, `secure: true` (except dev), `path: '/'`** (packages/kit/types/index.d.ts). Cookies propagate to `event.fetch`. | `setHeaders()` (once per header, no set-cookie). `+server` returns a `Response`. | `locals` (`App.Locals`), `platform` (`App.Platform`). |
| **SolidStart** | `APIEvent { request, params, response, locals, nativeEvent }` | `readBody`, `getQuery`, `getRequestHeader` (`@solidjs/start/http`, server-only). | `getCookie`, `setCookie`; sealed `useSession({ password ≥32 })`. | `response` stub, `setResponseHeader`. | `locals` (`RequestEventLocals`) |
| **Astro** | `APIContext` / `Astro` | `request`, `url`, `params`, `clientAddress` (adapter-trusted), `originPathname`, `routePattern`, `isPrerendered`. | `cookies.get` → `AstroCookie { json(), number(), boolean() }`; `set` (incl. `partitioned`); `merge`, `consume()`. On-demand only. | `Astro.response.status/statusText/headers` on pages; `Response` from endpoints. | `locals` (`App.Locals`) |

**Behavioral differences that matter:**
- Void has the richest *imperative* request API, through Hono, but the thinnest *documented* cookie story. Every other framework documents a cookie API. SvelteKit defaults to secure flags, React Router signs cookies and rotates secrets, Nuxt offers an isomorphic reactive `useCookie`, and Nuxt and SolidStart ship sealed sessions. In Void, sealed sessions exist only inside the Better Auth integration (out of scope).
- Client IP: Nuxt, SvelteKit and Astro have a helper that handles proxy trust explicitly. Void has none, so you read platform headers yourself (not found in docs or source).
- Typing of locals: Void uses a global module augmentation, like SvelteKit, Astro, SolidStart and Nuxt, so every key looks set even on routes where the middleware didn't run. TanStack Start infers context from the middleware chain. React Router's typed keys throw if read unset without a default.

**Void gap:** partial. Missing: documented cookie helpers with secure defaults (table stakes) and a proxy-aware client-IP helper (Common).

## Request validation helpers

| Framework | API | Slots | Libraries | Failure response | Form / multipart bodies | Type flow to client |
|---|---|---|---|---|---|---|
| **Void** | `defineHandler.withValidator({...})(handler)` on routes, page `loader`, `action`, `actions.*` | `body`, `query`, `params` | Standard Schema (Zod ≥3.25/4, Valibot ≥1, ArkType ≥2). Drizzle-derived through `void/drizzle-zod`, `void/drizzle-valibot`, `void/drizzle-arktype`. | 400 `{ error: 'Validation failed', issues: [{ slot, issues: [{ message, path }] }] }`. Page actions flatten this to `form.errors`. | **JSON only.** Non-JSON bodies get 400 `Invalid JSON body` (runtime/validator.ts). | Typed `fetch` `body/query/params`; `useForm` defaults and error keys. |
| **Next.js** | none (BYO) | — | — | — | — | — |
| **React Router** | none (BYO; return `data(errors, { status: 400 })`) | — | — | — | — | — |
| **TanStack Start** | `.validator()` on server functions and function middleware; route `validateSearch`, `params.parse` | data, search, params | Standard Schema or a function | Thrown to the caller | Server functions accept `FormData` (validator receives it) | Server-function input/output types |
| **Nuxt** | `readValidatedBody`, `getValidatedQuery`, `defineValidatedHandler({ validate: { body, query, headers } })` | body, query, **headers** | Standard Schema or a function | 400 with `data.issues` (`onError` override) | via h3 readers | Nuxt 5 typed `$fetch` enforces body, query and headers. |
| **SvelteKit** | Remote functions with a schema [exp]; `defineParams` (params, stable in v3) | args, params | Standard Schema | `handleError` kind `'validation'` → 400 | Remote `form` [exp] | Remote-function types |
| **SolidStart** | none | — | — | — | — | — |
| **Astro** | Actions `input` (not endpoints) | action input | Zod 4 | `BAD_REQUEST` `ActionError` | **`accept: 'form'`** auto-parses FormData | Typed `actions.*` |

**Behavioral differences that matter:** Void and Nuxt are the only frameworks with schema validation on *plain HTTP endpoints*. The others validate RPCs or actions only. Void cannot validate urlencoded or multipart bodies, which also blocks no-JS forms (area 4). Nuxt additionally validates headers.

**Void gap:** none for JSON endpoints, where Void is ahead. Partial for form/multipart bodies (Astro actions; SvelteKit remote forms, exp.) and for a header slot (Nuxt).

## Middleware

### Structure and scope

| Framework | Global | Per-route | Per-directory / nested | Client-side | Server-function middleware |
|---|---|---|---|---|---|
| **Void** | `middleware/*.ts` default export (`defineMiddleware(fn)` or any Hono middleware). `NN.` numeric prefix sets order; unnumbered files run last; `_` prefix ignored; nested dirs are still global. | `defineHandler(mw1…, handler)`: up to 5 typed overloads for a plain leaf; variadic when the leaf is itself a `defineHandler`/`withValidator` result (src: runtime/handler.ts). Applies to routes, page `loader`, `action(s)`, and wraps the **rendered page**. | ✗ | ✗ | n/a (no server functions) |
| **Next.js** | Single `proxy.ts` (formerly middleware). `config.matcher` takes path-to-regexp patterns with `has/missing`. Node runtime. | ✗ (matcher or inline branching) | ✗ | ✗ | ✗ |
| **React Router** | Root route's `middleware` | Route `middleware` export | **✓ nested chain root→leaf** | **✓ `clientMiddleware`** (wraps client navigations and fetchers; `next()` returns dataStrategy results) | ✗ |
| **TanStack Start** | `src/start.ts` `createStart({ requestMiddleware, functionMiddleware })` | Route `server.middleware`; per-method `createHandlers` middleware | **✓** pathless layout routes add middleware to groups; break-out routes escape it | **✓** function middleware `.client()` half | **✓** `createMiddleware({ type: 'function' })` with `.validator/.client/.server` and `sendContext` |
| **Nuxt** | `server/middleware/*.ts`, run before every server route and page render | ✗ by file. Use a `serverHandlers` entry `{ route, middleware: true }` or route rules (`headers`, `cors`, `redirect`, `proxy`). | ✗ | **✓** route middleware (`app/middleware`, `.global`, inline `definePageMeta`) runs on SSR and client navigations | ✗ |
| **SvelteKit** | `handle` in `hooks.server`; `sequence()`; `handleFetch` | ✗ (layout server `load` for pages) | ✗ | ✗ (`beforeNavigate` is a hook, not a chain) | ✗ (remote fns run through `handle`) |
| **SolidStart** | `solidStart({ middleware })` → `createMiddleware([h3 middleware])`. The `onRequest/onBeforeResponse` form is deprecated. | ✗ | ✗ | ✗ | ✗ (only `serverFunctions.onError`) |
| **Astro** | `src/middleware.ts` `onRequest`; `sequence()`; integrations `addMiddleware({ order: 'pre'\|'post' })`; adapter `middlewareMode: 'edge'` | ✗ (Hono route-scoped middleware possible inside `src/fetch.ts`) | ✗ | ✗ | ✗ |

### Behavior

| Framework | Order | Short-circuit | Post-process | Context passing / typing | Coverage |
|---|---|---|---|---|---|
| **Void** | Fixed stages: context and request ALS → config redirects/rewrites (skipped where the managed platform applies them first) → `routing.headers` rules → named-action marker → Void auth → **user global (numeric)** → WebSocket upgrades → `/api/auth/*` → `routes/` → pages → not-found fallback (src: router/compile.ts) | Return a `Response` | After `await next()`, read, edit or replace `c.res` (body included) | `c.set()` with global `CloudContextVariables` augmentation. Also `c.rewrite(dest)` for internal re-dispatch: middleware re-runs on each hop, so guard with `c.isRewritten()`; `c.originalUrl()` gives the original URL. | Every request that reaches the Worker, **including every client GET navigation and prefetch** (each is a server JSON request). Static assets usually bypass the Worker on Cloudflare. Prerendered static page-data fast-path reads skip it. ISR hits are served before the app (inferred from docs/guide/edge/revalidation.md and the compile.ts ISR wrapper). |
| **Next.js** | Config headers → redirects → Proxy → beforeFiles rewrites → filesystem → afterFiles → dynamic → fallback | Return `Response`, redirect or rewrite | ✗ (runs before rendering; can only set response headers on `next()`) | Request headers or cookies only | Every request including `_next/static` unless matched out; `_next/data` always |
| **React Router** | Nested root→leaf down, then back up | Throw `redirect()`/Response. `next()` can be called once and is auto-called if omitted. | Headers after `next()` (don't touch the body) | `context.set(createContext<T>())`: typed keys | Document requests always. Client navigations **only when a `.data` request is made** (a server loader/action must run). |
| **TanStack Start** | Dependency-first: global request → global function → per-function chain → handler; route-level before per-method | Don't call `next()` | `result.response` is mutable | `next({ context })` with **types inferred through the chain**; `sendContext` (must be validated server-side) | SSR, server routes, server functions |
| **Nuxt** | Not documented (alphabetical by filename; from memory, unverified) | Returning any value ends the request (discouraged) | ✗ in middleware (Nitro `response` hook instead) | `event.context` | Every request. **Nuxt 5:** a server-middleware error returns JSON even for a page navigation. |
| **SvelteKit** | `sequence()` | Return a `Response` without calling `resolve` | Edit `response.headers`; `resolve(event, { transformPageChunk, filterSerializedResponseHeaders, preload })` | `event.locals` (`App.Locals`) | Pages, endpoints, data requests, remote calls, prerender. Not static assets or prerendered pages. |
| **SolidStart** | Array order (onion) | Return a `Response` | After `await next()` | `event.locals` (typed); `getRequestEvent()` works inside | Docs: **not guaranteed on client navigations**, so don't use it for authorization |
| **Astro** | `sequence()` onion; integration pre/post | Return a `Response` | Full response, including body rewrite | `locals` (`App.Locals`; edge mode JSON-serializes it) | On-demand requests. **Runs at build for prerendered pages.** Attempts 404/500 pages. |

**Behavioral differences that matter:**
- **Navigation coverage:** in Void, every client navigation is a server request, so global auth middleware reliably guards navigations. The exceptions are prefetch-cache hits (default 30 s) and static page data. React Router covers navigations only when a server loader runs, SolidStart explicitly doesn't guarantee coverage, and Next.js covers them through Proxy on RSC fetches.
- **Middleware around the rendered page:** only Void (per-route `defineHandler(mw, loader)`) and React Router (route middleware on document requests) let route-scoped middleware see the final HTML/JSON page response. Void tests show `etag()` on pages returning 304.
- **Post-processing power:** Void (Hono), Astro, SolidStart and TanStack Start can replace the response body. React Router is headers-only, Next.js can't post-process, and Nuxt needs hooks.
- **Ordering model:** Void orders by numeric filename prefix. SvelteKit and Astro use explicit `sequence()`, React Router uses route nesting, and TanStack Start uses a dependency graph. Void can't express "only under `/admin/*`" except by branching on the path, which React Router's docs warn is bypassable through encoding tricks, or by attaching per-route middleware to every handler.
- **Typing:** Void's global augmentation means `c.get('user')` is typed everywhere whether or not the setter ran. TanStack Start's chain inference catches that at compile time.

**Void gap:** partial. Missing:
- directory-scoped (nested) middleware: Differentiator (React Router, TanStack Start);
- client-side middleware: Common (React Router, TanStack Start, Nuxt);
- per-chain inferred context: Differentiator (TanStack Start, React Router);
- server-function middleware: TanStack Start only, and moot until Void has RPC.

## Request-scoped context from deep code

| Framework | Getter(s) | Mechanism | Scope / limits |
|---|---|---|---|
| **Void** | **No generic getter.** AsyncLocalStorage-scoped helpers exist for specific resources: `getUser()`/`getSession()` (`void/auth`), `env` (`void/env`), resource modules (`void/db`, `void/kv`, …). Server-side `fetch` from `void/client` forwards `cookie`/`authorization` through an internal `requestContext` store `{ request, executionCtx }` (src: runtime/routing.ts, router/compile.ts `compileWorkerClient`). | ALS (internal) | The Hono `Context`, request, cookies and response headers are reachable only through `c` passed down by hand. |
| **Next.js** | `cookies()`, `headers()`, `draftMode()`, `connection()`, `next/root-params` | ALS (async functions) | Anywhere in the server render path. Not inside `use cache` [CC]. `cookies().set` only in actions and Route Handlers. |
| **React Router** | none (`request`/`context` args). Docs say `AsyncLocalStorage` works alongside, recommended for RSC. | — | — |
| **TanStack Start** | `getRequest()`, `getRequestHeader()`, `getCookie/setCookie`, `setResponseHeader/Status` | ALS | Server functions, middleware, server routes. Loaders are isomorphic, so they have no request. |
| **Nuxt** | `useRequestEvent()`, `useRequestHeaders()`, `useRequestURL()`, `useCookie()`, `useResponseHeader()` | unctx transform; native ALS via `experimental.asyncContext` (**exp.**, Node/Bun) | Nuxt app context. Server handlers take `event` explicitly. |
| **SvelteKit** | `getRequestEvent()` (`$app/server`) | ALS (Cloudflare needs `nodejs_als`) | Loads, actions, endpoints, hooks, remote fns. Unavailable after the response and in `init`. |
| **SolidStart** | `getRequestEvent()` (`solid-js/web`), plus argument-free helpers in `@solidjs/start/http` | ALS | SSR, API, middleware, queries, actions. Returns `undefined` outside a request. |
| **Astro** | none (`Astro`/`context` passed) | — | — |

**Behavioral differences that matter:** Void already runs every request inside ALS stores, and its own resource modules depend on them, but a user-level helper such as `getOrgId()` still has to accept `c`. Next.js, TanStack Start, SvelteKit and SolidStart let a deep helper read cookies or set response headers without plumbing.

**Void gap:** partial. Common (5: Next.js, TanStack Start, Nuxt, SvelteKit, SolidStart). Design note: the store exists (`requestContext`, ALS on all targets). Exposing `getContext()`/`getRequest()` plus cookie and response-header setters is mostly API surface. Response mutation must respect when the page response is built, since pages read `c.res.headers` at render time.

## Streaming responses & SSE

| Framework | Raw streaming | SSE server helper | SSE / stream client helper | Streaming RPC |
|---|---|---|---|---|
| **Void** | Hono `stream()`, `new Response(ReadableStream)` | **`void/sse` `eventStream(start, { signal, keepAlive })`.** Sets `Content-Type: text/event-stream; charset=utf-8`, `Cache-Control: no-cache, no-transform`, `X-Accel-Buffering: no`. `send({ id, event, retry, data })` takes JSON or a string; `comment()`, `closed`. Keepalive defaults to 15 s (`false` or `{ intervalMs, comment }` to change). Writing after close throws `SseStreamClosedError`. Also `getLastEventId(request)`, `formatSse/formatSseText`. | **`connectEventStream<EventMap>(url, { withCredentials, parse })`** gives typed `.on(event, cb)` and wraps EventSource (no custom headers or body). Also typed `fetchStream()` from `void/client`. | n/a (`void/live` handles pub/sub; out of scope) |
| **Next.js** | `ReadableStream` in Route Handlers; streaming guide | none (web streams work; unverified) | none | Server Functions (no stream helper) |
| **React Router** | Any `Response` from a resource route | none | none | `data()` promises streamed (Turbo Stream) |
| **TanStack Start** | `Response` | none | none | Server fns return typed `ReadableStream` / async generators (React only) |
| **Nuxt** | Return a `ReadableStream`/Node stream (labelled exp.) | not documented (h3 `createEventStream`; unverified) | Recipe: `$fetch(url, { method: 'POST', responseType: 'stream' })` | — |
| **SvelteKit** | `new Response(readable)`; docs warn about buffering platforms | none | none | Remote `query.live` (**exp.**) |
| **SolidStart** | `Response` (inferred) | none | none | Server fns return `ReadableStream` (Seroval) |
| **Astro** | `Response` (inferred) | none | none | — |

**Behavioral differences that matter:** platform buffering is handled ad hoc elsewhere. SvelteKit's adapter-bun sets `X-Accel-Buffering: no` and disables idle timeout for `text/event-stream`. Void sets these per response for every runtime.

**Void gap:** none. Void is unique here.

## Work after the response

| Framework | API | Callable from | Runtime coverage | Notes |
|---|---|---|---|---|
| **Void** | **none documented.** `c.executionCtx.waitUntil()` (Hono) is reachable on the Cloudflare target only. | anywhere with `c` | **Cloudflare only.** On Node/Bun/Deno, `executionCtx` isn't passed to `app.fetch` (src: runtime/routing.ts `nodeTarget`), so Hono's getter has nothing to return. | Internal ISR already uses `ctx.waitUntil`. The internal ALS store carries `executionCtx`. |
| **Next.js** | **`after(cb)`** (stable since 15.1); Proxy `event.waitUntil` | Server Components (incl. `generateMetadata`), Server Functions, Route Handlers, Proxy | Node, self-host (drains on SIGTERM) and serverless (host supplies `waitUntil`) | Runs even after errors, `notFound()` or `redirect()`. Static pages run it at build/revalidate. Bounded by `maxDuration`. `cookies()`/`headers()` throw inside the callback in Server Components. |
| **React Router** | none (Cloudflare example puts `ctx` into router context) | — | CF only | — |
| **TanStack Start** | not documented | — | — | — |
| **Nuxt** | **`event.waitUntil(promise)`** | Handlers using the Nitro/h3 event (not the portable `RequestEvent`) | Platform-native where available | — |
| **SvelteKit** | none. Platform options: `import { waitUntil } from 'cloudflare:workers'`, Vercel `@vercel/functions`, Node/Bun `sveltekit:shutdown` process event. | — | per platform | — |
| **SolidStart** | none for handlers (Nitro tasks only) | — | — | — |
| **Astro** | Adapter-level `app.render(req, { waitUntil })` for cache providers; Cloudflare `Astro.locals.cfContext.waitUntil()` | — | per adapter | — |

**Void gap:** partial. On Cloudflare Void matches React Router, SvelteKit and Astro, but this is undocumented. It lacks a portable API, which is a Differentiator (Next.js, Nuxt). Design: `after(fn)` or `waitUntil(p)` from `void`, resolved through the existing ALS store. Node/Bun/Deno need a pending-promise set drained on shutdown, like Next.js's self-host drain.

## Server-only code boundaries & env leakage

| Framework | File/dir convention | Marker | Enforcement | Env var protection | Other |
|---|---|---|---|---|---|
| **Void** | `.server.ts` page companions are server-only **by convention** (docs only show `import type { Props } from './x.server'`); **no check** on value imports (not found in packages/void/src). `routes/` and `middleware/` never enter the client graph. | none | Client-environment resolve rules (plugin-client-stubs.ts): **`void/live`, `void/durable` → build error**; `virtual:void-routes` → error; `void/sandbox`, `void/email` → throw at call time; **`void/db`, `void/kv`, `void/ai`, `void/queues`, `void/storage`, `void/isr` → silent no-op stubs**. | Reading a non-`VITE_` key of `void/env` in client code **fails the client build, per key** (plugin-env-client-guard.ts). `VITE_*` folded at build. `env.ts` `defineEnv` schema validated at startup. Production builds reject `worker.vars` declared as server keys. | — |
| **Next.js** | `'use client'` / `'use server'` | **`server-only` / `client-only`** packages | Build error | Non-`NEXT_PUBLIC_` vars become `''` in client bundles (silent) | `next/headers` and `next/root-params` are implicitly server-only; `experimental.taint`; `serverExternalPackages` |
| **React Router** | **`*.server.*` files and `.server/` dirs fail the build** if client-reachable; `*.client.*` excluded from server | RSC mode: `server-only` | Build error | Vite `VITE_` | Server exports (`loader`, `action`, `middleware`, `headers`) tree-shaken from client |
| **TanStack Start** | `**/*.server.*` denied in client; `**/*.client.*` denied in server | `@tanstack/react-start/server-only` / `client-only` | **Import protection:** dev mock + warning, build error checked after tree-shaking. Options: `behavior`, `include/exclude`, `ignoreImporters`, `maxTraceDepth`, `onViolation`. Full import trace with code frame. | `VITE_`/`PUBLIC_`; per-request `process.env` | `createServerOnlyFn` / `createClientOnlyFn` / `createIsomorphicFn` |
| **Nuxt** | `app/` and `server/` are separate bundles; `shared/` may import neither | `nuxt/server`, `#server` | Build error when imported from Vue components, plugins or `shared/` | Private `runtimeConfig` keys exist only on the server | `.server.vue` components/pages; `import.meta.server/client` DCE; separate tsconfigs |
| **SvelteKit** | **Any `server` filename segment or `server/` dir** (v3) | `$app/server`, `$app/env/private` | Build error with the import chain, even for unused re-exports and dynamic `import()`; `import type` allowed | `src/env.ts` `defineEnvVars` (`public`, `static`, `schema`), validated at build **and** startup | Packages opt in through `import '$app/server'` |
| **SolidStart** | `"use server"` | **`server-only` / `client-only`** | Dev or build error | `env:server` (fails if client-imported), `env:client`, `env:server/runtime` | — |
| **Astro** | By construction: frontmatter, endpoints, middleware and actions never ship | none | Some modules throw (`ServerOnlyModule`) | `PUBLIC_`; `astro:env` `context: 'server'`, `access: 'secret'` | — |

**Behavioral differences that matter:**
- In Void the `.server.ts` file is *the* recommended home for loaders and DB code, and it also exports the `Props` type that components import. A single `import { Props }` written without `type`, or a shared helper imported from it, ships server code with no warning. React Router, TanStack Start and SvelteKit make exactly this case a build error.
- Void's silent `{}` stubs for `void/db`, `void/kv` and friends turn a mistaken client import into a runtime `undefined` access rather than a build error. This is inconsistent with `void/live` and `void/durable`.
- Void's env guard is finer-grained than most, working per key rather than per module. Only SvelteKit's schema matches it on validation.

**Void gap:** partial; Table stakes (6). Design: deny `*.server.*` (and optionally `server/` dirs) in the client Vite environment with an import trace; allow `import type`; add a `void/server-only` marker; make the silent resource stubs build errors. Applies to all four adapters, including `.vue`/`.svelte` script blocks.

## Custom server entry / request pipeline control

| Framework | User-owned entry | Stage control | Interop / mounting |
|---|---|---|---|
| **Void** | **none.** The Hono app is generated (`virtual:void-routes`; client import refused). Custom SSR (`src/main.ssr.ts` `defineRender`) only replaces *page rendering* for unmatched non-API requests. `auxiliaryWorkers` adds separate Workers. | Fixed order (see Middleware). User middleware **cannot run before** config redirects/rewrites, header rules or Void auth, and cannot wrap the Worker `fetch` (for tracing or to inject `ctx`). | Native Hono for middleware and helpers. Mounting an external Hono app at a prefix requires a catch-all route that calls `subApp.fetch(c.req.raw)`, with no prefix stripping (not documented). |
| **Next.js** | Custom server (Node; incompatible with `standalone`); adapters API | Proxy runs after config headers/redirects | — |
| **React Router** | `createRequestHandler` + adapters (`@react-router/express`, cloudflare, architect) with `getLoadContext`. `entry.server.tsx`: default `handleRequest`, `handleDataRequest`, `handleError`, `streamTimeout`. `@react-router/serve` is zero-config. | Full (you own the server) | Express ecosystem |
| **TanStack Start** | `src/server.ts` `createServerEntry({ fetch })`, `createStartHandler`, `handler.fetch(request, { context })` with typed `requestContext`; `src/start.ts` | Full | Any fetch-handler code |
| **Nuxt** | No entry file. Nitro server plugins with runtime hooks `request`/`response`/`error`; renderer hooks `render:html`/`render:response`; `serverHandlers` | Hooks only | `nitro/h3`, `fromNodeMiddleware` (discouraged) |
| **SvelteKit** | `handle` is the first stage and can bypass routing; `init()`; adapter-node `handler.js` mounts into Express/Polka | Good | Connect middleware via adapter-node or Vite plugin (dev) |
| **SolidStart** | Server entry is an H3 app (`createHandler`); Nitro `server/routes` alongside; `decorateHandler/decorateMiddleware` (**exp.**) | Good | H3 / Nitro |
| **Astro** | **`src/fetch.ts`** (stable since 7.0; `fetchFile` config) composes `astro/fetch` stages: `trailingSlash`, `redirects`, `sessions`, `actions`, `middleware`, `pages`, `notFound` (7.4), `i18n`, `cache`. Or a Hono app via `astro/hono`. | **Full, per stage** | Hono |

**Behavioral differences that matter:**
- Astro 7 and TanStack Start let you reorder or replace the framework's own stages; Void's are hard-coded.
- Concrete Void consequences:
  - auth or rate-limit middleware can't run before config redirects;
  - there's no single place to start a trace span around the whole request;
  - Void's built-in auth middleware always runs before yours.

**Void gap:** partial, Table stakes (6 offer a user-owned entry or first-stage hook; Nuxt has hooks only). Design: an optional `src/server.ts` that receives the generated app or its stages, much like Astro's `src/fetch.ts` but Hono-native. Void is well placed because it already composes stages as Hono middleware.

## CORS, proxy and built-in security helpers

| Framework | CORS | External proxy | Built-in gate | Other |
|---|---|---|---|---|
| **Void** | `hono/cors` (documented), any `@hono/*` | **none** (`c.rewrite` is internal-only and throws on external URLs). Hono's `hono/proxy` may work (Hono API; unverified in Void). | **`basicAuth({ username, password, realm = 'Restricted', message })`**: values or callbacks; an empty password throws; `/__void/*` exempt; 401 with `Cache-Control: no-store`. | `routing.headers` rules; dev `X-Void-Routing` header; `X-Void-No-Match` on unmatched; `void/log` JSON logger |
| **Next.js** | none (config `headers`, Proxy) | **config `rewrites()` to external URLs** | — | BFF guide |
| **React Router** | none | none | — | CSP nonce plumbing |
| **TanStack Start** | none | none | — | — |
| **Nuxt** | **`cors` route rule, `handleCors(event)`** | **`proxy` route rule, `proxyRequest`** | `basicAuth` route rule removed in Nitro v3 (**Nuxt 5 change**) | — |
| **SvelteKit** | none (Vite dev only) | none (`handleFetch` rewrites server-side `fetch`) | — | `csrf.trustedOrigins` |
| **SolidStart** | Recipe (middleware) | none | — | — |
| **Astro** | none | none | — | `security.checkOrigin`, `allowedDomains`, CSP, body-size limits |

**Void gap:** external proxying only (Differentiator: Next.js, Nuxt). Void is ahead on CORS and basic auth through Hono.
