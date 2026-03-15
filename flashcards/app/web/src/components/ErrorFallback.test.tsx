import { describe, expect, it, vi } from "vitest";
import React from "react";
import { render, screen, fireEvent } from "@testing-library/react";
import { ErrorFallback } from "./ErrorFallback";

describe("ErrorFallback", () => {
  it("renders default message and retry button", () => {
    const onRetry = vi.fn();
    render(<ErrorFallback onRetry={onRetry} />);
    expect(screen.getByText("Something went wrong")).toBeInTheDocument();
    expect(
      screen.getByText(/Something went wrong in this section/)
    ).toBeInTheDocument();
    const button = screen.getByRole("button", { name: /try again/i });
    expect(button).toBeInTheDocument();
  });

  it("renders custom message and does not expose raw error content", () => {
    render(<ErrorFallback message="This tab had a problem." />);
    expect(screen.getByText("This tab had a problem.")).toBeInTheDocument();
    const body = document.body.textContent ?? "";
    expect(body).not.toMatch(/\bstack\b/i);
  });

  it("calls onRetry when retry button is clicked", () => {
    const onRetry = vi.fn();
    render(<ErrorFallback onRetry={onRetry} retryLabel="Retry" />);
    expect(screen.getByRole("button", { name: /retry/i })).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: /retry/i }));
    expect(onRetry).toHaveBeenCalledTimes(1);
  });

  it("has role alert and aria-live for accessibility", () => {
    render(<ErrorFallback />);
    const el = screen.getByRole("alert");
    expect(el).toBeInTheDocument();
    expect(el).toHaveAttribute("aria-live", "polite");
  });
});
