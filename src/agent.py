"""
Fraud detection agent using Google Gemini.

Public surface (matched by test_agent.py):
  dispatch(tool_name: str, tool_input: dict) -> dict
  run_agent(transaction: dict) -> tuple[str, dict | None]

Environment:
  GEMINI_API_KEY (or GOOGLE_API_KEY) must be set

"""

import json
import os
from dotenv import load_dotenv

from google import genai
from google.genai import types

from explain import explain_transaction
from rag import retrieve

load_dotenv()

# ---------------------------------------------------------------------------
# Model + client
# ---------------------------------------------------------------------------
MODEL = "gemini-2.0-flash"
client = genai.Client()  # reads GEMINI_API_KEY / GOOGLE_API_KEY from env


# ---------------------------------------------------------------------------
# Tool declarations (Gemini function-calling schema)
# ---------------------------------------------------------------------------
PREDICT_DECL = types.FunctionDeclaration(
    name="predict_and_explain",
    description=(
        "Score a transaction for fraud using the XGBoost model and return the "
        "fraud probability plus the top SHAP feature contributions. "
        "Always call this first before any other tool."
    ),
    parameters={
        "type": "object",
        "properties": {
            "transaction": {
                "type": "object",
                "description": "The transaction fields to score.",
                "properties": {
                    "step": {"type": "integer"},
                    "type": {
                            "type": "string",
                            "enum": ["CASH_IN", "CASH_OUT", "DEBIT", "PAYMENT", "TRANSFER"],
                        },
                    "amount": {"type": "number"},
                    "nameOrig": {"type": "string"},
                    "oldbalanceOrg": {"type": "number"},
                    "newbalanceOrig": {"type": "number"},
                    "nameDest": {"type": "string"},
                    "oldbalanceDest": {"type": "number"},
                    "newbalanceDest": {"type": "number"},
                },
            },
        },
        "required": ["transaction"],
    },
)

RETRIEVE_DECL = types.FunctionDeclaration(
    name="retrieve_context",
    description=(
        "Retrieve relevant fraud typology, regulatory context, or response "
        "guidance from the knowledge base. Use targeted queries based on what "
        "the SHAP features suggest. Call once or twice with different queries "
        "to cover the main risk signals."
    ),
    parameters={
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": (
                    "A short, specific query describing the fraud pattern or "
                    "context you are looking for."
                ),
            },
        },
        "required": ["query"],
    },
)

FINALIZE_DECL = types.FunctionDeclaration(
    name="finalize_report",
    description=(
        "Submit the final structured investigation report. Call this only "
        "after predict_and_explain and at least one retrieve_context call."
    ),
    parameters={
        "type": "object",
        "properties": {
            "verdict": {
                "type": "string",
                "enum": ["FRAUD", "LEGIT", "UNCERTAIN"],
            },
            "fraud_probability": {"type": "number"},
            "confidence": {
                "type": "string",
                "enum": ["HIGH", "MEDIUM", "LOW"],
            },
            "top_risk_signals": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "feature": {"type": "string"},
                        "observation": {"type": "string"},
                        "impact": {
                            "type": "string",
                            "enum": ["raises risk", "lowers risk"],
                        },
                    },
                    "required": ["feature", "observation", "impact"],
                },
            },
            "matched_typology": {"type": "string"},
            "recommended_action": {
                "type": "string",
                "enum": [
                    "AUTO_DECLINE",
                    "STEP_UP_AUTH",
                    "MANUAL_REVIEW",
                    "ALLOW",
                ],
            },
            "rationale": {"type": "string"},
        },
        "required": [
            "verdict",
            "fraud_probability",
            "confidence",
            "top_risk_signals",
            "matched_typology",
            "recommended_action",
            "rationale",
        ],
    },
)

TOOLS = [
    types.Tool(
        function_declarations=[PREDICT_DECL, RETRIEVE_DECL, FINALIZE_DECL],
    ),
]


# ---------------------------------------------------------------------------
# System instruction
# ---------------------------------------------------------------------------
SYSTEM = """You are a fraud analyst assistant for a mobile-first financial institution.

When given a transaction to investigate, you must follow these steps in order:

1. Call predict_and_explain to get the model's fraud score and top SHAP features.
2. Based on what the SHAP features suggest, call retrieve_context one or two
   times with targeted queries to find matching fraud typologies and response
   guidance.
3. Call finalize_report to submit your structured verdict.

Rules:
- Never skip predict_and_explain — the model score is required.
- Never call finalize_report before at least one retrieve_context call.
- Keep your rationale concise and actionable — write for a case worker, not a
  data scientist.
- Cite which specific feature drove each risk signal conclusion.
- Do not invent information not present in the model output or retrieved docs.
- Maximum 5 tool calls total. If you have enough information, finalize early."""


# ---------------------------------------------------------------------------
# dispatch() — routes a tool call to the right Python function
# ---------------------------------------------------------------------------
def dispatch(tool_name: str, tool_input: dict) -> dict:
    """Route a single tool call. Returns a dict (or list) for the caller
    to wrap into a Gemini function_response Part."""
    if tool_name == "predict_and_explain":
        return explain_transaction(tool_input["transaction"])

    if tool_name == "retrieve_context":
        return retrieve(tool_input["query"])

    if tool_name == "finalize_report":
        dispatch.last_report = tool_input
        return {"status": "report_submitted", "report": tool_input}

    return {"error": f"Unknown tool: {tool_name}"}


# Attribute storage so run_agent can recover the structured report after the
# model submits it. Reset at the start of every run_agent() call.
dispatch.last_report = None


# ---------------------------------------------------------------------------
# run_agent() — the main loop
# ---------------------------------------------------------------------------
def run_agent(transaction: dict) -> tuple[str, dict | None]:
    """Investigate a transaction and return (final_text, structured_report).

    The loop is capped at 2 iterations. If the model never returns a
    text-only response, we exit with a fallback warning — never an exception.
    """
    dispatch.last_report = None

    contents: list[types.Content] = [
        types.Content(
            role="user",
            parts=[
                types.Part(
                    text=(
                        "Investigate this transaction:\n\n"
                        + json.dumps(transaction, indent=2)
                    ),
                ),
            ],
        ),
    ]

    config = types.GenerateContentConfig(
        system_instruction=SYSTEM,
        tools=TOOLS,
        temperature=0.1,  # low, but not zero — tool calling benefits from a little variance
        max_output_tokens=2000,
    )

    max_iterations = 2
    for _ in range(max_iterations):
        response = client.models.generate_content(
            model=MODEL,
            contents=contents,
            config=config,
        )

        candidate = response.candidates[0]
        parts = candidate.content.parts or []
        function_calls = [p.function_call for p in parts if p.function_call is not None]

        # -- terminal state: model emitted only text, no function calls --
        if not function_calls:
            text = "".join(p.text or "" for p in parts if p.text)
            return text, dispatch.last_report

        # -- append the model's turn verbatim, so Gemini can see its own call --
        contents.append(candidate.content)

        # -- execute each function call and collect responses --
        tool_response_parts = []
        for fc in function_calls:
            args = dict(fc.args) if fc.args else {}
            result = dispatch(fc.name, args)

            # Part.from_function_response expects a dict; wrap bare lists.
            response_payload = result if isinstance(result, dict) else {"results": result}

            tool_response_parts.append(
                types.Part.from_function_response(
                    name=fc.name,
                    response=response_payload,
                ),
            )

        # Gemini convention: function responses are sent in a user-role turn.
        contents.append(types.Content(role="user", parts=tool_response_parts))

    # -- safety rail: loop exited without the model finalizing --
    fallback = (
        "⚠️ Agent reached maximum iterations without producing a final report. "
        "This may indicate an unexpected loop. Please review the transaction manually."
    )
    return fallback, dispatch.last_report


# ---------------------------------------------------------------------------
# CLI convenience — `uv run python src/agent.py` runs a sample transaction.
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    example_tx = {
        "step": 1,
        "amount": 181.0,
        "oldbalanceOrg": 181.0,
        "newbalanceOrig": 0.0,
        "oldbalanceDest": 0.0,
        "newbalanceDest": 0.0,
        "dest_is_merchant": 0,
        "type_CASH_IN": 0,
        "type_CASH_OUT": 0,
        "type_DEBIT": 0,
        "type_PAYMENT": 0,
        "type_TRANSFER": 1,
    }
    #text, report = run_agent(example_tx)
    print("=" * 70)
    print("FINAL TEXT")
    print("=" * 70)
    #print(text)
    print()
    print("=" * 70)
    print("STRUCTURED REPORT")
    print("=" * 70)
    #print(json.dumps(report, indent=2) if report else "(none)")