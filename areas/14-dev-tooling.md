# 14. Dev tooling & observability

**Versions:** Void 1.6.2 · Next.js 16.4 (App Router) · React Router 8 (framework mode) · TanStack Start 1.169 (React) · Nuxt 5.0 pre-release (4.x is stable) · SvelteKit 3.1 · SolidStart 2.0 · Astro 7.4

**Markers:** [exp] experimental, unstable or canary · [CC] Next.js with Cache Components on (the create-next-app default) · (src) found in Void's source but not in its docs · (unverified) not confirmed in docs or source

**Paths:** Void file paths are in the `voidzero-dev/void` repo. Short paths such as `pages/scan.ts` are under `packages/void/src/`; paths that start with a package name, such as `react/src/…`, are under `packages/`.

## At a glance

- **The dev loop is strong where it matters for an edge-first framework.** The app runs in **workerd** via `@cloudflare/vite-plugin`, with persisted local D1/KV/R2 and an optional remote-bindings mode. That is on par with or ahead of the others: React Router, TanStack, SolidStart and Astro also run workerd for Cloudflare; Next.js is Node-only; SvelteKit only emulates bindings.
- **Server-code edits** take effect on the next request without a restart, but nothing refreshes the page's data automatically. React Router's Hot Data Revalidation and Next.js's Server Component refresh do.
- **Error overlay exists but is undocumented and server-only.** Dev 500 document responses get an overlay with the `cause` chain and stack frames linked via `vscode://` (src). Client runtime errors get nothing beyond the console; compile errors use Vite's overlay.
- **Biggest gaps:**
  - No in-browser devtools or route/cache inspector (5/7 have one).
  - No server error-reporting hook (4/7, +2 partial).
  - No instrumentation/OpenTelemetry (3/7).
  - No MCP server (4/7) and no `llms.txt` (3/7).
  - No web-vitals helper (1/7), bundle analyzer (2/7) or configurable logger (1/7).
- **Clearly ahead in two places:**
  - **Generators.** `void gen model|route|middleware|ssr|migration|cron|queue`; no other framework documents in-project generators (Nuxt `nuxt add` is unverified).
  - **Agent onboarding.** Bundled version-matched docs, a managed `AGENTS.md` section, and two skills auto-linked into 16 detected agents' skill dirs. Only Next.js is comparable; it adds a built-in app-aware MCP endpoint, which Void lacks.
- **Type generation is on par** (`void prepare`, automatic in dev/build); there is no `typecheck` wrapper (Nuxt, SvelteKit, Astro have one).
- **Observability is platform-shaped.** It consists of a structured JSON logger (`void/log`) plus `void project logs/requests`. There are no framework hooks, so third-party APM/Sentry integrations have nowhere to attach (Next.js, React Router, SvelteKit, Nuxt all have one).

## Gap list for this area

| Gap in Void | Who has it (mechanism, briefly) | Prevalence | Notes for design (constraints, dependencies, adapter impact) |
|---|---|---|---|
| In-browser devtools (route, page-data, cache inspection) | Next.js DevTools + Navigation Inspector [CC]; TanStack Router devtools; Nuxt DevTools; SolidStart dev overlay (server-fn inspector); Astro Dev Toolbar (extensible) | Common (5) | Must be UI-library-agnostic (4 adapters) → Astro-style web-component toolbar. Data already exists: page object, `X-Void-Routing`, `x-isr-cache`, bindings, dev email inbox, cron/queue triggers. |
| Server error-reporting hook | Next.js `onRequestError`; React Router `handleError`; Nuxt Nitro `error` hook; SvelteKit `handleError` (+ TanStack, SolidStart partial) | Common (4) | Hook into `app.onError` and the deferred-stream/action error paths; needs `waitUntil` on Workers; must also see masked production errors. |
| Client error-reporting hook | Next.js `instrumentation-client`; React Router `HydratedRouter onError`; SvelteKit client `handleError` | Common (3) | Lives in shared `navigation-engine.ts` / `client.ts` → covers all adapters. Pair with render-error capture per adapter (React boundaries, Vue `errorCaptured`, etc.). |
| Instrumentation / OpenTelemetry | Next.js (`register()` + built-in spans), SvelteKit (`tracing.server` + `instrumentation.server.js`), React Router (stable `instrumentations` wrap API); TanStack [exp] recipe | Common (3) | Startup hook must run before app code in workerd and in Node. Span points: rules, middleware, handler/loader, action, render, ISR. Consider React Router's read-only wrap model (can't break requests). |
| MCP server | Next.js built-in `/_next/mcp` (app-aware); Nuxt and Astro hosted docs MCP; SvelteKit `sv add mcp` | Common (4) | The highest value is a dev-server MCP (errors, logs, routes, bindings, resources, deploy status), which builds on the skills Void already ships. App-aware MCP alone is a Differentiator. |
| `llms.txt` for docs | Next.js, Nuxt, SolidStart (inferred) | Common (3) | VitePress docs site; cheap. |
| Auto data refresh on server-code edits | React Router Hot Data Revalidation; Next.js Server Component refresh | Differentiator (2) | A dev-only HMR event from the worker environment → client `router.refresh()`; respects `preserveState`. |
| Client runtime error overlay / documented overlay | Next.js (server+client+build, source-mapped); SolidStart `devOverlay`; Astro overlay | Common (3) | Void's server overlay exists (undocumented, VS Code links only). Extend it to client errors and make the editor configurable. |
| Web vitals helper | Next.js `useReportWebVitals` (with soft-nav fields) | Differentiator (1) | Navigation IDs are already in the client engine. |
| Bundle analyzer | Next.js `next analyze`; Nuxt `nuxt analyze` | Differentiator (2) | Add Worker-size reporting against Workers limits. |
| Build timings / profiling | Next.js `--profile`/`--debug`; React Router `--profile`; Astro `--timings` | Common (3) | Prerender and deploy-time prerender timings are a natural first target. |
| Configurable logger (levels, sinks, debug) | Astro Logger API | Differentiator (1) | `void/log` contract (`{ msg, …fields }`) must stay stable for `void project logs` filtering. |
| Dev log forwarding (browser↔terminal) / request logging | Next.js `logging.browserToTerminal`, `incomingRequests`, `fetches`; Nuxt `features.devLogs` | Differentiator (2) | Useful for agents reading only the terminal. |
| Add-on / integration installer | `astro add`, `sv add`, `nuxt module add` | Common (3) | Could cover auth, DB dialect switch, adapters, Tailwind. |
| Upgrade codemods | `next upgrade` + `@next/codemod`; `nuxt upgrade`; `sv migrate` | Common (3) | `void migrate` covers config only. |
| Template / example flag on create | Next.js `--example`, React Router `--template`, Astro `--template`, SolidStart templates, TanStack `gitpick` | Common (5) | Void has 4 starters × 4 frameworks. |
| Typecheck wrapper | `nuxt typecheck`, `svelte-check`, `astro check` | Common (3) | Per-adapter checker differs (tsc / vue-tsc / svelte-check). |
| Agent-aware dev server (background mode, lock file, JSON logs, health) | Astro (full), Next.js (lock file) | Differentiator (2) | `/__void/ping` exists internally. |
| Coded diagnostics + debugging guide | Next.js messages, Nuxt error codes, SvelteKit catalog, Astro error reference; debugging guides (Next.js, Nuxt, SvelteKit) | Common (4) | Document `VOID_INSPECTOR_PORT`. |
| Page/layout generator | Nuxt `nuxt add` (unverified) | Differentiator (0–1) | Trivial given `gen ssr` exists. |

## Where Void is ahead

- **In-project generators for full-stack building blocks.** `void gen model` (Drizzle table + CRUD routes with an auto-detected validator), `route`, `middleware` (auto-ordered), `ssr` per UI library, `migration`, `cron`, `queue`. None of the other 7 documents in-project generators.
- **Agent onboarding without extra installs.** Version-pinned docs in `node_modules/void/docs/`, a managed `AGENTS.md` section, and 2 skills auto-linked into 16 agents' skill directories at `void init`, all reading the installed docs. Only Next.js is comparable; its skills are installed separately.
- **Production-shaped local runtime by default.** workerd, persisted local D1/KV/R2 (`persistTo`), a remote-bindings switch (`remote` / `VOID_REMOTE=1`), auxiliary Workers, and a dev email inbox plus cron/queue triggers. Plus a **binding-detection toast with one-click dev-server restart**, which is unique.
- **Edge-rule and cache debugging headers.** `X-Void-Routing` (matched rule and declaring file), `X-Void-No-Match`, `x-isr-cache` (undocumented). Rule files hot-reload without a restart.
- **Env validation tooling.** `void env check [--remote]` with value redaction, plus build-time guards against shipping server keys.
- **Structured logging aligned with first-party log tooling.** One JSON line per call with `child()` field binding, filterable by message and fields in `void project logs`.
- **Server error overlay with the `cause` chain** (undocumented). Nuxt also shows causes; Next.js shows more overall.

## Dev server and HMR

| Framework | Command / engine | Client HMR | Server-code edits | Runtime fidelity in dev | Notable options |
|---|---|---|---|---|---|
| **Void** | `vite dev` / `vp dev` (Vite 8) | Via each adapter's Vite plugin: React Fast Refresh (preamble injected into SSR HTML, src `routing-assets.ts`), `@vitejs/plugin-vue`, `vite-plugin-svelte`, `vite-plugin-solid`. **Island pages and `.md` pages force a full reload** (no client HMR). | Content edit → module invalidated, re-evaluated in workerd **on the next request** (no restart, no browser refresh, no data refresh). File add/remove under routes/pages → route module regenerated + full reload. `_redirects`/`_headers` change → rules re-merged + full reload. `env.ts` change → full reload. **New binding import detected (DB/KV/storage/AI/sandbox/email/auth) → in-page toast with click-to-restart** (src `plugin-restart.ts`, `/__void/restart` with a per-server token). | **Cloudflare target: workerd** (`@cloudflare/vite-plugin`), local D1/KV/R2 persisted to `.void/` (`voidPlugin({ persistTo })`), `remote: true` / `VOID_REMOTE=1` = deployed D1/KV/R2; Workers AI always remote. `auxiliaryWorkers` run alongside. Node target: Node. `vite preview` = workerd with local bindings (CF) or `app.js` (Node). | Dev email inbox, dev trigger endpoints for cron/queues (out of scope); undocumented `VOID_INSPECTOR_PORT` (workerd inspector port, `false` disables; src `index.ts`). |
| **Next.js** | `next dev` (Turbopack default; `--webpack`) | Fast Refresh JS/TS/CSS | **Server Component edits refresh** (HMR fetch cache) | Node only | `-p`/`-H`, `--experimental-https[-key\|-cert\|-ca]`, persistent Turbopack FS cache, `.next/dev/lock` (a second `next dev` prints the running server), `allowedDevOrigins`, dev and build can run concurrently, memory knobs [exp] |
| **React Router** | `react-router dev` (Vite) | Fast Refresh; route exports HMR-compatible; an extra custom export forces a full reload | **Hot Data Revalidation**: loaders affecting the current page re-run with no reload | workerd via `@cloudflare/vite-plugin`; Node otherwise | Vite flags; `unstable_optimizeDeps` [exp]; middleware-mode custom servers |
| **TanStack** | `vite dev` / `rsbuild dev` | Vite/Rsbuild | Not documented | workerd via Cloudflare plugin; Netlify plugin emulates the platform | Route tree regenerated on file change |
| **Nuxt** | `nuxt dev` | Vite | Server routes hot-reload | Nitro on Node; `@nuxt/vite-server` [exp] runs worker targets in workerd | `devServer { port, host, https, cors, loadingTemplate }`, `--inspect`, `experimental.watcher`, `devServerHandlers` |
| **SvelteKit** | `vite dev` (5173) | Svelte HMR; disabled on `csr = false` pages; full reload after an unexpected error | Vite SSR module runner (Node) | Node; Cloudflare bindings **emulated** via `platformProxy` (`getPlatformProxy`), not the workerd runtime | Service worker not bundled in dev |
| **SolidStart** | `vite dev` | Vite incl. route CSS | Not documented | Cloudflare plugin runs SSR in workerd; Netlify emulation | `// @refresh reload` in entries |
| **Astro** | `astro dev` (4321) | Vite | Vite | Cloudflare adapter: workerd for dev, preview **and** prerender | Hotkeys (`s`/`o`/`q`), `--background`, `--json`, `stop`/`status`/`logs`, lock files, programmatic `dev()` |

**Behavioral differences that matter:**
- **Edge fidelity.** Void runs real workerd *by default*, with production-shaped local bindings and a remote-bindings switch. React Router, TanStack, SolidStart and Astro get workerd only after you opt into the Cloudflare plugin or adapter; SvelteKit only emulates bindings. Void's binding-detection toast (prompting a restart when a new resource import appears) is unique.
- **Data freshness after a server edit.** In React Router, editing a loader updates the open page immediately. In Void the edit is live on the server, but the page keeps stale props until you navigate or reload.
- **Agent-friendly dev servers** (background mode, lock file with PID/port, health endpoint, JSON logs): Astro has all of these, Next.js has the lock. Void has a `/__void/ping` health endpoint, but it is internal to the restart flow.

**Void gap:** partial.
- No automatic page-data refresh on server-module edits (Differentiator: React Router HDR, Next.js RSC refresh).
- No dev HTTPS option of its own (Next.js, Nuxt; Vite `server.https` still works).
- No background/lock-file dev mode for agents (Differentiator: Astro, Next.js).
- The inspector port is undocumented.

## Error overlay

| Framework | Server errors | Client runtime errors | Build/compile errors | Editor links | Extras |
|---|---|---|---|---|---|
| **Void** | **Yes, undocumented** (src `runtime/routing-errors.ts`). Dev **500** HTML document responses (GET/HEAD, not `/api`, no extension, HTML-accepting) get an injected overlay: status, error + **`cause` chain** (depth-capped), parsed stack frames, minimize/restore. Also injected into a custom `public/500.html`. JSON/API/page-data error responses get none. A client navigation hitting a 500 falls back to a full document load, which then shows the overlay. | **None** (console only) | Vite's overlay (Vite behavior) | `vscode://file/…:line:col` only (no editor setting) | Same in all 4 adapters (server-side). `HTTPException` responses bypass it. |
| **Next.js** | Yes, source-mapped | Yes | Yes | Yes | [Cache Components] blocking-route insights with fix cards linking `/docs/messages/*` and a **Copy prompt** for agents; **Vulnerability Insight** for a known CVE in the installed version; `logging.browserToTerminal` |
| **React Router** | Unsanitized errors shown in `ErrorBoundary` in dev | Error boundary | Vite overlay (unverified) | — | — |
| **TanStack** | Not documented | — | Vite (unverified) | — | Import-protection violations print traces + code frames; dev "mock" mode keeps the app running |
| **Nuxt** | Dev error page with the `cause` chain | — | Overlay receives template diagnostics | — | Errors from deploy-target environments shown in the dev overlay |
| **SvelteKit** | Not documented | — | Vite overlay (unverified); `frame` excerpt for Svelte syntax errors | — | Dev `debugger` pause before a full reload on navigation failure |
| **SolidStart** | **`devOverlay`** (default `true`; excluded from production) | Yes ("inspecting application errors") | — | — | Also inspects **server function calls** |
| **Astro** | Dev overlay | — | Yes | — | Replaced by terminal logging if `500.astro` exists |

**Void gap:** partial.
- Client runtime and hydration errors have no overlay.
- No source-map statement (unverified whether frames are source-mapped under workerd).
- Editor links are VS Code-only.
- Errors on API/JSON page-data responses have no dev surface beyond the terminal.
- No agent-oriented "copy prompt" and no browser↔terminal log bridge.
- Undocumented.

## Devtools (in-browser panels, route inspection, cache inspection)

| Framework | In-browser panel | Route inspection | Cache / data inspection | Other |
|---|---|---|---|---|
| **Void** | **None** (grepped "devtools") | Dev-only **`X-Void-Routing`** response header (matched rule, destination and declaring file; `pass-through`); `X-Void-No-Match: 1` on unmatched requests; `.void/` route types. No route list command (`void info` lists resource names only). | **`x-isr-cache: HIT\|MISS\|STALE`** response header (undocumented, src `packages/isr`) | Binding-detection restart toast |
| **Next.js** | **Next.js DevTools** indicator (`devIndicators: { position }` or `false`), shows whether a route is static or dynamic | MCP `get_routes`; [Cache Components] **Navigation Inspector** freezes page-load and client-nav shells | — | Node inspector link from the overlay; React DevTools recommended |
| **React Router** | None | `react-router routes [--json]` (CLI route tree) | — | — |
| **TanStack** | **`@tanstack/react-router-devtools`**: `TanStackRouterDevtools` (dev-only), `…InProd`, `…Panel`; options `initialIsOpen`, `position`, `panelProps`, `shadowDOMTarget`, `containerElement`… | Router state, matches, masked routes (actual URL) | Router cache via panel | No server-function/middleware devtools |
| **Nuxt** | **`@nuxt/devtools`** (`devtools` option) | **Pages** tab (route names, params) | **Payload**, Virtual Files, Hooks, **Timeline**, Assets, Render Tree, Inspect, Vitest | `browserDevtoolsTiming` marks; `debug` hook timings; `features.devLogs`; `@nuxt/a11y` [alpha] |
| **SvelteKit** | Svelte **inspector** (vite-plugin-svelte `inspector`; element → source) | — | — | Debugging guides (VS Code, `--inspect`, WebStorm, Neovim) |
| **SolidStart** | **Dev toolbar/overlay** with a **server-function call inspector** | — | — | `createAsync({ name })` for debugging |
| **Astro** | **Dev Toolbar**: Astro menu ("Copy debug info"), **Inspect** (islands, props, directives), **Audit** (perf/a11y), Settings; `devToolbar.enabled/placement`; per-user `astro preferences` | — | Route cache: `X-Astro-Cache` header | **Extensible App API** (`addDevToolbarApp`, `defineToolbarApp`, client/server messaging, UI kit); `chromeDevtoolsWorkspace` [exp] |

**Behavioral differences that matter:**
- Void's debug surface is **headers you read in the Network tab**. Useful for edge rules and ISR, but nothing shows *page-level* state: which loader ran, its props, deferred keys, the shared props, island hydration status, or the prefetch cache.
- The extensible toolbar (Astro) and the module devtools (Nuxt) let integrations add panels. Void's adapters and resources (D1/KV/R2/queues/cron/email) are natural panel candidates: Void already ships a dev email inbox and dev trigger endpoints.

**Void gap:** missing. Common (5: Next.js, TanStack, Nuxt, SolidStart, Astro; SvelteKit has a partial inspector). Design notes:
- Must work across 4 UI libraries, so a framework-agnostic overlay (Astro-style web components) fits better than per-library devtools.
- Candidate data: the page object (`component`, `props`, `shared`, `deferred*`), the route match, `X-Void-Routing`, `x-isr-cache`, bindings and dev triggers.

## Type generation and type-check commands

| Framework | Generate | Automatic | Type-check command |
|---|---|---|---|
| **Void** | `void prepare` (all `.void/` types + TS config, no dev/build), `void env types` (`.void/env.d.ts`), `void init --tsconfig` | During `vite dev`/`vite build` | None (run `tsc`/`vue-tsc`/`svelte-check` yourself; not found) |
| **Next.js** | `next typegen` | dev/build | — (`next lint` removed in 16) |
| **React Router** | `react-router typegen [--watch] [--config] [--mode]` | dev | — |
| **TanStack** | `tsr generate` / `tsr watch` (Router CLI setups) | plugin | — |
| **Nuxt** | `nuxt prepare`; `prepare:types` hook | dev/build | **`nuxt typecheck`** (vue-tsc) |
| **SvelteKit** | `svelte-kit sync` (also via `prepare`) | dev/build | **`svelte-check`** (incl. omitted `$types` annotations) |
| **SolidStart** | None needed | — | — |
| **Astro** | `astro sync` (also hotkey `s`) | dev | **`astro check`** |

**Void gap:** none for generation. Minor: no `void check`/typecheck wrapper (Common: Nuxt, SvelteKit, Astro). This matters more for Void because Vue/Svelte SFCs need different checkers.

## Scaffolding and generators

| Framework | Create CLI options | Add-on / integration installer | In-project generators | Upgrade / migration |
|---|---|---|---|---|
| **Void** | `npm create void@latest` / `void init` with `--toolchain vite-plus\|vite`, `--framework react\|vue\|svelte\|solid`, `--starter sqlite\|postgresql\|mysql\|static`, `--deploy cloudflare\|void\|none`, `--tsconfig`, `--github` (Actions deploy workflow), `--git/--no-git`. Also sets up agents. | None | **`void gen model <name> [col:type[?]…]`** (Drizzle table + list/create/get-by-id routes; validator auto-detected: valibot/zod/arktype), **`gen route <path> [--methods]`**, **`gen middleware <name>`** (auto-numbered `01.auth.ts`), **`gen ssr [--react\|--vue\|--svelte\|--solid]`**, **`gen migration`**, **`gen cron`**, **`gen queue`**. No page/layout/component generator. | `void migrate` (legacy `void.json`/`wrangler.json(c)` → `void.config.ts` + `void.lock.json`) |
| **Next.js** | `create-next-app`: `--ts/--js`, `--tailwind`, `--react-compiler`, `--cache-components`, `--eslint/--biome/--no-linter`, `--app`, `--api`, `--src-dir`, `--empty`, `--turbopack/--webpack`, `--import-alias`, `--use-*`, **`--example`**, `--skip-install`, `--disable-git`, **`--agents-md`**, `--agent-feedback` | — | None | **`next upgrade [--revision] [--agent …]`**, `@next/codemod` |
| **React Router** | `create-react-router --template <repo>` | — | None (`react-router reveal` ejects entry files) | — |
| **TanStack** | `@tanstack/cli create` (package manager, add-ons); TanStack Builder (web, AI-first); `gitpick` examples | Add-ons at create time | None (auto-filled `createFileRoute` paths) | — |
| **Nuxt** | `create nuxt@latest` (npm/pnpm/bun/deno), `nuxt init` | **`nuxt module add <name>`** | `nuxt add` (component, page, layout, api…, from memory, **unverified**: CLI docs live in nuxt/cli) | **`nuxt upgrade`** |
| **SvelteKit** | `sv create` | **`sv add`** (prettier, eslint, vitest, playwright, better-auth, tailwind, drizzle, paraglide, mdsvex, storybook, `sveltekit-adapter=…`, mcp) | None | **`sv migrate sveltekit-3` / `app-state`** |
| **SolidStart** | `npm create solid` (template or official example, TS) | — | None | — |
| **Astro** | `create astro --template <example\|user/repo> --add <integration>` | **`astro add <integration>`** (installs + edits config) | None | — (agent prompt in the upgrade guide) |

**Behavioral differences that matter:**
- Void is the only framework whose generators produce **backend building blocks**: data model plus CRUD routes, middleware ordering, cron, queues and migrations. That matches its full-stack scope.
- The others invest in **ecosystem installers** (`astro add`, `sv add`, `nuxt module add`) and **upgrade codemods** (Next.js, SvelteKit, Nuxt). Void has neither. `void migrate` only migrates config, not code.

**Void gap:** partial.
- Page/layout generator (unverified competitor: Nuxt).
- Add-on/integration installer (Common: Nuxt, SvelteKit, Astro).
- Example/template flag (Common: Next.js `--example`, React Router `--template`, Astro `--template`, SolidStart, TanStack).
- Code-upgrade codemods (Common: Next.js, Nuxt, SvelteKit).

## AI-agent support

| Framework | Bundled version-pinned docs | `AGENTS.md` management | Skills | MCP | `llms.txt` | Agent-aware CLI / dev server |
|---|---|---|---|---|---|---|
| **Void** | **`node_modules/void/docs/`** (synced at package build) | **`void init`** creates or updates a Void section in `AGENTS.md`; asks first in existing projects and keeps user text; skipped in CI/non-interactive | **2 skills** (`void`, `migrate-vite-cloudflare-to-void`) **auto-linked** into detected agent dirs. 16 agents (src `cli/agents.ts`): Claude Code, Amp, Codex, Cursor, Windsurf, Gemini CLI, GitHub Copilot, Cline, Roo, Kilo, Continue, Goose, opencode, Trae, Junie, Kiro. Skills read the *installed* docs. | **None** (grepped src and docs config) | **None** | — |
| **Next.js** | **`node_modules/next/dist/docs/`** (16.2+); `@next/codemod agents-md` for older versions | **`next dev` manages an `AGENTS.md` block** when it detects an agent (default since 16.3; `agentRules`, `false` removes it); `create-next-app --agents-md` (default) | skills.sh: `next-dev-loop`, `next-bundle-optimizer`, `next-cache-components-*`, `next-partial-prefetching-*` (installed separately) | **Built-in `/_next/mcp` in dev** (app-aware): `get_errors`, `get_logs`, `get_page_metadata`, `get_project_metadata`, `get_routes`, `get_server_action_by_id`, `get_compilation_issues`, `compile_route`, `get_request_insights`; `experimental.mcpServer: false`. `next-devtools-mcp` bridge adds `nextjs_docs`, `browser_eval`… | `llms.txt`, `llms-full.txt`, `.md` URLs, `Accept: text/markdown` | `next upgrade --agent`; `experimental.agentUpgrade`, `agentFeedback`; overlay "Copy prompt"; dev lock file |
| **React Router** | No | No | No | No | No | "API + Mode Availability Table … mostly for the LLMs" |
| **TanStack** | No | No | No | No | No (GEO guide shows apps how to serve one) | TanStack Builder (AI-first, web) |
| **Nuxt** | `@nuxt/docs` npm package (raw markdown; separate install) | No | No | **Hosted** Nuxt MCP (docs filterable by 3.x/4.x/5.x, blog, deploy providers, modules, changelog; prompts; `X-MCP-Tools` header) | `nuxt.com/llms.txt` + `llms-full.txt` | — |
| **SvelteKit** | No | No | No | **`npx sv add mcp`** add-on | No | — |
| **SolidStart** | No | No | No | No | Docs site built with SolidBase `llms: true` (inferred) | — |
| **Astro** | No | No | No | **Hosted** Astro Docs MCP (`mcp.docs.astro.build`, kapa.ai) | No | **Background mode** auto-enabled when an agent is detected (dev + preview detach, lock files, JSON logs); `/_astro/status` health endpoint; `--json` |

**Behavioral differences that matter:**
- **Two families.** "Docs-as-a-service" (hosted MCP + llms.txt: Nuxt, Astro) is version-aware only through a filter. "Docs-in-node_modules" (Next.js, Void) is pinned to the installed version. Void and Next.js lead the second family.
- **App-aware tooling is Next.js's lead.** Its MCP endpoint reads *the running app* (errors, logs, routes, page metadata, compile issues). Void's skills only point agents at docs and commands. They can't ask the dev server what broke, so an agent must scrape the terminal or browser.
- **Skill distribution is Void's lead.** Automatic linking into 16 agent conventions at `void init`, versus Next.js's separately installed skills.

**Void gap:** partial.
- MCP server (Common: Next.js built-in, Nuxt and Astro hosted, SvelteKit add-on). The high-value variant is a dev-server MCP exposing errors, logs, routes, bindings and resources (Differentiator: Next.js).
- `llms.txt` for docs (Common: Next.js, Nuxt, SolidStart-inferred).
- Agent-aware dev server (background mode, lock file, JSON logs; Differentiator: Astro, Next.js).
- AGENTS.md is updated only at `void init`. Next.js re-syncs on every `next dev`, so Void's version-specific text can go stale after an upgrade.

## Instrumentation / OpenTelemetry

| Framework | Startup hook | Spans emitted automatically | Hook API | Client side | Config |
|---|---|---|---|---|---|
| **Void** | **None** | **None** | **None** (grepped `opentelemetry`, `otel`, `instrumentation`) | None | — |
| **Next.js** | `instrumentation.ts` `register()` (once per server instance, before ready; may be async; `NEXT_RUNTIME` branch) | **Yes**: `[http.method] [next.route]`, render, fetch; `NEXT_OTEL_VERBOSE=1` for more; `NEXT_OTEL_FETCH_DISABLED=1` | `@vercel/otel` or a manual `NodeSDK` | `instrumentation-client.ts` (runs before hydration) + `onRouterTransitionStart(url, 'push'\|'replace'\|'traverse', event?)` (`event` [exp] 16.3: `id`, `timestamp`, `fromRoutes`, `prefetchIntent`) | — |
| **React Router** | — | No built-in spans | **Stable `instrumentations` API**: server `handler.instrument({ request })`; client `router.instrument({ navigate, fetch })`; both `route.instrument({ loader, action, middleware, lazy })`. `call*()` returns `{ status, error }`, never throws; **read-only**; errors in instrumentation code are swallowed; composes in nesting order | `<HydratedRouter instrumentations>` | OTel example in docs |
| **TanStack** | Custom `src/server.ts` | No | **[exp] manual OTel recipe** (wrap handler/middleware); "Direct OpenTelemetry support is coming" (server functions, middleware, loaders) | `router.subscribe` | — |
| **Nuxt** | Nitro plugins | No | Building blocks only: Nitro `request`/`response`/`error` hooks, app hooks (`page:start/finish`, `app:rendered`, `render:route`) | App hooks | — |
| **SvelteKit** | **`src/instrumentation.server.js`** auto-loaded before app code (needs adapter `supports.instrumentation`, else a build error) | **Yes** with `tracing: { server: true }`: `handle` (+ `sequence` children), server loads, universal loads on the server, form actions, `+server`, remote functions | `event.tracing.root` / `.current` (`setAttribute`); `@opentelemetry/api` optional peer, auto-externalized | **Not supported** (server only) | Bundling caveats documented (`ssr.external`) |
| **SolidStart** | — | No | Middleware timing pattern only | — | — |
| **Astro** | — | No | — | — | — |

**Behavioral differences that matter:**
- The design space runs from **"we emit spans"** (Next.js, SvelteKit) to **"we give you wrap points"** (React Router: read-only, can't break the app). Both need a hook that runs before app code. On Workers that also implies an `AsyncLocalStorage`-style context, which Void already uses (`requestContext`, src `runtime/routing.ts`).
- Void's natural span boundaries are already explicit in the compiled Hono app: routing rules, middleware chain, route handler/loader, action, page render, deferred streaming, ISR lookup.

**Void gap:** missing. Common (3 stable: Next.js, React Router, SvelteKit; + TanStack [exp]). Design notes:
- Should be target-agnostic: Cloudflare has its own Workers tracing (not wired; not found), while Node can use the OTel SDK.
- Client navigation hooks (Next.js `onRouterTransitionStart`, React Router `router.instrument`) would sit in the shared `navigation-engine.ts`, so they would cover all 4 adapters at once.

## Server (and client) error reporting hooks

| Framework | Server hook | Payload / context | Client hook |
|---|---|---|---|
| **Void** | **None.** Internal `app.onError`: an `HTTPException` returns its own response; anything else → `console.error` + 500 page (src `routing-errors.ts`). Possible workaround: read `c.error` after `await next()` in middleware (Hono behavior; not documented by Void, unverified). | — | None (the React adapter only `reportError`s failures while restoring the previous page) |
| **Next.js** | `onRequestError(error, request, context)` in `instrumentation.ts` | Covers render, route, action and proxy errors; `renderType` incl. `'dynamic-resume'`; `revalidateReason` | `instrumentation-client.ts` |
| **React Router** | `handleError` export in `entry.server.tsx` | Error + request args | `onError` on `<HydratedRouter>` |
| **TanStack** | Partial: custom `src/server.ts` try/catch + `handleStartError` (Sentry example); middleware try/catch | — | `defaultOnCatch` |
| **Nuxt** | Nitro `error(error, { event })` hook; `defineErrorHandler`; `app:error`/`vue:error` (also during SSR). The docs contradict this elsewhere ("not yet possible") | event | `app:error`, `vue:error` |
| **SvelteKit** | `handleError` (`src/hooks.server`) | `{ error, event, status, message, kind, issues }` (v3: receives all errors with `kind`) | `handleError` in `hooks.client` |
| **SolidStart** | Partial: `serverFunctions.onError` (async; server functions only) | — | — |
| **Astro** | None (Logger API; Sentry integration) | — | — |

**Void gap:** missing.
- Server hook: Common (4: Next.js, React Router, Nuxt, SvelteKit; + TanStack and SolidStart partial).
- Client hook: Common (3: Next.js, React Router, SvelteKit).

Design notes:
- Must see loader, action, middleware, render and deferred-stream errors (deferred rejections are masked in production), and on Workers it must run inside `waitUntil`.
- Today the only production signal is `void project logs` (Cloudflare live tail; no history on direct deploys).

## Web vitals reporting

| Framework | Support |
|---|---|
| **Void** | None (grepped `vitals`, `LCP`, `INP`, `PerformanceObserver`) |
| **Next.js** | **`useReportWebVitals(cb)`** (`next/web-vitals`): TTFB, FCP, LCP, CLS, INP; fields `id`, `name`, `delta`, `entries`, `navigationType`, `rating`, `value` + **soft-navigation fields** (`navigationId`, `navigationURL`, `navigationStartTime`, `navigationInteractionId`); `experimental.webVitalsAttribution` |
| **React Router** | None (client `router.instrument` can time navigations) |
| **TanStack** | None (`router.subscribe` for analytics) |
| **Nuxt** | None (guidance only; `navigationRepaint` improves INP) |
| **SvelteKit** | None (guidance) |
| **SolidStart** | None |
| **Astro** | None in core (Vercel adapter `webAnalytics` for `@vercel/analytics` ≤1.3; toolbar Audit) |

**Void gap:** missing, but Differentiator (1). The valuable part is soft-navigation attribution. Void's client router knows navigation IDs (`navigation-engine.ts`), so it could tag metrics per visit across all 4 adapters.

## Logging helpers

| Framework | App logger | Levels / sinks | Dev logging aids | Production log access |
|---|---|---|---|---|
| **Void** | `void/log` `logger.error\|warn\|info(message, fields?)`, `logger.child(fields)` → **one JSON line** `{ msg, …fields }` via `console.*`. Errors serialized with `name/message/stack/cause` and cycle-safe; functions and `__proto__` keys dropped. | No `debug` level; no level threshold, sink, transport or redaction config | None (no request/fetch logging, no browser↔terminal forwarding) | `void project logs [--level --filter --range --deployment]` (Cloudflare: live tail only; Void platform: up to 7 days), `void project requests [--status --range]` (Void platform only; no paths) |
| **Next.js** | — | — | **`logging`**: `fetches`, `serverFunctions`, `incomingRequests`, **`browserToTerminal`** (`'warn'` default \| `'error'` \| `true` \| `false`) or `logging: false` | Host |
| **React Router** | — | — | — | Host |
| **TanStack** | Patterns (logging middleware, server-fn timing, debug headers) | — | — | Partners (Sentry, New Relic) |
| **Nuxt** | — | — | **`features.devLogs: true \| 'silent'`** (server logs streamed to the browser console; `dev:ssr-logs` hook); `debug` hook timings | Host |
| **SvelteKit** | — | — | Extensive dev diagnostics catalog | Host |
| **SolidStart** | `getServerFunctionMeta()` (server-fn `id` for logs) | — | — | Host |
| **Astro** | **Logger API** (stable 7.0): `Astro.logger`; `logger: { entrypoint, config }` | Built-ins `logHandlers.json({ pretty, level })`, `console({ level })`, `node({ level })` (default), `compose(…)`; custom `write/flush(per request)/close`; levels `debug\|info\|warn\|error\|silent` | `--verbose`/`--silent`, `--json` | Host |

**Void gap:** partial. Void's JSON logger is designed for its own log tooling (filtering by `msg` and fields), which is a strength. Missing:
- A `debug` level and level thresholds; pluggable sinks (Differentiator: Astro).
- Dev request/fetch logging.
- Browser↔terminal log forwarding (Differentiator: Next.js, Nuxt), which is especially useful for agents.
- A request-scoped logger carrying a request ID: `child()` exists, but nothing binds it per request.

## Build analysis / bundle analyzer / build profiling

| Framework | Bundle analyzer | Build timing / profiling |
|---|---|---|
| **Void** | None (Vite/Rolldown plugins usable as with any Vite app) | None |
| **Next.js** | **`next analyze`** (Turbopack analyzer UI; `--snapshot`, `-o`), `next analyze export` (16.4), `next build --analyze`; `next-bundle-optimizer` skill | `--profile`, `--debug`, `--debug-prerender`, `--no-mangling`, CPU profiling for dev/build/start, `--experimental-upload-trace` |
| **React Router** | — | `--profile` (dev/build) |
| **TanStack** | — | — |
| **Nuxt** | **`nuxt analyze`** / `build.analyze` | `debug` hook timings |
| **SvelteKit** | — | — |
| **SolidStart** | — | — |
| **Astro** | — | **`astro build --timings`** (7.4) |

**Void gap:** missing.
- Analyzer: Differentiator (2: Next.js, Nuxt).
- Build timings/profiling: Common (3: Next.js, React Router, Astro).

A Void-specific angle: per-page client chunk size would also show island payoff (zero-JS islands vs hydrated pages) and Worker bundle size against Workers limits. Void already enforces a Free-plan-compatible-by-default policy.

## Debugging and diagnostics

| Framework | Debugger guidance | Coded diagnostics / error catalog | Environment checks |
|---|---|---|---|
| **Void** | No guide; undocumented `VOID_INSPECTOR_PORT` | None (plain messages). Build errors for CF-only imports on other targets name the importing file. | **`void env check [--remote]`** (schema validation, value redaction, `VOID_ENV_UNMASK=1`); `void info [--json]` (resource names/bindings) |
| **Next.js** | Debugging guide; Node inspector link from the overlay | `/docs/messages/*` | `next info` |
| **React Router** | — | — | — |
| **TanStack** | "Debug router issues" how-to; ESLint plugins (`eslint-plugin-router`, `eslint-plugin-start`) | — | — |
| **Nuxt** | `--inspect`, VS Code/JetBrains configs | **Coded B/E diagnostics** with pages (`docs/errors/*`); `templateDiagnostics` (on) | — |
| **SvelteKit** | VS Code, `NODE_OPTIONS=--inspect`, WebStorm, Neovim | **255-entry message catalog** (e.g. `ssr_fetch_eager`, `server_only_import` with import chains) | — |
| **SolidStart** | — | — | — |
| **Astro** | — | Error reference pages (e.g. `CacheNotEnabled`) | `astro info`, "Copy debug info" |

**Void gap:** partial.
- No documented debugging guide (Common: Next.js, Nuxt, SvelteKit).
- No coded diagnostics catalog (Common: Next.js, Nuxt, SvelteKit, Astro).

Void's `env check` with redaction has no equivalent elsewhere.
