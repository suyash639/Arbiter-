/**
 * Centralized API client for Arbiter backend communication.
 */

import type {
  AgentSummary,
  ClientSummary,
  HealthResponse,
  ObservabilitySummary,
  QueryRequest,
  QueryResponse,
  ReadinessResponse,
  ReliabilitySummary,
  SecuritySummary,
  ToolSummary,
} from "./types";

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || "";

async function handleResponse<T>(res: Response): Promise<T> {
  if (!res.ok) {
    let errorMsg = `HTTP Error ${res.status}`;
    try {
      const data = await res.json();
      errorMsg = data.message || data.error || errorMsg;
    } catch {
      // ignore
    }
    throw new Error(errorMsg);
  }
  return res.json() as Promise<T>;
}

export const arbiterApi = {
  async getHealth(): Promise<HealthResponse> {
    const res = await fetch(`${API_BASE_URL}/health`);
    return handleResponse<HealthResponse>(res);
  },

  async getReadiness(): Promise<ReadinessResponse> {
    const res = await fetch(`${API_BASE_URL}/ready`);
    return handleResponse<ReadinessResponse>(res);
  },

  async submitQuery(payload: QueryRequest): Promise<QueryResponse> {
    const headers: Record<string, string> = {
      "Content-Type": "application/json",
    };
    if (payload.request_id) {
      headers["X-Request-ID"] = payload.request_id;
    }

    const res = await fetch(`${API_BASE_URL}/v1/query`, {
      method: "POST",
      headers,
      body: JSON.stringify(payload),
    });
    return handleResponse<QueryResponse>(res);
  },

  async getClients(): Promise<ClientSummary[]> {
    const res = await fetch(`${API_BASE_URL}/v1/clients`);
    return handleResponse<ClientSummary[]>(res);
  },

  async getAgents(): Promise<AgentSummary[]> {
    const res = await fetch(`${API_BASE_URL}/v1/agents`);
    return handleResponse<AgentSummary[]>(res);
  },

  async getTools(): Promise<ToolSummary[]> {
    const res = await fetch(`${API_BASE_URL}/v1/tools`);
    return handleResponse<ToolSummary[]>(res);
  },

  async getSecuritySummary(): Promise<SecuritySummary> {
    const res = await fetch(`${API_BASE_URL}/v1/security/summary`);
    return handleResponse<SecuritySummary>(res);
  },

  async getReliabilitySummary(): Promise<ReliabilitySummary> {
    const res = await fetch(`${API_BASE_URL}/v1/reliability/summary`);
    return handleResponse<ReliabilitySummary>(res);
  },

  async getObservabilitySummary(): Promise<ObservabilitySummary> {
    const res = await fetch(`${API_BASE_URL}/v1/observability/summary`);
    return handleResponse<ObservabilitySummary>(res);
  },
};
