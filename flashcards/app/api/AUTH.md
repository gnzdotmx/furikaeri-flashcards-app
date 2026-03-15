# Auth (register / login / sessions)

The API requires authentication for all endpoints except health, version, and auth (register/login). Each login or register creates a server-side session; every protected request is validated by middleware against that session.

## Environment

- **JWT_SECRET** (required): Must be set in the environment (e.g. in `.env`). Use a strong secret (at least 32 characters for HS256). The app will not start without it. See `.env.example`.
- **JWT_ALGORITHM** (default: `HS256`): Algorithm for signing JWTs.

## Endpoints

- `POST /api/auth/register` — body: `{ "username", "email", "password" }`. Creates user and session. Returns `{ "access_token", "token_type": "bearer", "user" }`.
- `POST /api/auth/login` — body: `{ "username", "password" }`. Creates session. Returns same shape.
- `POST /api/auth/logout` — invalidates the current session (requires valid Bearer token).
- `GET /api/auth/me` — returns current user (requires valid session). No body.

## Middleware (onion)

A single auth-session middleware runs as the outer layer for each request:

- **Public paths** (no auth): `/health`, `/api/health`, `/api/version`, `/api/auth/register`, `/api/auth/login`.
- **Protected paths**: all other `/api/*` routes require a valid `Authorization: Bearer <token>` and a matching valid session in the DB. Invalid or missing token/session returns 401.

Sessions are stored in `auth_sessions` (migration 0010). Login/register create a session and put its id (`jti`) in the JWT; logout deletes the session so the token cannot be reused.

## Session cookie

Login and register responses set an HttpOnly cookie (`furikaeri_session`) with the same token. The middleware accepts the token from either the `Authorization: Bearer` header or this cookie, so same-origin requests can rely on the cookie (e.g. after a refresh). Logout clears the cookie.

## Frontend

The web app uses a **landing page** (login/register only) when not authenticated; there are no tabs until the user signs in. After login, the user sees the tabbed app (Study, Import, Decks, etc.) with Study as the default tab. The token is stored in `sessionStorage` and sent as `Authorization: Bearer`; requests use `credentials: "include"` so the session cookie is also sent. Logout calls `POST /api/auth/logout` to invalidate the server session and clear the cookie, then clears the stored token.
