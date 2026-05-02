/** Bearer token and auth headers for API calls. */

let authToken: string | null = null;

export function setAuthToken(token: string | null): void {
  authToken = token;
}

export function authHeaders(): Record<string, string> {
  return authToken ? { Authorization: `Bearer ${authToken}` } : {};
}

export function isDev(): boolean {
  const meta = import.meta as { env?: { DEV?: boolean; MODE?: string } };
  if (typeof meta === "undefined" || !meta.env) return false;
  // Vitest runs with DEV true; avoid noisy client debug logs during npm test.
  if (meta.env.MODE === "test") return false;
  return !!meta.env.DEV;
}
