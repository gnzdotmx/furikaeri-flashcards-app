/**
 * Account tab: profile and logout. Only shown in the tabbed app when authenticated.
 * Login/register lives on the landing page (LandingView), not in tabs.
 */
import React from "react";
import { useAuth } from "../context/AuthContext";

export function AccountTab() {
  const { user, isAuthenticated, logout } = useAuth();

  if (!isAuthenticated || !user) {
    return (
      <div className="panel">
        <h2 className="panelTitle">Account</h2>
        <p className="panelSubtitle">Session may have expired.</p>
        <div className="row" style={{ marginTop: 16 }}>
          <button type="button" className="button buttonSecondary" onClick={logout}>
            Log out
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="panel">
      <h2 className="panelTitle">Account</h2>
      <p className="panelSubtitle">
        Logged in as <strong>{user.username ?? user.email ?? user.id}</strong>
      </p>
      {user.email ? (
        <p className="muted" style={{ marginTop: 8 }}>
          {user.email}
        </p>
      ) : null}
      <div className="row" style={{ marginTop: 16 }}>
        <button type="button" className="button buttonSecondary" onClick={logout}>
          Log out
        </button>
      </div>
    </div>
  );
}
