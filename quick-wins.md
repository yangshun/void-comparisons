# Quick wins

Small changes that close a gap or fix a rough edge, taken from the area comparisons. Several are already half-built in Void's source.

- **Expose `cacheVisitedPageData`.** It's already implemented, so this would give back/forward reuse without a refetch.
- **`InferProps<T>` = `Serialize<…>`** so page prop types match what actually arrives.
- **Honor `c.status()`** on rendered pages and page JSON.
- **Await `head()`**, which makes it async.
- **Expose the route id and pattern** in `useRouter()`. `useParams<'/users/:id'>()` is typed; inferring that pattern from the component file, and typing `c.req.param()` without a `PageParams` cast, are still open.
- **Turn silent client stubs into build errors.**
- **Adapter parity:**
  - per-submit `replace` and the other visit options for React `useForm`. `preserveScroll` is a hook option, and an in-place action keeps scroll by default;
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
