# Bugs and hazards found in Void's source

Found while comparing Void with the other frameworks. When a bug is fixed, its row is removed. Re-checked against [`b73d577`](https://github.com/voidzero-dev/void/commit/b73d5776e3ba546100098fa0984282fae3f2ed28) (1.12.0 plus 6 commits on `main`, 2026-11-26); every row below is still present. The row on client errors after a deploy was removed: navigations now reload when the server runs another build (see [Build and deploy](areas/13-build-deploy.md)).

These are separate from feature gaps. Every row was found by a comparison agent and cites the file it comes from. **Double-checked** marks the ones then confirmed a second time by reading the code directly.

| Double-checked | Issue | Where | Impact |
|---|---|---|---|
| Yes | **SSR asset tags ignore Vite `base`.** Production `<script>`, stylesheet and modulepreload URLs are built as `'/' + file`. | `packages/void/src/runtime/routing/assets.ts` `createClientAssetTags` | Apps with a non-root or CDN `base` reference wrong asset URLs |
| Yes | **A custom `public/500.html` is served for every failing request**, including `/api/*` and non-GET. The built-in page negotiates HTML vs text, but the custom page path skips that check. | `packages/void/src/runtime/routing/errors.ts` `serveCustomPage` | JSON API clients receive HTML error documents |
| Yes | **`head.script.innerHTML` is emitted unescaped.** It is raw by design, but there is no escaped or JSON alternative. Page data uses `escapeScriptJson`; head scripts do not. | `packages/void/src/pages/head.ts` | JSON-LD built from loader data containing `</script>` breaks out of the tag (XSS hazard) |
| No | **Stale page-cache entries have no expiration.** KV `put` sets no `expirationTtl`, so a failed re-render keeps serving the last good entry. A later 404 or 410 deletes it only after a 24-hour grace (`ISR_STALE_EVICT_GRACE_MS`). `docs/guide/edge/prerendering.md` says an expired page blocks the next request. | `packages/isr` `writeIsrCache` | Docs and code disagree; staleness has no upper bound while revalidation fails |
| No | **`.server.ts` value imports into client code are not blocked.** | build | Server code leaks into the client bundle. Also the first item under *What to work on first* in the [summary](overview.md) |
| No | **On Node/Bun/Deno a page's `revalidate` export is silently ignored.** The build warning only fires for `routing.revalidate`. A non-literal page export now warns at scan time, but a literal is still ignored on these targets. | `packages/void/src/index.ts` | Users assume caching that isn't happening |
| No | **`preserveState` is honored only by Vue and Solid.** React and Svelte ignore it, though it is documented as a shared `Link`/visit option. | adapters | Behavior differs by adapter |
| No | **`app.onError` (the HTML 500 renderer) is installed only for Pages apps.** API-only and custom-SSR apps get Hono's default text 500. Pages apps with an `_error` component no longer use this path for loader failures. | `router/compile.ts` | Inconsistent error responses outside Pages mode |
