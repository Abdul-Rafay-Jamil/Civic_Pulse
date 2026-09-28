/**
 * API client — typed against the backend contract.
 * All API calls go through this module.
 */

import { config } from '../config';
import type {
  Complaint,
  ComplaintCreate,
  PaginatedComplaints,
  StatsResponse,
  ProviderInfo,
  Category,
  Priority,
  Status,
  APIError,
} from './types';

const BASE = config.API_BASE_URL;

class APIClient {
  private async request<T>(
    path: string,
    options: RequestInit = {},
  ): Promise<{ data: T; headers: Headers }> {
    const url = `${BASE}${path}`;
    const response = await fetch(url, {
      ...options,
      headers: {
        'Content-Type': 'application/json',
        ...options.headers,
      },
    });

    if (!response.ok) {
      const errorBody = await response.json().catch(() => ({
        detail: `HTTP ${response.status}: ${response.statusText}`,
      }));
      const error: APIError = errorBody;
      throw { status: response.status, ...error };
    }

    const data = await response.json();
    return { data: data as T, headers: response.headers };
  }

  /** POST /api/complaints — Submit a new complaint */
  async createComplaint(body: ComplaintCreate): Promise<Complaint> {
    const { data } = await this.request<Complaint>('/api/complaints', {
      method: 'POST',
      body: JSON.stringify(body),
    });
    return data;
  }

  /** GET /api/complaints/{id} */
  async getComplaint(id: string): Promise<Complaint> {
    const { data } = await this.request<Complaint>(`/api/complaints/${id}`);
    return data;
  }

  /** GET /api/complaints — Paginated, filterable list */
  async listComplaints(params: {
    page?: number;
    page_size?: number;
    category?: Category;
    priority?: Priority;
    status?: Status;
  } = {}): Promise<PaginatedComplaints> {
    const searchParams = new URLSearchParams();
    if (params.page) searchParams.set('page', String(params.page));
    if (params.page_size) searchParams.set('page_size', String(params.page_size));
    if (params.category) searchParams.set('category', params.category);
    if (params.priority) searchParams.set('priority', params.priority);
    if (params.status) searchParams.set('status', params.status);

    const query = searchParams.toString();
    const path = `/api/complaints${query ? `?${query}` : ''}`;
    const { data } = await this.request<PaginatedComplaints>(path);
    return data;
  }

  /** PATCH /api/complaints/{id}/status — Update complaint status */
  async updateStatus(id: string, status: Status): Promise<Complaint> {
    const { data } = await this.request<Complaint>(
      `/api/complaints/${id}/status`,
      {
        method: 'PATCH',
        body: JSON.stringify({ status }),
      },
    );
    return data;
  }

  /** GET /api/stats — Returns stats + X-Cache header */
  async getStats(): Promise<{ stats: StatsResponse; cacheHit: boolean }> {
    const { data, headers } = await this.request<StatsResponse>('/api/stats');
    const cacheHeader = headers.get('X-Cache');
    return { stats: data, cacheHit: cacheHeader === 'HIT' };
  }

  /** GET /api/meta/providers — Active provider info */
  async getProviderInfo(): Promise<ProviderInfo> {
    const { data } = await this.request<ProviderInfo>('/api/meta/providers');
    return data;
  }
}

export const api = new APIClient();
