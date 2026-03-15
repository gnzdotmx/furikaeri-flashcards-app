/** Landing: login/register. Tabbed app is shown after auth. */
import React, { useState } from "react";
import { useAuth } from "../context/AuthContext";

export function LandingView() {
  const { authLoading, authError, login, register, clearAuthError } = useAuth();
  const [mode, setMode] = useState<"login" | "register">("login");
  const [username, setUsername] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [confirmError, setConfirmError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  const switchMode = (newMode: "login" | "register") => {
    setMode(newMode);
    clearAuthError();
    setConfirmError(null);
    setConfirmPassword("");
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    clearAuthError();
    setConfirmError(null);
    if (mode === "register") {
      if (password !== confirmPassword) {
        setConfirmError("Passwords do not match.");
        return;
      }
    }
    setSubmitting(true);
    try {
      if (mode === "login") {
        await login(username.trim(), password);
      } else {
        await register(username.trim(), email.trim(), password);
      }
      setUsername("");
      setEmail("");
      setPassword("");
      setConfirmPassword("");
    } catch {
      // error shown via authError
    } finally {
      setSubmitting(false);
    }
  };

  if (authLoading) {
    return (
      <div className="page landingPage">
        <main id="main-content" className="landingMain">
          <div className="panel">
            <p className="muted">Loading…</p>
          </div>
        </main>
      </div>
    );
  }

  return (
    <div className="page landingPage">
      <a href="#main-content" className="skip-link">
        Skip to main content
      </a>
      <header className="appHeader landingHeader">
        <div>
          <div className="title">Furikaeri</div>
          <div className="subtitle">Local JLPT flashcards app</div>
        </div>
      </header>
      <main id="main-content" className="landingMain">
        <div className="panel landingPanel">
          <h1 className="panelTitle">Sign in</h1>
          <p className="panelSubtitle">
            Log in or create an account to use the app.
          </p>

          <div className="row" style={{ marginTop: 16, gap: 8 }}>
            <button
              type="button"
              className={`button ${mode === "login" ? "buttonPrimary" : "buttonSecondary"}`}
              onClick={() => switchMode("login")}
              aria-pressed={mode === "login"}
              disabled={submitting}
            >
              Log in
            </button>
            <button
              type="button"
              className={`button ${mode === "register" ? "buttonPrimary" : "buttonSecondary"}`}
              onClick={() => switchMode("register")}
              aria-pressed={mode === "register"}
              disabled={submitting}
            >
              Register
            </button>
          </div>

          <form onSubmit={handleSubmit} style={{ marginTop: 20 }} aria-busy={submitting}>
            {authError ? (
              <div className="alert" role="alert" style={{ marginBottom: 12 }}>
                {authError}
              </div>
            ) : null}
            {confirmError ? (
              <div id="landing-confirm-error" className="alert" role="alert" style={{ marginBottom: 12 }}>
                {confirmError}
              </div>
            ) : null}
            <div className="label" style={{ marginBottom: 10 }}>
              <label htmlFor="landing-username">Username</label>
              <input
                id="landing-username"
                type="text"
                className="input"
                autoComplete="username"
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                required
                minLength={2}
                maxLength={32}
                disabled={submitting}
              />
            </div>
            {mode === "register" ? (
              <div className="label" style={{ marginBottom: 10 }}>
                <label htmlFor="landing-email">Email</label>
                <input
                  id="landing-email"
                  type="email"
                  className="input"
                  autoComplete="email"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  required
                  disabled={submitting}
                />
              </div>
            ) : null}
            <div className="label" style={{ marginBottom: mode === "register" ? 10 : 16 }}>
              <label htmlFor="landing-password">Password</label>
              <input
                id="landing-password"
                type="password"
                className="input"
                autoComplete={mode === "login" ? "current-password" : "new-password"}
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                required
                minLength={mode === "register" ? 8 : 1}
                aria-invalid={confirmError ? true : undefined}
                disabled={submitting}
              />
              {mode === "register" ? (
                <span className="muted" style={{ fontSize: 12, marginTop: 4, display: "block" }}>
                  At least 8 characters
                </span>
              ) : null}
            </div>
            {mode === "register" ? (
              <div className="label" style={{ marginBottom: 16 }}>
                <label htmlFor="landing-password-confirm">Confirm password</label>
                <input
                  id="landing-password-confirm"
                  type="password"
                  className="input"
                  autoComplete="new-password"
                  value={confirmPassword}
                  onChange={(e) => {
                    setConfirmPassword(e.target.value);
                    setConfirmError(null);
                  }}
                  required
                  minLength={8}
                  aria-invalid={confirmError ? true : undefined}
                  aria-describedby={confirmError ? "landing-confirm-error" : undefined}
                  disabled={submitting}
                />
              </div>
            ) : null}
            <button type="submit" className="button buttonPrimary" disabled={submitting}>
              {submitting ? "…" : mode === "login" ? "Log in" : "Register"}
            </button>
          </form>
        </div>
      </main>
    </div>
  );
}
