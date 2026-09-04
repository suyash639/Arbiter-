import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { App } from "../App";
import { StatusBadge } from "../components/StatusBadge";
import { AskArbiterPage } from "../pages/AskArbiterPage";
import { ClientsPage } from "../pages/ClientsPage";

// Mock API client
vi.mock("../api/client", () => ({
  arbiterApi: {
    getHealth: vi.fn().mockResolvedValue({ status: "ok", service: "arbiter" }),
    getReadiness: vi.fn().mockResolvedValue({
      status: "ready",
      clients_loaded: 25,
      instruments_loaded: 14,
      llm_provider: "gemini",
      llm_model: "gemini-3.6-flash",
    }),
    getClients: vi.fn().mockResolvedValue([
      {
        client_id: "cli_1014",
        name: "Test Client",
        risk_profile: "Moderate Growth",
        kyc_status: "verified",
        accounts_count: 3,
        total_suitability_reviews: 2,
        target_risk: "Moderate Growth",
      },
    ]),
    getAgents: vi.fn().mockResolvedValue([
      { id: "router", name: "Router", role: "Coordinator", tool_count: 0, description: "Test", color: "indigo" },
      { id: "book_qa", name: "Book QA", role: "Accounting", tool_count: 16, description: "Test", color: "emerald" },
    ]),
    getTools: vi.fn().mockResolvedValue([
      {
        name: "get_cash_balance",
        owning_agents: ["book_qa"],
        is_client_scoped: true,
        description: "Returns balance",
        expected_shape: "dict",
        argument_schema: "CashBalanceArgs",
        verification_status: "active",
      },
    ]),
    getSecuritySummary: vi.fn().mockResolvedValue({
      status: "active",
      controls: [{ name: "Prompt Injection Defense", status: "active", description: "Test" }],
      trust_boundaries: { untrusted: ["User"], trusted: ["DataStore"] },
    }),
    getReliabilitySummary: vi.fn().mockResolvedValue({
      status: "active",
      max_attempts: 3,
      initial_backoff_seconds: 1.0,
      max_backoff_seconds: 8.0,
      jitter_enabled: true,
      llm_timeout_seconds: 15.0,
      circuit_breaker: { failure_threshold: 5, recovery_seconds: 30.0, state: "CLOSED" },
      non_retryable_categories: ["NON_RETRYABLE_CLIENT_ERROR (4xx)"],
    }),
    getObservabilitySummary: vi.fn().mockResolvedValue({
      total_requests: 10,
      successful_requests: 8,
      refused_requests: 1,
      abstained_requests: 1,
      error_requests: 0,
      p50_latency_ms: 12.5,
      p95_latency_ms: 45.0,
      recent_traces: [],
    }),
    submitQuery: vi.fn().mockResolvedValue({
      request_id: "req_test_abc",
      question_id: "q_test_abc",
      answer: "The cash balance is $125,450.00 USD.",
      answer_value: "125450.00",
      abstained: false,
      refused: false,
      citations: ["cli_1014", "acc_1014_01"],
      confidence: 1.0,
      flags: [],
      agents: ["router", "book_qa"],
    }),
  },
}));

describe("Arbiter Frontend Component & Shell Tests", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("renders global application shell and navigation items", async () => {
    render(<App />);
    await waitFor(() => {
      expect(screen.getAllByText("ARBITER").length).toBeGreaterThanOrEqual(1);
      expect(screen.getByText("Console Overview")).toBeInTheDocument();
      expect(screen.getAllByText("Ask Arbiter").length).toBeGreaterThanOrEqual(1);
      expect(screen.getAllByText("Client Book").length).toBeGreaterThanOrEqual(1);
    });
  });

  it("navigates between views when clicking sidebar tabs", async () => {
    render(<App />);
    const toolsTabs = screen.getAllByText("Tool Verification");
    fireEvent.click(toolsTabs[0]);
    expect(await screen.findByText(/Verified Tool Registry/i)).toBeInTheDocument();
  });

  it("renders StatusBadge with appropriate visual statuses", () => {
    const { rerender } = render(<StatusBadge abstained={false} refused={false} />);
    expect(screen.getByText("SUCCESS")).toBeInTheDocument();

    rerender(<StatusBadge abstained={false} refused={true} />);
    expect(screen.getByText("POLICY REFUSED")).toBeInTheDocument();

    rerender(<StatusBadge abstained={true} refused={false} />);
    expect(screen.getByText("ABSTAINED")).toBeInTheDocument();

    rerender(<StatusBadge abstained={true} refused={false} flags={["upstream_issue"]} />);
    expect(screen.getByText("UPSTREAM FALLBACK")).toBeInTheDocument();
  });

  it("submits query from AskArbiterPage and displays formatted results", async () => {
    render(<AskArbiterPage selectedClientId="cli_1014" />);
    const runBtn = screen.getByRole("button", { name: /run query/i });
    fireEvent.click(runBtn);

    expect(await screen.findByText("The cash balance is $125,450.00 USD.")).toBeInTheDocument();
    expect(screen.getByText("125450.00")).toBeInTheDocument();
    expect(screen.getByText("req_test_abc")).toBeInTheDocument();
  });

  it("selects client in ClientsPage and displays authorized metadata", async () => {
    const onSelect = vi.fn();
    const onNav = vi.fn();
    render(<ClientsPage onSelectClient={onSelect} onNavigate={onNav} />);

    expect(await screen.findByText("cli_1014")).toBeInTheDocument();
    expect(screen.getByText("Test Client")).toBeInTheDocument();
    expect(screen.getByText(/Cross-Client Isolation/i)).toBeInTheDocument();

    const queryBtn = screen.getByRole("button", { name: /query/i });
    fireEvent.click(queryBtn);
    expect(onSelect).toHaveBeenCalledWith("cli_1014");
    expect(onNav).toHaveBeenCalledWith("ask");
  });
});
