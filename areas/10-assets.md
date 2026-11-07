# 10. Images, fonts & scripts

**Versions:** Void 1.6.2 · Next.js 16.4 (App Router) · React Router 8 (framework mode) · TanStack Start 1.169 (React) · Nuxt 5.0 pre-release (4.x is stable) · SvelteKit 3.1 · SolidStart 2.0 · Astro 7.4

**Note:** Every claim that Void lacks something was checked by searching `packages/` and `docs/`; the search terms are listed in each section.

**Paths:** Void file paths are in the `voidzero-dev/void` repo. Short paths such as `pages/scan.ts` are under `packages/void/src/`; paths that start with a package name, such as `react/src/…`, are under `packages/`.

## At a glance

- **Void has no asset optimization layer.** There is no image component or pipeline, no font optimization, and no third-party script loader. In that respect it matches React Router, TanStack Start and SolidStart. Next.js and Astro ship all three built in; Nuxt ships them as official modules.
- **Image optimization is the largest gap.** Next.js, Astro, Nuxt (`@nuxt/image`) and SvelteKit (`@sveltejs/enhanced-img`, build-time only) have it. Void's default runtime (Cloudflare Workers, no sharp) shapes the design: Astro's answer there is a build-time service plus a `cloudflare-binding` runtime service.
- **Fonts:** Next.js, Astro and Nuxt self-host fonts, subset them, compute metric-adjusted fallbacks and preload them. Void has nothing in this area.
- **Third-party scripts:** only Next.js (`next/script` strategies) and Nuxt (`@nuxt/scripts` triggers and facades) have a loading-strategy API; Astro offers Partytown worker offloading. Void has `head.script` entries, which are SSR-only and not re-applied on client navigation.

## Gap list for this area

| Gap in Void | Who has it (mechanism, briefly) | Prevalence | Notes for design (constraints, dependencies, adapter impact) |
|---|---|---|---|
| Image optimization (component + pipeline) | Next.js (`next/image`, runtime), Astro (`astro:assets`, build + runtime), Nuxt (`@nuxt/image` official module), SvelteKit (`@sveltejs/enhanced-img`, build-time, local only) | Common (4) | Needs a component in 4 adapters plus a Markdown `![]()` hook. Workers runtime has no sharp: build-time transforms for prerendered/static pages, plus a pluggable runtime service (Cloudflare Images binding, as in Astro's `cloudflare-binding`). |
| Remote image allowlist / SSRF-safe proxy | Next.js (`remotePatterns`, `dangerouslyAllowLocalIP`), Astro (`domains`, `remotePatterns`), Nuxt Image | Common (3) | Required as soon as a runtime endpoint exists. Copy Astro's "redirect targets must match" rule. |
| Image CDN providers / custom loaders | Next.js (`loader`/`loaderFile`), Astro (image services + adapter CDNs), Nuxt Image (providers) | Common (3) | Fits Void's target model (Cloudflare default, Node/Bun/Deno alternatives). |
| Blur/LQIP placeholder | Next.js (auto `blurDataURL` for static imports); Nuxt Image (from memory, unverified) | Differentiator (1–2) | Build-time only for static imports. |
| Font optimization (self-host, subset, fallback metrics, preload) | Next.js (`next/font`), Astro (Fonts API), Nuxt (`@nuxt/fonts` official module); SvelteKit opt-in preload only | Common (3) | UI-library-agnostic. Config-driven (Astro) maps onto Void config `head` + per-route CSS. Per-route preload needs Next.js-style tracking of which routes use which font. |
| Third-party script loading strategies | Next.js (`next/script` `afterInteractive`/`lazyOnload`/`beforeInteractive`), Nuxt (`@nuxt/scripts` triggers, proxies) | Differentiator (2) | The client runtime is shared across adapters, so one implementation serves all 4. Head scripts also need client-nav support (see area 9). |
| Worker offloading (Partytown) | Astro (`@astrojs/partytown`); Next.js `worker` is experimental and Pages Router only | Differentiator (1) | — |

## Image optimization: availability and pipeline

| Framework | Shipped as | When transforms happen | Local / remote sources | Remote allowlist and safety | Providers / custom loaders | Output formats |
|---|---|---|---|---|---|---|
| **Void** | **None.** Vite asset import gives a hashed URL; `public/` is served as-is. Markdown `![]()` gets `loading="lazy"` and relative-path normalization only (packages/md/src/plugins/image.ts). Grepped `srcset`, `sharp`, `imagetools`, `<Image`, `fetchpriority` in `packages/`: no image feature. | — | — | — | — | — |
| Next.js | Built in: `next/image` `<Image>`, `getImageProps()` | **Runtime, on demand** at `/_next/image` (sharp). Disk LRU cache (`maximumDiskCacheSize`, default 50% of free disk); `minimumCacheTTL` 14400 s. Static export needs a custom loader. | Local + remote (remote must match `remotePatterns`); `localPatterns` | `remotePatterns` (protocol/hostname/port/pathname/search, `*`/`**`); `maximumRedirects` 3 (targets not re-validated); `maximumResponseBody` 50 MB; `dangerouslyAllowLocalIP` false (SSRF guard); `dangerouslyAllowSVG` false; `contentSecurityPolicy`, `contentDispositionType` | `loader` prop / `loaderFile`; `next/image-optimizer-transform` exposes the sharp pipeline | `formats` default `['image/webp']`, add `'image/avif'`; chosen by `Accept` |
| Astro | Built in: `astro:assets` `<Image>`, `<Picture>`, `getImage()`; SVG components | **Build time** for prerendered pages; **runtime** at `/_image` for on-demand pages. 7.4 adds a split `image.service: { build, runtime }`. Crops by default, never upscales (v6). | Local `src/` images (imported) + remote if authorized. **`public/` is never optimized.** | `image.domains` (no wildcards), `image.remotePatterns` (`**.`/`*.` hosts, `/**`/`/*` paths); redirect targets must match too; `dangerouslyProcessSVG` false; `limitInputPixels` | Services: sharp (default), `passthroughImageService()`, custom. Adapters: Vercel (`imageService`), Netlify Image CDN (default), Cloudflare (`cloudflare-binding` default, `cloudflare`, `compile`, `passthrough`, custom) | `format` default webp; `<Picture formats>` + `fallbackFormat` |
| Nuxt | Official module `@nuxt/image` (`<NuxtImg>`, `<NuxtPicture>`) | Via provider; IPX is the default local provider (from memory, unverified) | Local + remote | (from memory, unverified) | 20+ image-CDN providers (from memory, unverified) | WebP/AVIF via `format`; `<NuxtPicture>` sources |
| SvelteKit | Official Vite plugin `@sveltejs/enhanced-img` (`<enhanced:img>`, `?enhanced` imports, `import.meta.glob` with `query: { enhanced: true }`) | **Build time only** (imagetools; cache `node_modules/.cache/imagetools`) | **Local only.** Remote/CMS images are pointed to CDNs or `@unpic/svelte`. | n/a | `adapter-vercel` `images` config (`sizes`, `formats`, `minimumCacheTTL`, `domains`) configures Vercel's optimizer, but no component uses it | `<picture>` with avif + webp + original |
| React Router | None (Vite assets; `assetsInlineLimit` 4096) | — | — | — | — | — |
| TanStack Start | None ("does not automatically provide the Next.js image optimizer"; Unpic + an image service suggested) | — | — | — | — | — |
| SolidStart | None (Vite assets, `public/`) | — | — | — | — | — |

## Image component props (frameworks that have one)

Void, React Router, TanStack Start and SolidStart have no image component and are omitted from this table.

| Capability | Next.js `<Image>` | Astro `<Image>`/`<Picture>` | Nuxt `<NuxtImg>`/`<NuxtPicture>` | SvelteKit `<enhanced:img>` |
|---|---|---|---|---|
| Responsive `sizes` → `srcset` | `sizes`. Without `sizes`: a 1x/2x srcset (with `width`) or `deviceSizes` (with `fill`); with `sizes`: a full `w` srcset from `deviceSizes` + `imageSizes` | `sizes`; auto-generated for `constrained`/`full-width` layouts from `image.breakpoints` | `sizes` → responsive output | `sizes` triggers `srcset` (smallest auto width 540 px) |
| Explicit widths | Global `deviceSizes` [640…3840] / `imageSizes` [32…384] | `widths: number[]` (requires `sizes`; never upscales) | (from memory, unverified) | `?w=1280;640;400` |
| Densities | Implicit 1x/2x | `densities: (number \| '2x')[]` (exclusive with `widths`; ignored with `layout`) | `densities` (from memory, unverified) | Default 1x + 2x (provide 2x sources) |
| Formats | Global `formats` | `format` (webp default, avif, png, jpeg, svg); `<Picture formats>` + `fallbackFormat` | `format` | Fixed avif + webp + original |
| Quality | `quality` 1–100, coerced to the nearest `qualities` entry (default `[75]`; effectively required since 16) | `quality`: `'low' \| 'mid' \| 'high' \| 'max'` or 0–100, normalized per format | `quality` (from memory, unverified) | imagetools `?quality=` directive |
| Placeholder | `placeholder`: `empty` \| `blur` \| `data:` URL. `blurDataURL` **auto-generated** for static jpg/png/webp/avif imports | None found | `placeholder` (from memory, unverified) | None (`?blur=` is a transform, not a placeholder) |
| Priority / preload | `preload` (16.0; `<link rel=preload>`); `priority` **deprecated in 16**; `loading` (`lazy` default), `fetchPriority` | `priority` → `loading="eager"`, `decoding="sync"`, `fetchpriority="high"`; default `lazy` + `async` | `preload: { fetchPriority }`, `loading`, `fetchpriority` (documented) | Not documented |
| Layout modes / fit | `fill` (fills a positioned parent) + `objectFit` | `layout`: `constrained` \| `full-width` \| `fixed` \| `none`; `fit` (cover by default), `position`, `background`; global `image.layout/objectFit/objectPosition/responsiveStyles` | `fit` (from memory, unverified) | — |
| Intrinsic size / CLS | `width`/`height` required unless a static import or `fill` | Inferred for `src/`; required for `public/`/remote unless `inferSize` (allow-listed domains only) | `width`/`height` | `width`/`height` inserted automatically |
| Art direction | `getImageProps()` for `<picture>` and theme switching | `<Picture pictureAttributes>`; `getImage()` | `<NuxtPicture>` | — |
| In Markdown | via MDX | `![]()` in `src/` and remote images optimized; responsive when `image.layout` is set | via `@nuxt/content` (not documented here) | via mdsvex (not documented) |

**Behavioral differences that matter:**
- Next.js optimizes **at runtime only** (an origin server or edge with sharp is needed, or a CDN loader). SvelteKit optimizes **at build time only**, local files only. Astro does both (build for prerendered pages, runtime for on-demand pages) and lets adapters swap in host CDNs.
- Astro never optimizes `public/`. Next.js optimizes any allow-listed URL. That split matters for Void, whose `public/` and Markdown images are currently untouched.

**Void gap:** missing entirely: component, responsive srcset, format conversion, quality, placeholder, priority, layout modes, remote allowlist, build/runtime pipeline and providers.

## Font optimization

| Framework | Mechanism | Self-host / providers | Subsetting / variants | Fallback metrics (CLS) | Preload | Notes |
|---|---|---|---|---|---|---|
| **Void** | **None.** Grepped `font-face`, `fontaine`, `fontsource`, `preconnect`, `font optim`: only MIME-type entries for `.woff`/`.woff2`. | — | — | — | — | Fonts via `public/` + CSS, or `head.link` |
| Next.js | `next/font/google`, `next/font/local` (called in code) | Downloaded at build; no browser requests to Google | `subsets` (preload warns if missing), `weight` (required for non-variable fonts), `style`, `axes` | `adjustFontFallback` (google `true`; local `'Arial' \| 'Times New Roman' \| false`); `fallback` | `preload` (true): preloaded **only on routes whose page/layout calls the loader** | `display` (`swap`), `variable` (CSS var), `declarations`. Returns `className`/`style`/`variable`. |
| Astro | `fonts: [{ provider, name, cssVariable, … }]` config + `<Font cssVariable preload?>` in head (stable since v6) | `fontProviders.local/adobe/bunny/fontshare/fontsource/google/googleicons/npm` or custom; served from `_astro/fonts` with long caching | `weights` [400], `styles` [normal, italic], `subsets` [latin], `formats` [woff2], `unicodeRange`, `stretch`, `featureSettings`, `variationSettings` | `optimizedFallbacks` true (from the last generic in `fallbacks`, default `sans-serif`) | `preload`: `false` \| `true` \| `[{ weight, style, subset }]` | `display` swap; `fontData` / `experimental_getFontFileURL()` (used for OG images) |
| Nuxt | Official module `@nuxt/fonts`: **zero-config**, resolves any `font-family` found in your CSS | `public/` first, then Google, Bunny, Fontshare (pluggable); proxied and cached under `/_fonts` | — | fontaine metric-adjusted fallbacks | — | Hashed names, long-lived cache headers |
| SvelteKit | No automation. **Fonts are not preloaded by default.** | Manual (Fontsource) | Manual subsetting recommended | — | Opt-in via `handle` → `resolve(event, { preload: ({ type, filename }) => … })` | — |
| React Router, TanStack Start, SolidStart | None (self-host / Fontsource / `@font-face`) | — | — | — | — | — |

**Void gap:** missing: self-hosting from providers, subsetting, metric-adjusted fallbacks and per-route preload. A config-driven design like Astro's fits Void's config `head` and per-route CSS collection, and is independent of the UI library.

## Third-party script loading

| Framework | Declaration points | Loading strategies | Worker offload | Consent / facades | CSP nonce | Client-nav behavior |
|---|---|---|---|---|---|---|
| **Void** | `head.script` (`src`, `innerHTML`, any attribute such as `async`, `defer`, `type`, `nonce`) in config, middleware `headDefaults` or page `head()`. Markdown `<script>` client block (page-scoped). | **None** beyond raw `async`/`defer`. Always in `<head>`. | None (grepped `partytown`) | None | **No framework plumbing.** Grepping `nonce` in `packages/void/src` finds only dev CSS; a static nonce can be set by hand as an attribute. | **SSR-only.** A script from page B's `head()` does not run when navigating to B on the client. |
| Next.js | `next/script` in any component; `beforeInteractive` in the root layout only | `strategy`: `beforeInteractive` (head; before first-party code; once per document), `afterInteractive` (**default**), `lazyOnload` (idle), `worker` | `worker` is **experimental, Pages Router only**, needs `nextScriptWorkers`; not supported by Turbopack | `@next/third-parties` (Google Analytics, Tag Manager, Maps, YouTube embeds) | Per-request nonce generated in Proxy (CSP header) is attached by Next.js automatically; needs dynamic rendering (`G/content-security-policy.mdx`) | `onLoad` (client components only), `onReady` (every mount), `onError`; inline scripts need an `id` |
| React Router | React 19 elements, root `Layout`, `links` (`rel: preload`), `.client` modules | None | — | — | `<Scripts nonce>` (app runtime only) | React-managed |
| TanStack Start | Route `head().scripts` (head), route `scripts()` (body, before hydration), `ScriptOnce` | None | — | — | `ssr.nonce` | Tags load/unload with routes |
| Nuxt | Core: `useHead({ script: [{ src, async, defer, tagPosition: 'bodyClose' }] })`, `app.head.script`. Official module `@nuxt/scripts`. | Registry composables, e.g. `useScriptGoogleAnalytics({ id, scriptOptions: { trigger: 'manual' } })` → `{ onLoaded, proxy }` (the proxy queues calls until loaded). Generic `useScript(src, { trigger })` with `onNuxtReady` (default), `client`, `server`, `manual`, promise or element triggers (from memory, unverified) | — | Consent trigger, `bundle: true` self-hosting, facade components such as `<ScriptYouTubePlayer>` (from memory, unverified) | `render:html` hook | Reactive / disposed |
| SvelteKit | `app.html` (`%sveltekit.env.PUBLIC_*%`), `<svelte:head>` | None | Docs recommend Partytown's SvelteKit integration | — | `%sveltekit.nonce%` | `<svelte:head>` mounts and unmounts with its component |
| SolidStart | `entry-server.tsx` document; service worker in `entry-client` | None | — | — | `createHandler` `nonce` | — |
| Astro | `<script is:inline src>` (as-is); processed `<script>` (bundled); integrations `injectScript(stage)`: `head-inline`, `before-hydration`, `page`, `page-ssr` | None | **`@astrojs/partytown`** official integration | — | CSP config (stable since v6) | ClientRouter keeps scripts |

**Behavioral differences that matter:**
- Next.js's default `afterInteractive` defers third-party code until after hydration. Void's head scripts block like any `<head>` script unless the author adds `defer`/`async`, and they never run for client-navigated pages.
- Nuxt's registry composables give typed, queued proxies (call `gtag` before it loads). Nothing comparable exists outside Nuxt.

**Void gap:** missing: a loading-strategy API (after-hydration, idle, on-interaction or consent triggers), worker offload, per-route scripts on client navigation, embed facades, and framework-managed CSP nonces. Partial: raw `head.script` entries.
