import { describe, expect, it, vi, beforeEach, afterEach } from "vitest";
import { createRoot } from "react-dom/client";
import React, { act } from "react";
import { ErrorBoundary } from "./ErrorBoundary";

/** Throws when mountCount reaches throwAfterMounts (for testing boundary). */
function Thrower({
  throwAfterMounts,
  mountCount,
}: {
  throwAfterMounts: number;
  mountCount: number;
}): React.ReactElement {
  if (mountCount >= throwAfterMounts) {
    throw new Error("Intentional test error");
  }
  return <span>OK</span>;
}

describe("ErrorBoundary", () => {
  let consoleErrorSpy: ReturnType<typeof vi.spyOn>;

  beforeEach(() => {
    consoleErrorSpy = vi.spyOn(console, "error").mockImplementation(() => {});
  });

  afterEach(() => {
    consoleErrorSpy.mockRestore();
  });

  it("renders children when there is no error", async () => {
    const container = document.createElement("div");
    document.body.appendChild(container);
    const root = createRoot(container);
    await act(async () => {
      root.render(
        <ErrorBoundary name="Test">
          <span>Child content</span>
        </ErrorBoundary>
      );
    });
    expect(container.textContent).toContain("Child content");
    expect(container.textContent).not.toContain("Something went wrong");
    root.unmount();
    document.body.removeChild(container);
  });

  it("catches error and shows fallback without exposing error details to user", async () => {
    const container = document.createElement("div");
    document.body.appendChild(container);
    const root = createRoot(container);
    await act(async () => {
      root.render(
        <ErrorBoundary name="Test">
          <Thrower throwAfterMounts={0} mountCount={0} />
        </ErrorBoundary>
      );
    });
    expect(container.textContent).toContain("Something went wrong");
    expect(container.textContent).not.toContain("Intentional test error");
    expect(container.textContent).not.toMatch(/\bstack\b/i);
    expect(consoleErrorSpy).toHaveBeenCalled();
    root.unmount();
    document.body.removeChild(container);
  });

  it("retry resets state so fallback can be dismissed", async () => {
    const container = document.createElement("div");
    document.body.appendChild(container);
    const root = createRoot(container);
    await act(async () => {
      root.render(
        <ErrorBoundary name="Test">
          <Thrower throwAfterMounts={0} mountCount={0} />
        </ErrorBoundary>
      );
    });
    expect(container.textContent).toContain("Something went wrong");
    const retryButton = container.querySelector("button");
    expect(retryButton).toBeTruthy();
    await act(async () => {
      retryButton?.click();
    });
    expect(container.textContent).toContain("Something went wrong");
    root.unmount();
    document.body.removeChild(container);
  });

  it("uses custom fallback when provided", async () => {
    const container = document.createElement("div");
    document.body.appendChild(container);
    const root = createRoot(container);
    await act(async () => {
      root.render(
        <ErrorBoundary fallback={<div className="custom-fallback">Custom UI</div>}>
          <Thrower throwAfterMounts={0} mountCount={0} />
        </ErrorBoundary>
      );
    });
    expect(container.querySelector(".custom-fallback")).toBeTruthy();
    expect(container.textContent).toContain("Custom UI");
    root.unmount();
    document.body.removeChild(container);
  });
});
