import { describe, expect, it, vi } from "vitest";
import React from "react";
import { fireEvent, render, screen, within, waitFor } from "@testing-library/react";
import App from "./App";
import { AuthContext, AuthProvider } from "./context/AuthContext";
import { LandingView } from "./views/LandingView";

function renderApp() {
  return render(
    <AuthProvider>
      <App />
    </AuthProvider>
  );
}

/** Mock auth: authenticated user so App renders the tabbed app (not the landing page). */
const mockLogout = vi.fn();
const mockAuthenticatedValue = {
  user: { id: "1", username: "testuser", email: "test@example.com" },
  isAuthenticated: true,
  authLoading: false,
  authError: null,
  login: async () => {},
  register: async () => {},
  logout: mockLogout,
  clearAuthError: () => {},
};

function renderAuthenticatedApp() {
  return render(
    <AuthContext.Provider value={mockAuthenticatedValue}>
      <App />
    </AuthContext.Provider>
  );
}

describe("App", () => {
  it("renders without crashing when wrapped in AuthProvider", async () => {
    renderApp();
    await waitFor(() => {
      expect(screen.getByText("Furikaeri")).toBeInTheDocument();
    });
  });

  it("when not authenticated shows landing page only (no tabs)", async () => {
    renderApp();
    await waitFor(() => {
      expect(screen.getByText("Furikaeri")).toBeInTheDocument();
    });
    expect(screen.getByRole("heading", { name: /sign in/i })).toBeInTheDocument();
    expect(screen.getByText(/Log in or create an account to use the app/i)).toBeInTheDocument();
    const logInButtons = screen.getAllByRole("button", { name: /log in/i });
    expect(logInButtons).toHaveLength(2); // mode toggle + submit
    expect(logInButtons[1]).toHaveAttribute("type", "submit");
    expect(screen.getByRole("button", { name: /register/i })).toBeInTheDocument();
    expect(screen.queryByRole("navigation", { name: /primary/i })).not.toBeInTheDocument();
  });

  it("when authenticated shows tabbed app with Study as default tab", async () => {
    renderAuthenticatedApp();
    await waitFor(() => {
      expect(screen.getByText("Furikaeri")).toBeInTheDocument();
    });
    const nav = screen.getByRole("navigation", { name: /primary/i });
    expect(nav).toBeInTheDocument();
    const studyButton = within(nav).getByRole("button", { name: /^study$/i });
    expect(studyButton).toHaveAttribute("aria-current", "page");
  });

  it("renders tab navigation with Study, Decks, Search, Metrics, Leeches when authenticated", async () => {
    renderAuthenticatedApp();
    await waitFor(() => {
      expect(screen.getByRole("navigation", { name: /primary/i })).toBeInTheDocument();
    });
    const nav = screen.getByRole("navigation", { name: /primary/i });
    expect(within(nav).getByRole("button", { name: /^study$/i })).toBeInTheDocument();
    expect(within(nav).getByRole("button", { name: /^decks$/i })).toBeInTheDocument();
    expect(within(nav).getByRole("button", { name: /^search$/i })).toBeInTheDocument();
    expect(within(nav).getByRole("button", { name: /^metrics$/i })).toBeInTheDocument();
    expect(within(nav).getByRole("button", { name: /^leeches$/i })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /account menu/i })).toBeInTheDocument();
  });

  it("renders skip navigation link and main content landmark when not authenticated", async () => {
    renderApp();
    await waitFor(() => {
      expect(screen.getByText("Furikaeri")).toBeInTheDocument();
    });
    const skipLink = screen.getByRole("link", { name: /skip to main content/i });
    expect(skipLink).toBeInTheDocument();
    expect(skipLink).toHaveAttribute("href", "#main-content");
    expect(document.getElementById("main-content")).toBeInTheDocument();
  });

  it("register mode shows Password and Confirm password fields", async () => {
    renderApp();
    await waitFor(() => {
      expect(screen.getByText("Furikaeri")).toBeInTheDocument();
    });
    fireEvent.click(screen.getByRole("button", { name: /register/i }));
    expect(screen.getByLabelText(/^password$/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/confirm password/i)).toBeInTheDocument();
  });

  it("register with mismatched passwords shows error and does not submit", async () => {
    renderApp();
    await waitFor(() => {
      expect(screen.getByText("Furikaeri")).toBeInTheDocument();
    });
    fireEvent.click(screen.getByRole("button", { name: /register/i }));
    fireEvent.change(screen.getByLabelText(/^username$/i), { target: { value: "newuser" } });
    fireEvent.change(screen.getByLabelText(/^email$/i), { target: { value: "u@example.com" } });
    fireEvent.change(screen.getByLabelText(/^password$/i), { target: { value: "password123" } });
    fireEvent.change(screen.getByLabelText(/confirm password/i), { target: { value: "password456" } });
    const registerButtons = screen.getAllByRole("button", { name: /register/i });
    const submitButton = registerButtons.find((b) => (b as HTMLButtonElement).type === "submit");
    fireEvent.click(submitButton!);
    await waitFor(() => {
      expect(screen.getByText("Passwords do not match.")).toBeInTheDocument();
    });
  });

  it("disables form and shows loading state on submit (prevents double submit)", async () => {
    const neverResolve = () => new Promise<void>(() => {});
    const mockAuthValue = {
      user: null,
      isAuthenticated: false,
      authLoading: false,
      authError: null,
      login: neverResolve,
      register: neverResolve,
      logout: vi.fn(),
      clearAuthError: vi.fn(),
    };
    render(
      <AuthContext.Provider value={mockAuthValue}>
        <LandingView />
      </AuthContext.Provider>
    );
    fireEvent.click(screen.getByRole("button", { name: /^register$/i }));
    fireEvent.change(screen.getByLabelText(/^username$/i), { target: { value: "newuser" } });
    fireEvent.change(screen.getByLabelText(/^email$/i), { target: { value: "u@example.com" } });
    fireEvent.change(screen.getByLabelText(/^password$/i), { target: { value: "password123" } });
    fireEvent.change(screen.getByLabelText(/confirm password/i), { target: { value: "password123" } });
    const registerButtons = screen.getAllByRole("button", { name: /register/i });
    const submitButton = registerButtons.find((b) => (b as HTMLButtonElement).type === "submit")!;
    fireEvent.click(submitButton);
    await waitFor(() => {
      expect(submitButton).toBeDisabled();
      expect(submitButton).toHaveTextContent("…");
    });
    expect(screen.getByLabelText(/^username$/i)).toBeDisabled();
    expect(screen.getByLabelText(/^password$/i)).toBeDisabled();
  });

  it("switches tab content when tab button is clicked (authenticated)", async () => {
    renderAuthenticatedApp();
    const nav = screen.getByRole("navigation", { name: /primary/i });
    await waitFor(() => {
      expect(within(nav).getByRole("button", { name: /study/i })).toBeInTheDocument();
    });

    fireEvent.click(within(nav).getByRole("button", { name: /^decks$/i }));
    expect(
      await screen.findByText(/Import grammar, vocabulary, and kanji from CSV, or export a deck/i)
    ).toBeInTheDocument();
    expect(screen.getByLabelText(/choose grammar csv/i)).toBeInTheDocument();
    expect(screen.getAllByText(/CSV header:/i).length).toBeGreaterThanOrEqual(1);
    expect(screen.queryByLabelText(/choose vocabulary csv/i)).not.toBeInTheDocument();
    expect(screen.queryByLabelText(/choose kanji csv/i)).not.toBeInTheDocument();
    expect(
      screen.getByText(/japanese_expression, english_meaning, grammar_structure, labels, notes, example_1/i)
    ).toBeInTheDocument();
    expect(screen.getByText(/Export to CSV/)).toBeInTheDocument();
    expect(screen.getByText(/Reimport \/ Sync/)).toBeInTheDocument();

    fireEvent.click(within(nav).getByRole("button", { name: /metrics/i }));
    expect(await screen.findByText("Metrics")).toBeInTheDocument();
  });

  it("does not show API online or Refresh in header when authenticated", async () => {
    renderAuthenticatedApp();
    await waitFor(() => {
      expect(screen.getByText("Furikaeri")).toBeInTheDocument();
    });
    const header = screen.getByRole("banner");
    expect(within(header).queryByText("API online")).not.toBeInTheDocument();
    expect(within(header).queryByRole("button", { name: /^refresh$/i })).not.toBeInTheDocument();
  });

  it("shows account dropdown with current user and Log out when authenticated", async () => {
    renderAuthenticatedApp();
    await waitFor(() => {
      expect(screen.getByRole("button", { name: /account menu/i })).toBeInTheDocument();
    });
    const trigger = screen.getByRole("button", { name: /account menu/i });
    expect(trigger).toHaveTextContent("testuser");

    fireEvent.click(trigger);
    expect(await screen.findByText(/Logged in as/i)).toBeInTheDocument();
    expect(screen.getByRole("menu", { name: /account options/i })).toBeInTheDocument();
    const logoutButton = screen.getByRole("menuitem", { name: /log out/i });
    expect(logoutButton).toBeInTheDocument();

    fireEvent.click(logoutButton);
    expect(mockLogout).toHaveBeenCalled();
  });
});
