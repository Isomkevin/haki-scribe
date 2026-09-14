# Routes

TanStack Start uses **file-based routing**. Every `.tsx` file in this directory
defines a route. Do **not** create `src/pages/`, `src/routes/_app/index.tsx`, or
`app/layout.tsx` — those are Next.js / Remix conventions. The only root layout
is `src/routes/__root.tsx`.

## HakiScribe routes

| File | URL | Access |
| --- | --- | --- |
| `index.tsx` | `/` | Public landing |
| `login.tsx` | `/login` | Public sign-in (`?next=` return path) |
| `new.tsx` | `/new` | Private — start session + library |
| `sessions.$sessionId.tsx` | `/sessions/:sessionId` | Private — record → Action Tray |
| `tracker.tsx` | `/tracker` | Private — case / matter tracker |
| `research.tsx` | `/research` | Private — Exa research / news |
| `settings.tsx` | `/settings` | Private — profile, workspace, security, connectors, about (`?section=`) |
| `connectors.tsx` | `/connectors` | Redirects to `/settings?section=connectors` |
| `__root.tsx` | — | App shell — wraps every page; preserve `<Outlet />` |

Private pages wrap content in `RequireAuth` (`src/components/hakiscribe/auth-gate.tsx`).
Signed-out users are sent to `/login` and returned afterward.

## File-based routing conventions

| File | URL |
| --- | --- |
| `index.tsx` | `/` |
| `users/$id.tsx` | `/users/:id` (dynamic — bare `$`, no curly braces) |
| `posts/{-$category}.tsx` | `/posts/:category?` (optional segment) |
| `files/$.tsx` | `/files/*` (splat — read via `_splat` param, never `*`) |
| `_layout.tsx` | layout route (renders children via `<Outlet />`) |
| `__root.tsx` | app shell — wraps every page; preserve `<Outlet />` |

`routeTree.gen.ts` is auto-generated. Don't edit it by hand.
