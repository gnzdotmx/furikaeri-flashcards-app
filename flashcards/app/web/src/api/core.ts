/** Bearer token and auth headers for API calls. */

let authToken: string | null = null;

export function setAuthToken(token: string | null): void {
  authToken = token;
}

export function authHeaders(): Record<string, string> {
  return authToken ? { Authorization: `Bearer ${authToken}` } : {};
}

export function isDev(): boolean {
  const meta = import.meta as { env?: { DEV?: boolean } };
  return typeof meta !== "undefined" && !!meta?.env?.DEV;
}
