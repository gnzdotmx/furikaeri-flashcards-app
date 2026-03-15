import React from "react";

export interface ErrorFallbackProps {
  /** User-safe short message (no stack traces or internal details). */
  message?: string;
  /** Callback to reset error state and retry (e.g. re-mount children). */
  onRetry?: () => void;
  /** Optional label for the retry button. */
  retryLabel?: string;
}

const DEFAULT_MESSAGE = "Something went wrong in this section. You can try again or switch to another tab.";

/** Fallback UI when an error boundary catches; no raw errors or stack traces. */
export function ErrorFallback({
  message = DEFAULT_MESSAGE,
  onRetry,
  retryLabel = "Try again",
}: ErrorFallbackProps): React.ReactElement {
  return (
    <div className="errorFallback" role="alert" aria-live="polite">
      <div className="errorFallbackIcon" aria-hidden="true">
        ⚠
      </div>
      <p className="errorFallbackTitle">Something went wrong</p>
      <p className="errorFallbackMessage">{message}</p>
      {onRetry && (
        <button type="button" className="button buttonPrimary errorFallbackButton" onClick={onRetry}>
          {retryLabel}
        </button>
      )}
    </div>
  );
}
