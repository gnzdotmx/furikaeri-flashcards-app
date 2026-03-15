import React from "react";
import { useApp } from "../context/AppContext";
import { fetchHealth } from "../api";

export function DebugTab() {
  const { health, setHealth, setError } = useApp();

  return (
    <section className="panel">
      <div className="panelHeader">
        <div>
          <div className="panelTitle">Debug</div>
          <div className="panelSubtitle">Raw API responses (for troubleshooting)</div>
        </div>
      </div>

      <div className="row">
        <button
          className="button"
          onClick={async () => {
            setError(null);
            try {
              setHealth(await fetchHealth());
            } catch (e: unknown) {
              setError(e instanceof Error ? e.message : "Unknown error");
            }
          }}
        >
          Refresh health
        </button>
      </div>

      <details className="details" open>
        <summary>API health</summary>
        {health ? <pre className="mono">{JSON.stringify(health, null, 2)}</pre> : <div className="muted">Loading…</div>}
      </details>
    </section>
  );
}
