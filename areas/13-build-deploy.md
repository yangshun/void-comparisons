# 13. Build output & deployment

**Versions:** Void 1.5.0 · Next.js 16.4 (App Router) · React Router 8 (framework mode) · TanStack Start 1.169 (React) · Nuxt 5.0 pre-release (4.x is stable) · SvelteKit 3.1 · SolidStart 2.0 · Astro 7.4

**Markers:** [exp] experimental, unstable or canary · (src) found in Void's source but not in its docs · (unverified) not confirmed in docs or source

**Note:** Deployment is compared as a **framework capability**: what the build emits, which runtimes it targets, how hosts plug in, and which edge rules live in config. Void's `void deploy` provisioning and rollback are out of scope, except where they change framework behavior (for example, ISR and deploy-time prerendering exist only on the Cloudflare target).

**Paths:** Void file paths are in the `voidzero-dev/void` repo. Short paths such as `pages/scan.ts` are under `packages/void/src/`; paths that start with a package name, such as `react/src/…`, are under `packages/`.

## At a glance

- **Shape.** Void emits one Vite multi-environment build (`dist/client/` + `dist/ssr/`) for one of four built-in targets: Cloudflare Workers (default, full features), Node, Bun or Deno. There is **no adapter/preset model** and no Vercel/Netlify/Lambda target. On Node/Bun/Deno the only portable seam is `dist/ssr/app.js`, a Hono app whose `.fetch` can be hosted anywhere. All 7 others reach Vercel and Netlify, and 5 expose a public adapter or preset API.
- **Output modes are mostly on par.** `output: "static"` prerenders at build, and pages it can't prerender are served by a Worker that is added automatically at deploy. `output: "server"` with per-page `prerender = true` prerenders at deploy time into the ISR cache, but only on Cloudflare. **Missing:** an app-wide SPA switch for Pages apps and a "strict static" check.
- **Strongest area: config-level edge rules.** These are `routing.headers`, `redirects`, `rewrites`, `fallbacks` and `alwaysUseHttps`, plus Netlify-style `_headers`/`_redirects` files that are merged with config. They are richer than React Router, TanStack, SvelteKit, SolidStart or Astro (none has config rewrites; only Astro and Nuxt have config redirects). They are close to Next.js and Nuxt, and they run identically on Node/Bun/Deno (compiled into Hono middleware). Missing versus Next.js: `has`/`missing` conditions, external proxy rewrites, and rewrites that apply during client navigation.
- **Biggest gaps:**
  - **No base path** (7/7 others have one).
  - **No asset prefix/CDN option.** SSR-injected asset tags are hard-coded root-relative, so even Vite `base` doesn't reach them (src).
  - **No skew protection** (5/7): no deployment ID, no version polling, and no reload when a chunk fails to load or the manifest doesn't match.
  - **No trailing-slash policy** (4/7).
- **Feature parity across targets is the structural limit.** These are Cloudflare-only and produce compile errors, warnings or no-ops elsewhere: ISR/`routing.revalidate`, deploy-time prerender, `void/env` (typed env schema), `void/db|kv|storage|auth|ai|sandbox`, `*.ws.ts`, inbound email, cron scheduling, `c.executionCtx` and `alwaysUseHttps`. Next.js, Nuxt and Astro all keep server-side page caching on self-hosted Node.
- **Node/Bun/Deno output is not self-contained.** App dependencies stay as imports, so production needs `node_modules`. The server entry reads only `PORT`: no host, graceful-shutdown, proxy-header or body-limit settings (src). Next.js (traced `standalone`), Nuxt (fully bundled `.output`) and SvelteKit (`adapter-bun` single executable) go further.
- **Env inlining is strict and safe.** Only `VITE_*` values are inlined, `.env` is ignored by builds, and a client import of a server key fails the build. But there is no runtime-configurable public config (Nuxt `runtimeConfig.public`, SvelteKit 3 dynamic public vars).
- No multi-zone/microfrontend support (Next.js has it stable, Nuxt experimental).

## Gap list for this area

| Gap in Void | Who has it (mechanism, briefly) | Prevalence | Notes for design (constraints, dependencies, adapter impact) |
|---|---|---|---|
| App base path | Next.js `basePath`; React Router `basename`; TanStack `basepath`; Nuxt `app.baseURL` (runtime-overridable); SvelteKit `paths.base`; SolidStart `<Router base>`; Astro `base` | Table stakes (7) | Touches the route matcher, typed `routeUrl()`/`RouteDestination`, `Link`/`useForm`/`visit` in **all 4 adapters**, edge rules (Next.js opts rules in by default, `basePath: false` per rule), `/_void/pages/*.json`, `/api` detection, ISR keys. Prerequisite for zones. |
| Vercel / Netlify / serverless targets | All 7 (adapters, presets or Vite plugins) | Table stakes (7) | `app.js` is already a fetch handler. The blockers are the Cloudflare-only features (ISR, `void/env`, bindings) and having no way to describe host routing/edge rules to the platform. |
| Public adapter / preset API | Next.js Adapter API; React Router presets + `createRequestHandler`; Nuxt Nitro presets (+ [exp] server-builder contract); SvelteKit `Adapter`; Astro `setAdapter` | Common (5) | Would need to expose: build outputs (prerendered files, server entry, assets), the merged routing rules, the static-vs-Worker split (`asset-worker-bypass.ts`), plus a feature-support declaration (Astro-style) to replace the hard-coded per-target table. |
| Skew protection (version ID + reload on mismatch + chunk-error recovery) | Next.js `deploymentId`; React Router manifest version; Nuxt `appManifest` + `emitRouteChunkError`; SvelteKit `version.*` + `updated`; Astro adapter skew headers | Common (5) | Same in all adapters (shared `navigation-engine.ts`). Add a deploy ID header on `X-VoidPages` responses and a reload on mismatch or on import failure. Asset retention across deploys is a separate (platform) concern. |
| Asset prefix / CDN | Next.js `assetPrefix`; Nuxt `app.cdnURL`; SvelteKit `paths.assets`; Astro `build.assetsPrefix`; TanStack `transformAssets` [exp] | Common (4 stable + 1 exp) | Today even Vite `base` isn't applied to SSR asset tags (`routing-assets.ts` hard-codes `/`); fix that first. Interacts with the hashed-asset cache policy and the Cloudflare asset-Worker bypass. |
| Trailing-slash policy | Next.js `trailingSlash`; TanStack router `trailingSlash`; SvelteKit page option; Astro `trailingSlash` | Common (4) | Today: implicit 301 to the no-slash form for unmatched routes only. Needs matcher support, prerender file naming (`about/index.html`) and Link active-state logic. |
| Server-side page caching on Node/Bun/Deno | Next.js (ISR + `cacheHandler`), Nuxt (Nitro `swr`/`cache` on any preset), Astro (`memoryCache()` provider) | Common (3) | `packages/isr` is built on Cloudflare storage and the edge cache. Needs a storage abstraction; deploy-time prerender also depends on it. |
| Self-contained Node output (dependency bundling or tracing) | Next.js `standalone` (nft); Nuxt `.output` (all deps bundled); SvelteKit `adapter-bun` `compile` | Common (3) | Currently only `void`-related packages are inlined; `@hono/node-server` stays external. Option: `ssr.noExternal: true` with a native-addon escape list. |
| Production server settings (host, proxy headers, body limit, graceful shutdown) | SvelteKit adapter-node/bun (extensive env); Astro Node (`HOST`, certs, `bodySizeLimit`); Nuxt (`NITRO_HOST`, SSL, cluster); Next.js (`HOSTNAME`, shutdown guide) | Common (4) | Generated `index.js` reads only `PORT` (`compileNodeServer`). Proxy/forwarded headers also affect `c.req.url`, CSRF and origin checks elsewhere. |
| App-wide SPA mode for Pages apps | Next.js export/SPA guide; React Router `ssr: false`; TanStack `spa.enabled`; Nuxt `ssr: false`; SvelteKit `ssr = false` + `fallback`; SolidStart `ssr: false` | Table stakes (6) | Per-page `ssr = false` exists; missing are a global default and a single SPA-fallback shell. Overlaps area 2. |
| Strict static export validation | Next.js `output: 'export'` (build errors); SvelteKit `adapter-static` `strict` | Differentiator (2) | Void auto-adds a Worker instead. A `strict` flag would guard self-hosted `dist/client`-only deploys. |
| Rewrites applied during client navigation | Next.js rewrites; SvelteKit `reroute`; TanStack router `rewrite` | Common (3) | Void documents the mismatch as a caveat. The client router would need the rule list (or a server "resolve" round-trip). |
| External proxy rewrites | Next.js `rewrites()` to URLs; Nuxt `routeRules.proxy` | Differentiator (2) | Destinations are validated as internal today. Needs streaming proxying and header hygiene. |
| Request-conditioned rules (`has`/`missing`: header, cookie, query, host) | Next.js | Differentiator (1) | Void has literal host-prefixed redirects only. |
| Runtime-configurable public env | Nuxt `runtimeConfig.public` (`NUXT_PUBLIC_*`); SvelteKit 3 dynamic public vars | Differentiator (2) | Conflicts with the "VITE_ inlined, `.env` ignored" model; would need a payload channel (Pages page object `shared` could carry it). |
| Typed env schema on Node/Bun/Deno | SvelteKit `defineEnvVars`, Astro `astro:env` (all adapters) | Differentiator (2) | `void/env` is a CF-only import today; the schema/validation part is target-agnostic. |
| Multi-zones / microfrontends | Next.js Multi-Zones; Nuxt `future.multiApp` [exp] | Differentiator (1 stable + 1 exp) | Depends on base path and asset prefix. |
| Per-route runtime / region selection | SvelteKit adapter-vercel `config` (runtime, regions, memory); Next.js `runtime` (deprecated) | Differentiator (1) | Low value for an edge-first framework. |
| Declarative per-target feature support | Astro `supportedAstroFeatures`; SvelteKit `supports.*` | Differentiator (2) | Void's compile-error table works but isn't extensible. |
| Post-build hook exposing the build manifest | Next.js `onBuildComplete`, React Router `buildEnd`, Nuxt hooks, Astro `astro:build:*` | Common (4) | Prerequisite for third-party adapters. |

## Where Void is ahead

- **Config-level edge rules as a first-class, portable feature.**
  - Headers, redirects, rewrites and fallbacks, each in a separate phase.
  - Netlify-compatible `_headers`/`_redirects` merged under config precedence.
  - Host-scoped redirects and `alwaysUseHttps`.
  - Query-merge semantics with a `?` reset; duplicate-source linting.
  - A dev-only `X-Void-Routing` header naming the matched rule and its file, plus rule changes picked up without a restart.
  - The same rules apply on Node/Bun/Deno. Only Next.js and Nuxt come close, and 5 of 7 have no config rewrites at all.
- **Automatic static/hybrid deployment split.** `output: "static"` never forces you to give up API routes, middleware, cron or queues: a Worker is added only if needed. On Cloudflare, prerendered pages skip the Worker entirely when nothing requires it.
- **Deploy-time prerender into the ISR cache, before traffic switches** (Cloudflare). No other framework prerenders "per deployment" at the edge. Also the per-deployment ISR namespace, so a redeploy never serves stale HTML from the old build.
- **Edge-first runtime with full platform features by default.** No adapter to install. Bindings, cron, queues, email and WebSockets work out of the box on Workers, where the others need an adapter plus platform-specific code.
- **Strict, safe env model.** Fixed `VITE_` boundary, `.env` ignored by production builds, client build fails on a server-key import, schema validation at deploy and at Worker startup, redacted diagnostics.
- **Embeddable fetch app on self-host targets.** `dist/ssr/app.js` serves routes *and* static assets in one Hono app. SvelteKit's `handler.js` is the closest equivalent (Node-only); Astro middleware mode does no static serving. It works across Node, Bun and Deno from one config key, and as a Web `fetch` handler rather than a Node `(req, res)` one.
- **Early, precise target errors.** CF-only imports on other targets fail the build and name the importing file, rather than failing at runtime.

## Output modes (server, static export, hybrid, SPA) and what each emits

| Framework | Server (default) | Static export | Hybrid (per-route prerender inside a server build) | SPA | Notes |
|---|---|---|---|---|---|
| **Void** | `output: "server"`: `dist/client/` (assets, `.vite/manifest.json`) plus `dist/ssr/`. On Cloudflare that is the Worker bundle and its config; on Node/Bun/Deno it is `index.js` + `app.js`. A fourth shape is custom SSR (`src/main.ssr.ts`, user-owned render). | `output: "static"`: every page is prerendered unless it sets `prerender = false` or is dynamic without `getPrerenderPaths()`. Emits `about.html`-style files (fixed, no format option; src `prerender-render.ts`), `/_void/pages/*.json` page data for client navigation, and a default `404.html` (overridable with `public/404.html` or a `/404` page). Prerender failures only warn. | Both directions. (a) `static` + `prerender = false`: the Worker renders that page. (b) `server` + `prerender = true`: deploy-time "edge prerender" into the ISR cache, **Cloudflare only**; failures never block the deploy. Also `routing.prerender: [paths]`, and Markdown pages and island pages without a loader are auto-prerendered. | **No app-wide switch for Pages apps.** Per page, `ssr = false` gives a shell with embedded loader props, which can be prerendered. `inference.appType: "spa"` serves a plain Vite SPA (+ `routes/` API) with a 200 `index.html` fallback. `routing.notFound: 'single-page-application'`. | The deploy step picks "fully static" (no Worker at all) or "hybrid" automatically. On Cloudflare, prerendered pages without `.server.ts` skip the Worker. They still go through it if the app uses middleware, auth, live updates, edge rules, a custom Vite `base`, a non-`none` `notFound`, or a top-level dynamic page (docs/guide/ssg.md). |
| **Next.js** | `.next` + `next start` (the only mode that supports every feature); `output: 'standalone'`. | `output: 'export'` → `out/`. **Fails the build** on what it can't support: dynamic routes without `generateStaticParams`/with `dynamicParams: true`, intercepting routes, cookies, Proxy, Server Actions, ISR, default image optimization, config `rewrites`/`redirects`/`headers`, `use cache`, `after`, streaming `loading`. | Automatic static/dynamic split + `generateStaticParams`; with Cache Components, PPR static shells with dynamic holes. | Via `export` + client components (SPA guide). | Output tracing (`@vercel/nft`), `outputFileTracingIncludes/Excludes`. |
| **React Router** | `ssr: true` → `build/client` + `build/server/index.js` (`serverBuildFile`, `serverModuleFormat: "esm"\|"cjs"`). | `ssr: false` + `prerender` → `build/client` only, with an SPA-fallback html for non-prerendered paths. | `ssr: true` + `prerender` emits `.html` + `.data` files; `prerender: { paths, concurrency }`. | `ssr: false` → `index.html`, no server build. | `ssr: "unstable_api-only"` [exp]; RSC build [exp]; `serverBundles` splits the server build. |
| **TanStack** | Nitro `.output/server/index.mjs` + `.output/public`; Rsbuild `dist/server/index.js` exporting `{ fetch }`. | Static prerender (can be mixed with server). | Prerender + selective SSR per route. | `spa.enabled` shell + optional prerendered pages. | Netlify publishes `dist/client`. |
| **Nuxt** | `nuxt build` → `.output/server/index.mjs` + `.output/public`. | `nuxt generate` (crawler) → `.output/public` with 200/404 fallbacks. | `routeRules` `prerender` inside a server build. | `ssr: false` + generate → `index.html`. | `@nuxt/vite-server` [exp] emits a web `{ fetch }` server and generate crawls it; `nuxt preview`. |
| **SvelteKit** | The adapter decides. Build = Vite (server, client, service worker; prerender runs here) → `adapt`. | `adapter-static`, `strict: true` by default: **fails** unless every route is prerendered or a `fallback` is set. | Page option `prerender: true \| 'auto'`, cascading from layouts. | `adapter-static` `fallback`, or `router.type: 'hash'`. | A missing adapter warns (`adapter_missing`); `output.bundleStrategy: 'split'\|'single'\|'inline'`. |
| **SolidStart** | Deployment plugin output (Nitro v3 [beta] `.output/` per preset; Netlify and Cloudflare plugins). | Nitro prerender (`crawlLinks`); no dedicated static-export command documented. | Nitro prerender routes. | `ssr: false` (server functions/API routes still work). | `vite preview` only checks the build. |
| **Astro** | `output: 'server'` (everything on demand). | `output: 'static'` (default) → `dist/`, no adapter needed. | `prerender = false` per route + an adapter. | No distinct SPA mode. | `build.format: directory\|file\|preserve`; actions, server islands, sessions and on-demand images need an adapter even on static sites; `adapterFeatures.buildOutput`. |

**Behavioral differences that matter:**
- **What "static" means.** Void, Astro and Nuxt treat static as "prerender what you can, keep a server for the rest". Next.js `export` and SvelteKit `adapter-static` (strict) **fail the build** when something can't be static. Void has no strict mode. If you self-host only `dist/client/`, API routes, middleware and non-prerendered pages simply 404, with no build-time signal (no strict option found in config.ts).
- **Two prerender timings are unique to Void.** There is build-time SSG, and deploy-time prerender "before traffic is routed to the new version", which seeds the ISR cache (default TTL one year, wiped on each deploy). The deploy-time path depends on Cloudflare ISR. On other targets `prerender = true` under `output: "server"` does nothing; you must use `output: "static"`.
- **Client-navigation data for static pages.** Void (`/_void/pages/*.json`), React Router (`.data`) and Nuxt (`_payload.json`) all emit per-page data files, so static sites keep SPA navigation. Void's client also falls back to a static JSON fast path (src `navigation-engine.ts`).
- **SPA.** 6 of 7 have an app-wide "no SSR" switch for their full router (Astro does not). Void has one only for non-Pages Vite SPAs. A Pages app must set `ssr = false` in every page companion.

**Void gap:** partial.
- No app-wide `ssr: false`/SPA-shell output for Pages apps.
- No strict-static validation (`adapter-static strict`, Next.js `export` errors).
- No output-format option (`build.format`, `trailingSlash`-driven `about/index.html`).
- Deploy-time prerender is Cloudflare-only.

## Runtime targets and per-route runtime selection

| Framework | Node | Bun | Deno | Cloudflare Workers | Vercel / Netlify / serverless | Per-route runtime |
|---|---|---|---|---|---|---|
| **Void** | `target: "node"` (`@hono/node-server`, installed separately) | `target: "bun"` (`Bun.serve`) | `target: "deno"` (`Deno.serve`) | **Default** (`target: "cloudflare"`), workerd | **None.** The `dist/ssr/app.js` fetch handler can be wrapped by hand ("serverless environments that accept a fetch handler", docs/integrations/nodejs-bun-deno.md). | No (one target per app) |
| **Next.js** | First-class (≥20.9); Cache Components *require* it | Verified adapter | Deno Deploy (own integration) | Cloudflare's own integration (unverified; "working on" a verified adapter) | Vercel (verified adapter); Netlify, Amplify, Firebase, Appwrite (own integrations) | Only the deprecated segment `runtime` export (forbidden under Cache Components); Go route handlers [exp] |
| **React Router** | Official (Active LTS) | ALS note only | ALS note only | Official adapter + `@cloudflare/vite-plugin` | AWS Lambda (`@react-router/architect`); Vercel/Netlify host templates | No; `serverBundles` splits the server build per route branch (needs host routing) |
| **TanStack** | Nitro; srvx/Express with Rsbuild | React 19 only (Nitro `bun` preset or a reference Bun server) | Not documented | `@cloudflare/vite-plugin` | Netlify plugin; Vercel/Railway via Nitro; Appwrite | No |
| **Nuxt** | `node-server` (default), `node_cluster` | Preset | Preset | Zero-config Workers/Pages | Vercel (+`vercel-edge`), Netlify (+`netlify-edge`); "more than 15 presets" | No (one preset per build) |
| **SvelteKit** | `adapter-node` | `adapter-bun` (new in v3) | Not documented | `adapter-cloudflare` (Workers + Pages) | `adapter-vercel` (Node 22/24/26 or Bun; edge removed in v3), `adapter-netlify` (Functions or Edge) | **Yes, via adapter `config`**: Vercel `runtime`, `regions`, `memory`, `maxDuration`, `split`, `isr`, cascading from layouts |
| **SolidStart** | Nitro `node_server` | Nitro preset | Nitro preset | Cloudflare Vite plugin (SSR in workerd) | Netlify plugin; Nitro presets (v1 list: vercel(-edge), netlify(-edge), aws_lambda, deno_deploy…) | No |
| **Astro** | `@astrojs/node` | Recipe ("rough edges") | `@deno/astro-adapter` (Deno-maintained) | `@astrojs/cloudflare` (workerd in dev/preview/prerender) | `@astrojs/vercel`, `@astrojs/netlify` | No; only middleware can move to the edge (`middlewareMode: 'edge'`) |

**Behavioral differences that matter:**
- **Void is edge-first; most others are Node-first.** Void's default and best-supported runtime is Workers. The others make Node the default and treat Workers as one adapter among several. For Void, the risk is the reverse of Next.js's: Node is the reduced target.
- **Per-route runtime is a niche.** Only SvelteKit's Vercel adapter does it in a stable way (per-route `runtime`/`regions`/`memory`). Next.js deprecated its version.
- **Fetch-handler portability.** React Router (`createRequestHandler`), TanStack (`export default { fetch }`), Astro (`createApp()`) and Void (`app.js`) all expose a Web-standard handler. Void's handler exists **only** for non-Cloudflare targets, and those lose the Cloudflare-only features.

**Void gap:** partial. Vercel, Netlify and AWS Lambda/serverless targets are missing (7/7 others reach Vercel and Netlify). There is no per-route runtime (Differentiator; low priority).

## Feature parity across targets (what breaks where)

| Framework | Mechanism for declaring support | What breaks off the primary target |
|---|---|---|
| **Void** | Hard-coded. CF-only imports throw a **compile-time error** naming the importing file (src `plugin-node-target.ts`); some config is **warned and ignored**; auth **fails the build**. | **Node/Bun/Deno lose:** ISR/`routing.revalidate` (warned, ignored) and deploy-time prerender; `routing.alwaysUseHttps`; `void/env` (typed schema; use `process.env`/`Deno.env.get()`); `void/db`, `kv`, `storage`, `auth`, `ai`, `sandbox`; `*.ws.ts` (Durable Objects); inbound email/`sendEmail`; cron (compiled but never scheduled); `c.executionCtx`; `void deploy`. `inference.bindings`, `remote` and `worker` are ignored. **Kept:** routes, middleware, Pages SSR in all 4 adapters, typed fetch, `routing.headers/redirects/rewrites/fallbacks` (rewrites/fallbacks confirmed in src: `router/compile.ts` emits the rules middleware for every non-managed target), SSG, `vite preview`. |
| **Next.js** | Docs tables ("Deploying to platforms") plus the adapter output types. | `export` loses the list above. Cache Components need Node ("other runtimes not guaranteed"); Edge is deprecated. Multi-instance self-hosting needs a shared `cacheHandler`, encryption key, `deploymentId` and `refreshTags` coordination. |
| **React Router** | Per-adapter docs. | Cloudflare needs a custom `entry.server`; ALS caveats on Bun/Deno. |
| **TanStack** | Per-host docs. | Bun only with React 19; on Workers, env must be read per request (module-scope reads are `undefined`); Cloudflare/Netlify setups are Vite-only (no Rsbuild). |
| **Nuxt** | Nitro preset capabilities. | The `isr` CDN cache works only on Netlify/Vercel (elsewhere it behaves like `swr` on Nitro storage); `@nuxt/vite-server` [exp] lacks `defineCachedFunction`/handlers; Cloudflare Rocket Loader and email obfuscation must be off. |
| **SvelteKit** | Adapter `supports.read()` / `supports.instrumentation()`, checked at dev and build (build error `adapter_instrumentation_unsupported`); `emulate()` for dev `platform`. | Cloudflare: no `fs` (use `read()`), no Durable Object/Workflow exports, `_headers`/`_redirects` apply to static assets only. ISR, draft-mode bypass and skew protection are Vercel-only; Netlify Forms need prerendered pages. |
| **SolidStart** | Per-plugin docs. | Preset names changed in Nitro v3; WebSockets need `nitro.features.websocket`; tasks are [exp]. |
| **Astro** | **`supportedAstroFeatures`** per adapter (`staticOutput`, `hybridOutput`, `serverOutput`, `i18nDomains`, `envGetSecret`, `sharpImageService` → `stable\|experimental\|limited\|deprecated\|unsupported`, custom message, `suppress`), with build-time warnings. | Actions, server islands, sessions and on-demand image endpoints need an adapter; Vercel ISR; Vercel/Netlify skew protection. |

**Behavioral differences that matter:**
- Void fails early and loudly at compile time, which is good. But its rules are hard-coded rather than a declarative matrix like Astro's `supportedAstroFeatures` or SvelteKit's `supports.*`, so third-party targets could not declare support even if an adapter API existed.
- **Server-side page caching on self-hosted Node:** Next.js (built-in ISR with the filesystem cache or a `cacheHandler`), Nuxt (Nitro `swr`/`cache` route rules on any preset) and Astro (`memoryCache()` route-cache provider). Void's ISR exists only on Cloudflare.

**Void gap:** partial.
- ISR/page caching on Node/Bun/Deno is missing (Common: Next.js, Nuxt, Astro).
- The typed env schema (`void/env`) doesn't work off Cloudflare.
- There is no declarative per-target feature-support API.

## Adapter / preset model

| Framework | Official targets | Community | Public adapter API | What an adapter controls |
|---|---|---|---|---|
| **Void** | 4 values of `target`, built into `void` (not separate packages). Deploy CLI: `--platform cloudflare\|void` (out of scope). | — | **None** (no adapter/preset hook in `VoidConfig`; grepped config.ts). | n/a. Cloudflare-specific escape hatches: the `cloudflare` key (complete Worker config passthrough), `worker` (`compatibility_*`, `vars`, `limits.cpu_ms`) and `voidPlugin({ auxiliaryWorkers })`. |
| **Next.js** | **Deployment Adapter API** (`adapterPath`, stable 16.2; `NEXT_ADAPTER_PATH`). Verified adapters: Vercel, Bun. | Cloudflare, Netlify, Amplify, Firebase, Appwrite, Deno (own integrations). | `NextAdapter { modifyConfig(config, {phase, nextVersion, projectDir}), onBuildComplete({routing, outputs, projectDir, repoRoot, distDir, config, nextVersion, buildId}) }`. | Config and post-build packaging. Typed `outputs` (`pages`, `appPages`, `appRoutes`, `prerenders`, `staticFiles`, `middleware`…) and routing phases; `@next/routing resolveRoutes()`; PPR resume protocol; compatibility test harness. Runtime caching goes through `cacheHandler(s)`, not the adapter. |
| **React Router** | 3 adapters (`express`, `architect`, `cloudflare`) + `@react-router/node`, `@react-router/serve`. | Host templates (Vercel, Netlify, EdgeOne…). | `createRequestHandler({ build, getLoadContext?, mode? })`; **Presets API** (contribute config, validate via `reactRouterConfigResolved`); `buildEnd({ buildManifest, … })`; `serverBundles`. | Request bridging and load context; presets are limited to config. |
| **TanStack** | Targets: cloudflare-workers, netlify, railway, nitro, vercel, node-server, bun, appwrite-sites. | — | **None Start-specific**: hosts integrate via Vite plugins (`nitro()`, `@cloudflare/vite-plugin`, `@netlify/vite-plugin-tanstack-start`) or by hosting the `fetch` entry. | Whatever the plugin does. |
| **Nuxt** | Nitro presets ("more than 15"; full list at nitro.build), many **auto-detected zero-config**; `compatibilityDate` pins preset behavior. | Custom Nitro presets. | Nitro preset API (not documented in Nuxt docs); **server-builder contract** [exp] (`@nuxt/kit/internal`: `getServerRuntime()`, `createNuxtRenderer()`, `setServerBuild()`, `runtime.handler`); app-builder contract (`builder: vite\|webpack\|rspack\|{ bundle }`). | Server bundle shape, entry, public dir, platform mapping of route rules (e.g. Netlify/Vercel native redirects/headers). |
| **SvelteKit** | 6 (node, bun, static, cloudflare, netlify, vercel) + deprecated cloudflare-workers + `adapter-auto`. | Listed at /packages. | `Adapter { name, adapt(builder), supports?: { read, instrumentation }, emulate?(), vite?: { getRequest, setResponse, plugins } }` (verified in `packages/kit/types/index.d.ts`); Builder (`writeClient/Server/Prerendered`, `generateServerInstance`, `compress`, `instrument`…); `server.init()`/`respond()`. | Packaging, dev/preview request bridging, platform emulation, per-route `config`. |
| **SolidStart** | "Choose one deployment plugin": Nitro v3 [beta], Netlify, Cloudflare. | Any Environment-API Vite plugin. | None SolidStart-specific (the Vite Environment API *is* the contract). | Whatever the plugin does. |
| **Astro** | 4 (node, netlify, vercel, cloudflare) + Deno-maintained; ~30 host deploy guides. | Integrations directory. | `setAdapter({ name, serverEntrypoint, entrypointResolution, previewEntrypoint, client: { internalFetchHeaders, assetQueryParams }, supportedAstroFeatures, adapterFeatures: { middlewareMode, buildOutput, staticHeaders, preserveBuildClientDir/ServerDir } })`; `createApp()`; `setPrerenderer()`; build hooks. | Entry, preview, feature support, skew headers, edge middleware, static headers, custom prerenderer. |

**Behavioral differences that matter:**
- Three integration styles exist:
  - A **formal adapter interface** (Next.js, SvelteKit, Astro).
  - **Presets over a portable server layer** (Nuxt/Nitro, React Router presets).
  - **"Bring a Vite plugin"** (TanStack, SolidStart).

  Void has none of these. Its Vite plugin *is* the target, so the targets can't be extended outside the `void` package.
- What adapters typically own that Void hard-codes:
  - The platform mapping of edge rules: Nuxt routeRules → Netlify/Vercel config; Astro Netlify adapter writes `_redirects`.
  - Skew headers: Astro `client.internalFetchHeaders`.
  - Dev emulation: SvelteKit `emulate()`.
  - Feature declarations: Astro, SvelteKit.

**Void gap:** missing.
- No adapter/preset API (Common: Next.js, React Router, Nuxt, SvelteKit, Astro).
- No Vercel/Netlify/Lambda targets (Table stakes).

Design note: Void already has the pieces an adapter would need: a fetch-handler app (`app.js`), a resolved routing-rules list (`mergeRoutingRules`), the prerender manifest, and its asset-cache policy.

## Config-level headers

| Framework | Mechanism | Matching | Conditions | Merge / precedence | Scope & limits |
|---|---|---|---|---|---|
| **Void** | `routing.headers: { '/pattern': ['Name: value', …] }` + `public/_headers` (and framework-produced `_headers`) | `*` = any chars incl. `/`; everything else literal (`:` is literal; src `matchLiteralPattern`) | None | **All matches merge; last match wins** per header name; file rules first, config rules after (config overrides). User `Cache-Control` replaces the built-in default. | Static assets, SSR, API, hashed assets — but it can't replace `Cache-Control`, `Content-Type`, `Content-Encoding`, `Content-Length`, `Content-Range`, `Accept-Ranges` or `Transfer-Encoding` on hashed files. **Not applied to ISR cache hits.** On a Void platform `Set-Cookie` is ignored and `Clear-Site-Data` restricted. Works on all targets. |
| **Next.js** | `headers()` (async) | path-to-regexp (`:slug`, `:slug*`, regex) | **`has` / `missing`** (`header`, `cookie`, `host`, `query`, with named captures); `basePath: false`, `locale: false` | Last key wins; checked **first** (before redirects, proxy and the filesystem) | Can't override `Cache-Control` on immutable assets; unavailable with `export`. |
| **React Router** | None in config (route `headers` export, deepest wins; host files) | — | — | — | — |
| **TanStack** | None (route `headers()`, middleware; host `_headers`) | — | — | — | — |
| **Nuxt** | `routeRules['/path/**'].headers` | rou3/URLPattern (Nuxt 5: `*` matches nested segments) | None | Route rules merge (more specific over less) | Mapped to Netlify/Vercel native header rules where possible. |
| **SvelteKit** | None (`handle`, `setHeaders`); Cloudflare/Netlify `_headers` = static assets only | — | — | — | — |
| **SolidStart** | None (middleware); Nitro `routeRules` not documented (unverified) | — | — | — | — |
| **Astro** | `server.headers` = **dev/preview only**; production via adapter `staticHeaders` (CSP) or host `_headers` | — | — | — | — |

**Void gap:** none for the core feature. Void is ahead of 5/7. Missing versus Next.js: `has`/`missing` request conditions (Differentiator) and named captures in header patterns.

## Config-level redirects

| Framework | Mechanism | Source syntax | Status codes | Query handling | Conditions / host | Order & precedence |
|---|---|---|---|---|---|---|
| **Void** | `routing.redirects: { '/old': '/new', '/blog/*': { to, status } }` + `public/_redirects` | `*` (any chars incl. `/`) captured as `:splat`. **Undocumented (src `packages/edge/src/pattern.ts`):** `:name` (one segment) and `:name*` (multi-segment) named captures | 301, 302 (default), 303, 307, 308 | Request query merged into `Location`; on a per-key conflict **the destination wins**; a destination ending in `?` drops the incoming query; `#fragment` is preserved after the merge | **Host-prefixed sources** `https://www.example.com/*` (literal https host; no port, wildcard or userinfo; `http://` and `//` rejected). External destinations allowed. `routing.alwaysUseHttps` → 308 (Cloudflare only; localhost exempt). | **First match wins.** Config redirects → config rewrites → `_redirects` rules in one ordered list; runs **before** assets, ISR, SSR and user middleware. Duplicate sources are linted. |
| **Next.js** | `redirects()` (async) | path-to-regexp incl. regex groups | `permanent` → 308/307, or `statusCode` | Query passed through | `has` / `missing` (header/cookie/host/query) with captures; `basePath: false`, `locale: false` | Headers → **redirects** → proxy → beforeFiles rewrites → filesystem…; unavailable with `export`. |
| **React Router** | None in config (`redirect()` in loaders/actions/middleware; host files) | — | — | — | — | — |
| **TanStack** | None (`redirect()` in `beforeLoad`, `statusCode`) | — | — | — | — | — |
| **Nuxt** | `routeRules.redirect: '/new' \| { to, status }` (Nuxt 5 renames `statusCode` → `status`, with a warning); `definePageMeta({ redirect })` | rou3/URLPattern | Any | not documented | none | **Also applied client-side** via the app manifest; mapped to Netlify/Vercel native redirects. |
| **SvelteKit** | None (`handle` / `redirect()`; external redirects need opt-in in v3) | — | — | — | — | — |
| **SolidStart** | None (middleware) | — | — | — | — | — |
| **Astro** | `redirects: { '/old': '/new' \| { status, destination } }` | File-route syntax; dynamic params must match (`/blog/[...slug]` → `/articles/[...slug]`); static and dynamic can't mix | Default **301 (GET) / 308 (other)** | not documented | External `http(s)` since 5.2 | **File routes win over redirects.** Static output without an adapter emits **meta-refresh HTML** (status ignored); adapters write host config. `redirectPage` [exp]. |

**Behavioral differences that matter:**
- **Where redirects run.** Void evaluates redirects before the Worker on its platform, and before any route on other targets, so a redirect beats a real page. Astro does the opposite: file routes win. Next.js sits in between (before the filesystem, after headers).
- **Client navigation.** Nuxt applies redirect rules during client navigation. Void's client router sees a followed `fetch` redirect (`response.redirected`) and re-targets the visit, or does a full load if the redirect goes cross-origin (src `navigation-engine.ts`). That is one extra round-trip but correct.

**Void gap:** mostly none; Void is ahead of 4/7. Missing versus Next.js:
- `has`/`missing` conditions on cookie, header and query (Differentiator).
- Regex sources.
- A wildcard host (only literal hosts are allowed).
- Named captures exist but are undocumented.

## Config-level rewrites, fallbacks and proxying

| Framework | Pre-route rewrite | Post-route fallback | External proxy | Client-navigation aware | Programmatic |
|---|---|---|---|---|---|
| **Void** | `routing.rewrites` ("forced", runs **before** static assets and routes); `_redirects` `200!` | `routing.fallbacks` (only when no asset or route matched); `_redirects` `200`; SPA apps fall back to `index.html` automatically | **No.** Destinations must be internal paths. | **No.** Docs warn that `<Link href="/docs">` may fetch loader data for `/docs`, not `/en/docs`; use `<a>`. | `c.rewrite()` in middleware: re-runs middleware at the destination; `c.isRewritten()`, `c.originalUrl()`; a destination without `?` keeps the query; a rewrite to an asset extension throws `VoidAssetRewriteError`; typed `RewriteDestination`. ISR keys on the **destination** path. Dev header `X-Void-Routing` names the matched rule and the file that declared it. |
| **Next.js** | `rewrites()` array (= afterFiles) or `{ beforeFiles, afterFiles, fallback }` | `fallback` phase | **Yes** (external URLs; incremental adoption) | **Yes** (applies to client-side routing) | `NextResponse.rewrite` in Proxy |
| **React Router** | None | None | None | — | Middleware only |
| **TanStack** | Router `rewrite` (input/output; client + server). Runtime code, not config. | — | — | **Yes** | `basepath` is implemented as a rewrite |
| **Nuxt** | No rewrite key; `routeRules.proxy: '/x' \| { to, ...h3 proxy options }` | — | **Yes** (`proxy`) | Not documented | Server middleware |
| **SvelteKit** | `reroute` hook (universal, internal only, async with `fetch`, cached per URL on the client) | — | Catch-all `+server` or platform rules; `server.proxy` in dev only | **Yes** (`reroute` runs on the client) | — |
| **SolidStart** | None | — | Host config | — | Middleware |
| **Astro** | None in config | — | — | — | `Astro.rewrite()`, middleware `next('/path')` |

**Behavioral differences that matter:**
- Void's two phases map onto Next.js's `beforeFiles` (rewrites) and `fallback` phases. It has no `afterFiles` phase (after static files, before dynamic routes).
- Client-aware rewriting is the real behavioral difference. With Next.js rewrites, SvelteKit `reroute` or TanStack `rewrite`, client navigation resolves the same route as SSR. In Void, a rewritten URL can resolve differently on client navigation than on a full load.

**Void gap:** partial.
- External proxy rewrites (Differentiator: Next.js, Nuxt).
- Rewrites applied in client navigation (Common: Next.js, TanStack, SvelteKit).
- No `afterFiles` phase.

## Trailing slash

| Framework | Option | Values / default | Behavior |
|---|---|---|---|
| **Void** | **None** (not in `RoutingConfig`) | — | Fixed, undocumented (src `routing-pages.ts`): an **unmatched** `/x/` (GET/HEAD, not `/api`, no extension, no fallback hit) → **301** to `/x`, query kept. Static assets: only via the Cloudflare passthrough `cloudflare.assets.html_handling` (`auto-trailing-slash` \| `force-trailing-slash` \| `drop-trailing-slash`). Prerender always writes `about.html`. Link active-state matching treats the slash as significant. |
| **Next.js** | `trailingSlash` | `false` (default: `/about/` → `/about`) \| `true` (reverse; files and `.well-known/` exempt) | Redirect; `skipTrailingSlashRedirect` escape hatch; affects the `export` file layout. |
| **React Router** | None | — | `.data` URLs are trailing-slash aware in v8. |
| **TanStack** | Router `trailingSlash` | `'never'` (default) \| `'always'` \| `'preserve'` | Router-level normalization. |
| **Nuxt** | No global policy | — | vue-router `strict` matching; `<NuxtLink trailingSlash: 'append'\|'remove'>` rewrites hrefs only. |
| **SvelteKit** | Page option `trailingSlash` | `'never'` (default) \| `'always'` \| `'ignore'`; cascades from layouts | Redirects to the canonical form; drives `about.html` vs `about/index.html`. |
| **SolidStart** | None found | — | — |
| **Astro** | `trailingSlash` | `'ignore'` (default) \| `'always'` \| `'never'` | Production redirect 301 (GET) / 308 (other); a dev warning page; endpoints with an extension are exempt; `build.format` changes files and `Astro.url`. |

**Void gap:** missing. No policy option, no `always` mode, no per-route control, and no output-format coupling. Common (4: Next.js, TanStack, SvelteKit, Astro).

## Base path and asset prefix / CDN

| Framework | App base path | Link/router integration | Asset prefix / CDN | Notes |
|---|---|---|---|---|
| **Void** | **None.** No routing base; route patterns are always root-relative. | — | **None.** Vite `base` is effectively unsupported for SSR pages: the production asset tags (entry `<script>`, CSS `<link>`, `modulepreload`) are built as `'/' + file` (src `packages/void/src/runtime/routing-assets.ts`), so a non-root or CDN `base` isn't applied to them. Only Vite-generated client imports honor it. A custom `base` also forces every page through the Worker on Cloudflare (docs/guide/ssg.md). | Hashed-asset dir is configurable via Vite `build.assetsDir` (immutable caching follows it). |
| **Next.js** | `basePath` (build-time) | Auto-prefixes `next/link`, router and config rules (`basePath: false` per rule); **not** `next/image` `src` or `<Form formAction>` | `assetPrefix` | Used by Multi-Zones. |
| **React Router** | `basename` (default `/`) | Router, `discoverRoutes`, `useFormAction` | Not documented (Vite `base`; from memory, unverified) | — |
| **TanStack** | Router `basepath` (implemented as a rewrite) | Yes | Vite `base`; **`transformAssets`** [exp] (prefix string, `{ prefix, crossOrigin }`, or per-asset callback; cached; warmup) | Server-fn base `/_serverFn`. |
| **Nuxt** | `app.baseURL` (runtime override `NUXT_APP_BASE_URL`) | Yes | `app.cdnURL` (production; `NUXT_APP_CDN_URL`); `app.buildAssetsDir` (`/_nuxt/`) | Dynamic `:src` values need manual prefixing. |
| **SvelteKit** | `paths.base` (`''` or `/x`) | Manual via `resolve()`; prerender flags out-of-base links | `paths.assets` (absolute URL; incompatible with service workers); `paths.relative` (default `true`); `asset()` | `appDir` (default `_app`). |
| **SolidStart** | `<Router base>` | `<A>` | Not documented | — |
| **Astro** | `base` (+ `--base`) | **Manual prefixing** (no link helper) | `build.assetsPrefix` (string, or a per-extension map with `fallback`) | `BASE_URL` normalized by `trailingSlash`. |

**Void gap:** missing on both counts.
- Base path is Table stakes (7/7).
- Asset prefix is Common (Next.js, Nuxt, SvelteKit, Astro stable; TanStack [exp]).

Design notes:
- A base path touches the route matcher, the `Link`/`useForm`/`router.visit` URL builders in all 4 adapters, typed `routeUrl()`, the edge rules, `/_void/pages/*.json` and `/api` detection.
- An asset prefix needs `routing-assets.ts` to stop hard-coding `/`.

## Standalone / self-contained server output and embedding

| Framework | Self-contained artifact | Dependency handling | Entry / embedding | Production server settings (env) |
|---|---|---|---|---|
| **Void** | Node/Bun/Deno: `dist/ssr/index.js` (starts the server) + `dist/ssr/app.js`; deploy `dist/ssr` + `dist/client` together. Cloudflare: a fully bundled Worker (the Worker build sets `resolve.external = []`, src). | `void`, `@void/*` and installed packages that import `void` are inlined. Other dependencies stay external, so production **`node_modules` is required**. `@hono/node-server` is explicitly external; native-addon deps must be app `dependencies` (docs + src `plugin-node-target.ts`). No file tracing, no single binary. | `app.js` default-exports the Hono app. Use `app.fetch(Request)` in any fetch host, mount it in Hono, or call it from tests; `vite preview` uses it. | **`PORT` only** (default 3000). Generated entries are `serve({ fetch, port })` / `Bun.serve` / `Deno.serve` (src `router/compile.ts` `compileNodeServer`): no host or socket option, no graceful shutdown, no proxy/forwarded-header trust, no body-size limit. |
| **Next.js** | `output: 'standalone'` → `.next/standalone` with **traced** `node_modules` + `server.js`. Doesn't copy `public` or `.next/static`; can't combine with a custom server. | `@vercel/nft` tracing; `outputFileTracingRoot`, `outputFileTracingIncludes`/`Excludes`. | Custom server (non-standalone). | `PORT`, `HOSTNAME`; self-hosting guide: graceful shutdown, multi-instance (shared cache, keys), streaming through proxies, `sharp`. |
| **React Router** | Not self-contained (server build + `node_modules`; Docker templates). | Externals. | `createRequestHandler` in Express/any server; custom server compiled via the Environment API. | Via your server. |
| **TanStack** | Nitro `.output` (`node .output/server/index.mjs`); self-containment not stated. | Per Nitro. | `export default { fetch }` server entry. | Nitro env. |
| **Nuxt** | `.output/` **self-contained**; Nitro v3 **bundles every dependency** by default. | Bundled; Vue compiler mocked out of the server bundle (~860 KB saved). | Nitro presets. | `NITRO_PORT`/`PORT`, `NITRO_HOST`/`HOST`, `NITRO_SSL_CERT`/`KEY`; `node_cluster`. |
| **SvelteKit** | `adapter-node` `build/` (+ prod `node_modules`; devDeps bundled). **`adapter-bun` `compile: true` → a single executable** (runtime, assets and deps embedded; cross-compile). | Deps external (node) / embedded (bun compile). | `handler.js` for Express/Polka/http. | Node: `PORT`, `HOST`, `SOCKET_PATH`, `PROTOCOL_HEADER`/`HOST_HEADER`/`PORT_HEADER`, `ADDRESS_HEADER`/`XFF_DEPTH`, `BODY_SIZE_LIMIT`, `SHUTDOWN_TIMEOUT`, `IDLE_TIMEOUT`, `KEEP_ALIVE_TIMEOUT`, `HEADERS_TIMEOUT`, systemd socket activation; Bun has an equivalent set. |
| **SolidStart** | Nitro output per preset (not documented explicitly). | Per Nitro. | — | Nitro env. |
| **Astro** | Node `mode: 'standalone'` (`node ./dist/server/entry.mjs`, serves `dist/client`, immutable `_astro/`); Docker recipe. | Not stated. | Node `mode: 'middleware'` exports `handler` for Express/Fastify. | `HOST`, `PORT`, `SERVER_CERT_PATH`/`SERVER_KEY_PATH`; `bodySizeLimit` (1 GB); `staticHeaders`. |

**Behavioral differences that matter:**
- Void's `app.js` is a clean embedding seam. It is comparable to SvelteKit `handler.js` (which also serves prerendered pages and static assets), Astro middleware mode (no static serving) or React Router's request handler. Being a Web `fetch` app, it embeds in fetch-native hosts without a Node bridge.
- Production hardening, though, is left to the user or a reverse proxy. SvelteKit, Astro, Nuxt and Next.js document host binding, proxy headers, body limits and shutdown.

**Void gap:** partial.
- Dependency bundling or tracing for a node_modules-free artifact (Common: Next.js, Nuxt, SvelteKit-bun).
- Production server settings: host, proxy headers, body limit, graceful shutdown (Common: Next.js, Nuxt, SvelteKit, Astro).

## Skew protection / version-mismatch handling

| Framework | Version identity | Detection | Recovery | Host routing to the old deployment | Related |
|---|---|---|---|---|---|
| **Void** | **None** (no deployment ID or build ID exposed to the client; grepped `skew`, `deploymentId`, `preloadError`, `chunk load`). | None | Partial, incidental. A GET page response **without** `X-VoidPages` (error page, non-Void response) triggers a full document load. But a **failed dynamic import** of a page/layout chunk, or a new-deploy payload naming a component the old client doesn't know (`pages: Unknown page component`), **rejects the navigation with no reload** (src `navigation-engine.ts`, `client.ts`, `link.ts`). | None | Hashed assets are immutable and "can be reused across deploys" at the edge cache (no retention guarantee). The ISR cache is namespaced by deployment and wiped on deploy (src `packages/isr`). The client ships the full route manifest eagerly. |
| **Next.js** | `deploymentId` / `NEXT_DEPLOYMENT_ID` | `x-deployment-id` request header on navigations; `x-nextjs-deployment-id` response header; `data-dpl-id` on `<html>` | **Hard reload on mismatch** | `?dpl=<id>` on JS/CSS/image URLs; the host/CDN must route on it | ID in `use cache` keys; `outputHashSalt` + immutable assets; Server Action IDs rotate per build ("Failed to find Server Action"). |
| **React Router** | Manifest `version` | Lazy route discovery `/__manifest?version=…` | Navigation → reload the destination; fetcher → reload the current document. [exp] `unstable_useRouteDiscovery({ onManifestMismatch })` with `defaultBehavior()`, `loadAllRoutes()` (needs old assets retained) | None | `routeDiscovery: { mode: 'lazy' \| 'initial' }`. |
| **TanStack** | None | — | — | — | Server-fn IDs are stable hashes; deterministic custom IDs are recommended. |
| **Nuxt** | `buildId` | `experimental.appManifest` (on) polls every `checkOutdatedBuildInterval` (1 h; `false` disables) → `app:manifest:update` hook | `emitRouteChunkError: 'automatic'` (hard reload of the target route on chunk error) \| `'automatic-immediate'` \| `'manual'` (`app:chunkError`) \| `false`; `restoreState` [opt-in] restores `useState` after the reload | None | `entryImportMap` keeps chunk hashes stable. |
| **SvelteKit** | `version.name` (deterministic, e.g. a git SHA; default = build timestamp) | `version.pollInterval` (3 600 000 ms; `0` = off) + the `x-sveltekit-version` header on data/remote/form responses + tab focus/visibility; `updated.current`, `updated.check()` | On route-module load failure with a new version detected → full-page navigation (+ service worker update) | `adapter-vercel` cookie-based skew protection | — |
| **SolidStart** | None | — | — | — | — |
| **Astro** | Adapter-provided | — | — | Vercel `skewProtection` (Pro/Enterprise); Netlify automatic (deploy ID on internal fetches for actions, server islands, view transitions, prefetch) | Adapter hooks `client.internalFetchHeaders`, `assetQueryParams`; `ASTRO_KEY` keeps the server-island key stable across deploys. |

**Behavioral differences that matter:**
- Everyone who handles skew converges on the same recovery: **detect a newer version, then do a hard navigation to the target URL**. Detection comes from an ID header (Next.js, SvelteKit), a manifest version, polling (Nuxt, SvelteKit) or a chunk error (Nuxt, SvelteKit).
- Void has the cheapest possible hook point. Every client navigation already goes through one fetch path with a custom header (`X-VoidPages`), so a response header carrying the deploy ID plus a reload-on-mismatch would cover navigations. Handling `vite:preloadError`/import rejection would cover chunk failures.

**Void gap:** missing. Common (5: Next.js, React Router, Nuxt, SvelteKit, Astro). Design notes:
- Cloudflare readiness checks already use a version-metadata binding or Version URLs (docs/integrations/cloudflare.md), which is a natural source of a deployment ID.
- Old-asset retention across deploys is not guaranteed today. On a Void platform, missing `/assets/*` files 404 (docs/guide/app-types.md).
- Server-side handlers are referenced by route rather than per-build IDs, so Void avoids Next.js's "Failed to find Server Action" class of skew.

## Multi-app / zones / microfrontends

| Framework | Support |
|---|---|
| **Void** | None. Related only: `voidPlugin({ auxiliaryWorkers })` runs extra Cloudflare Workers alongside the app (`configPath`, `config`, `viteEnvironment`, `devOnly`); host-prefixed redirects; deploying other frameworks via `voidPlugin()` (framework mode). |
| **Next.js** | **Multi-Zones** (stable guide): each zone sets `assetPrefix` and is stitched by rewrites or proxy; navigation between zones is a hard navigation. |
| **React Router** | None found. |
| **TanStack** | None found. |
| **Nuxt** | `future.multiApp` [exp, tracker issue]; layers (`extends`, code sharing, not runtime composition); `asyncEntry` for module federation. |
| **SvelteKit** | `embedded: true` (mount inside a larger page; listeners on the parent; only one app per page). |
| **SolidStart** | None found. |
| **Astro** | None found. |

**Void gap:** missing. Differentiator (Next.js stable; Nuxt [exp]). Depends on base path and asset prefix first.

## Build-time env inlining rules

| Framework | Client-exposed values | Inlined at build? | Runtime public config | Server env | Schema / validation | Guardrails |
|---|---|---|---|---|---|---|
| **Void** | `VITE_*` only; **fixed prefix even if `envPrefix` is customized** | Yes. **Builds ignore `.env` for client values** (supply them from the build shell or a schema default); SSR uses the same build values | **None** | Cloudflare: `env` from `void/env`, validated again at Worker startup; secrets via `void secret`; `worker.vars` plaintext. Node/Bun/Deno: `process.env` / `Deno.env.get()` (`void/env` is a compile error) | `env.ts` `defineEnv` (`string/number/boolean/url/email/oneOf/json`, `.optional()`, `.default()`, any Standard Schema); `void env check [--remote]`, `void env types` | Reading a non-`VITE_` key of `void/env` in client code **fails the client build** (src `plugin-env-client-guard.ts`); `__VOID_` names reserved; only a single root `.env` (no `.env.local`/`.env.[mode]`); diagnostics redact values |
| **Next.js** | `NEXT_PUBLIC_*` | Yes (others become `''` in client bundles) | None (read server-side during dynamic rendering) | `process.env` at runtime for dynamic rendering | None | — |
| **React Router** | Vite default (`VITE_*`); not documented by React Router | Yes (Vite) | — | — | — | — |
| **TanStack** | `VITE_` (Vite) / `PUBLIC_` (Rsbuild) | Yes | Pattern: serve it via a server function | `process.env` **per request** (module-scope reads are undefined on Workers and may be inlined into client code); `server.build.staticNodeEnv` (default `true`) | — | Import protection for `*.server.*` |
| **Nuxt** | `runtimeConfig.public` | **No.** Serialized in the payload; **overridable at runtime** by `NUXT_PUBLIC_*` | **Yes** | `runtimeConfig` (private keys server-only), `NUXT_*` overrides at runtime; `.env` read by the CLI, not the production server | None | `$development`/`$production`/`$env.<name>` overrides |
| **SvelteKit 3** | `src/env.ts` `defineEnvVars({ X: { public: true } })` → `$app/env/public`, `%sveltekit.env.X%` in `app.html` | **Dynamic (runtime) by default**; `static: true` inlines (dead-code elimination) | **Yes** (dynamic public) | `$app/env/private` (blocked from the browser) | Standard Schema or a function; fails **start or build** (relax with `building`) | `$env/*` deprecated |
| **SolidStart** | `env:client` (`CLIENT_*`) | Yes (build-time) | No | `env:server` (`SERVER_*`, build-time, client import fails), `env:server/runtime` (runtime) | — | — |
| **Astro** | `PUBLIC_*` (Vite); `astro:env` `context: 'client'` | Yes | No (client vars inlined) | `astro:env/server` (public = runtime; `access: 'secret'` via `getSecret`) | `envField` string/number/enum/boolean × context × access; `validateSecrets` | "Client secrets are impossible" |

**Behavioral differences that matter:**
- Void is the only framework that **ignores `.env` during production builds** for public values, which prevents a developer's local value from shipping. Combined with the build-failing client guard, it is the strictest model here.
- Void has no way to change a public value without rebuilding. Nuxt and SvelteKit 3 make that the default; TanStack documents a server-function pattern.
- The typed schema is Cloudflare-only. Node/Bun/Deno apps fall back to raw `process.env` (no validation, no types), while SvelteKit/Astro schemas work on every adapter.

**Void gap:** partial.
- Runtime public config (Differentiator: Nuxt, SvelteKit).
- A typed env schema on non-Cloudflare targets.
- Per-mode env files (`.env.[mode]`, `.env.local`: TanStack, SvelteKit, Astro via Vite). This one is deliberate in Void.

## Build hooks and build controls (brief)

| Framework | Post-build hook / manifest | Build controls |
|---|---|---|
| **Void** | None of its own (Vite plugin hooks apply). `inference.build` (custom build command), `inference.outputDir`. | Vite options pass through; `worker.limits.cpu_ms`. |
| **Next.js** | Adapter `onBuildComplete` | `generateBuildId`, `distDir`, `--debug-build-paths`, static-generation concurrency/retry [exp], `productionBrowserSourceMaps`, `enablePrerenderSourceMaps`. |
| **React Router** | `buildEnd({ buildManifest, reactRouterConfig, viteConfig })` | `--sourcemapClient/Server`, `--minify`, `serverModuleFormat`. |
| **TanStack** | — | `server.build.staticNodeEnv`. |
| **Nuxt** | Nuxt/Nitro build hooks (modules) | `sourcemap {server, client}`, `experimental.buildCache`, `compileHints`. |
| **SvelteKit** | Adapter `adapt(builder)` | `output.bundleStrategy`, `linkHeaderPreload`. |
| **SolidStart** | — | Nitro options. |
| **Astro** | `astro:build:start/setup/ssr/generated/done` | `build.concurrency`, `parallelPrerender` [exp], `incrementalBuild` [exp]. |

**Void gap:** partial. There is no framework-level post-build hook that exposes the route/prerender manifest (Common: Next.js, React Router, Nuxt, Astro). This matters mainly for an adapter story.
