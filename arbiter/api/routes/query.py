"""
arbiter/api/routes/query.py
---------------------------
Primary query endpoint delegating natural language questions to ArbiterOrchestrator.
"""

from __future__ import annotations

import logging
from fastapi import APIRouter, Depends, Request, Response
from starlette.concurrency import run_in_threadpool

from arbiter.api.dependencies import get_orchestrator, get_request_id
from arbiter.api.schemas import QueryRequest, QueryResponse
from arbiter.orchestrator import ArbiterOrchestrator

logger = logging.getLogger("arbiter.api.query")

router = APIRouter(tags=["Query"])


@router.post(
    "/v1/query",
    response_model=QueryResponse,
    summary="Submit Financial Query",
    description="Route a natural language question for an authorized client to Arbiter specialist agents.",
)
async def submit_query(
    body: QueryRequest,
    request: Request,
    response: Response,
    orchestrator: ArbiterOrchestrator = Depends(get_orchestrator),
    req_id: str = Depends(get_request_id),
) -> QueryResponse:
    """Validate request, establish trusted client context, and execute ArbiterOrchestrator."""
    effective_req_id = body.request_id or req_id
    response.headers["X-Request-ID"] = effective_req_id
    question_id = f"q_{effective_req_id}"

    payload = {
        "question_id": question_id,
        "client_id": body.client_id,
        "prompt": body.question,
        "request_id": effective_req_id,
    }

    # Execute synchronous orchestrator pipeline within worker threadpool
    result = await run_in_threadpool(orchestrator.answer, payload)

    return QueryResponse(
        request_id=effective_req_id,
        question_id=result.get("question_id", question_id),
        answer=result.get("answer", ""),
        answer_value=result.get("answer_value"),
        abstained=result.get("abstained", False),
        refused=result.get("refused", False),
        reason=result.get("reason"),
        citations=result.get("citations", []),
        confidence=result.get("confidence", 1.0),
        flags=result.get("flags", []),
        agents=result.get("agents", []),
    )
