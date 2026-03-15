import { authHeaders } from "./core";

export type AuthUser = { id: string; username: string | null; email: string | null };

export type LoginResponse = {
  access_token: string;
  token_type: string;
  user: AuthUser;
};

export type RegisterResponse = LoginResponse;

export async function loginApi(username: string, password: string): Promise<LoginResponse> {
  const res = await fetch("/api/auth/login", {
    method: "POST",
    headers: { "Content-Type": "application/json", ...authHeaders() },
    body: JSON.stringify({ username, password }),
    credentials: "include",
  });
  const data = await res.json();
  if (!res.ok) throw new Error((data as { detail?: string })?.detail ?? `login failed: ${res.status}`);
  return data as LoginResponse;
}

export async function registerApi(
  username: string,
  email: string,
  password: string,
): Promise<RegisterResponse> {
  const res = await fetch("/api/auth/register", {
    method: "POST",
    headers: { "Content-Type": "application/json", ...authHeaders() },
    body: JSON.stringify({ username, email, password }),
    credentials: "include",
  });
  const data = await res.json();
  if (!res.ok) throw new Error((data as { detail?: string })?.detail ?? `register failed: ${res.status}`);
  return data as RegisterResponse;
}

export async function fetchMe(): Promise<AuthUser> {
  const res = await fetch("/api/auth/me", { headers: authHeaders(), credentials: "include" });
  const data = await res.json();
  if (!res.ok) throw new Error((data as { detail?: string })?.detail ?? `me failed: ${res.status}`);
  return data as AuthUser;
}

export async function logoutApi(): Promise<void> {
  const res = await fetch("/api/auth/logout", {
    method: "POST",
    headers: authHeaders(),
    credentials: "include",
  });
  if (!res.ok && res.status !== 401) {
    const data = await res.json().catch(() => ({}));
    throw new Error((data as { detail?: string })?.detail ?? `logout failed: ${res.status}`);
  }
}

export type HealthResponse = {
  status: "ok";
  db: { ok: boolean; path: string; exists: boolean; writable_dir: boolean };
};

export async function fetchHealth(): Promise<HealthResponse> {
  const res = await fetch("/api/health", {
    method: "GET",
    headers: { "Content-Type": "application/json", ...authHeaders() },
    credentials: "include",
  });
  if (!res.ok) throw new Error(`health failed: ${res.status}`);
  return (await res.json()) as HealthResponse;
}
