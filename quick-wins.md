# Quick wins

Small changes that close a gap or fix a rough edge, taken from the area comparisons. Several are already half-built in Void's source.

- **Expose `cacheVisitedPageData`.** It's already implemented, so this would give back/forward reuse without a refetch.
- **`InferProps<T>` = `Serialize<…>`** so page prop types match what actually arrives.
- **Honor `c.status()`** on rendered pages and page JSON.
- **Await `head()`**, which makes it async.
- **Expose the route id and pattern** in `useRouter()`. **Type `useParams()`** from the route map that codegen already generates.
- **Turn silent client stubs into build errors.**
- **Adapter parity:**
  - per-submit visit options (`preserveScroll`, `replace`, …) for React `useForm`, which today always scrolls to the top;
  - multipart uploads from `useIslandForm`, which today always sends JSON;
  - consistent `preserveState` across adapters.
- **Validate island strategy strings** (a typo currently means the island never hydrates, with no warning) and page-flag exports (non-literal `ssr`/`prerender`/`revalidate` values are silently ignored).
- **A code-only prefetch option** (Common 5).
- **Default `<meta charset>` and viewport tags.**
- **Docs only:**
  - `hono/cookie`
  - the `default`-export catch-all method handler
  - `public/404.html` and `500.html` for Worker apps
  - the `x-isr-cache` header
  - the dev error overlay
  - Svelte `<svelte:head>`
  - `VOID_INSPECTOR_PORT`
  - `c.executionCtx.waitUntil` on Cloudflare
  - Tailwind
  - `llms.txt`
