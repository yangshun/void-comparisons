# 5. Caching & revalidation

**Versions:** Void 1.6.2 · Next.js 16.4 (App Router) · React Router 8 (framework mode) · TanStack Start 1.169 (React) · Nuxt 5.0 pre-release (4.x is stable) · SvelteKit 3.1 · SolidStart 2.0 · Astro 7.4

**Markers:** [exp] experimental, unstable or canary · [CC] Next.js with Cache Components on (the create-next-app default) · [prev] Next.js's pre-16 caching model, still documented · (unverified) not confirmed in docs or source

**Paths:** Void file paths are in the `voidzero-dev/void` repo. Short paths such as `pages/scan.ts` are under `packages/void/src/`; paths that start with a package name, such as `react/src/…`, are under `packages/`.

## At a glance

- **Void has a real built-in page cache (ISR), but on Cloudflare only.** It is a two-level store: the per-colo Cache API (L1) plus KV (L2, global). The managed Void platform uses R2 and its edge, purged through a proxy. On `target: "node" | "bun" | "deno"` it is ignored. A build warning fires only when `routing.revalidate` is set (`packages/void/src/index.ts:835`); page `revalidate` exports are dropped without a word. Next.js, Nuxt and Astro each have a server HTML cache that works on Node.
- **Void's cache is the most privacy-conservative in the set, and that is its biggest strength.**
  - Bypass: any `Cookie`, `Authorization`, `Cf-Access-Jwt-Assertion`, `Range` or `Accept: text/event-stream` request skips the cache.
  - Refusal to store: any `Set-Cookie`, `Cache-Control: private|no-store|no-cache`, or `Vary` other than `X-VoidPages`.
  - Eviction: a page that later turns private is removed from the cache.
  - Query strings: excluded unless allowlisted. A request with unlisted params is served the cached page, or renders live *without storing*.
  - Compare Astro's memory provider, which ignores `Cookie` for `Vary`.
- **Invalidation is path-only.** `revalidate({ paths })` takes exact paths plus their query/rewrite variants; `{ all: true }` purges everything.
  - No tags (Next.js `cacheTag`/`revalidateTag`/`updateTag`; Astro `cache.invalidate({ tags })`).
  - No path patterns or subtrees (Next.js `revalidatePath(p, 'layout')`).
  - On self-hosted Cloudflare a purge clears KV but only **the current colo's** edge copies.
- **No data- or function-level cache at all.** Next.js has `use cache` with `cacheLife` profiles and `cacheTag`; Nuxt has Nitro `defineCachedFunction`. Request-scoped memoization exists in 5 of 7 frameworks (Next.js, Nuxt, SvelteKit, SolidStart, TanStack). Void has only Hono `cache()` per route and user-managed KV.
- **TTL model is simpler than the leaders'.** One TTL per response. The sources, most specific first: `x-revalidate` header, page export, config pattern, global. There is no bound on how long stale content may be served: stale entries live until revalidated, purged or redeployed. Next.js has `stale`/`revalidate`/`expire` plus named profiles; Astro has `maxAge` + `swr` seconds.
- **The client navigation cache is a prefetch cache only.** It is configurable `cacheFor` (default 30 s) with an SWR pair `[fresh, expire]`, which is good. Visited pages are not cached unless they arrived through a still-valid prefetch entry. Next.js, TanStack, SolidStart, Nuxt and SvelteKit all reuse visited route data in some form.
- **No draft/preview mode.** Next.js (`draftMode()`) and Nuxt (`usePreviewMode()`) have one in core; SvelteKit and Astro have one through their Vercel adapters.
- **Where Void is ahead:** deploy-time prerender seeds the cache, cache keys are deployment- and host-scoped, HTML and page-JSON are separate cached variants, `x-isr-cache` reports HIT/STALE/MISS, `revalidate()` works from cron and queue handlers, and the safety rules above.

## Gap list for this area

| Gap in Void | Who has it (mechanism, briefly) | Prevalence | Notes for design (constraints, dependencies, adapter impact) |
|---|---|---|---|
| Cross-request data/function cache | Next.js (`'use cache'`, `unstable_cache`), Nuxt (Nitro `defineCachedFunction`/`defineCachedHandler`); SvelteKit remote `prerender` [exp], TanStack Static Server Functions [exp] (build-time only) | Common (4; 2 stable at runtime) | Adapter-independent (server-only). Natural backend: the same KV + Cache API as ISR. Needs a key over serialized args, TTL, tags, and deployment scoping (Next.js's doesn't survive deploys except `unstable_cache`). This is what makes cookie-bypassed (logged-in) traffic cheap |
| Request-scoped memoization / dedupe | Next.js (`fetch` memo, `React.cache`), Nuxt (`useAsyncData` keys), SvelteKit (remote `query` [exp]), SolidStart (`query()`), TanStack (shared in-flight loaders) | Common (5) | Void has an internal AsyncLocalStorage `requestContext`, so a `cached(fn)` per request is cheap. Matters for middleware + loader + deferred resolvers hitting the same source |
| Visited-page client cache with stale/gc times and back/forward reuse | Next.js (Client Cache, `staleTimes` [exp]), TanStack (`staleTime`/`gcTime`), SolidStart (query cache), Nuxt (payload cache, `keepalive`), SvelteKit (dependency-based reuse) | Common (5) | The engine already has `cacheVisitedPageData` (unexposed). Expose it per adapter plugin and per link, reusing the `cacheFor` syntax. Prefetch entries already carry resolved deferred data (resolved inline), so a visited-page cache could reuse that shape |
| Server HTML cache on non-Cloudflare runtimes | Next.js (Node), Nuxt (any Nitro preset), Astro (`memoryCache` on any adapter) | Common (3) | Pairs with a provider interface (next row). Keep Void's safety rules (cookie bypass, `Set-Cookie`/private refusal) in the core, not the provider |
| Pluggable cache provider / handler | Next.js (`cacheHandlers`, `cacheHandler`), Astro (provider API), Nuxt (Nitro storage) | Common (3) | Two surfaces are needed: page cache (ISR) and data cache. Purge propagation (`refreshTags`-like) belongs in the interface |
| Bounded staleness (`expire` / swr window) | Next.js (`cacheLife.expire`, `expireTime`), Astro (`swr` seconds), TanStack via CDN `stale-while-revalidate=N`; Nuxt `staleMaxAge` (unverified) | Common (3–4) | KV writes could set `expirationTtl = ttl + maxStale`. Also fix the docs: `edge/prerendering.md` claims blocking after expiry |
| Draft / preview mode | Next.js (`draftMode()`), Nuxt (`usePreviewMode()`); SvelteKit and Astro via the Vercel adapter | Common (4; 2 in core) | Cookie bypass already exists. Add signed enable/disable, an `isDraft(c)` check, and a draft path for prerendered pages that are served as static files without the Worker |
| Tag-based invalidation | Next.js (`cacheTag` + `revalidateTag`/`updateTag`), Astro (`cache.set({tags})` + `cache.invalidate({tags})`, live-collection entries) | Differentiator (2) | Needs a tag index: a KV key per tag listing ISR keys, written at store time. Tags could come from a response header (`x-cache-tags`, like `x-revalidate`) and a loader helper. Cloudflare's Cache API can't purge by tag, so per-colo L1 copies must be deleted by key or carry short TTLs (the same problem the path purge has now) |
| Purge reaching all colos (self-hosted Cloudflare) | Astro CDN providers [exp] (platform tag purge); SvelteKit/Astro Vercel ISR (platform). Next.js purges only the local instance | Differentiator (2) | Void platform already purges the edge. Self-hosted would need the Cloudflare zone purge API (token, zone ID), or short L1 TTLs |
| Path-pattern / subtree purge | Next.js (`revalidatePath('/blog/[slug]', 'page')`, `'layout'` purges descendants) | Differentiator (1) | KV prefix listing is already used for variants; a pattern purge is a list + filter |
| Conditional requests (ETag / Last-Modified / 304) for pages | Next.js (`generateEtags`), Astro (`etag`/`lastModified` cache options + `setConditionalHeaders`) | Differentiator (2) | ISR client responses are `max-age=0, must-revalidate` with no validator, so every browser revalidation downloads the full page. Hashing the stored body at write time is cheap |
| Request-header `Vary` variants | Astro (memory provider: one variant per `Vary` request header); Nuxt `varies` (unverified) | Differentiator (1–2) | Today any `Vary` other than `X-VoidPages` disables caching (safe). Allowing an allowlist (e.g. `Accept-Language`) needs a bounded variant count, as the query allowlist has |
| Named cache-lifetime profiles | Next.js (`cacheLife` presets + custom, typed) | Differentiator (1) | Could map onto `routing.revalidate` values (`'hours'`) |
| Scoped client invalidation (by key/URL/filter) | SolidStart (`revalidate(key)`), TanStack (`invalidate({filter})`), SvelteKit (`invalidate(url\|predicate)`), Nuxt (`refreshNuxtData(keys)`) | Common (4) | Void has `flush(url)` for prefetch only, and every non-GET wipes the whole prefetch cache |

## Where Void is ahead

- **Zero-config edge ISR for every app shape**: Pages (React, Vue, Svelte, Solid), custom SSR, `routes/` GET handlers matching page patterns, and supported framework apps. Nothing to wire on Cloudflare; the platform handles managed deploys. Next.js needs a cache handler for multi-instance; TanStack and React Router delegate to the CDN; SvelteKit needs Vercel.
- **Privacy-safe by default.** Bypass on `Cookie`/`Authorization`/Access JWT/`Range`/SSE. Refusal to store `Set-Cookie`, `private|no-store|no-cache` and foreign `Vary`. **Automatic eviction** when a cached page later turns private. A policy-version stamp rejects entries written under older rules. Astro's memory provider ignores `Cookie` for `Vary`, and TanStack's docs warn about cross-tenant leaks with `public`.
- **Query-string handling that is safe on both axes.** An allowlist per pattern; unlisted params get the cached page or render live **without being stored** (no poisoning, no fan-out); a cap of 200 variants per path. Nuxt 5 strips the query before the handler runs.
- **Deployment- and host-scoped keys.** Cached HTML can never reference another deploy's hashed assets, and multi-domain apps don't share entries. Deploy-time prerender **seeds** the cache before traffic switches.
- **Per-response TTL override** via an `x-revalidate` header from any handler, at the top of a clear precedence chain (header → page → pattern → global).
- **Purge from cron and queue handlers** (host registry). `revalidate({ all: true })` covers whole-site purges.
- **Resilient revalidation.** A failed background render keeps the last good entry, and 404/410 evicts only after a 24 h grace.
- **HTML and page-JSON variants** are cached side by side (`Vary: X-VoidPages`), so client navigations to ISR pages hit the edge too. Nuxt's `_payload.json` is comparable; Next.js's RSC variants are more complex.
- **Prefetch cache with a per-link SWR window** (`cacheFor: [fresh, expire]`), single-use mode (`0`), awaitable `router.prefetch`, and `flush`/`flushAll`. It is more expressive than SolidStart's fixed 5 s or Next.js's 30 s minimum.
- **Observable.** `x-isr-cache: HIT|STALE|MISS` on responses (Astro has `X-Astro-Cache`; Next.js has none in the inventory).

## HTML / page cache

| Framework | Where it lives | Runtimes | Cache key | Query / cookies / headers | What bypasses it | Variants | Status |
|---|---|---|---|---|---|---|---|
| **Void** | L1 per-colo Cache API (`caches.default`) + L2 KV (`ISR_CACHE`, global, authoritative). Managed platform: R2 + edge via `__VOID_PROXY`. Deploys start empty (deployment ID in the key) | **Cloudflare only.** Not compiled into dev builds (`packages/void/src/plugin-routing.ts`) | `<proj>/isr/v3/<deploymentId>/<host>/<path>[#rw=<hash(original URL)>]`. **Host-scoped.** Rewrites add the original URL. Middleware `c.rewrite()` runs after lookup, so it doesn't vary the key. At most **200 variants per path** | Query **dropped** unless `routing.revalidateQueryAllowlist` (`{ '/search': ['q'], '*': [] }`; sorted). Unlisted params → served the cached page, or rendered live without storing. Responses with `Vary` other than `X-VoidPages` (incl. `Vary: *`) are not stored | Request: `Cookie` (**any** cookie), `Authorization`, `Cf-Access-Jwt-Assertion`, `Range`, `Accept: text/event-stream`, non-GET, `/api/*`. Response not stored: non-200, `Set-Cookie`, `Cache-Control: private\|no-store\|no-cache`, `x-revalidate: 0`. An existing entry is **deleted** when the page later returns one of these | HTML and Pages JSON (`X-VoidPages`) kept apart. JSON is served only from the per-colo edge cache; a colo that hasn't rendered the HTML renders JSON live | Stable |
| Next.js | Disk (self-host) or platform durable storage; in-memory LRU for `use cache` (`cacheMaxMemorySize`) | Node (Edge runtime: no ISR) | Build ID / `deploymentId` + path (+ params). Responses vary on `rsc`, `next-router-*`, `next-url`; `_rsc` hash as fallback | Reading `cookies()`/`headers()`/`searchParams` makes that subtree dynamic ([CC] it must sit behind Suspense), so caching follows **what the render reads** | Draft Mode cookie (`__prerender_bypass`); dynamic APIs | HTML + RSC payload + segment-prefetch files (`.segments/_tree.segment.rsc`) | Stable |
| React Router | **No server cache.** HTTP `Cache-Control` via the route `headers` export, for a CDN/browser | — | CDN-defined | — | — | `.data` URLs (`v8_trailingSlashAwareDataRequests` changed their shape) | — |
| TanStack | **No server cache.** CDN via `Cache-Control` (`headers` route option, `setResponseHeader(s)`, middleware) | — | CDN-defined | Docs warn: `public` on identity-dependent responses leaks across tenants | — | — | — |
| Nuxt | Nitro cache handlers wrapping matching routes; Netlify/Vercel native config via route rules | Any Nitro preset (`node-server` caches the full response). Not `@nuxt/vite-server` | Path only (Nuxt 5: **query stripped before the handler runs** unless `allowQuery: true \| string[]`) | `varies`, `getKey`, `shouldBypassCache` (Nitro, from memory, **unverified** in docs) | Not documented | HTML + `_payload.json` (written on first render; CDN-cacheable) | `routeRules` labelled "Experimental" |
| SvelteKit | **No framework store.** `adapter-vercel` ISR only | Vercel | Path + `allowQuery` (default: all ignored) | — | `__prerender_bypass` cookie / `x-prerender-revalidate` | — | Stable (adapter) |
| SolidStart | **None** (Nitro `routeRules` not mentioned in docs) | — | — | — | — | — | — |
| Astro | Pluggable provider (`cache: { provider }`): `memoryCache()` LRU in-process, or CDN providers [exp] | Any adapter; **on-demand pages and endpoints only**. Disabled in dev | Memory provider: URL with **sorted query**, tracking params removed (`exclude` defaults to `utm_*`, `fbclid`, `gclid`, …, `ref`; or `include`) + **a variant per `Vary` request header** | **`Cookie` is always ignored for Vary** (the author must opt out on personalized pages) | `Astro.cache.set(false)` | — | Stable since 7.0 (CDN providers exp) |

**Behavioral differences that matter:**
- Void decides cacheability from **request and response headers**. Next.js decides from **what the code reads**. Void's rule is safer by default but blunt: any analytics or consent cookie turns every request into a miss, and there is no cookie allowlist.
- Void's query handling ("unlisted → don't store") prevents both cache poisoning and unbounded fan-out. Nuxt 5 strips the query before the handler runs, so handlers can't read it. Astro keys on all non-tracking params.
- Void caches `routes/` GET handlers whose URL matches a page pattern or `routing.revalidate` pattern, as well as pages. Astro caches on-demand endpoints too. Next.js caches route handlers as static/ISR.
- The client-facing `Cache-Control` on ISR responses is `public, max-age=0, must-revalidate`. Pages have no ETag, so every browser revalidation downloads the full body.

**Void gap:** partial.
- No cache on Node/Bun/Deno targets.
- No `Vary`-based variants.
- No cookie allowlist ("ignore these cookies").
- No request coalescing on misses: concurrent misses each render.

## Time-based revalidation (TTL, SWR)

| Framework | TTL sources (precedence) | Stale-while-revalidate semantics | Max staleness | First request / miss | Notes |
|---|---|---|---|---|---|
| **Void** | **Most specific wins:** (1) response header `x-revalidate: <s>` (`0` = don't cache), (2) page `export const revalidate = n` (non-negative integer literal), (3) `routing.revalidate` pattern map (first match wins; `*` crosses `/`), (4) global number or `'*'`. Prerendered pages default to `31536000` (1 year, effectively "until deploy", the max). Kill switch `routing.isr: false` | Stale hit → served (`x-isr-cache: STALE`, edge copy `s-maxage=min(10, ttl)`) while a background render runs (`ctx.waitUntil`). A failed re-render keeps the last good entry; 404/410 evicts it after a 24 h grace | **Unbounded.** KV entries carry no expiration (`packages/isr/src/runtime.ts writeIsrCache`). `docs/guide/edge/prerendering.md` says an expired prerendered page makes the next request wait, which conflicts with the code | Miss → blocking render, stored in the background. No coalescing: every stale hit can trigger a re-render | Header-level override per response is unusual and useful (route handlers too) |
| Next.js | [CC] `cacheLife(profile \| {stale, revalidate, expire})` per cached scope. **An explicit outer `cacheLife` wins.** Otherwise the outer scope uses `default` but is shortened by inner scopes. [prev] `export const revalidate`, `fetch(..., {next:{revalidate}})`, `unstable_cache({revalidate})`, and the **lowest value in the route wins** | After `revalidate`, serve stale and regenerate in the background | **`expire`**: after it, with no traffic, the next request blocks. `expireTime` sets CDN SWR | Known params: prerendered. [CC] unknown params: App Shell first, then the cached full page | Presets (`stale`/`revalidate`/`expire`): `seconds` 30 s/1 s/1 min · `minutes` 5 min/1 min/1 h · `hours` 5 min/1 h/1 d · `days` 5 min/1 d/1 wk · `weeks` 5 min/1 wk/30 d · `max` 5 min/30 d/1 yr · `default` 5 min/15 min/never. Custom profiles in config, typed. Prerender thresholds (`revalidate:0` or `expire < 5 min` → dynamic hole) |
| React Router | Not built in (HTTP headers only) | CDN | CDN | — | — |
| TanStack | `Cache-Control: public, max-age, s-maxage, stale-while-revalidate` from the `headers` route option. Docs say regeneration is the CDN's job | CDN | `stale-while-revalidate=N` | CDN | "A `Cache-Control` header alone does not guarantee the same regeneration … on every host" |
| Nuxt | Route rules `swr: n \| true`, `isr: n \| true` (CDN on Netlify/Vercel), `cache: { maxAge, swr, … }`. Inline `defineRouteRules` [exp] | Serve stale, regenerate in the background | `swr: true` sends SWR with no max-age; Nitro `staleMaxAge` (**unverified**) | Blocking render | `isr: true` = until next deploy |
| SvelteKit | Vercel only: `export const config = { isr: { expiration, bypassToken?, allowQuery? } }` (cascades like other page options; universal `config` wins in v3) | Vercel ISR | `expiration` (s or `false`) | Vercel | Ignored on prerendered routes |
| SolidStart | Not found | — | — | — | — |
| Astro | `routeRules: { '/products/[id]': { maxAge, swr, tags } }` (file-route syntax, no globs) merged with `Astro.cache.set({...})`. **Last write wins** for `maxAge`/`swr`/`etag`; `lastModified` takes the newest; tags accumulate across middleware, layouts, loaders and the page | Runtime providers revalidate in the background (`ctx.waitUntil`); `X-Astro-Cache: HIT\|MISS\|STALE` | `swr` seconds | Miss renders | Vercel adapter `isr: true \| { expiration, bypassToken, exclude }`; Netlify `cacheOnDemandPages`. Prerendered output refreshes only on rebuild |

**Behavioral differences that matter:**
- Void's precedence runs **response → page → config**, so code can always override config. Next.js composes TTLs **across data sources** inside one page (shortest wins). Void has one TTL per page response, because it caches pages, not data.
- Void can serve a stale page indefinitely to low-traffic paths, since a revalidation only starts on a hit. Next.js's `expire` and Astro's `swr` window cap staleness.
- No named profiles in Void (`routing.revalidate` numbers only).

**Void gap:** partial.
- No `expire` / max-stale bound.
- No named lifetime profiles.
- No coalescing of concurrent background revalidations.
- Doc/code mismatch on the expiry of prerendered entries.

## On-demand invalidation

| Framework | By path | By tag | By key / other | Where callable | Propagation | Dev behavior |
|---|---|---|---|---|---|---|
| **Void** | `revalidate({ paths: [...] })` from `void/isr`: **exact pathnames** (plus each path's rewrite/query variants, across every host registered for the deployment). Purge the **destination** path for rewrites | **None** (signature is `{ paths?, all? }`) | `revalidate({ all: true })`; CLI `void project purge-cache` (Void platform) | Any server code: route handlers, actions, **cron and queue handlers** (a host registry lets purges run without a request host) | Self-hosted Cloudflare: KV (global) + **current colo's** Cache API only; other colos serve edge copies until their TTL. Managed platform: proxy → API deletes from R2 + purges edge | **No-op** (client stub; ISR not compiled in dev) |
| Next.js | `revalidatePath(path, 'page' \| 'layout')`: literal or pattern (`/product/[slug]` needs a type); `'layout'` purges nested pages; `revalidatePath('/', 'layout')` purges everything incl. the Client Cache. Max 1024 chars, destination path | `revalidateTag(tag, profile \| {expire})` (stale-while-revalidate; one-arg form deprecated = `{expire:0}`); **`updateTag(tag)`** (Server Actions only, immediate expiry, read-your-writes); tags via `cacheTag()` / `fetch next.tags` (256 chars, 128 per call) | `refresh()` (actions), `router.refresh()` | Server Functions, Route Handlers (not Proxy/client) | **Local instance only** unless the cache handler implements `refreshTags()`; **does not purge CDNs** | `use cache` works in dev (HMR hash in key) |
| React Router | — (no server cache) | — | Client: re-running loaders (`useRevalidator`, `shouldRevalidate`) | — | — | — |
| TanStack | Doc pattern: a secret-protected POST server route that calls your CDN's purge API | — | Client: `router.invalidate({ filter, sync, forcePending })`, `router.clearCache` | — | CDN-defined | — |
| Nuxt | **Not found in docs** | **Not found** | Client: `refreshNuxtData`, `clearNuxtData` | — | — | — |
| SvelteKit | Vercel only: `GET`/`HEAD` with `x-prerender-revalidate: <bypassToken>` (≥ 32 chars, fixed at build) | — | Client: `invalidate(url \| predicate)`, `refreshAll()` | Any HTTP client | Vercel platform | — |
| SolidStart | — (no server cache) | — | **Client** `revalidate(key \| key[], force?)`: prefix match on query keys (the query name works like a tag); `query.set/delete/clear`; actions target keys via `X-Revalidate` | — | — | — |
| Astro | `cache.invalidate({ path })`: **exact match only** | `cache.invalidate({ tags })`: purges any entry with any of the tags; live-collection entries can be passed directly | Vercel adapter bypass token | Endpoints, middleware, pages | Provider-dependent: memory = single instance; CDN providers [exp] purge platform tags (they auto-tag by path, `astro-path:{path}`); Vercel tag purge is soft (SWR) | API present but does nothing in dev |

**Behavioral differences that matter:**
- Content-driven sites invalidate by **entity**, not URL: "post 42 changed" should clear the post page, every list page and the feed. Next.js and Astro do this with tags. In Void the user must compute every URL.
- Void has no read-your-own-writes primitive for cached pages (Next.js `updateTag`). After `revalidate()`, the next GET of that path renders fresh (KV entry deleted), and the action response itself is uncached, so the current page is fine. Other colos may still show stale copies on self-hosted Cloudflare.
- Void's purge from cron/queue handlers without a request is a real strength. Next.js's `revalidateTag` can't run in Proxy.

**Void gap:** partial.
- Tag invalidation is missing.
- No path patterns or subtree purge.
- Self-hosted purge doesn't reach other colos.
- No immediate-expiry vs SWR choice on invalidation (Next.js `updateTag` vs `revalidateTag(…,'max')`).

## Data-level / function-level caching

| Framework | Cross-request server data cache | Request-scoped memoization | Lifetimes / profiles | Keys & tags | Status |
|---|---|---|---|---|---|
| **Void** | **None.** Workarounds: Hono `cache()` middleware per route (Cloudflare Cache API; one response per URL; skips `Authorization` **but not cookies**, as the docs warn), or user-managed `void/kv` | **None** server-side (one loader per request; deferred groups share one resolver call) | — | — | — |
| Next.js | **`'use cache'`** (file/component/function; async). Key = build ID + function ID + serialized args (**closures bound as args**) + root params read. In-memory LRU by default. `'use cache: remote'` (durable shared handler; not across deploys). `'use cache: private'` (may read cookies/headers; per-request + **browser** cache only). [prev] `fetch` cache (`force-cache`, `next.revalidate`, `next.tags`), `unstable_cache(fn, keyParts, {tags, revalidate})` (the only one that **persists across deployments**) | `fetch` GET memoized per render pass; `React.cache()`; `use cache: private` per request | `cacheLife` presets + custom profiles (typed) | `cacheTag()`; soft tags derived from paths | Stable (CC since 16.0) |
| React Router | None (docs recommend backend caches) | None documented | — | — | — |
| TanStack | None at runtime. **Static Server Functions [exp]**: `staticFunctionMiddleware` (last) on a GET server function writes its result as static JSON during prerender (key = function ID + payload hash), embeds it in HTML, and later client calls fetch the JSON | In-flight loader work shared between preload and navigation (same match); RSC `React.cache` [exp] | — | — | Exp |
| Nuxt | **`defineCachedFunction()` / `defineCachedHandler()`** from `nitro/cache` (not portable to `@nuxt/vite-server`). Options not in the docs clone (`maxAge`, `swr`, `getKey`, `varies`, … **unverified**) | `useAsyncData`/`useFetch` keys dedupe and share refs in one SSR pass (`dedupe: 'cancel' \| 'defer'`); `callOnce`; `sharedPrerenderData` | Nitro options (unverified) | Key-based | Stable (Nitro) |
| SvelteKit | Remote `prerender` functions [exp]: build-time results served from CDN and the browser Cache API until the next deploy | Remote `query` [exp]: same args run once per request (devalue-serialized, order-insensitive key) | — | Arg-derived | Exp |
| SolidStart | None | `query(fn, name)`: per request on the server, keyed by name + args | Fixed constants (5 s preload reuse, 180 s GC; not options) | Name + args | Stable |
| Astro | None (content-layer build cache, image/font caches only) | — | — | — | — |

**Behavioral differences that matter:**
- With no data cache, a slow upstream shared by several pages, such as a CMS "site settings" call in middleware `shared`, is fetched on **every** uncached request. In Void that is every request carrying a cookie. Next.js and Nuxt cache it once per TTL.
- Void's cookie bypass makes page-level ISR useless for logged-in traffic. A data cache (`use cache`-style, keyed by args) is the usual complement for personalized pages, and Void has none.

**Void gap:** missing.
- No cached server function or `use cache` equivalent.
- No request-scoped memoization helper.
- No lifetimes or tags at the data level.

## Client navigation cache

| Framework | What is cached | Freshness / retention defaults | Back / forward | Prefetch cache | Invalidation |
|---|---|---|---|---|---|
| **Void** | **Prefetch cache only** (page JSON + deferred resolved inline), keyed `METHOD:url`. Static builds read `/_void/pages/<path>.json` and put it into the same cache. An internal `cacheVisitedPageData` option exists but is **not exposed** by any adapter plugin | `cacheFor` per link, `router.prefetch`, or app-wide `prefetch.cacheFor` (default **`'30s'`**). Number (ms), `'30s'`-style string (ms/s/m/h/d), or **`[fresh, expire]`**: a stale entry is used immediately and refetched in the background. `0` = single use. Entries are **not consumed** by a visit, so they are reused until expiry | Re-fetches, **unless** a still-valid prefetch entry exists for that URL | As above. Concurrent prefetches share one promise | `router.flush(url)`, `router.flushAll()`, `router.refresh()`. **Any non-GET visit flushes everything** |
| Next.js | Router **Client Cache**: RSC payloads per segment. Layouts/loading reused; shared layouts never refetched | `stale` from the shortest `cacheLife.stale` among the route's entries (sent as `x-nextjs-stale-time`, **min 30 s**). `staleTimes` [exp]: `dynamic` 0 s, `static` 300 s | **Reused** | App Shell per route (Partial Prefetching) + per-link full prefetch; invalidations silently refresh prefetches; `prefetch(href, {onInvalidate})` | `router.refresh()`, `revalidatePath('/', 'layout')`, `revalidateTag`/`updateTag` from actions |
| React Router | **None** (all active loaders revalidate on every navigation in SSR mode) | — | Re-fetch; `unstable_fetch` + `cache: 'force-cache'` on POP [exp] | `<link rel=prefetch>` (browser HTTP cache) | `shouldRevalidate`, `useRevalidator`, call-site `defaultShouldRevalidate` |
| TanStack | Router SWR cache of loader data, keyed by parsed pathname + `loaderDeps` | `staleTime` **0** (shows cached data, reloads in the background), `gcTime` **5 min**, `preloadStaleTime` **30 s**, `preloadGcTime` 5 min, `staleReloadMode: 'background' \| 'blocking'`, `shouldReload` | Cached data shown; reloaded in the background if stale | Joins in-flight loaders; speculative lane never promoted | `router.invalidate({ filter, sync, forcePending })`, `router.clearCache({ filter })` |
| Nuxt | Payload-level: prefetched or extracted `_payload.json` → `nuxtApp.static.data`; default `getCachedData` reuses it (prerendered + ISR/SWR routes only) | No stale time. `purgeCachedData` (on) clears caches on navigation. Custom `getCachedData(key, nuxtApp, {cause})` for time-based caching. `<KeepAlive>` (`keepalive`) | Refetches unless `keepalive` or a custom `getCachedData` | NuxtLink prefetch (visibility/interaction) fetches chunks + `_payload.json` | `refreshNuxtData`, `clearNuxtData`, `useNuxtData` |
| SvelteKit | `load` results kept **until their tracked dependencies change** ("conservative invalidation"); remote `query` instances while in use | No TTL | Re-runs loads except where dependencies are unchanged | Hover/tap preload results reused by the next navigation | `invalidate(url \| predicate)`, `refreshAll()`, `depends()` |
| SolidStart | Router `query` cache (module-level `Map`) | Preload reuse **5 s**, GC **180 s** (fixed constants) | **Reused without refetch** | Hover (~20 ms)/focus preload into the query cache | `revalidate(key \| key[])`, `query.set/delete/clear`, action `X-Revalidate` |
| Astro | None (browser HTTP cache only) | — | Browser | `<link rel=prefetch>` / `fetch()` of whole documents; depends on HTTP cache headers | — |

**Behavioral differences that matter:**
- Void's prefetch cache is more configurable than its peers'. Only Void lets you set an SWR `[fresh, expire]` pair per link; TanStack has separate options and SolidStart uses fixed constants. But Void treats a visit as "fetch again" unless a prefetch happened. Next.js, TanStack and SolidStart serve visited data on back/forward without a network round trip.
- Every non-GET visit in Void drops the entire prefetch cache. That is coarse but safe: there is no tag- or key-scoped client invalidation (Solid `revalidate(key)`, TanStack `invalidate({filter})`, SvelteKit `invalidate(url)`).

**Void gap:** partial.
- Visited-page cache with `staleTime`/`gcTime` is missing (the engine has an unexposed `cacheVisitedPageData`).
- No back/forward reuse without a prefetch.
- No scoped client invalidation.

## HTTP cache-header helpers

| Framework | Config-level rules | Per route / response | Auto-generated | Conditional requests | Typed helper |
|---|---|---|---|---|---|
| **Void** | `routing.headers`: pattern → `["Name: value"]`; all matches merge, **last match wins**. User `Cache-Control` overrides defaults. **Not applied to ISR cache hits.** Can't override `Cache-Control`/`Content-*` on hashed assets. Platform: `Set-Cookie` ignored, `Clear-Site-Data` restricted. Framework `_headers` files are read first | Hono `c.header()` in loaders and handlers (copied onto page responses, `packages/void/src/pages/protocol.ts pageResponseHeaders`); `x-revalidate` | Hashed `assets/*`: `public, max-age=31536000, immutable`. Other static files: `public, s-maxage=31536000, max-age=0, must-revalidate`. ISR client responses: `public, max-age=0, must-revalidate` + `x-isr-cache: HIT\|STALE\|MISS` | ETag/304 for static assets only; **none for pages** | None |
| Next.js | `headers()` in config (`source`, `has`/`missing`; later rules override) | `Response` headers in Route Handlers/Proxy | Static `s-maxage=31536000`; ISR `s-maxage=…, stale-while-revalidate=…`; dynamic `private, no-cache, no-store, …`; `/_next/static` immutable (not overridable) | `generateEtags` (on by default) | None (`cacheLife` drives headers) |
| React Router | — | `headers` export (`parentHeaders`, `loaderHeaders`, `actionHeaders`, `errorHeaders`); **only the deepest route's headers are sent** (merge by hand; `Set-Cookie` bubbles automatically); `entry.server` `responseHeaders`; middleware; `handleDataRequest` for `.data` | — | — | None |
| TanStack | — | Route `headers({ matches, match, params, loaderData })`; `setResponseHeader(s)`, `appendResponseHeader`; middleware after `next()` | — | ETag middleware example | None |
| Nuxt | `headers` route rule | `useResponseHeader(name)` (writable ref); `event.res.headers` | `swr`/`isr` emit cache headers; with `early404`, `cache.maxAge` also applies to 404s | — | None |
| SvelteKit | — | `setHeaders({...})` in load (once per header; no `set-cookie`); `handle` | — | adapter-node/bun ETags for static files | None; **dev-time validation** of `cache-control` directives |
| SolidStart | — | `<HttpHeader name value append>` (server only; removed on unmount during SSR); `GET(fn)` makes a server function HTTP-GET cacheable | — | — | None |
| Astro | — | `Astro.response.headers`; `cache.set({ maxAge, swr, etag, lastModified })` → provider emits headers | Hashed `_astro/` long-lived (Node/Cloudflare adapters) | `etag` / `lastModified` via `setConditionalHeaders` | `buildCacheControlDirectives`, `pathTag`, `normalizeTags` (provider utils) |

**Void gap:** partial.
- No conditional requests (ETag/Last-Modified/304) for SSR/ISR pages (Next.js, Astro).
- No typed cache-control builder (Astro only).
- No dev-time validation of `Cache-Control` (SvelteKit).

## Draft / preview mode

| Framework | API | Mechanism | Effect on caches |
|---|---|---|---|
| **Void** | **None.** The only implicit bypass is that any `Cookie`/`Authorization` request skips ISR | — | — |
| Next.js | `draftMode()` → `isEnabled`, `enable()`, `disable()` (enable/disable only in Route Handlers or Server Actions) | `__prerender_bypass` cookie, regenerated per build | `use cache` re-executes with no writes; fetch cache bypassed for reads and writes; `isEnabled` is readable inside cache scopes. Not available with static export |
| Nuxt | `usePreviewMode({ shouldEnable?, getState?, onEnable?, onDisable? })` → `{ enabled, state }` | Client-driven: `?preview=true`; `token` query → `state` | Calls `refreshNuxtData()` so preview content replaces static/extracted payloads. **Server SWR/ISR bypass not documented** |
| SvelteKit | Vercel only | `__prerender_bypass=<bypassToken>` cookie | Renders an ISR route at request time |
| Astro | Vercel adapter only | `__prerender_bypass` cookie = `bypassToken` | Vercel ISR bypass |
| React Router / TanStack / SolidStart | Not found | — | — |

**Void gap:** missing. Common (4 incl. adapter-level; 2 in core). Void's cookie bypass already gives "skip ISR". What's missing is a signed enable/disable endpoint helper, an `isDraft(c)` check for loaders, and a way to make prerendered and static pages render live in draft. Prerendered pages without a `.server.ts` are served as static files without the Worker in hybrid deploys (`docs/guide/ssg.md`), so draft would need to route those through the Worker.

## Cache providers / pluggability

| Framework | Pluggable? | Built-in backends | Multi-instance story |
|---|---|---|---|
| **Void** | **No.** Fixed per target | Cloudflare KV + Cache API (self-host); R2 + edge (Void platform); none on Node/Bun/Deno | Global KV + per-colo L1; purge reaches KV + the local colo only |
| Next.js | `cacheHandlers: { default, remote, <name> }` (`get`, `set`, `refreshTags`, `getExpiration`, `updateTags`; streamed values; soft tags) for `'use cache: <name>'`; singular `cacheHandler` for ISR / fetch / `unstable_cache` (`get`, `set`, `revalidateTag`, `resetRequestCache`) | In-memory LRU; disk for ISR | "Shared cache recommended". Tags propagate only via `refreshTags()` |
| Astro | Provider API: runtime `onRequest(ctx, next)` or CDN `setHeaders(options, request)`, plus `invalidate()`; `CacheProviderFactory(config)` | `memoryCache({ max: 1000, query })`; `cacheNetlify()`, `cacheVercel()`, `cacheCloudflare()` [exp] | CDN providers purge by platform tag |
| Nuxt | Nitro storage-backed cache (mount configurable; storage driver details **unverified** in docs); `isr` maps to Netlify/Vercel | Nitro default storage | Platform mapping |
| SvelteKit | Adapter (Vercel) | Vercel ISR | Platform |
| React Router / TanStack | CDN only (TanStack docs give Cloudflare/Netlify/Vercel header recipes) | — | CDN |
| SolidStart | — | — | — |

**Void gap:** partial. There is no provider interface, so Node/Bun/Deno deployments get no ISR, and nobody can plug in Redis or another CDN. Void's own two-level design (L1 edge + L2 global) is a good default to keep as the Cloudflare provider.
