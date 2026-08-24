import json

import openai
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

import db
from config import Config
from tools import TOOL_DEFINITIONS, TOOL_DISPATCH

SYSTEM_PROMPT = """You are a read-only agent for the Sequencer medical therapy orchestration \
system — a platform that manages CAR-T cell therapy orders through their full lifecycle.

Order lifecycle (in order):
  SLOT_REQUESTED → APHERESIS_SCHEDULED → IN_TRANSIT_INBOUND → ACCESSIONED →
  MANUFACTURING → QC_IN_PROGRESS → RELEASED → IN_TRANSIT_OUTBOUND →
  RECEIVED_AT_CENTER → INFUSED → MONITORING → CLOSED (success terminal)

Failure terminals: FAILED, CANCELLED

You have live database tools. Always call the appropriate tool before answering — never \
guess or estimate data from a database query.

You CAN help with:
- Current status of an order (by order ID or patient name)
- Full audit trail of status transitions for an order
- Finding all orders for a specific patient
- Listing orders by status
- Describing what pipeline stage a patient's therapy is at

You CANNOT help with:
- Modifying any record — you are strictly read-only
- Questions outside therapy order tracking (weather, general knowledge, code, etc.)

When asked something outside your domain, say so briefly and give one example of what \
you CAN answer. For example: "I'm a read-only therapy order agent. I can look up the \
current status of order X or find orders by patient name."

When a query returns no data, say clearly that no matching record was found — never invent \
or estimate data."""

app = FastAPI(title="Sequencer Agent", version="1.0.0")

_config: Config | None = None
_client: openai.OpenAI | None = None

_MAX_TOOL_ROUNDS = 10  # guard against runaway loops


@app.on_event("startup")
def _startup() -> None:
    global _config, _client
    _config = Config.from_env()
    db.init(_config.database_url)
    _client = (
        openai.OpenAI(api_key=_config.openai_api_key)
        if _config.openai_api_key
        else openai.OpenAI()  # falls back to OPENAI_API_KEY env var
    )


class Message(BaseModel):
    role: str
    content: str


class ChatRequest(BaseModel):
    messages: list[Message]


class ChatResponse(BaseModel):
    response: str
    tools_used: list[str]


@app.get("/")
def root() -> dict:
    return {
        "service": "Sequencer Agent",
        "version": "1.0.0",
        "endpoints": {
            "chat": "POST /chat",
            "health": "GET /health",
            "docs": "GET /docs",
        },
    }


@app.get("/health")
def health() -> dict:
    try:
        with db.get_cursor() as cur:
            cur.execute("SELECT 1")
        db_status = "ok"
    except Exception as exc:
        db_status = str(exc)
    overall = "ok" if db_status == "ok" else "degraded"
    return {"status": overall, "db": db_status}


@app.post("/chat", response_model=ChatResponse)
def chat(req: ChatRequest) -> ChatResponse:
    messages: list[dict] = [{"role": "system", "content": SYSTEM_PROMPT}]
    messages += [{"role": m.role, "content": m.content} for m in req.messages]

    tools_called: list[str] = []

    for _ in range(_MAX_TOOL_ROUNDS):
        response = _client.chat.completions.create(
            model=_config.openai_model,
            messages=messages,
            tools=TOOL_DEFINITIONS,
            tool_choice="auto",
        )
        choice = response.choices[0]

        if choice.finish_reason != "tool_calls":
            return ChatResponse(
                response=choice.message.content or "No response generated.",
                tools_used=list(dict.fromkeys(tools_called)),
            )

        # append the assistant turn with its tool_calls
        messages.append(choice.message)

        # execute every tool call in this turn
        for tool_call in choice.message.tool_calls:
            name = tool_call.function.name
            tools_called.append(name)

            fn = TOOL_DISPATCH.get(name)
            if fn is None:
                result = json.dumps({"error": f"Unknown tool '{name}'"})
            else:
                try:
                    kwargs = json.loads(tool_call.function.arguments)
                    result = fn(**kwargs)
                except Exception as exc:
                    result = json.dumps({"error": str(exc)})

            messages.append(
                {
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "content": result,
                }
            )

    raise HTTPException(
        status_code=500,
        detail=f"Agent did not reach a final answer within {_MAX_TOOL_ROUNDS} tool rounds",
    )
