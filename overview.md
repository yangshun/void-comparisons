# Void vs. the major metaframeworks: feature gap analysis

*Covers framework features only: routing, rendering, data, mutations, caching, server, errors, types, head/SEO, assets, build/deploy and dev tooling. Out of scope: auth, databases, KV/storage, queues, cron, email, realtime, i18n, AI, testing, and Void's mode as a deploy layer under other frameworks.*

This page compares **Void** (native "Void app" mode) with seven metaframeworks, area by area. The comparisons go down to individual props and options, and they compare behavior rather than API names. The goal is to find Void's feature gaps and inform its roadmap. Nothing here is scored or graded.

<!--AREA-GRID-->

## Versions compared

Each framework's docs were cloned from its GitHub repo between 2026-10-29 and 2026-11-04. Void was read from both its docs and its source. The commit column records exactly what was read.

| Framework | Version documented | Notes |
|---|---|---|
| Void | 1.5.0 | Docs plus `packages/` source |
| Next.js | 16.4 stable | App Router only; a few 16.5-canary items are flagged |
| React Router | 8.x | Framework mode only |
| TanStack Start | 1.169+ (first stable) | React flavor; gaps in the Solid flavor are noted |
| Nuxt | 5.0 **pre-release** (release est. Q4 2026) | Most APIs already shipped in 4.x; anything new in 5 is flagged |
| SvelteKit | 3.x (3.1.1) | Generated API types were checked as well as the docs |
| SolidStart | 2.0 | Its Nitro v3 deploy layer is still beta |
| Astro | 7.4 | |

| Framework | Repo and paths read | Commit (date) |
|---|---|---|
| Void | [voidzero-dev/void](https://github.com/voidzero-dev/void): `docs/`, `packages/` | [`65eb7f07f020fda6586dba4c2d2d03aaab000cc3`](https://github.com/voidzero-dev/void/commit/65eb7f07f020fda6586dba4c2d2d03aaab000cc3) (2026-11-04) |
| Next.js | [vercel/next.js](https://github.com/vercel/next.js): `docs/01-app/` | [`a47959503adac8080a8b9a35f79617740d97925f`](https://github.com/vercel/next.js/commit/a47959503adac8080a8b9a35f79617740d97925f) (2026-11-03) |
| React Router | [remix-run/react-router](https://github.com/remix-run/react-router): `docs/` | [`db80dda076ec9cdcefff480079252fe0c977710e`](https://github.com/remix-run/react-router/commit/db80dda076ec9cdcefff480079252fe0c977710e) (2026-11-02) |
| TanStack Start | [TanStack/router](https://github.com/TanStack/router): `docs/start/`, `docs/router/` | [`da8c28c498230a5730ce75b2693baeeb3ef68ac1`](https://github.com/TanStack/router/commit/da8c28c498230a5730ce75b2693baeeb3ef68ac1) (2026-11-03) |
| Nuxt | [nuxt/nuxt](https://github.com/nuxt/nuxt): `docs/` | [`9496b7e5fe75740a5f8ef9826a2918667e4b4a82`](https://github.com/nuxt/nuxt/commit/9496b7e5fe75740a5f8ef9826a2918667e4b4a82) (2026-11-03) |
| SvelteKit | [sveltejs/kit](https://github.com/sveltejs/kit): `documentation/docs/`, `packages/kit/types/` | [`fe4deb1b76d876bdca56db489388c98ed74973f5`](https://github.com/sveltejs/kit/commit/fe4deb1b76d876bdca56db489388c98ed74973f5) (2026-11-04) |
| SolidStart | [solidjs/solid-docs](https://github.com/solidjs/solid-docs): `src/routes/solid-start/`, `src/routes/solid-router/` | [`9a9d77a75642f6e2ab68d80b0081d45ad3424b13`](https://github.com/solidjs/solid-docs/commit/9a9d77a75642f6e2ab68d80b0081d45ad3424b13) (2026-10-29) |
| Astro | [withastro/docs](https://github.com/withastro/docs): `src/content/docs/en/` | [`c73a3bea5a635c1afce0f0516ff22ecb34a3d7d4`](https://github.com/withastro/docs/commit/c73a3bea5a635c1afce0f0516ff22ecb34a3d7d4) (2026-11-03) |

**To update this analysis later**, diff each repo from its recorded commit, limited to the paths above, and re-check only the areas those changes touch. For Void:

```bash
git -C void log --oneline 65eb7f07f020fda6586dba4c2d2d03aaab000cc3..HEAD -- docs packages
```

Then update the affected area pages and this table. The same command works for each framework repo with its own commit and paths.

## How to read the gap lists

- **Prevalence** counts how many of the 7 others have the capability:
  - **Table stakes**: 6–7 of the 7 others have it.
  - **Common**: 3–5 have it.
  - **Differentiator**: 1–2 have it.

  This is a count, not a priority. The area files mark experimental or canary features **[exp]**. A gap that only experimental features elsewhere fill is a weaker signal.
- **Checking.** Every claim that Void lacks something was checked against Void's source (`packages/`), not just its docs. The comparison step corrected the inventories where needed; each area file notes what changed.
- **Unverified items.** A few third-party details could not be checked against docs and are marked as unverified in the area files. Most are options of Nuxt's official modules (`@nuxt/image`, `@nuxt/scripts`, sitemap and og-image) and a few Nitro cache options.

---

## Void's design shapes both its gaps and its strengths

Three design decisions explain most of what follows:

1. **An Inertia-style page protocol.** Each page has *one* server-only `loader` in a `.server.ts` companion file. Every client navigation is one server request that returns a JSON page object, and actions re-run that loader in the same response.
   - **Benefits:** no loader waterfalls, predictable cost per navigation, and server middleware sees every navigation.
   - **Costs:** layouts can't load data, there are no client or isomorphic loaders, every query-string change refetches, and only the prefetch cache exists on the client.
2. **One API across four UI libraries** (React, Vue, Svelte, Solid). No other framework does this. It also means each new feature lands four times, and some features are uneven across adapters today: component streaming is React-only, and `preserveState` only works in Vue and Solid.
3. **Cloudflare first, with Hono as the server layer.** The benefits are workerd in dev, deploy-time prerendering into an edge page cache (ISR), and the whole Hono middleware ecosystem. The cost is portability: the page cache, the typed env schema and `waitUntil` are Cloudflare-only, and there are no Vercel or Netlify targets and no adapter API.

---

## What to work on first

The gaps cluster around a handful of foundations. Several of them change the **page-object protocol**: layout data, richer serialization, error page objects, action results and status codes. **Recommendation: design them together as one protocol revision ("page protocol v2")** rather than migrating the client engine, the prefetch cache, the static `/_void/pages/*.json` files and all four adapters several times over.

The clusters below are in suggested order. The reasoning is in the last column of each.

### A. Correctness and safety (no dependencies; do first)

| Gap | Prevalence | Why it matters now | Area |
|---|---|---|---|
| **Build-time enforcement of server-only code.** A value import from a `.server.ts` companion into a component ships to the client. There is no `server-only` marker, and the client stubs for `void/db`, `kv`, `ai`, `queues`, `storage` and `isr` are silent no-ops. | Table stakes (6) | `.server.ts` holds loaders and DB access *and* exports the `Props` type, so a mistaken value import leaks server code. The fix: a client-environment resolve check with an import trace; allow `import type`; turn the silent stubs into errors. | [6](areas/06-server-api.md) |

### B. Page protocol v2 (the foundation for most user-facing gaps)

| Gap | Prevalence | Notes | Area |
|---|---|---|---|
| **Error and 404 UI rendered by the app**, kept inside layouts. Today any loader, action or render error is a whole-document static 500 (`public/500.html` or a built-in page) with no app components. Client navigations that hit an error do a full page reload. | Table stakes (7) | The protocol needs an "error page object" (status, message, data) that the client engine commits instead of setting `location.href`, plus an error/404 component convention in all 4 adapters. Includes throwable `notFound()` and `redirect()` (Common 5), per-segment boundaries (Common 4) and retry/reset (Common 4). | [7](areas/07-loading-error.md) |
| **Status codes on rendered pages.** `c.status()` is ignored and pages are always 200. | Common (5); Table stakes (7) for error statuses | Small change in `renderedResponse`; ISR stores only 200s. | [7](areas/07-loading-error.md) |
| **Layout server companions:** loaders, `head`, mode flags. | Table stakes (7) for loaders and for head | The biggest single unlock. Also gives subtree `ssr`/`prerender` inheritance (Common 4), parent-data access (Common 3), nested middleware and layout error boundaries. Needs parallel execution coalesced into one response, per-layout revalidation (so every navigation doesn't re-run every layout), a page object keyed by layout, and in-place prop updates (layouts persist across navigations in all 4 adapters). | [1](areas/01-routing.md), [2](areas/02-rendering.md), [3](areas/03-data-loading.md), [9](areas/09-metadata-seo.md) |
| **A richer data format than plain JSON** (devalue/Seroval-class) | Table stakes (7) | Today `Date` arrives as a string, `Map`/`Set` become `{}`, and `BigInt` throws. Also enables promises anywhere in loader data, started as soon as they're created (Common 5), richer island props (Common 3) and custom type hooks (Common 3). **Do the type fix right away:** `InferProps<T>` currently claims the loader's raw types (e.g. `Date`) while the wire sends JSON. Make it `Serialize<…>`. | [3](areas/03-data-loading.md), [8](areas/08-type-safety.md) |
| **Actions return data to the caller** | Table stakes (7) | A plain return value is ignored today, and a non-page 2xx `Response` forces a full page load. Add an ephemeral typed `result` to mutation responses, exposed as `form.result` and from `action()`. | [4](areas/04-mutations.md) |

### C. Forms and mutations (depends on B)

| Gap | Prevalence | Notes | Area |
|---|---|---|---|
| **Forms that work without JavaScript** | Common (5) | React's `Form` renders a client function as its action. Vue, Svelte and Solid render a `<form>` with no `action`/`method` and call `preventDefault()`. The server already re-renders HTML for non-JS POSTs. What's missing: `method`/`action` attributes (with `?name`), a method override for PUT/PATCH/DELETE, and seeding `useForm` data and errors from the server page object. | [4](areas/04-mutations.md) |
| **Validation of urlencoded and multipart bodies** | Common (3) | `withValidator` parses JSON only. This blocks the row above, validated file uploads, and GET/search forms (Common 4). | [4](areas/04-mutations.md), [6](areas/06-server-api.md) |
| **Concurrent submissions that don't navigate** | Common (3) | Every submission is a router visit, and a new visit aborts the previous one on the client while the server keeps running. Needs fetcher-style keyed submissions with tracked state. | [4](areas/04-mutations.md) |
| **Targeted or opt-out revalidation** | Common (4–5) | The current loader always re-runs, even after a `ValidationError`. There is no "only these props" or "skip the loader", no invalidation by key, tag or URL, and deferred props stay stale after a mutation. | [3](areas/03-data-loading.md), [4](areas/04-mutations.md) |

### D. Streaming

| Gap | Prevalence | Notes | Area |
|---|---|---|---|
| **Deferred content as streamed HTML** (SEO, no-JS) | Table stakes (6; 5 stable) | When a page has deferred props, the React adapter cuts React's stream at the shell marker (`readDeferredShell`). Resolved content is then rendered on the client in all 4 adapters, so crawlers see only fallbacks. React fix: let React stream the resolved boundaries and keep the data scripts. Keep the property that status and head are settled before the first byte. | [2](areas/02-rendering.md) |
| **Component streaming in the Vue and Solid adapters** | Varies by adapter | SolidStart streams by default; Nuxt's streaming is experimental. Svelte matches SvelteKit already. | [2](areas/02-rendering.md) |

### E. Server pipeline and request APIs

| Gap | Prevalence | Notes | Area |
|---|---|---|---|
| **A server entry the app owns**, with control over pipeline stages | Table stakes (6) | User middleware always runs after Void's redirect, rewrite, header and auth stages. Expose those stages as composable Hono middleware. | [6](areas/06-server-api.md) |
| **Documented cookie API** with secure defaults | Table stakes (7) | `hono/cookie` already works; mostly a docs job, or a thin wrapper. | [6](areas/06-server-api.md) |
| **Request getter usable from deep code** | Common (5) | The internal AsyncLocalStorage `requestContext` already exists on every target. | [6](areas/06-server-api.md) |
| **`after()`/`waitUntil` that works on every target** | Differentiator (2) | Cloudflare-only via `c.executionCtx` today, and undocumented. | [6](areas/06-server-api.md) |

### F. Router and URL model

| Gap | Prevalence | Notes | Area |
|---|---|---|---|
| **Base path** | Table stakes (7) | Also a prerequisite for an asset prefix/CDN (Common 4) and for multi-zones. Touches `Link`, `routeUrl` types, static JSON URLs, edge rules and ISR keys. | [1](areas/01-routing.md), [13](areas/13-build-deploy.md) |
| **Current-route introspection** (route id, pattern, matched chain) and static route metadata | Table stakes (6) / Common (4) | The page id and pattern are already known on the client; expose them through `useRouter()`. | [1](areas/01-routing.md) |
| **Navigation lifecycle hooks**, plus blocking that covers back/forward and programmatic navigation | Table stakes (6) / Common (5) | Today the only guard is `Link onNavigate`. | [1](areas/01-routing.md) |
| **Segment features:** optional segments (5), zero-length catch-all (4), param matchers that affect matching (4), partial-segment params (4) | Common | One parser plus the client matcher. | [1](areas/01-routing.md) |
| **URL/search changes without a loader re-run**, plus history `state`, shallow routing and modal routes | Common (4–5) | Every query change refetches today, and Vue remounts the page. | [1](areas/01-routing.md) |
| **Skew protection** (deployment ID, reload when versions mismatch or a chunk fails to load) | Common (5) | An unknown page component or a chunk-load failure after a deploy currently rejects the navigation with no reload. | [13](areas/13-build-deploy.md) |
| **Trailing-slash policy** | Common (4) | | [1](areas/01-routing.md), [13](areas/13-build-deploy.md) |

### G. Caching

| Gap | Prevalence | Notes | Area |
|---|---|---|---|
| **Visited-page client cache** with back/forward reuse | Common (5) | **Already implemented** as `cacheVisitedPageData` in the navigation engine but not exposed by any adapter plugin. | [5](areas/05-caching.md) |
| **Request-scoped memoization** | Common (5) | Cheap with the existing `requestContext`. | [5](areas/05-caching.md) |
| **Cross-request data/function cache** | Common (4; 2 stable at runtime) | This is what makes logged-in traffic cheap, because any request with a cookie bypasses Void's page cache. | [5](areas/05-caching.md) |
| **Pluggable cache provider**, which also brings the page cache to Node/Bun/Deno | Common (3) | Keep Void's safety rules in the core rather than in the provider. | [5](areas/05-caching.md), [13](areas/13-build-deploy.md) |
| **A limit on how long stale pages are served** | Common (3–4) | Stale entries currently never expire. | [5](areas/05-caching.md) |
| **Draft/preview mode** | Common (4; 2 in core) | | [5](areas/05-caching.md) |
| **Tag-based invalidation** | Differentiator (2) | Central for content sites. Needs a tag index, and per-colo copies in the Cloudflare edge cache can't be purged by tag. | [5](areas/05-caching.md) |

### H. Head, SEO and assets

| Gap | Prevalence | Notes | Area |
|---|---|---|---|
| Head tag coverage: `meta` limited to name/property/content/charset; no `http-equiv`, `media` or `itemprop`; no `style`, `noscript` or `base`; no body-position scripts. Scripts and html/body attributes are not updated on client navigation. | Table stakes (6) | | [9](areas/09-metadata-seo.md) |
| Head from components (React, Vue, Solid; Svelte works but is undocumented) | Common (5) | React renders inside `#app`, so React 19's metadata hoisting can't reach `<head>` during SSR. | [9](areas/09-metadata-seo.md) |
| Async `head()` | Common (3–4) | Await `headFn` in `protocol.ts`. | [9](areas/09-metadata-seo.md) |
| Sitemap generation | Common (3) | | [9](areas/09-metadata-seo.md) |
| Image optimization: a component plus a build-time pipeline and a pluggable runtime service (no sharp on Workers) | Common (4) | | [10](areas/10-assets.md) |
| Font optimization; production critical-CSS inlining | Common (3) each | | [10](areas/10-assets.md), [11](areas/11-styling.md) |
| Server-rendered components in Markdown (MDX-style) | Common (5) | The islands pipeline already statically renders unmarked components on island pages. | [12](areas/12-markdown.md) |
| Tailwind and preprocessor docs and scaffolding | Table stakes (7) | Probably works through Vite already; mostly docs plus a `void init` option. | [11](areas/11-styling.md) |

### I. Rendering controls

| Gap | Prevalence | Area |
|---|---|---|
| App-wide SPA mode for Pages apps | Table stakes (6) | [2](areas/02-rendering.md), [13](areas/13-build-deploy.md) |
| Client-only components (`<ClientOnly>`/`useHydrated`) in all adapters | Common (5) | [2](areas/02-rendering.md) |
| Prerender controls: crawling (4), failing the build on errors (5), configurable concurrency (6) | Common to Table stakes | [2](areas/02-rendering.md) |
| More island hydration strategies: interaction, never, delay, options on idle/visible | Common (3) / Differentiator (2) | [2](areas/02-rendering.md) |
| Static shell with dynamic holes (PPR / server islands) | Differentiator (2) | [2](areas/02-rendering.md) |
| Server components | Common (4; only Next.js stable) | [2](areas/02-rendering.md) |

### J. Deployment portability and observability

| Gap | Prevalence | Area |
|---|---|---|
| Vercel/Netlify/serverless targets | Table stakes (7) | [13](areas/13-build-deploy.md) |
| Public adapter/preset API (with post-build hook and per-target feature declarations) | Common (5) | [13](areas/13-build-deploy.md) |
| Self-contained Node output; production server settings (host, proxy headers, body limit, graceful shutdown) | Common (3) / Common (4) | [13](areas/13-build-deploy.md) |
| Server and client error-reporting hooks | Common (4) | [7](areas/07-loading-error.md), [14](areas/14-dev-tooling.md) |
| Instrumentation / OpenTelemetry | Common (3) | [14](areas/14-dev-tooling.md) |
| In-browser devtools (route, page data, cache), which must work for all four UI libraries | Common (5) | [14](areas/14-dev-tooling.md) |
| MCP server (an app-aware dev-server MCP is the most valuable kind); `llms.txt` | Common (4) / Common (3) | [14](areas/14-dev-tooling.md) |

---

## Where Void is already ahead

The roadmap should protect these:

- **One router, data and form API across React, Vue, Svelte and Solid.** No competitor covers more than two UI libraries with one routing and data API.
- **Prefetching:**
  - 4 triggers that can be combined;
  - a per-link cache TTL with a stale-while-revalidate pair (`cacheFor: [fresh, expire]`);
  - an awaitable `router.prefetch()`;
  - code and data loaded in parallel, with deferred data resolved inline.
- **A robust navigation engine:**
  - abort-safe visits, where a stale visit never commits;
  - built-in active-link marking;
  - scroll restoration that survives a reload;
  - view transitions in all 4 adapters;
  - non-GET `Link`s.
- **Correct streaming semantics.** Status, headers and head are settled before the first byte, so there is no "200 on a streamed 404", no dropped headers and no head patch scripts.
- **Deploy-time prerendering in the production Worker** that seeds the edge page cache before traffic switches. Unique.
- **The most privacy-safe page cache in the set:**
  - it bypasses on any cookie or authorization header;
  - it refuses to store `Set-Cookie` or private responses;
  - it evicts a page that later turns private;
  - unlisted query params are never stored.

  Cache keys are scoped by deployment and by host.
- **Config-level edge rules** (headers, redirects, rewrites, fallbacks, Netlify-style files). Richer than 5 of the 7 others, and they work identically on Node, Bun and Deno.
- **Type coverage:**
  - one typed route map covers pages, HTTP and WebSocket routes, `c.rewrite()`, typed `fetch` and forms;
  - typed `fetch` is strict by default and validator-driven;
  - Drizzle → validator → handler → client in one pipeline.
- **`useForm` state.** Typed field errors, `hasChanges`, `recentlySuccessful`, `reset` variants, routing of errors by status, and 429-aware `Form`. Only SvelteKit's experimental remote `form` is comparable.
- **Named actions on real HTTP methods** (PUT/PATCH/DELETE on the page URL).
- **First-party SSE** on both server and client (`void/sse`), and **Hono-native middleware**: any Hono middleware works globally, per route or around a page.
- **Env safety.** Schema validation, a per-key build error when client code reads a server key, and validation at deploy and at boot.
- **Markdown pages in all 4 adapters:** Shiki, containers, a TOC, and frontmatter that becomes head tags.
- **Generators and agent onboarding:**
  - `void gen model|route|middleware|…`;
  - version-pinned docs in `node_modules`;
  - a managed `AGENTS.md`;
  - skills linked into 16 agents' skill folders.
- **Dev fidelity.** workerd in dev, persisted local resources, and a prompt to restart when a new binding is detected.

---

## Method

1. **Choosing the areas.** The areas were chosen with one rule: an area is in scope if Next.js has it. There were 12 at first; "Assets & styling" was later split into three (images, fonts & scripts; CSS & styling; Markdown & content) because it mixed unrelated topics. The inventories still use the original 12 headings.
2. **Inventories.** For each of the 8 frameworks, an agent read that framework's current docs: Void's docs plus source; the others' docs from a sparse clone of their repos, plus SvelteKit's generated type definitions. Each agent wrote an option-level inventory of every public API in scope, with defaults, behavior and edge cases, citing a file for each claim.
3. **Comparisons.** For each area, an agent compared all 8 inventories by capability, re-checked doubtful claims against the docs, and checked every "Void lacks X" against `packages/`. The comparisons corrected the inventories where needed; each area file notes these corrections. The inventories under **Sources** are the raw, uncorrected versions, so where they disagree, the area files win.
4. **Spot-checks.** The highest-impact claims were checked a second time by reading Void's source directly.
