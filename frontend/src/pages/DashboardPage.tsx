import { useState, useEffect, useCallback } from 'react';
import { api } from '../api/client';
import type { Complaint, Category, Priority, Status, PaginatedComplaints } from '../api/types';

const CATEGORIES: Category[] = ['water', 'electricity', 'sanitation', 'roads', 'streetlights', 'other'];
const PRIORITIES: Priority[] = ['high', 'normal', 'low'];
const STATUSES: Status[] = ['open', 'in_progress', 'resolved', 'rejected'];

// Valid transitions — mirrors backend
const VALID_TRANSITIONS: Record<Status, Status[]> = {
  open: ['in_progress', 'rejected'],
  in_progress: ['resolved', 'rejected'],
  resolved: [],
  rejected: [],
};

/**
 * Dashboard view — paginated, filterable complaint list.
 * Operator can advance status; invalid transition surfaces server's 409 message.
 */
export function DashboardPage() {
  const [data, setData] = useState<PaginatedComplaints | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [statusError, setStatusError] = useState<string | null>(null);

  // Filters
  const [categoryFilter, setCategoryFilter] = useState<Category | ''>('');
  const [priorityFilter, setPriorityFilter] = useState<Priority | ''>('');
  const [statusFilter, setStatusFilter] = useState<Status | ''>('');
  const [page, setPage] = useState(1);
  const pageSize = 10;

  const fetchComplaints = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const result = await api.listComplaints({
        page,
        page_size: pageSize,
        category: categoryFilter || undefined,
        priority: priorityFilter || undefined,
        status: statusFilter || undefined,
      });
      setData(result);
    } catch (err: unknown) {
      const e = err as { detail?: string };
      setError(e.detail || 'Failed to load complaints');
    } finally {
      setLoading(false);
    }
  }, [page, categoryFilter, priorityFilter, statusFilter]);

  useEffect(() => {
    fetchComplaints();
  }, [fetchComplaints]);

  const handleStatusChange = async (complaint: Complaint, newStatus: Status) => {
    setStatusError(null);
    try {
      await api.updateStatus(complaint.id, newStatus);
      fetchComplaints(); // Refresh
    } catch (err: unknown) {
      const e = err as { status?: number; detail?: string };
      if (e.status === 409) {
        // Surface the server's 409 message verbatim, not a generic "error"
        setStatusError(e.detail || 'Invalid status transition');
      } else {
        setStatusError(e.detail || 'Failed to update status');
      }
    }
  };

  const totalPages = data ? Math.ceil(data.total / pageSize) : 0;

  return (
    <div>
      <h1 style={{ fontSize: 'var(--font-size-2xl)', fontWeight: 700, marginBottom: 'var(--space-lg)' }}>
        📋 Operations Dashboard
      </h1>

      {/* Filters */}
      <div className="filters">
        <select
          className="form-select"
          style={{ width: 'auto' }}
          value={categoryFilter}
          onChange={(e) => { setCategoryFilter(e.target.value as Category | ''); setPage(1); }}
          id="filter-category"
        >
          <option value="">All Categories</option>
          {CATEGORIES.map((c) => (
            <option key={c} value={c}>{c}</option>
          ))}
        </select>

        <select
          className="form-select"
          style={{ width: 'auto' }}
          value={priorityFilter}
          onChange={(e) => { setPriorityFilter(e.target.value as Priority | ''); setPage(1); }}
          id="filter-priority"
        >
          <option value="">All Priorities</option>
          {PRIORITIES.map((p) => (
            <option key={p} value={p}>{p}</option>
          ))}
        </select>

        <select
          className="form-select"
          style={{ width: 'auto' }}
          value={statusFilter}
          onChange={(e) => { setStatusFilter(e.target.value as Status | ''); setPage(1); }}
          id="filter-status"
        >
          <option value="">All Statuses</option>
          {STATUSES.map((s) => (
            <option key={s} value={s}>{s.replace('_', ' ')}</option>
          ))}
        </select>

        <button className="btn btn-secondary btn-sm" onClick={() => {
          setCategoryFilter('');
          setPriorityFilter('');
          setStatusFilter('');
          setPage(1);
        }}>
          Clear Filters
        </button>
      </div>

      {/* Status transition error — surfaces server's 409 message verbatim */}
      {statusError && (
        <div className="alert alert-error">⚠️ {statusError}</div>
      )}

      {error && <div className="alert alert-error">⚠️ {error}</div>}

      {loading ? (
        <div className="loading-overlay">
          <div className="spinner spinner-lg" />
          <span>Loading complaints...</span>
        </div>
      ) : data && data.items.length > 0 ? (
        <>
          <div className="table-container">
            <table>
              <thead>
                <tr>
                  <th>Summary</th>
                  <th>Location</th>
                  <th>Category</th>
                  <th>Priority</th>
                  <th>Status</th>
                  <th>Provider</th>
                  <th>Actions</th>
                </tr>
              </thead>
              <tbody>
                {data.items.map((c) => (
                  <tr key={c.id}>
                    <td style={{ maxWidth: '250px' }}>
                      <div style={{ fontWeight: 500, marginBottom: 2 }}>
                        {c.ai_summary || c.text.substring(0, 60) + '...'}
                      </div>
                      <div style={{ fontSize: 'var(--font-size-xs)', color: 'var(--color-text-muted)' }}>
                        {new Date(c.created_at).toLocaleDateString()}
                      </div>
                    </td>
                    <td style={{ fontSize: 'var(--font-size-xs)' }}>{c.location}</td>
                    <td><span className={`badge badge-${c.category}`}>{c.category}</span></td>
                    <td><span className={`badge badge-${c.priority}`}>{c.priority}</span></td>
                    <td><span className={`badge badge-${c.status}`}>{c.status.replace('_', ' ')}</span></td>
                    <td style={{ fontFamily: 'monospace', fontSize: 'var(--font-size-xs)' }}>{c.triaged_by}</td>
                    <td>
                      {VALID_TRANSITIONS[c.status].length > 0 ? (
                        <div style={{ display: 'flex', gap: '4px' }}>
                          {VALID_TRANSITIONS[c.status].map((targetStatus) => (
                            <button
                              key={targetStatus}
                              className={`btn btn-sm ${targetStatus === 'rejected' ? 'btn-danger' : 'btn-secondary'}`}
                              onClick={() => handleStatusChange(c, targetStatus)}
                            >
                              → {targetStatus.replace('_', ' ')}
                            </button>
                          ))}
                        </div>
                      ) : (
                        <span style={{ fontSize: 'var(--font-size-xs)', color: 'var(--color-text-muted)' }}>
                          Terminal
                        </span>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          {/* Pagination */}
          <div className="pagination">
            <button
              className="btn btn-secondary btn-sm"
              disabled={page <= 1}
              onClick={() => setPage(page - 1)}
            >
              ← Previous
            </button>
            <span className="pagination-info">
              Page {page} of {totalPages} ({data.total} total)
            </span>
            <button
              className="btn btn-secondary btn-sm"
              disabled={page >= totalPages}
              onClick={() => setPage(page + 1)}
            >
              Next →
            </button>
          </div>
        </>
      ) : (
        <div className="loading-overlay">
          <span>No complaints found.</span>
        </div>
      )}
    </div>
  );
}
