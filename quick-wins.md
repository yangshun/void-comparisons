# Quick wins

Small changes that close a gap or fix a rough edge, taken from the area comparisons. Several are already half-built in Void's source. Re-checked against [`268c271`](https://github.com/voidzero-dev/void/commit/268c2717981fa09b34994b155966da7d01076b49) (1.10.0, 2026-11-17).

## Already in the engine

### Expose `cacheVisitedPageData`

Back and forward always refetch the page JSON. The navigation engine already keeps a visited-page cache with stale-while-revalidate, and none of the adapter plugins pass the option through. Wiring it on the plugin, reusing the existing `cacheFor` syntax, gives back/forward reuse. Prefetch is the only client cache today, so a still-valid prefetch entry is the only return visit that skips the loader. Common (5). [Caching](areas/05-caching.md).

### Await `head()`

`head()` is called and not awaited in `pages/protocol.ts`, so it cannot be async. Awaiting `headFn` is the whole change. Async work can already happen in the loader, with the result passed into a sync `head()`. Common (3–4): Next.js `generateMetadata` is async, TanStack head may return a Promise, and Astro allows top-level await. [Metadata](areas/09-metadata-seo.md).

### Expose the route id and pattern

The client already knows the page id and the URL pattern, from the manifest and the page object. `useRouter()` returns `url`, `path`, `query`, `params`, `visit`, `refresh`, `prefetch`, `flush` and `flushAll`. Exposing the id and the pattern is the change.

`useParams<'/users/:id'>()` types the param names when the caller passes the pattern. Two larger pieces stay open: inferring that pattern from the component file, and typing `c.req.param()` without an `as PageParams<…>` cast (`CloudContext` has no path generic). Table stakes (6). [Routing](areas/01-routing.md), [Type safety](areas/08-type-safety.md).

## Safety

### Turn silent client stubs into build errors

A value import from a `.server.ts` companion into a component ships to the client. There is no `server-only` marker. The client stubs for `void/db`, `kv`, `ai`, `queues`, `storage` and `isr` are silent no-ops (`pages/plugin-client-stubs.ts`), so a mistaken import can leak server code or a client call can look like it worked. `void/live` and `void/durable` already fail the build. `void/sandbox` and `void/email` throw at call time. Reading a server env key from the client already fails the build, per key (`plugin-env-client-guard.ts`).

The same treatment for the remaining stubs, plus a client-environment resolve check that allows `import type` and prints an import trace, is the first item under *What to work on first* in the [summary](overview.md). The check has to cover `.vue` and `.svelte` script blocks as well as React and Solid. `routes/` and `middleware/` stay out of the client graph already. Also a row in [Bugs](bugs.md). Table stakes (6). [Server API](areas/06-server-api.md).

## Adapter parity

### Per-submit visit options on React `useForm`

An in-place action keeps scroll by default: `preserveScroll` is on when the submission stays on the same path and query. React `useForm` accepts `preserveScroll` as a hook option. Vue, Svelte and Solid take `replace`, `viewTransition` and a data override on each submit call. React's submit methods are native form-action callbacks, so those options are absent there. `action()` already takes `preserveScroll` per call in every adapter. Common (3) for `replace` and history `state`. [Mutations](areas/04-mutations.md).

### Multipart uploads from `useIslandForm`

`useForm` and `action()` switch to `multipart/form-data` when the body contains a `File`, `Blob` or `FileList`. `useIslandForm` always sends JSON (`pages/island-action.ts`) and reloads the page on success, so an island cannot upload a file. Table stakes (7) for file uploads from every submission helper. [Mutations](areas/04-mutations.md).

### `preserveState` on every adapter

It is documented as a shared `Link` and visit option. Vue honors it, and otherwise remounts the page on every GET, including a query-only change. Solid honors it, and otherwise recreates the page on GET and on param change. React and Svelte ignore it: the same component instance survives by reconciliation, and there is no remount key. Also a row in [Bugs](bugs.md), and design point 2 in the [summary](overview.md). [Routing](areas/01-routing.md).

## Validation

### Island strategy strings and page-flag exports

An island import is `with { island: 'load' | 'visible' | 'idle' | 'media:(q)' }`. An unknown string never hydrates, and nothing warns (`pages/island-imports.ts`, `client.ts` `scheduleHydration`). `ssr`, `prerender` and `revalidate` are read as AST literals (`pages/scan.ts`). A non-literal, such as `export const revalidate = 60 * 5`, now produces a scan warning and is ignored. Astro errors instead of warning.

A separate bug sits next to this: on Node, Bun and Deno a page `revalidate` export is ignored even when it is a literal, and the build warning only fires for `routing.revalidate` (`packages/void/src/index.ts`). [Rendering](areas/02-rendering.md), [Bugs](bugs.md).

### A code-only prefetch option

Every Void prefetch loads the page chunk and runs the loader. SvelteKit (`preload-code`), TanStack (`loadRouteChunk`), Solid (`usePreloadRoute`), Next.js (`auto`) and Nuxt (code and payload for prerendered pages) can prefetch code without data. That matters for a link whose loader is expensive or user-specific. The page and layout chunks are already separate dynamic imports, so this is a strategy flag such as `prefetch={{ data: false }}`. `router.prefetch()` is a separate path, and the Save-Data / slow-connection skip on `Link` prefetch does not apply to it. Common (5). [Routing](areas/01-routing.md).

### Default charset and viewport

Pages mode owns the HTML document, and the shell emits neither `<meta charset>` nor a viewport tag unless `head.meta` in `void.config.ts` adds them. Next.js always emits both. Nuxt defaults `charset: utf-8` and `width=device-width, initial-scale=1`. Emitting those two tags from the React, Vue, Svelte and Solid shells, and from the island template, is the change.

A `theme-color` that varies by color scheme is a separate gap. `meta` in `pages/head.ts` serializes name, property, content and charset, so two `theme-color` entries collapse. Differentiator (2). [Metadata](areas/09-metadata-seo.md).

## Docs only

These already work. The docs do not say so.

| Item | What to write down | Area |
|---|---|---|
| `hono/cookie` | Cookie get, set and delete. Hono's helpers are the cookie API, and loaders can use them. Table stakes (7). | [Server API](areas/06-server-api.md) |
| `default` export | A `routes/` file with no recognized method export is registered with `app.all()` and dispatched to `default` (`router/compile.ts`). Typing that export, and failing the build when it is missing, is a small step past the docs. Common (4). | [Server API](areas/06-server-api.md) |
| `public/404.html` and `500.html` | Documented for static builds, and they also work for Worker apps. Component `_error` / `_not-found` pages are documented. A custom `500.html` is still served for every failing request, including `/api/*` and non-GET (`runtime/routing/errors.ts` `serveCustomPage`). That over-broad serving stays an open bug. | [Loading and errors](areas/07-loading-error.md) |
| `x-isr-cache` | Response header `HIT`, `MISS` or `STALE`, from `packages/isr`. `X-Void-Routing` and `X-Void-No-Match` are the documented edge-rule headers. | [Dev tooling](areas/14-dev-tooling.md) |
| Dev error overlay | The server overlay exists, shows the `cause` chain, and its links open VS Code only. Client errors stay out of it. Documenting the overlay is the quick part. Extending it to client errors and a configurable editor is Common (3). | [Dev tooling](areas/14-dev-tooling.md) |
| Svelte `<svelte:head>` | Svelte SSR injects it into `<head>` (`packages/svelte/src/plugin-pages.ts`). React, Vue and Solid have no component-level head, Common (5). React renders inside `#app`, so React 19 metadata hoisting cannot reach `<head>` during SSR. | [Metadata](areas/09-metadata-seo.md) |
| `VOID_INSPECTOR_PORT` | The inspector port is undocumented, and there is no debugging guide. Coded diagnostics are Common (4). | [Dev tooling](areas/14-dev-tooling.md) |
| `c.executionCtx.waitUntil` | Works on Cloudflare, and internal ISR uses it. On Node, Bun and Deno `executionCtx` is not passed to `app.fetch` (`runtime/routing/index.ts` `nodeTarget`). A portable `after()` is Differentiator (2) and stays a separate piece of work. | [Server API](areas/06-server-api.md) |
| Tailwind | It should already work through Vite. What is missing is a docs page and a `void init` option. Table stakes (7). An installer in the style of `astro add` is the larger idea, Common (3). | [Styling](areas/11-styling.md) |
