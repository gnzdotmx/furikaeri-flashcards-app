/** Header account dropdown: current user and Log out. Uses AuthContext. */
import React, { useCallback, useEffect, useRef, useState } from "react";
import { useAuth } from "../context/AuthContext";

const DROPDOWN_ID = "account-dropdown-menu";

export function AccountDropdown() {
  const { user, isAuthenticated, logout } = useAuth();
  const [open, setOpen] = useState(false);
  const containerRef = useRef<HTMLDivElement>(null);

  const close = useCallback(() => setOpen(false), []);

  useEffect(() => {
    if (!open) return;
    const handleEscape = (e: KeyboardEvent) => {
      if (e.key === "Escape") close();
    };
    const handleClickOutside = (e: MouseEvent) => {
      if (containerRef.current && !containerRef.current.contains(e.target as Node)) {
        close();
      }
    };
    document.addEventListener("keydown", handleEscape);
    document.addEventListener("mousedown", handleClickOutside);
    return () => {
      document.removeEventListener("keydown", handleEscape);
      document.removeEventListener("mousedown", handleClickOutside);
    };
  }, [open, close]);

  const handleLogout = useCallback(() => {
    close();
    logout();
  }, [close, logout]);

  if (!isAuthenticated || !user) {
    return (
      <div className="accountDropdownWrap">
        <button
          type="button"
          className="button buttonSecondary accountDropdownTrigger"
          onClick={logout}
          aria-label="Log out"
        >
          Log out
        </button>
      </div>
    );
  }

  const displayName = user.username ?? user.email ?? user.id;

  return (
    <div className="accountDropdownWrap" ref={containerRef}>
      <button
        type="button"
        className="button buttonSecondary accountDropdownTrigger"
        onClick={() => setOpen((prev) => !prev)}
        aria-expanded={open}
        aria-haspopup="menu"
        aria-controls={open ? DROPDOWN_ID : undefined}
        aria-label="Account menu"
      >
        <span className="accountDropdownLabel">{displayName}</span>
        <span className="accountDropdownChevron" aria-hidden="true">
          {open ? "▴" : "▾"}
        </span>
      </button>
      {open ? (
        <div
          id={DROPDOWN_ID}
          className="accountDropdownMenu"
          role="menu"
          aria-label="Account options"
        >
          <div className="accountDropdownUser" role="presentation">
            <span className="accountDropdownUserLabel">Logged in as</span>
            <strong>{displayName}</strong>
            {user.email && user.email !== displayName ? (
              <span className="accountDropdownEmail">{user.email}</span>
            ) : null}
          </div>
          <button
            type="button"
            className="button buttonSecondary accountDropdownLogout"
            role="menuitem"
            onClick={handleLogout}
          >
            Log out
          </button>
        </div>
      ) : null}
    </div>
  );
}
