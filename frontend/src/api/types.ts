/**
 * API types — typed against the backend's OpenAPI schema.
 * These types mirror the backend Pydantic models.
 */

export type Category = 'water' | 'electricity' | 'sanitation' | 'roads' | 'streetlights' | 'other';
export type Priority = 'high' | 'normal' | 'low';
export type Status = 'open' | 'in_progress' | 'resolved' | 'rejected';

export interface Complaint {
  id: string;
  text: string;
  location: string;
  reporter_contact: string | null;
  category: Category;
  priority: Priority;
  status: Status;
  ai_summary: string | null;
  triaged_by: string;
  triage_latency_ms: number;
  created_at: string;
  updated_at: string;
}

export interface ComplaintCreate {
  text: string;
  location: string;
  reporter_contact?: string;
}

export interface PaginatedComplaints {
  items: Complaint[];
  total: number;
  page: number;
  page_size: number;
}

export interface StatsResponse {
  by_category: Record<string, number>;
  by_priority: Record<string, number>;
  by_status: Record<string, number>;
  total: number;
}

export interface ProviderInfo {
  active_provider: string;
  recent_outcomes: TriageOutcome[];
}

export interface TriageOutcome {
  complaint_id: string;
  provider: string;
  latency_ms: number;
  fallback: boolean;
  timestamp: string;
}

export interface ValidationError {
  field: string;
  message: string;
}

export interface APIError {
  detail: string;
  errors?: ValidationError[];
}
