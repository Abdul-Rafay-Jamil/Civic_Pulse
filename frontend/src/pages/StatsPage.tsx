import { useState, useEffect } from 'react';
import { api } from '../api/client';
import type { StatsResponse, ProviderInfo } from '../api/types';

/**
 * Stats view — aggregate counts by category and priority.
 * Displays cache-hit state from X-Cache header.
 */
export function StatsPage() {
  const [stats, setStats] = useState<StatsResponse | null>(null);
  const [cacheHit, setCacheHit] = useState<boolean | null>(null);
  const [providerInfo, setProviderInfo] = useState<ProviderInfo | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchData = async () => {
    setLoading(true);
    setError(null);
    try {
      const [statsResult, provider] = await Promise.all([
        api.getStats(),
        api.getProviderInfo(),
      ]);
      setStats(statsResult.stats);
      setCacheHit(statsResult.cacheHit);
      setProviderInfo(provider);
    } catch (err: unknown) {
      const e = err as { detail?: string };
      setError(e.detail || 'Failed to load statistics');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
  }, []);

  if (loading) {
    return (
      <div className="loading-overlay">
        <div className="spinner spinner-lg" />
        <span>Loading statistics...</span>
      </div>
    );
  }

  if (error) {
    return <div className="alert alert-error">⚠️ {error}</div>;
  }

  const categoryColors: Record<string, string> = {
    water: 'var(--color-water)',
    electricity: 'var(--color-electricity)',
    sanitation: 'var(--color-sanitation)',
    roads: 'var(--color-roads)',
    streetlights: 'var(--color-streetlights)',
    other: 'var(--color-other)',
  };

  return (
    <div>
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 'var(--space-lg)' }}>
        <h1 style={{ fontSize: 'var(--font-size-2xl)', fontWeight: 700 }}>
          📊 Statistics
        </h1>
        <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-sm)' }}>
          <span className={`cache-indicator ${cacheHit ? 'cache-hit' : 'cache-miss'}`}>
            {cacheHit ? '⚡ Cache HIT' : '🔄 Cache MISS'}
          </span>
          <button className="btn btn-secondary btn-sm" onClick={fetchData}>
            Refresh
          </button>
        </div>
      </div>

      {stats && (
        <>
          {/* Total */}
          <div className="stats-grid" style={{ marginBottom: 'var(--space-xl)' }}>
            <div className="stat-card">
              <div className="stat-value">{stats.total}</div>
              <div className="stat-label">Total Complaints</div>
            </div>
          </div>

          {/* By Category */}
          <div className="card" style={{ marginBottom: 'var(--space-lg)' }}>
            <h2 className="card-title" style={{ marginBottom: 'var(--space-md)' }}>By Category</h2>
            <div className="stats-grid">
              {Object.entries(stats.by_category).map(([cat, count]) => (
                <div key={cat} className="stat-card" style={{ borderLeft: `3px solid ${categoryColors[cat] || 'var(--color-border)'}` }}>
                  <div className="stat-value">{count}</div>
                  <div className="stat-label" style={{ textTransform: 'capitalize' }}>{cat}</div>
                </div>
              ))}
            </div>
          </div>

          {/* By Priority */}
          <div className="card" style={{ marginBottom: 'var(--space-lg)' }}>
            <h2 className="card-title" style={{ marginBottom: 'var(--space-md)' }}>By Priority</h2>
            <div className="stats-grid">
              {Object.entries(stats.by_priority).map(([pri, count]) => (
                <div key={pri} className="stat-card">
                  <div className="stat-value">{count}</div>
                  <div className="stat-label">
                    <span className={`badge badge-${pri}`}>{pri}</span>
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* By Status */}
          <div className="card" style={{ marginBottom: 'var(--space-lg)' }}>
            <h2 className="card-title" style={{ marginBottom: 'var(--space-md)' }}>By Status</h2>
            <div className="stats-grid">
              {Object.entries(stats.by_status).map(([st, count]) => (
                <div key={st} className="stat-card">
                  <div className="stat-value">{count}</div>
                  <div className="stat-label">
                    <span className={`badge badge-${st}`}>{st.replace('_', ' ')}</span>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </>
      )}

      {/* Provider Info */}
      {providerInfo && (
        <div className="card">
          <h2 className="card-title" style={{ marginBottom: 'var(--space-md)' }}>
            🤖 Triage Provider
          </h2>
          <div style={{ marginBottom: 'var(--space-md)' }}>
            <span style={{ color: 'var(--color-text-secondary)' }}>Active: </span>
            <span style={{ fontFamily: 'monospace', color: 'var(--color-primary)' }}>
              {providerInfo.active_provider}
            </span>
          </div>

          {providerInfo.recent_outcomes.length > 0 && (
            <>
              <h3 style={{ fontSize: 'var(--font-size-sm)', color: 'var(--color-text-secondary)', marginBottom: 'var(--space-sm)' }}>
                Recent Triage Outcomes (last 20)
              </h3>
              <div className="table-container">
                <table>
                  <thead>
                    <tr>
                      <th>Provider</th>
                      <th>Latency</th>
                      <th>Fallback</th>
                      <th>Time</th>
                    </tr>
                  </thead>
                  <tbody>
                    {providerInfo.recent_outcomes.map((outcome, i) => (
                      <tr key={i}>
                        <td style={{ fontFamily: 'monospace', fontSize: 'var(--font-size-xs)' }}>
                          {outcome.provider}
                        </td>
                        <td>{outcome.latency_ms} ms</td>
                        <td>
                          {outcome.fallback ? (
                            <span className="badge badge-high">Yes</span>
                          ) : (
                            <span style={{ color: 'var(--color-text-muted)' }}>No</span>
                          )}
                        </td>
                        <td style={{ fontSize: 'var(--font-size-xs)' }}>
                          {outcome.timestamp ? new Date(outcome.timestamp).toLocaleString() : '—'}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </>
          )}
        </div>
      )}
    </div>
  );
}
