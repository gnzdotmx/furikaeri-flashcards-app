import React, { useCallback, useEffect, useState } from "react";
import { fetchMe, loginApi, logoutApi, registerApi, setAuthToken } from "../api";
import type { AuthUser } from "../api";
import { AuthContext, useAuth, type AuthContextValue } from "./contextAuth";

// eslint-disable-next-line react-refresh/only-export-components
export { AuthContext, useAuth, type AuthContextValue };

const AUTH_TOKEN_KEY = "furikaeri_access_token";

function getSessionStorage(): Storage | null {
  return typeof sessionStorage !== "undefined" ? sessionStorage : null;
}

function clearStoredToken(): void {
  try {
    getSessionStorage()?.removeItem(AUTH_TOKEN_KEY);
  } catch {
    // ignore
  }
}

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<AuthUser | null>(null);
  const [authLoading, setAuthLoading] = useState(true);
  const [authError, setAuthError] = useState<string | null>(null);

  const loadStoredToken = useCallback(() => {
    try {
      const stored = getSessionStorage()?.getItem(AUTH_TOKEN_KEY) ?? null;
      if (stored) {
        setAuthToken(stored);
        return stored;
      }
    } catch {
      // ignore
    }
    setAuthToken(null);
    return null;
  }, []);

  useEffect(() => {
    const token = loadStoredToken();
    if (!token) {
      setAuthLoading(false);
      return;
    }
    fetchMe()
      .then((u) => setUser(u))
      .catch(() => {
        setAuthToken(null);
        clearStoredToken();
      })
      .finally(() => setAuthLoading(false));
  }, [loadStoredToken]);

  const applyAuthSuccess = useCallback((token: string, userData: AuthUser) => {
    setAuthToken(token);
    setUser(userData);
    try {
      getSessionStorage()?.setItem(AUTH_TOKEN_KEY, token);
    } catch {
      // ignore
    }
  }, []);

  const login = useCallback(
    async (username: string, password: string) => {
      setAuthError(null);
      try {
        const data = await loginApi(username, password);
        applyAuthSuccess(data.access_token, data.user);
      } catch (e: unknown) {
        const message = e instanceof Error ? e.message : "Login failed";
        setAuthError(message);
        throw e;
      }
    },
    [applyAuthSuccess]
  );

  const register = useCallback(
    async (username: string, email: string, password: string) => {
      setAuthError(null);
      try {
        const data = await registerApi(username, email, password);
        applyAuthSuccess(data.access_token, data.user);
      } catch (e: unknown) {
        const message = e instanceof Error ? e.message : "Registration failed";
        setAuthError(message);
        throw e;
      }
    },
    [applyAuthSuccess]
  );

  const logout = useCallback(() => {
    logoutApi().catch(() => { /* best-effort invalidate server session */ });
    setAuthToken(null);
    setUser(null);
    setAuthError(null);
    clearStoredToken();
  }, []);

  const clearAuthError = useCallback(() => setAuthError(null), []);

  const value: AuthContextValue = {
    user,
    isAuthenticated: user != null && (user.username != null || user.email != null),
    authLoading,
    authError,
    login,
    register,
    logout,
    clearAuthError,
  };

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}
