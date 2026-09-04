import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { ToolsPage } from "../pages/ToolsPage";
import { AgentsPage } from "../pages/AgentsPage";
import { SecurityPage } from "../pages/SecurityPage";
import { ReliabilityPage } from "../pages/ReliabilityPage";
import { ObservabilityPage } from "../pages/ObservabilityPage";
import { StatusIndicator } from "../components/StatusIndicator";
import { EmptyState } from "../components/EmptyState";
import { Database } from "lucide-react";

vi.mock("../api/client", () => ({
  arbiterApi: {
    getTools: vi.fn().mockResolvedValue([
      {
        name: "get_cash_balance",
        owning_agents: ["book_qa"],
        is_client_scoped: true,
        description: "Returns client total available cash across bank accounts",
        expected_shape: "dict",
        argument_schema: "CashBalanceArgs(client_id: str)",
        verification_status: "active",
      },
      {
        name: "get_stock_price",
        owning_agents: ["market_desk"],
        is_client_scoped: false,
        description: "Returns latest close price for covered equity ticker",
        expected_shape: "float",
        argument_schema: "StockPriceArgs(ticker: str)",
        verification_status: "active",
      },
    ]),
    getAgents: vi.fn().mockResolvedValue([]),
    getSecuritySummary: vi.fn().mockResolvedValue({ status: "active" }),
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
      total_requests: 15,
      successful_requests: 12,
      refused_requests: 2,
      abstained_requests: 1,
      error_requests: 0,
      p50_latency_ms: 24.5,
      p95_latency_ms: 68.0,
      recent_traces: [
        {
          request_id: "req_test_001",
          question_id: "q_test_001",
          client_id: "cli_1014",
          provider: "gemini",
          model: "gemini-3.6-flash",
          agent_path: ["router", "book_qa"],
          total_latency_ms: 32.1,
          tool_call_count: 1,
          abstained: false,
          refused: false,
          success: true,
        },
      ],
    }),
  },
}));

describe("Arbiter Operations Pages & Components Tests", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("renders ToolsPage with tool list, domain filtering, and expandable details", async () => {
    render(<ToolsPage />);
    expect(await screen.findByText("VERIFIED TOOL REGISTRY")).toBeInTheDocument();
    expect(await screen.findByText("get_cash_balance")).toBeInTheDocument();
    expect(screen.getByText("get_stock_price")).toBeInTheDocument();

    // Click on Book QA filter
    const bookQaFilter = screen.getByRole("button", { name: /book qa/i });
    fireEvent.click(bookQaFilter);
    expect(screen.getByText("get_cash_balance")).toBeInTheDocument();

    // Expand tool details
    fireEvent.click(screen.getByText("get_cash_balance"));
    expect(screen.getByText(/CashBalanceArgs/i)).toBeInTheDocument();
  });

  it("renders AgentsPage with 6-agent hierarchy and coordinator hub", async () => {
    render(<AgentsPage />);
    expect(await screen.findByText("SPECIALIST AGENT NETWORK")).toBeInTheDocument();
    expect(screen.getByText("Router Coordinator")).toBeInTheDocument();
    expect(screen.getByText("Book QA Specialist")).toBeInTheDocument();
    expect(screen.getByText("Compliance Specialist")).toBeInTheDocument();
    expect(screen.getByText("0 Tools")).toBeInTheDocument(); // Compliance has 0 tools
  });

  it("renders SecurityPage with trust boundaries and 6 security controls", async () => {
    render(<SecurityPage />);
    expect(await screen.findByText("SECURITY ARCHITECTURE & TRUST BOUNDARIES")).toBeInTheDocument();
    expect(screen.getByText("UNTRUSTED INPUTS")).toBeInTheDocument();
    expect(screen.getByText("SECURITY GATEWAY")).toBeInTheDocument();
    expect(screen.getByText("TRUSTED CORE")).toBeInTheDocument();
    expect(screen.getByText("Direct Prompt Injection Defense")).toBeInTheDocument();
    expect(screen.getByText("Deterministic Client Isolation")).toBeInTheDocument();
  });

  it("renders ReliabilityPage with retry configuration and circuit breaker", async () => {
    render(<ReliabilityPage />);
    expect(await screen.findByText("RELIABILITY ENGINE & FAULT TOLERANCE")).toBeInTheDocument();
    expect(await screen.findByText(/Retry & Backoff Policy/i)).toBeInTheDocument();
    expect(screen.getByText(/Circuit Breaker Isolation/i)).toBeInTheDocument();
  });

  it("renders ObservabilityPage with telemetry metrics and request traces table", async () => {
    render(<ObservabilityPage />);
    expect(await screen.findByText("OBSERVABILITY & REQUEST TELEMETRY")).toBeInTheDocument();
    expect(await screen.findByText("req_test_001")).toBeInTheDocument();
    expect(screen.getByText("cli_1014")).toBeInTheDocument();
  });

  it("renders StatusIndicator with multiple semantic states", () => {
    const { rerender } = render(<StatusIndicator status="ONLINE" />);
    expect(screen.getByText("ONLINE")).toBeInTheDocument();

    rerender(<StatusIndicator status="READY" />);
    expect(screen.getByText("READY")).toBeInTheDocument();

    rerender(<StatusIndicator status="REFUSED" />);
    expect(screen.getByText("REFUSED")).toBeInTheDocument();

    rerender(<StatusIndicator status="ABSTAINED" />);
    expect(screen.getByText("ABSTAINED")).toBeInTheDocument();
  });

  it("renders EmptyState with custom title, description, and optional action button", () => {
    const onAction = vi.fn();
    render(
      <EmptyState
        icon={Database}
        title="No Records Found"
        description="No database records match the query filter."
        actionLabel="Reset Filter"
        onAction={onAction}
      />
    );
    expect(screen.getByText("No Records Found")).toBeInTheDocument();
    expect(screen.getByText("No database records match the query filter.")).toBeInTheDocument();
    const actionBtn = screen.getByRole("button", { name: /reset filter/i });
    fireEvent.click(actionBtn);
    expect(onAction).toHaveBeenCalledTimes(1);
  });
});
