# 8. Type safety

**Versions:** Void 1.5.0 · Next.js 16.4 (App Router) · React Router 8 (framework mode) · TanStack Start 1.169 (React) · Nuxt 5.0 pre-release (4.x is stable) · SvelteKit 3.1 · SolidStart 2.0 · Astro 7.4

**Paths:** Void file paths are in the `voidzero-dev/void` repo. Short paths such as `pages/scan.ts` are under `packages/void/src/`; paths that start with a package name, such as `react/src/…`, are under `packages/`.

## At a glance

- **Void's URL typing is broad.** One generated map (`.void/routes.d.ts`) covers page, HTTP and WebSocket routes. It types string `Link href`s (opt-in `routing.typedRoutes`), the `routeUrl()` and `RouteDestination` builders, router methods, `c.rewrite()`, typed `fetch`, `useForm` and `action()`. No other framework covers all of these surfaces from one map.
- **Void's typed fetch is the strictest of its kind.** An unknown path or an unexported method is a compile error by default. `body`, `query` and `params` are typed from the Standard Schema validator that also checks them at runtime, and responses go through `Serialize<T>`. Only Nuxt 5's rebuilt `$fetch` is comparable, and Nuxt needs `strictRouteTypes: true` to be as strict.
- **Typed forms are a Void strength.** `useForm` and `action()` give URL autocomplete (including `?named` actions), `data` typed from the body schema, and typed `errors` keys. Only SvelteKit's experimental remote `form` and Astro Actions' `isInputError().fields` come close.
- **Typed env is a Void strength.** Void validates env through a schema, guards server keys from client code at build time, and validates again before deploy and at boot. Only SvelteKit 3 (`src/env.ts`) and Astro (`astro:env`) are at the same level.
- **Gap: route params are not typed from the file path.** `useParams<T>()` takes a manual generic, and `c.req.param()` in loaders is untyped (`CloudContext = Context<CloudEnv>`, with no path generic). Five of the seven others type params per route.
- **Gap: page prop types are wrong for values that JSON changes.** `InferProps<typeof loader>` gives the loader's raw return type, but page props are sent as plain JSON. A `Date` is typed `Date` but arrives as a `string`, and `undefined` keys disappear. Every other framework either uses a rich serializer or applies serialization-aware types.
- **Gap: loader→component typing takes three manual steps.** You `export type Props = InferProps<typeof loader>`, then `import type`, then annotate. Every other framework gives the type with no annotation or with one generated import.
- **Gap: client search params are untyped.** Only TanStack has typed and validated search params, so this is a differentiator rather than table stakes. Void already validates `query` on the server.
- **Middleware context is typed by one global augmentation (`CloudContextVariables`).** This is the same model as SvelteKit, SolidStart and Astro. Its index signature makes unknown keys `unknown` rather than an error. TanStack infers context down the middleware chain, and React Router uses typed keys.

## Gap list for this area

| Gap in Void | Who has it (mechanism, briefly) | Prevalence | Notes for design (constraints, dependencies, adapter impact) |
|---|---|---|---|
| Page prop types don't match the runtime value (`Date` typed but a string arrives; `undefined` keys dropped) | Rich serializer or serialization-aware types: Next.js/Astro (no round-trip for server-rendered output), React Router (serialization-aware types), TanStack (serializer + `strict`), Nuxt (JSON-mapped types + devalue), SvelteKit (devalue), SolidStart (seroval) | Table stakes (7) | Cheapest fix: make `InferProps<T>` = `Serialize<output>` (the type already exists). Switching the JSON page protocol to devalue would touch all 4 adapters' hydration and the prefetch cache. |
| Loader→component typing needs export + import + annotate | No annotation: Next.js, TanStack, Nuxt, SvelteKit (language tools), SolidStart, Astro. One generated import: React Router (`./+types`). | Table stakes (7) | A generated per-page sibling type (React Router-style `rootDirs`) works for all 4 adapters. A Svelte/Vue language-tool injection would be adapter-specific. |
| Route params not typed from the file path (`useParams<T>()` manual; `c.req.param()` untyped) | Next.js (`PageProps<'/r'>`), React Router (`+types`), TanStack (inferred), Nuxt (`useRoute('name')`), SvelteKit (`$types` + matcher types); Astro static-only | Common (5) | `RoutePathMap` already holds the param names. Make `useParams()` accept a pattern (`useParams('/users/:id')`), or emit per-page `Params`. A path-generic `CloudContext` would also type `c.req.param()`. |
| Integrated type-check / editor support | Next.js (TS plugin + `tsc` in build), Nuxt (`nuxt typecheck`, `typeCheck: 'build'`), SvelteKit (`svelte-check` + zero-config injection), Astro (`astro check`, language server) | Common (4) | Needs per-adapter dispatch (`tsc` / `vue-tsc` / `svelte-check`). Overlaps area 14. |
| Import-and-call typed RPC | TanStack (`createServerFn` + validator), Astro (Actions), Next.js (Server Actions), SolidStart (`"use server"`); SvelteKit remote functions [experimental]; React Router RSC [unstable] | Common (4 stable) | Cross-area (4/6). Void's typed fetch already covers HTTP routes. RPC needs a compiler transform and an endpoint convention for each adapter. |
| Typed and validated client search params | TanStack (`validateSearch`, input/output types, parent inheritance, `retainSearchParams` / `stripSearchParams`) | Differentiator (1) | Reuse the loader's `withValidator({ query })` schema on the client (`useRouter().query`, `Link data`, `routeUrl` `query`). Needs a parse/serialize convention; TanStack is JSON-first. A page-level validation failure should render an error page, not a JSON 400. |
| Per-chain inferred middleware context | TanStack (inferred `next({ context })`), React Router (`createContext<T>` keys; throws when unset) | Differentiator (2) | `defineHandler(mw…, handler)` could thread context types. Dropping the `[key: string]: unknown` index signature on `CloudContextVariables` would at least make typos errors (a breaking change). |
| Typed error payloads | Astro (`ActionError` codes, `isInputError().fields`), SvelteKit (`App.Error`) | Differentiator (2) | `useForm` errors are already typed; extend this to `FetchError<E>` per route. |
| Typed relative links | TanStack (`from` + `.`/`..`) | Differentiator (1) | Void rejects relative strings on purpose; low priority. |
| Typing external APIs / augmenting the route map | Nuxt (`createUseFetch({ routes })`, `ServerRoutes` augmentation) | Differentiator (1) | — |

## Where Void is ahead

- **One route map for every URL surface:** string `Link href`s, builders (`routeUrl`, `RouteDestination`), router methods, `c.redirect`/`c.rewrite`, typed `fetch`, `useForm`/`action()`, and **WebSocket routes**. Others type at most a subset; nobody else types rewrite destinations or WebSocket routes.
- **Both string checking and builders.** Next.js checks strings only; React Router and SvelteKit have builders only.
- **Typed fetch is strict by default.** Unknown paths and methods are errors, and the validator is both the runtime check and the client type, with `Serialize<T>` on responses. Only Nuxt 5 is comparable, and it is opt-in strict.
- **Validator-driven forms.** `useForm` and `action()` with per-named-action typed `data` and `errors`, the same in all 4 adapters. Only SvelteKit's experimental remote `form` and Astro Actions compare.
- **Drizzle schema → validator → handler → client** in one type pipeline (`void/drizzle-zod|valibot|arktype`).
- **Typed, validated env with a build-time guard against server keys in client code** and validation before deploy and at boot. Matched only by SvelteKit 3 and Astro.
- **The same type surface across React, Vue, Svelte and Solid.** Every other framework is single-library, or (Astro) leaves island typing to each library.

## Typed route paths and links

| Framework | Mechanism | Surfaces checked | Relative paths | Escape hatch / limits | Notes |
|---|---|---|---|---|---|
| **Void** | **Both kinds.** (a) String checking via `routing.typedRoutes` (default on in `void init` apps, off otherwise). (b) Builders: `routeUrl(pattern, { params, query, hash })` and `RouteDestination` objects `{ pathname, params, query, hash }`. | `Link href`, `router.visit/prefetch/flush`, `c.rewrite()`. `c.redirect()` takes `routeUrl()`/`RouteDestination`. Patterns cover page, HTTP and **WebSocket** routes. | **Rejected** (`../x` is a type error). Same-page `?x`/`#x` are allowed. | Cast with `as RouteUrl` / `as Href`. A dynamic segment matches any text, including empty (`/users/` passes for `/users/:id`). `routeUrl` throws `TypeError` at runtime on missing params. Restart dev or run `void prepare` after toggling. | Same API in all 4 adapters. Params are `string \| number` and URL-encoded. Catch-all is written `/files/:path{.+}`. External `http(s):`, `mailto:` and `tel:` are allowed. |
| Next.js | String checking via `typedRoutes` (stable, opt-in, TS only). Checks literal and template-literal hrefs, including dynamic segments. | `<Link>`, `next/navigation` `push/replace/prefetch`. `next/router` is untyped. | Not documented. | `as Route`; `Route<T>` for wrapper components. | No builder function. |
| React Router | Builder: `href(path, params)` (codegen). Supports optional params (`/:lang?/about`). | `href()` only. **`<Link to>` is untyped** (wrap it with `href`). | Relative `to` works at runtime but is untyped. | — | Params are percent-encoded per segment; splat values keep `/`. |
| TanStack Start | Object props: `to` (route path with `$param`), plus `params`, `search`, `hash` and `state`, all checked. Helpers: `linkOptions()`, `createLink()`, `Validate*` types. | `Link`, `navigate`, `redirect`, `<Navigate>`, `Route.redirect`. | **Typed** via `from` plus `.`/`..`. | `strict: false`; `href` prop for prebuilt URLs. | Registered through `Register` declaration merging. `protocolAllowlist` acts as an XSS guard. |
| Nuxt | String or named-route-object checking via `typedPages` (native vue-router). **On by default in Nuxt 5**; experimental opt-in in 4.x. | `<NuxtLink :to>`, `navigateTo`, `router.push`. Build warning `NUXT_B4025` for an unknown static `to`. | Untyped. | Routes added with `router.addRoute()` need manual augmentation. | Layout names, layout props and middleware names are typed too. |
| SvelteKit | Builder: `resolve('/blog/[slug]', { slug })` typed against `RouteId`; `Path` type. | `resolve()` only. **`<a href>` is unchecked** (there is no Link component). | n/a | Throws on missing params, absolute URLs, and params with a leading or trailing `/`. | `$app/types` exports `RouteId`, `RouteParams<T>`, `Path`, `AssetPath`. |
| SolidStart | None. `<A href: string>`, `navigate(string)`. | — | — | — | TanStack Solid Router is the documented typed alternative. |
| Astro | None. Plain `<a href>`, no Link component. | — | — | — | — |

**Behavioral differences that matter:**
- Void and Next.js both check plain strings, including template literals with dynamic segments. Void's check is looser: an empty dynamic segment passes (`/users/` matches `/users/:id`), and a root `[slug]` page lets `//example.com` through (docs/guide/type-safety.md).
- React Router and SvelteKit only check their builder functions. Void checks strings **and** has builders, so it is a superset of both approaches.
- TanStack is the only framework that types relative navigation (`from` + `..`). Void rejects relative strings on purpose.
- Void's typed destinations also reach server-side `c.rewrite()`. No other framework types an internal rewrite target.

**Void gap:** none for the core capability. Partial at option level: no typed relative paths (TanStack only), and no typed `search` per destination (`routeUrl`'s `query` is a generic `RouteQuery`).

## Typed route params (inferred from the file path vs manual)

| Framework | In components | In loaders / handlers | Inferred from file path? | Value types / transforms |
|---|---|---|---|---|
| **Void** | `useParams<T extends Record<string,string>>()`: a **manual generic** that defaults to `Record<string,string>`. Same in all 4 adapters (packages/react/src/runtime/use-params.ts). | `c.req.param()` is **untyped**, because `CloudContext = Context<CloudEnv>` has no path generic (packages/void/src/runtime/handler.ts:136). Params are typed **and validated** only through `defineHandler.withValidator({ params: schema })`. | **No.** The generated `RoutePathMap` knows the param names but does not feed them to components. | Strings. A validator can coerce. No optional segments exist (area 1). |
| Next.js | `PageProps<'/blog/[slug]'>`, `LayoutProps<'/x'>` (global generated helpers; you pass the route literal) | `RouteContext<'/x'>` for Route Handlers | Yes (generated) | `string \| string[] \| undefined`; `params` is a Promise. Static route params are `{}`. |
| React Router | `Route.ComponentProps['params']` from `./+types/<route>` | `Route.LoaderArgs`, `Route.ActionArgs`, middleware args | Yes (codegen from `routes.ts`) | Optional `:x?` params are typed optional. |
| TanStack Start | `Route.useParams()`, `getRouteApi(id).useParams()` | `loader`/`beforeLoad` `params`; server routes | Yes (`routeTree.gen.ts` + inference) | `params.parse` output types flow to consumers (e.g. `number`). |
| Nuxt | `useRoute('posts-id').params` (pass the route name) | Server routes: `getRouterParam(event, 'name')` (typing not documented) | Yes for pages | Strings |
| SvelteKit | `PageProps.params` (injected with zero config in `.svelte` by the language tools) | `PageServerLoad`, `RequestHandler` from `./$types` | Yes (`svelte-kit sync`) | Matcher output types (`number`, `boolean`, `bigint`) via `defineParams` (v3) |
| SolidStart | `useParams<T>()`, `RouteSectionProps<T>` (manual) | Manual | No | `string \| undefined` |
| Astro | `Astro.params` via `InferGetStaticParamsType` | — | Partial (static routes only, from `getStaticPaths`) | — |

**Behavioral differences that matter:**
- In Void, a typo in `useParams<{ slgu: string }>()` compiles and returns `undefined` at runtime. In React Router, TanStack and SvelteKit it is a type error.
- SvelteKit and TanStack let a param parser change the param's *type* (`number`). In Void that only happens through `withValidator({ params })`, which also makes a failed match a 400 instead of a not-found.

**Void gap:** partial. Missing: per-route param types in components (all 4 adapters' `useParams`) and in loader/head `c.req.param()`. Also missing: a typed transform or matcher for params (SvelteKit, TanStack).

## Typed search params

| Framework | Read API and type | Validation / coercion | Defaults; input vs output types | Inheritance / middleware | Server side |
|---|---|---|---|---|---|
| **Void** | `useRouter().query`: plain `URLSearchParams` (untyped) | **Client: none.** Server: `withValidator({ query })` on a page loader or API handler (Standard Schema; multi-value keys become arrays). A failure on a **page loader** returns a raw 400 JSON response, with no page-level error UI. | Schema defaults apply server-side only. | None | Typed `fetch` `query` is typed from the validator. `routeUrl`'s `query` and `Link data` take a generic `RouteQuery` (keys are not route-specific). |
| Next.js | `PageProps.searchParams` (Promise of `Record<string, string \| string[] \| undefined>`), `useSearchParams` | None | — | — | Pages only (not layouts) |
| React Router | `useSearchParams()` → `URLSearchParams` | None | `defaultInit` does not write to the URL | — | `new URL(request.url).searchParams` |
| TanStack Start | `Route.useSearch()`, `useSearch({ from, select })`: **inferred** | `validateSearch` (a function, `.parse`, or any Standard Schema; Zod v3 via an adapter with `fallback()`). A throw puts the route in an error state (`VALIDATE_SEARCH`) and renders `errorComponent`. | Input and output types are inferred separately, so `.default()` fields are optional on `<Link search>`. | Children merge parent schemas. `search.middlewares`: `retainSearchParams`, `stripSearchParams`. JSON-first serializer with structural sharing. Loaders read search only through `loaderDeps`. | Server functions validate their own input. |
| Nuxt | `route.query` (`LocationQuery`, untyped) | None | — | — | `useFetch({ query })` is enforced against a validated server handler. |
| SvelteKit | `page.url.searchParams` | None | — | — | Remote functions validate args. |
| SolidStart | `useSearchParams<T>()` (manual generic; values `string \| string[]`) | None (setters stringify) | — | Setters merge into the current search. | — |
| Astro | `Astro.url.searchParams` | None | — | — | — |

**Behavioral differences that matter:**
- TanStack treats search params as typed, validated route state, with the schema inherited from parent routes. Everyone else, Void included, treats them as strings on the client.
- Void is ahead of six frameworks on the **server** side, because one `withValidator({ query })` both validates loader input and types `fetch`. The cost is that a failed query validation on a page gives a JSON 400, not a rendered error page.

**Void gap:** partial. Missing: client-side typed and validated search params (a route-level schema reused by `useRouter()`, `Link data` and `routeUrl` `query`), input/output (default) typing, and inheritance. Only TanStack has these.

## Loader / server data → component typing

| Framework | How the component gets the type | Annotation needed | Do types reflect serialization? | Parent / layout data | Deferred / streamed |
|---|---|---|---|---|---|
| **Void** | `export type Props = InferProps<typeof loader>` in `.server.ts`, then `import type { Props }` in the component, then annotate it (`defineProps<Props>()` / `(props: Props)` / `$props()`). Alternatively `defineHandler<Props>()` with a hand-written interface. | **Yes** (export + import + annotate). | **No.** `InferProps<T>` reads `__output`, the raw loader return (packages/void/src/pages/defer.ts:25), but page props go through `JSON.stringify` (packages/void/src/pages/serialize.ts). So `Date` is typed `Date` but arrives as a string, and `undefined`, `bigint` and functions are dropped at runtime but still typed. `Serialize<T>` is applied only to typed `fetch`. | Layouts have **no loader**. `useShared()` is typed from the global `CloudContextVariables['shared']` and is not tied to which middleware ran. | `Deferred<T>`: React `Promise<T>` + `use()`; Vue/Svelte/Solid `{ loading, value, error }`. Typed per adapter. |
| Next.js | Direct: an async Server Component fetches its own data | None | Server Components need no serialization (`Date`, `Map`, `Set` survive). The client-component props boundary has no generated types. | Layouts fetch for themselves (memoized `fetch`). | Promises passed to the client, unwrapped with `use()` |
| React Router | `Route.ComponentProps` (`loaderData`, `actionData`, `params`, `matches`) | One `import type { Route } from './+types/x'` | **Yes** ("types reflect serialization"). `clientLoader.hydrate = true as const` changes the inferred type. | `matches` is typed; `useRouteLoaderData` is less precise. | Typed promises |
| TanStack Start | `Route.useLoaderData()`, `getRouteApi(id).useLoaderData()` | None | Serializer covers `Date`, `Error`, `FormData`, `undefined`. Server functions enforce serializability (`strict`). | `beforeLoad` returns merge into the typed context of child routes. | Typed deferred promises |
| Nuxt | `useAsyncData` / `useFetch` infer `data` (after `transform`/`pick`; `default` widens it) | None | **Yes** for server routes (JSON mapping: `Date` → `string`, `toJSON` respected). The payload uses devalue (keeps `Date`/`Map`/`Set`). | — | `NuxtError<unknown>` error type |
| SvelteKit | `PageProps`, `PageData`, `LayoutData` from `./$types` | None in `.svelte` (language tools inject them) | devalue keeps rich types; the `transport` hook keeps custom classes. | `LayoutData`; `page.data` via `App.PageData` | Streamed promises |
| SolidStart | `createAsync(() => query())` inferred; `RouteSectionProps<T>` for `preload` data (manual) | None for `createAsync` | seroval round-trips rich types. Not reflected in types beyond plain TS. | — | — |
| Astro | Frontmatter variables in the same file; `interface Props`; `InferGetStaticPropsType` | `Props` for components | Server-only render (no round-trip); island props are serialized. | — | — |

**Behavioral differences that matter:**
- Void is the only framework that both serializes page data as **plain JSON** *and* types the props from the **unserialized** loader return. Others either keep rich types (devalue, seroval, turbo-stream, RSC) or map the types (React Router, Nuxt).
- React Router, TanStack and SvelteKit give per-route types for parent/layout data. Void's only cross-page data channel (`shared`) is one global type.

**Void gap:** partial. Missing: (1) serialization-aware page props, either `InferProps` = `Serialize<output>` or a rich serializer; (2) zero-ceremony typing, i.e. a generated sibling type or language-tool injection instead of export/import/annotate; (3) typed layout data, which depends on layout loaders (area 3).

## Typed server calls (RPC / server functions / typed fetch)

| Framework | Mechanism | Input typing and runtime validation | Output typing | Errors | Forms / notes |
|---|---|---|---|---|---|
| **Void** | Typed `fetch` from `void/client` (ofetch) over the generated `RouteMap`; `fetchStream()` for SSE text | Path must be a `RouteMap` key and the method must be exported (otherwise a compile error). `body`, `query` and `params` are typed from `withValidator` (Standard Schema: Zod 3.25+/4, Valibot ≥1, ArkType ≥2; Drizzle-derived via `void/drizzle-*`) and validated on the server → 400 `{ error, issues[{ slot, issues }] }`. Bodies are **JSON only**. `headers` are untyped. | Inferred handler return through `Serialize<T>`; 204 → `undefined` | `FetchError<T = unknown>` `{ status, data, response }`. The error body is **not typed per route** (packages/void/src/runtime/fetch-error.ts). | `useForm(url, defaults, { params })` and `action()` are typed via `PageActionMap`: URL autocomplete including `?name`, `data` from the body schema, `errors` keys typed, `reset()` args typed. **No import-and-call RPC.** |
| Next.js | Server Actions (imported `'use server'` functions) | TS types only; no built-in runtime validation | Inferred through the import | Thrown errors / `useActionState` | Route Handlers have no typed client. |
| React Router | `action` + `Route.ActionArgs` / `actionData`; `useFetcher<typeof action>()` (manual generic) | No built-in validation | Serialization-aware | — | RSC server functions (**unstable**) are plain TS imports. |
| TanStack Start | `createServerFn().validator(fn \| schema).handler()` | Input inferred from the validator (function param or schema output); validated on the server | Inferred; serializability enforced at type level (`strict`); `ReadableStream<T>` and async generators typed | Thrown errors, `redirect`, `notFound` | Middleware `context` additions inferred. Server routes' `params` typed. |
| Nuxt 5 | `$fetch` / `useFetch` typed from **generated route types** (fetchdts) | Method-aware (GET vs `.post.ts`). `body`, `query` and `headers` are **enforced** when the handler uses `defineValidatedHandler` / `readValidatedBody` (Standard Schema). `experimental.strictRouteTypes`: `false` (default: unknown paths → `unknown`), `true`, or `'isomorphic'`. `baseURL` is resolved in the types. | Inferred | `NuxtError<unknown>` | `ServerRoutes` augmentation for routes Nuxt can't see; `createUseFetch({ routes })` types a **third-party API**. Rebuilt in Nuxt 5 (4.x used `InternalApi`, which slowed past about 300 routes). |
| SvelteKit | Remote functions `query` / `form` / `command` / `prerender` **[experimental]** | Standard Schema validated, or `'unchecked'` (TS only) | Inferred | `error()` typed via `App.Error` | `form` fields typed from the schema. Form actions: `ActionData` union. `+server` `fetch` is untyped. |
| SolidStart | `"use server"` functions, `action()`, `useAction` | TS only; no validator | `Promise<NarrowResponse<U>>` | `submission.error` is `any` (docs recommend *returning* errors) | — |
| Astro | Actions: `defineAction({ input: zodSchema, handler })` | Zod (`astro/zod`) validated before the handler; failure → `BAD_REQUEST` `ActionError` | `SafeResult<T>`, `ActionReturnType` | **Typed** `ActionError` codes; `isInputError(e).fields[name]` | Endpoints (`APIRoute`) have untyped bodies. |

**Behavioral differences that matter:**
- Void's model is "typed HTTP to file routes", like Nuxt 5, not "call an imported function" like TanStack, Next.js, SolidStart, Astro Actions and SvelteKit remote functions. The routes stay plain HTTP endpoints, usable by other clients, and the types come from codegen rather than a compiler transform.
- Void is stricter by default than Nuxt 5: an unknown path is an error, not `unknown`. Void cannot type an **external** API or a route added outside `routes/` (Nuxt has `ServerRoutes` augmentation and `createUseFetch({ routes })`).
- Validation is JSON-only in Void. Astro accepts `FormData` input, and SvelteKit's remote `form` validates `FormData` against the schema.
- Error typing: only Astro (codes and field errors) and SvelteKit (`App.Error`) type errors. Void types field errors in `useForm` but not `FetchError.data`.

**Void gap:** partial. Missing: typed error payloads per route; typing for external APIs or augmented routes; typed `headers`; import-and-call RPC (cross-area; see areas 4 and 6).

## Typed request / middleware context

| Framework | Mechanism | Per-chain narrowing | Unknown key | Built-ins typed |
|---|---|---|---|---|
| **Void** | Global augmentation: `declare module 'void' { interface CloudContextVariables { … } }`; `c.get/set` typed everywhere | **No.** A key is typed as present even on routes where the middleware that sets it didn't run. `defineHandler(mw1…mw5, handler)` keeps the leaf's validator/output types but adds no context types. | `unknown` (the interface has a `[key: string]: unknown` index signature, so a typo is not an error) | `user`, `session` (auth), `headDefaults`, `shared` (added by adapters). `c.env` typed from `CloudBindings` + generated `env.d.ts`. |
| Next.js | No locals object; data passes via headers or cookies | — | — | — |
| React Router | `createContext<T>(default?)` keys; `context.get(key)` / `context.set(key, value)` | Per key (not per route) | Reading an unset key with no default **throws** | `Route.MiddlewareFunction[]`, `Route.ClientMiddlewareFunction[]` |
| TanStack Start | Middleware `next({ context })` additions **inferred down the chain**; router context via `createRootRouteWithContext<T>()` + `beforeLoad` returns | **Yes** | Type error | `sendContext` typed both ways (client `next()` result only for middleware known in the chain); `Register.server.requestContext` |
| Nuxt | `event.context` locals | — | Typing not documented | Plugin `provide` typed on `useNuxtApp()`; `useState<T>` |
| SvelteKit | `App.Locals`, `App.Platform`, `App.PageData`, `App.PageState`, `App.Error` in `src/app.d.ts` | No (global) | Type error (no index signature by default) | `platform` typed per adapter |
| SolidStart | `App.RequestEventLocals` augmentation | No | — | `@solidjs/start/env` types |
| Astro | `App.Locals` augmentation | No | — | `defineMiddleware` |

**Behavioral differences that matter:** Void's index signature is looser than SvelteKit's or Astro's global `Locals`: `c.get('reqestId')` compiles and returns `unknown`. TanStack's inferred chain is the only model where types prove that the middleware actually ran.

**Void gap:** partial. Missing: per-chain inference (TanStack) and typed keys that fail when unset (React Router). Optional: dropping the index signature so typos become errors.

## Typed environment variables

| Framework | Declaration | Typed access | Validation (when) | Client/server split |
|---|---|---|---|---|
| **Void** | `env.ts`: `defineEnv({ … })` with `string()`, `number()`, `boolean()`, `url()`, `email()`, `oneOf([...])`, `json<T>()` + `.optional()` / `.default()`, or any Standard Schema | `env` proxy from `void/env`; typed `c.env` via generated `.void/env.d.ts` (`void env types`) | `void env check` (local), `void env check --remote`. Secret commands validate before upload; `void deploy` requires every server key. Validated **again at Worker startup**. Diagnostics redact values. | `VITE_*` = client (build-time; builds ignore `.env` client values). **Build error when client code reads a server key**, warning on computed access (packages/void/src/plugin-env-client-guard.ts). |
| Next.js | Convention | `experimental.typedEnv` (IntelliSense only) | None | `NEXT_PUBLIC_*` inlined; other keys become `''` in client bundles |
| React Router | Not documented | — | — | — |
| TanStack Start | Recipe: `src/env.d.ts` + Zod runtime validation (manual) | Manual | User code | `VITE_` (Vite) / `PUBLIC_` (Rsbuild); server reads `process.env` per request |
| Nuxt | `runtimeConfig` / `app.config` defaults in config | Generated types ("partial" for runtime config) | None (`NUXT_*` overrides cast with destr at runtime) | Private keys are server-only; `public` goes into the payload |
| SvelteKit 3 | `src/env.ts`: `defineEnvVars({ NAME: { public, static, schema, description } })` | `$app/env/private` and `$app/env/public` typed; descriptions on hover | Schema (Standard Schema or function) validated **at build and at startup** | `public` flag; `static: true` inlines and dead-code-eliminates |
| SolidStart | `env:server` / `env:client` / `env:server/runtime` virtual modules (prefixes `SERVER_` / `CLIENT_`) | Not documented | None | Importing `env:server` from client code fails |
| Astro | `astro:env` `envField` (string/number/enum/boolean × context client/server × access public/secret) | Typed via `astro sync` | Validated; secrets on import of `astro:env/server` unless `validateSecrets` | Client secrets impossible |

**Void gap:** none. Void is at parity with SvelteKit 3 and Astro, and ahead of the rest on validation at deploy and boot. Missing at option level: a `static`/inline flag for dead-code elimination (SvelteKit) and per-key descriptions on hover (SvelteKit).

## Codegen vs pure inference (artifacts, triggers, CLI, editor)

| Framework | Model | Artifacts | Regenerated when | CLI | Editor / build type-check |
|---|---|---|---|---|---|
| **Void** | **Codegen for the maps, inference for payloads.** `RouteMap` entries point at `typeof import()` of handler modules, so return types are inferred by TS live. | `.void/routes.d.ts` (augments `void/routes`: `RouteMap`, `WebSocketRouteMap`, `PageActionMap`, `RoutePathMap`, `RewriteDestination`), `env.d.ts`, `db.d.ts`, generated `tsconfig.json` (project `extends: "./.void/tsconfig.json"`) | `vite dev` (file watcher on add/change/unlink, packages/void/src/plugin-routing.ts) and `vite build`. Toggling `typedRoutes` needs a dev restart. | `void prepare` (CI / fresh clone), `void env types`, `void init --tsconfig` | **No typecheck command and no TS language-service plugin** (not found). Per adapter, the user runs `tsc`, `vue-tsc` or `svelte-check`. |
| Next.js | Codegen | `.next/types` (`.next/dev/types` in dev), `next-env.d.ts` | `next dev`, `next build` | `next typegen [dir]` | TS plugin (checks segment-config values, `'use client'` misuse). `next build` runs `tsc` by default (`typescript.ignoreBuildErrors`). |
| React Router | Codegen | `.react-router/types/**/+types/<route>.d.ts` (`rootDirs` gives sibling imports) | `react-router dev`; on route-config change | `react-router typegen [--watch]` | `typegen && tsc` in CI |
| TanStack Start | **Pure inference** + one generated file | `src/routeTree.gen.ts` (also maintains `createFileRoute()` path strings) | Bundler plugin in dev/build | `tsr generate` / `tsr watch` (Router-only) | TS performance guidance; ESLint rule for property order |
| Nuxt | Codegen | `.nuxt/` types + project-reference tsconfigs (`tsconfig.app/server/node/shared.json`) | `nuxt dev`, `nuxt build` | `nuxt prepare`, `nuxt typecheck` (vue-tsc) | `typescript.typeCheck: true \| 'build'`; experimental `typescriptPlugin` (@dxup/nuxt) |
| SvelteKit | Codegen | `.svelte-kit/types/**/$types.d.ts`; user tsconfig must extend `$app/tsconfig` (v3) | `svelte-kit sync` (the `prepare` script, dev, build) | `svelte-kit sync` | Language tools inject `$types` with **zero config**; `svelte-check` |
| SolidStart | None | — | — | — | Types from `@solidjs/start/env` |
| Astro | Codegen | `.astro/types.d.ts` (content, env, actions) | dev, build, check, `s + enter` hotkey | `astro sync`, `astro check` (exits 1 on errors) | Astro language server; integrations add types via `injectTypes()` |

**Behavioral differences that matter:** like Next.js, React Router, Nuxt, SvelteKit and Astro, Void needs a generate step before `tsc` works on a fresh clone. TanStack needs none beyond the route tree. Void is the only codegen framework with **no built-in type-check entry point**. That is harder for Void because its four adapters need four different checkers.

**Void gap:** partial. Missing: an integrated `void check`/typecheck command (it would dispatch to `tsc`, `vue-tsc` or `svelte-check`) and editor-level injection or a plugin, which would also remove the export/import ceremony above.
