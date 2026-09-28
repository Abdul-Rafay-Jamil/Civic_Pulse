import { useState } from 'react';
import { api } from '../api/client';
import type { Complaint, ComplaintCreate } from '../api/types';

/**
 * Submit view — free-text complaint with validation, loading state,
 * and display of triage results (category, priority, AI summary, provider).
 */
export function SubmitPage() {
  const [form, setForm] = useState<ComplaintCreate>({
    text: '',
    location: '',
    reporter_contact: '',
  });
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<Complaint | null>(null);
  const [submitError, setSubmitError] = useState<string | null>(null);

  const validate = (): boolean => {
    const errs: Record<string, string> = {};
    if (form.text.length < 10) errs.text = 'Complaint must be at least 10 characters';
    if (form.text.length > 2000) errs.text = 'Complaint must be at most 2000 characters';
    if (form.location.length < 3) errs.location = 'Location must be at least 3 characters';
    if (form.location.length > 200) errs.location = 'Location must be at most 200 characters';
    setErrors(errs);
    return Object.keys(errs).length === 0;
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setSubmitError(null);
    setResult(null);

    if (!validate()) return;

    setLoading(true);
    try {
      const complaint = await api.createComplaint({
        text: form.text,
        location: form.location,
        reporter_contact: form.reporter_contact || undefined,
      });
      setResult(complaint);
      setForm({ text: '', location: '', reporter_contact: '' });
    } catch (err: unknown) {
      const error = err as { status?: number; detail?: string; errors?: Array<{ field: string; message: string }> };
      if (error.status === 429) {
        setSubmitError(error.detail || 'Rate limit exceeded. Please try again later.');
      } else if (error.status === 422 && error.errors) {
        const fieldErrors: Record<string, string> = {};
        for (const e of error.errors) {
          fieldErrors[e.field] = e.message;
        }
        setErrors(fieldErrors);
      } else {
        setSubmitError(error.detail || 'An error occurred while submitting your complaint.');
      }
    } finally {
      setLoading(false);
    }
  };

  return (
    <div>
      <h1 style={{ fontSize: 'var(--font-size-2xl)', fontWeight: 700, marginBottom: 'var(--space-lg)' }}>
        📝 Submit a Complaint
      </h1>

      <div className="card">
        <form onSubmit={handleSubmit} id="complaint-form">
          <div className="form-group">
            <label className="form-label" htmlFor="complaint-text">
              Complaint Details *
            </label>
            <textarea
              id="complaint-text"
              className={`form-textarea ${errors.text ? 'error' : ''}`}
              value={form.text}
              onChange={(e) => setForm({ ...form, text: e.target.value })}
              placeholder="Describe your complaint in detail... (e.g., Burst water main flooding Street 12 since fajr)"
              maxLength={2000}
              disabled={loading}
            />
            <div className="char-count">{form.text.length} / 2000</div>
            {errors.text && <div className="form-error">{errors.text}</div>}
          </div>

          <div className="form-group">
            <label className="form-label" htmlFor="complaint-location">
              Location *
            </label>
            <input
              id="complaint-location"
              type="text"
              className={`form-input ${errors.location ? 'error' : ''}`}
              value={form.location}
              onChange={(e) => setForm({ ...form, location: e.target.value })}
              placeholder="Street address or area (e.g., Street 12, Gulberg III, Lahore)"
              maxLength={200}
              disabled={loading}
            />
            {errors.location && <div className="form-error">{errors.location}</div>}
          </div>

          <div className="form-group">
            <label className="form-label" htmlFor="complaint-contact">
              Contact (Optional)
            </label>
            <input
              id="complaint-contact"
              type="text"
              className="form-input"
              value={form.reporter_contact}
              onChange={(e) => setForm({ ...form, reporter_contact: e.target.value })}
              placeholder="Phone number or email"
              maxLength={200}
              disabled={loading}
            />
          </div>

          {submitError && (
            <div className="alert alert-error">⚠️ {submitError}</div>
          )}

          <button
            type="submit"
            className="btn btn-primary"
            disabled={loading}
            id="submit-complaint-btn"
          >
            {loading ? (
              <>
                <div className="spinner" />
                Triaging with AI...
              </>
            ) : (
              '🚀 Submit Complaint'
            )}
          </button>
        </form>
      </div>

      {/* Result card — shows after successful submission */}
      {result && (
        <div className="result-card">
          <div className="result-header">
            <span style={{ fontSize: '1.5em' }}>✅</span>
            <span style={{ fontWeight: 600, fontSize: 'var(--font-size-lg)' }}>
              Complaint Submitted Successfully
            </span>
          </div>

          <div className="result-details">
            <div className="result-field">
              <span className="result-field-label">Category</span>
              <span className={`badge badge-${result.category}`}>{result.category}</span>
            </div>
            <div className="result-field">
              <span className="result-field-label">Priority</span>
              <span className={`badge badge-${result.priority}`}>{result.priority}</span>
            </div>
            <div className="result-field">
              <span className="result-field-label">AI Summary</span>
              <span className="result-field-value">{result.ai_summary || '—'}</span>
            </div>
            <div className="result-field">
              <span className="result-field-label">Triaged By</span>
              <span className="result-field-value" style={{ fontFamily: 'monospace', fontSize: 'var(--font-size-xs)' }}>
                {result.triaged_by}
              </span>
            </div>
            <div className="result-field">
              <span className="result-field-label">Triage Latency</span>
              <span className="result-field-value">{result.triage_latency_ms} ms</span>
            </div>
            <div className="result-field">
              <span className="result-field-label">Complaint ID</span>
              <span className="result-field-value" style={{ fontFamily: 'monospace', fontSize: 'var(--font-size-xs)' }}>
                {result.id}
              </span>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
