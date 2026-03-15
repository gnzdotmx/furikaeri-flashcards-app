import { describe, expect, it, vi } from "vitest";
import React from "react";
import { fireEvent, render, screen } from "@testing-library/react";
import { AccountDropdown } from "./AccountDropdown";
import { AuthContext } from "../context/AuthContext";

const mockLogout = vi.fn();

function renderWithAuth(value: React.ComponentProps<typeof AuthContext.Provider>["value"]) {
  return render(
    <AuthContext.Provider value={value}>
      <AccountDropdown />
    </AuthContext.Provider>
  );
}

describe("AccountDropdown", () => {
  it("shows Log out button when user is not authenticated", () => {
    renderWithAuth({
      user: null,
      isAuthenticated: false,
      authLoading: false,
      authError: null,
      login: async () => {},
      register: async () => {},
      logout: mockLogout,
      clearAuthError: () => {},
    });
    const logoutButton = screen.getByRole("button", { name: /log out/i });
    expect(logoutButton).toBeInTheDocument();
    fireEvent.click(logoutButton);
    expect(mockLogout).toHaveBeenCalled();
  });

  it("shows account trigger with username and opens dropdown with Log out", () => {
    renderWithAuth({
      user: { id: "1", username: "johndoe", email: "john@example.com" },
      isAuthenticated: true,
      authLoading: false,
      authError: null,
      login: async () => {},
      register: async () => {},
      logout: mockLogout,
      clearAuthError: () => {},
    });
    const trigger = screen.getByRole("button", { name: /account menu/i });
    expect(trigger).toHaveTextContent("johndoe");

    fireEvent.click(trigger);
    expect(screen.getByText(/Logged in as/i)).toBeInTheDocument();
    expect(screen.getByRole("menu", { name: /account options/i })).toBeInTheDocument();
    const logoutButton = screen.getByRole("menuitem", { name: /log out/i });
    fireEvent.click(logoutButton);
    expect(mockLogout).toHaveBeenCalled();
  });
});
