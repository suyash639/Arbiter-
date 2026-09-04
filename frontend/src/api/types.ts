/**
 * TypeScript type definitions for Arbiter API models.
 */

export interface QueryRequest {
  client_id: string;
  question: string;
  request_id?: string;
}

export interface QueryResponse {
  request_id: string;
  question_id: string;
  answer: string;
  answer_value?: string | null;
  abstained: boolean;
  refused: boolean;
  reason?: string | null;
  citations: string[];
  confidence: number;
  flags: string[];
  agents: string[];
}

export interface HealthResponse {
  status: string;
  service: string;
}

export interface ReadinessResponse {
  status: string;
  clients_loaded: number;
  instruments_loaded: number;
  llm_provider: string;
  llm_model: string;
}

export interface ClientSummary {
  client_id: string;
  name: string;
  risk_profile: string;
  kyc_status: string;
  accounts_count: number;
  total_suitability_reviews: number;
  target_risk: string;
}

export interface AgentSummary {
  id: string;
  name: string;
  role: string;
  tool_count: number;
  description: string;
  color: string;
}

export interface ToolSummary {
  name: string;
  owning_agents: string[];
  is_client_scoped: boolean;
  description: string;
  expected_shape: string;
  argument_schema: string;
  verification_status: string;
}

export interface SecurityControl {
  name: string;
  status: string;
  description: string;
}

export interface SecuritySummary {
  status: string;
  controls: SecurityControl[];
  trust_boundaries: {
    untrusted: string[];
    trusted: string[];
  };
}

export interface ReliabilitySummary {
  status: string;
  max_attempts: number;
  initial_backoff_seconds: number;
  max_backoff_seconds: number;
  jitter_enabled: boolean;
  llm_timeout_seconds: number;
  circuit_breaker: {
    failure_threshold: number;
    recovery_seconds: number;
    state: string;
  };
  non_retryable_categories: string[];
}

export interface TraceSummary {
  request_id: string;
  question_id: string;
  client_id: string;
  provider: string;
  model: string;
  agent_path: string[];
  total_latency_ms?: number | null;
  router_latency_ms?: number | null;
  specialist_latency_ms?: number | null;
  tool_call_count: number;
  refused: boolean;
  abstained: boolean;
  success: boolean;
  error?: string | null;
}

export interface ObservabilitySummary {
  total_requests: number;
  successful_requests: number;
  refused_requests: number;
  abstained_requests: number;
  error_requests: number;
  p50_latency_ms: number;
  p95_latency_ms: number;
  recent_traces: TraceSummary[];
}
