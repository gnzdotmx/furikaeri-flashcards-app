import React, { useEffect, useRef, useState } from "react";
import { useApp } from "../context/AppContext";
import { fetchMetrics, type MetricsResponse } from "../api";

export function MetricsTab() {
  const { setError } = useApp();
  const [metrics, setMetrics] = useState<MetricsResponse | null>(null);
  const [metricsLoading, setMetricsLoading] = useState(false);
  const [metricsError, setMetricsError] = useState<string | null>(null);
  const [metricsSubTab, setMetricsSubTab] = useState<"overview" | "ratings" | "focus" | "methodology">("overview");
  const metricsRequestIdRef = useRef(0);
  const metricsFetchInFlightRef = useRef(false);

  useEffect(() => {
    if (metricsFetchInFlightRef.current) return;
    metricsFetchInFlightRef.current = true;
    const requestId = ++metricsRequestIdRef.current;
    setMetricsError(null);
    setMetricsLoading(true);
    fetchMetrics()
      .then((data) => {
        if (requestId !== metricsRequestIdRef.current) return;
        setMetrics(data ?? null);
        setMetricsError(null);
      })
      .catch((e: unknown) => {
        if (requestId !== metricsRequestIdRef.current) return;
        setMetricsError(e instanceof Error ? e.message : "Failed to load metrics");
      })
      .finally(() => {
        metricsFetchInFlightRef.current = false;
        if (requestId !== metricsRequestIdRef.current) return;
        setMetricsLoading(false);
      });
  }, []);

  const handleRefresh = async () => {
    setError(null);
    setMetricsError(null);
    setMetricsLoading(true);
    try {
      setMetrics(await fetchMetrics());
    } catch (e: unknown) {
      setMetricsError(e instanceof Error ? e.message : "Unknown error");
    } finally {
      setMetricsLoading(false);
    }
  };

  return (
    <section className="panel panelMetrics">
      <div className="panelHeader">
        <div>
          <div className="panelTitle">Progress & focus</div>
          <div className="panelSubtitle">See how you learn — retention, effort, and methodology</div>
        </div>
        <button className="button buttonSecondary" disabled={metricsLoading} onClick={handleRefresh} aria-label="Refresh metrics">
          {metricsLoading ? "Loading…" : "Refresh"}
        </button>
      </div>

      {metricsError ? (
        <div className="metricsEmpty" role="alert">
          <p className="metricsEmptyTitle">Failed to load metrics</p>
          <p className="metricsEmptyText">{metricsError}</p>
          <p className="metricsEmptyText">Check that the API is running and try Refresh.</p>
        </div>
      ) : metricsLoading && metrics == null ? (
        <div className="metricsEmpty">
          <p className="metricsEmptyTitle">Loading metrics…</p>
        </div>
      ) : (
        <>
          <nav className="metricsTabs" aria-label="Metrics views">
            {([["overview", "Overview", "○"], ["ratings", "Ratings", "▣"], ["focus", "Focus", "◷"], ["methodology", "Methodology", "◈"]] as const).map(([key, label, icon]) => (
              <button
                key={key}
                className={metricsSubTab === key ? "metricsTab metricsTabActive" : "metricsTab"}
                onClick={() => setMetricsSubTab(key)}
                aria-current={metricsSubTab === key ? "true" : undefined}
              >
                <span className="metricsTabIcon" aria-hidden>{icon}</span>
                {label}
              </button>
            ))}
          </nav>

          {metricsSubTab === "overview" ? (
            metrics ? (
              <div className="metricsOverview">
                {((metrics.streak_days != null && metrics.streak_days > 0) || (metrics.daily_goal_reviews != null && metrics.daily_goal_reviews > 0)) ? (
                  <div className="metricsDailyRow">
                    {metrics.streak_days != null && metrics.streak_days > 0 ? (
                      <div className="metricCard metricCardStreak">
                        <div className="metricCardIcon" aria-hidden>
                          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M8 2v4M16 2v4M3 10h18M5 4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2V6a2 2 0 0 0-2-2" /></svg>
                        </div>
                        <div className="metricCardContent">
                          <div className="metricCardLabel">Streak</div>
                          <div className="metricCardValue">{metrics.streak_days} day{metrics.streak_days !== 1 ? "s" : ""}</div>
                          <div className="metricCardHint">Consecutive days with at least one review</div>
                        </div>
                      </div>
                    ) : null}
                    {metrics.daily_goal_reviews != null && metrics.daily_goal_reviews > 0 ? (
                      <div className="metricCard metricCardDailyGoal">
                        <div className="metricCardIcon" aria-hidden>
                          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M9 11l3 3L22 4" /><path d="M21 12v7a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11" /></svg>
                        </div>
                        <div className="metricCardContent">
                          <div className="metricCardLabel">Today&apos;s goal</div>
                          <div className="metricCardValue">{(metrics.reviews_done_today ?? 0)} / {metrics.daily_goal_reviews}</div>
                          <div className="metricCardHint">Reviews done today</div>
                        </div>
                      </div>
                    ) : null}
                  </div>
                ) : null}
                {metrics.n > 0 ? (
                  <div className="metricsOverviewGrid">
                    <div className="metricCard metricCardRetention">
                      <div className="metricCardIcon" aria-hidden>
                        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round">
                          <circle cx="12" cy="12" r="10" strokeOpacity="0.25" />
                          <circle cx="12" cy="12" r="10" strokeDasharray={`${(metrics.retention_proxy ?? 0) * 62.83} 62.83`} transform="rotate(-90 12 12)" />
                        </svg>
                      </div>
                      <div className="metricCardContent">
                        <div className="metricCardLabel">Retention</div>
                        <div className="metricCardValue">{Math.round((metrics.retention_proxy ?? 0) * 100)}%</div>
                        <div className="metricCardHint">Higher = more cards remembered</div>
                      </div>
                    </div>
                    <div className="metricCard metricCardReviews">
                      <div className="metricCardIcon" aria-hidden>
                        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M4 19.5A2.5 2.5 0 0 1 6.5 17H20" /><path d="M6.5 2H20v20H6.5A2.5 2.5 0 0 1 4 19.5v-15A2.5 2.5 0 0 1 6.5 2z" /></svg>
                      </div>
                      <div className="metricCardContent">
                        <div className="metricCardLabel">Reviews (sample)</div>
                        <div className="metricCardValue">{metrics.n}</div>
                        <div className="metricCardHint">Last ~200 answers</div>
                      </div>
                    </div>
                    <div className="metricCard metricCardTime">
                      <div className="metricCardIcon" aria-hidden>
                        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><circle cx="12" cy="12" r="10" /><path d="M12 6v6l4 2" /></svg>
                      </div>
                      <div className="metricCardContent">
                        <div className="metricCardLabel">Avg time per card</div>
                        <div className="metricCardValue">{Math.round((metrics.avg_time_ms ?? 0) / 1000)}s</div>
                        <div className="metricCardHint">Steady pace supports focus</div>
                      </div>
                    </div>
                  </div>
                ) : null}
              </div>
            ) : (
              <div className="metricsEmpty">
                <p className="metricsEmptyTitle">No data yet</p>
                <p className="metricsEmptyText">Do some reviews, then come back here to see retention and focus metrics.</p>
                <p className="metricsEmptyText">If you’ve already done reviews, click <strong>Refresh</strong> above or open the <strong>Methodology</strong> tab to see raw response.</p>
              </div>
            )
          ) : metricsSubTab === "ratings" ? (
            metrics && metrics.n > 0 ? (
              <div className="metricsRatings">
                <p className="metricsSectionHint">Distribution of your last answers — aim for more Good/Easy over time.</p>
                <div className="ratingBars">
                  {(["again", "hard", "good", "easy"] as const).map((r) => {
                    const count = metrics.by_rating?.[r] ?? 0;
                    const pct = metrics.n ? (count / metrics.n) * 100 : 0;
                    return (
                      <div key={r} className="ratingBarRow">
                        <span className={`ratingBarLabel ratingBarLabel-${r}`}>{r}</span>
                        <div className="ratingBarTrack">
                          <div className={`ratingBarFill ratingBarFill-${r}`} style={{ width: `${pct}%` }} />
                        </div>
                        <span className="ratingBarCount">{count}</span>
                      </div>
                    );
                  })}
                </div>
                <div className="metricCard metricCardAgainRate">
                  <div className="metricCardLabel">Again rate</div>
                  <div className="metricCardValue">{typeof metrics.again_rate === "number" ? (metrics.again_rate * 100).toFixed(1) : metrics.again_rate}%</div>
                  <div className="metricCardHint">Lower is better — fewer cards forgotten</div>
                </div>
              </div>
            ) : (
              <div className="metricsEmpty">
                <p className="metricsEmptyTitle">No ratings yet</p>
                <p className="metricsEmptyText">Complete a few cards to see your rating distribution.</p>
              </div>
            )
          ) : metricsSubTab === "focus" ? (
            metrics && metrics.n > 0 ? (
              <div className="metricsFocus">
                <div className="metricCard metricCardFocus">
                  <div className="metricCardIcon" aria-hidden>
                    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><circle cx="12" cy="12" r="10" /><path d="M12 6v6l4 2" /></svg>
                  </div>
                  <div className="metricCardContent">
                    <div className="metricCardLabel">Focus (avg time)</div>
                    <div className="metricCardValue">{Math.round((metrics.avg_time_ms ?? 0) / 1000)}s per card</div>
                    <div className="metricCardHint">
                      {(metrics.avg_time_ms ?? 0) >= 60000 ? "Slower pace — good for hard material." : (metrics.avg_time_ms ?? 0) >= 15000 ? "Steady focus — keep it up." : "Quick reviews — ideal for consolidation."}
                    </div>
                  </div>
                </div>
                <div className="focusTips">
                  <p><strong>Effort signals</strong></p>
                  <ul>
                    <li>Time per card reflects engagement; very fast may mean guessing.</li>
                    <li>Use &quot;Again&quot; when you didn’t recall — it improves long-term retention.</li>
                    <li>Short, regular sessions beat rare long ones.</li>
                  </ul>
                </div>
              </div>
            ) : (
              <div className="metricsEmpty">
                <p className="metricsEmptyTitle">No focus data yet</p>
                <p className="metricsEmptyText">Review some cards to see your average time and effort signals.</p>
              </div>
            )
          ) : (
            <div className="metricsMethodology">
              <p className="metricsSectionHint">Principles that make spaced repetition effective — no extra data, just how to learn better.</p>
              <div className="methodologyCards">
                <div className="methodologyCard">
                  <div className="methodologyCardTitle">Spaced repetition</div>
                  <p>Review at increasing intervals. &quot;Again&quot; resets the interval; &quot;Good&quot;/&quot;Easy&quot; extend it. Trust the schedule.</p>
                </div>
                <div className="methodologyCard">
                  <div className="methodologyCardTitle">Honest ratings</div>
                  <p>Rate only after trying to recall. If you didn’t know it, choose Again — the algorithm adapts and you retain more.</p>
                </div>
                <div className="methodologyCard">
                  <div className="methodologyCardTitle">Focus & consistency</div>
                  <p>Short daily sessions beat cramming. Steady pace (a few seconds per card when fluent) is a sign of good focus.</p>
                </div>
                <div className="methodologyCard">
                  <div className="methodologyCardTitle">Retention over speed</div>
                  <p>Aim for high retention (few &quot;Again&quot;s). It’s better to do fewer cards well than many with low recall.</p>
                </div>
              </div>
              <details className="details">
                <summary>Raw metrics (for power users)</summary>
                {metrics && metrics.n === 0 ? (
                  <p className="metricsEmptyText" style={{ marginBottom: "0.5rem" }}>
                    Metrics use rated answers only. Rate each card with <strong>Again / Hard / Good / Easy</strong> so the server records them. If you did rate but still see zeros, try <strong>Refresh</strong>.
                  </p>
                ) : null}
                <pre className="mono">{metrics ? JSON.stringify(metrics, null, 2) : "No data yet."}</pre>
              </details>
            </div>
          )}
        </>
      )}
    </section>
  );
}
