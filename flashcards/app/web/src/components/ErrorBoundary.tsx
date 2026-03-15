import React, { Component, type ErrorInfo, type ReactNode } from "react";
import { ErrorFallback } from "./ErrorFallback";

export interface ErrorBoundaryProps {
  children: ReactNode;
  /** Optional fallback UI; defaults to <ErrorFallback /> with retry. */
  fallback?: ReactNode;
  /** Optional user-safe message (never pass error details here). */
  fallbackMessage?: string;
  /** Optional name for logging (e.g. tab or section name). */
  name?: string;
}

interface ErrorBoundaryState {
  hasError: boolean;
}

const LOG_PREFIX = "[ErrorBoundary]";

/** Catches render/lifecycle errors, logs to console, shows fallback. No stack traces to user. */
export class ErrorBoundary extends Component<ErrorBoundaryProps, ErrorBoundaryState> {
  constructor(props: ErrorBoundaryProps) {
    super(props);
    this.state = { hasError: false };
  }

  static getDerivedStateFromError(): ErrorBoundaryState {
    return { hasError: true };
  }

  componentDidCatch(error: Error, errorInfo: ErrorInfo): void {
    const name = this.props.name ? ` ${this.props.name}` : "";
    // Log for developers only; never render these in UI
    if (typeof console !== "undefined" && console.error) {
      console.error(`${LOG_PREFIX}${name}`, error, errorInfo.componentStack);
    }
  }

  handleRetry = (): void => {
    this.setState({ hasError: false });
  };

  render(): ReactNode {
    if (this.state.hasError) {
      if (this.props.fallback != null) {
        return this.props.fallback;
      }
      return (
        <ErrorFallback
          message={this.props.fallbackMessage}
          onRetry={this.handleRetry}
          retryLabel="Try again"
        />
      );
    }
    return this.props.children;
  }
}
