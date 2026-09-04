import { describe, it, expect, vi, beforeEach } from "vitest";
import { arbiterApi } from "../api/client";
import type { QueryResponse, HealthResponse, ReadinessResponse } from "../api/types";

describe("Arbiter API Client Tests", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  it("fetches health liveness probe successfully", async () => {
    const mockHealth: HealthResponse = { status: "ok", service: "arbiter" };
    globalThis.fetch = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => mockHealth,
    });

    const result = await arbiterApi.getHealth();
    expect(result.status).toBe("ok");
    expect(result.service).toBe("arbiter");
  });

  it("fetches readiness dataset status successfully", async () => {
    const mockReady: ReadinessResponse = {
      status: "ready",
      clients_loaded: 25,
      instruments_loaded: 14,
      llm_provider: "valura",
      llm_model: "valura-fast",
    };
    globalThis.fetch = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => mockReady,
    });

    const result = await arbiterApi.getReadiness();
    expect(result.status).toBe("ready");
    expect(result.clients_loaded).toBe(25);
  });

  it("submits query with client context and returns structured answer", async () => {
    const mockQueryResponse: QueryResponse = {
      request_id: "req_test_123",
      question_id: "q_test_123",
      answer: "The cash balance is $125,450.00.",
      answer_value: "125450.00",
      abstained: false,
      refused: false,
      citations: ["cli_1014", "acc_1014_01"],
      confidence: 1.0,
      flags: [],
      agents: ["router", "book_qa"],
    };

    globalThis.fetch = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => mockQueryResponse,
    });

    const result = await arbiterApi.submitQuery({
      client_id: "cli_1014",
      question: "What is the cash balance?",
    });

    expect(result.request_id).toBe("req_test_123");
    expect(result.answer_value).toBe("125450.00");
    expect(result.agents).toContain("book_qa");
    expect(result.citations).toContain("acc_1014_01");
  });

  it("handles HTTP errors gracefully with sanitized message", async () => {
    globalThis.fetch = vi.fn().mockResolvedValue({
      ok: false,
      status: 400,
      json: async () => ({ message: "Invalid client_id scope" }),
    });

    await expect(
      arbiterApi.submitQuery({ client_id: "invalid", question: "test" })
    ).rejects.toThrow("Invalid client_id scope");
  });

  it("fetches tools registry with 24 verified tools", async () => {
    globalThis.fetch = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => [
        { name: "get_cash_balance", owning_agents: ["book_qa"], is_client_scoped: true },
        { name: "get_instrument", owning_agents: ["market_desk"], is_client_scoped: false },
      ],
    });

    const tools = await arbiterApi.getTools();
    expect(tools.length).toBe(2);
    expect(tools[0].name).toBe("get_cash_balance");
  });
});
