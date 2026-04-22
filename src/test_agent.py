"""
Pytest test suite for agent.py.

Run: uv run pytest src/test_agent.py -v

All external dependencies are mocked:
  - agent.client.models.generate_content  (Gemini API)
  - agent.explain_transaction             (XGBoost + SHAP)
  - agent.retrieve                        (FAISS knowledge base)

Assumed agent.py contract:
  - Uses `google-genai` (imported as `from google import genai`).
  - Client built with `client = genai.Client()` at module scope.
  - `dispatch(tool_name: str, tool_input: dict) -> dict`
      Returns a plain dict (Gemini's `Part.from_function_response` wants a dict,
      not a JSON string like Anthropic's tool_result).
      For finalize_report, returns {"status": "report_submitted", "report": ...}
      and stashes the report on dispatch.last_report.
      For unknown tools, returns {"error": "..."} — does not raise.
  - `run_agent(transaction: dict) -> tuple[str, dict | None]`
      Loops up to 5 iterations. Detects tool calls by checking whether any
      part in `response.candidates[0].content.parts` has `.function_call` set.
      Exits when no part has a function_call (all text).
"""

import os
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

# Make `src/` importable no matter where pytest is invoked from.
sys.path.insert(0, str(Path(__file__).parent))

# google-genai reads GEMINI_API_KEY (and falls back to GOOGLE_API_KEY). Set a
# dummy value so `genai.Client()` at the top of agent.py does not fail on import.
os.environ.setdefault("GEMINI_API_KEY", "test-key-for-unit-tests")
os.environ.setdefault("GOOGLE_API_KEY", "test-key-for-unit-tests")

import agent  # noqa: E402  (import must follow sys.path + env setup)


# ---------------------------------------------------------------------------
# Fake Gemini response builders
# ---------------------------------------------------------------------------
#
# Minimum attributes the agent loop reads:
#
#   response.candidates[0].content.parts          -> list of Part
#   part.text                                     -> str or None
#   part.function_call                            -> FunctionCall or None
#   part.function_call.name, part.function_call.args   (args is a dict-like)
#
# We use tiny classes instead of MagicMock so any attribute the agent happens
# to read but we forgot to populate fails loudly.

class FakeFunctionCall:
    """Stand-in for google.genai.types.FunctionCall."""

    def __init__(self, name: str, args: dict):
        self.name = name
        self.args = args  # Gemini deserializes the protobuf Struct to a dict.


class FakePart:
    """Stand-in for google.genai.types.Part.

    Exactly one of `text` or `function_call` is set per part in the responses
    we build — matching what Gemini returns in practice.
    """

    def __init__(self, text: str | None = None,
                 function_call: FakeFunctionCall | None = None):
        self.text = text
        self.function_call = function_call


class FakeContent:
    """Stand-in for google.genai.types.Content."""

    def __init__(self, parts: list, role: str = "model"):
        self.parts = parts
        self.role = role


class FakeCandidate:
    """Stand-in for google.genai.types.Candidate."""

    def __init__(self, content: FakeContent, finish_reason: str = "STOP"):
        self.content = content
        self.finish_reason = finish_reason


class FakeResponse:
    """Stand-in for google.genai.types.GenerateContentResponse."""

    def __init__(self, candidates: list):
        self.candidates = candidates


def tool_call_response(name: str, args: dict) -> FakeResponse:
    """Build a response that invokes a single function call."""
    part = FakePart(function_call=FakeFunctionCall(name, args))
    return FakeResponse(
        candidates=[FakeCandidate(FakeContent(parts=[part], role="model"))],
    )


def end_turn_response(text: str = "Investigation complete.") -> FakeResponse:
    """Build a response that emits final text only (no function_call)."""
    part = FakePart(text=text)
    return FakeResponse(
        candidates=[FakeCandidate(FakeContent(parts=[part], role="model"))],
    )


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def sample_transaction():
    return {
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


@pytest.fixture
def sample_explanation():
    return {
        "fraud_probability": 0.87,
        "prediction": "FRAUD",
        "top_features": [
            {"feature": "amount", "value": 181.0,
             "shap_contribution": 0.41, "direction": "raises risk"},
            {"feature": "newbalanceOrig", "value": 0.0,
             "shap_contribution": 0.33, "direction": "raises risk"},
        ],
    }


@pytest.fixture
def sample_retrieval():
    return [
        {"title": "money_mule_patterns",
         "content": "Fraudsters drain origin accounts to zero...",
         "score": 0.91},
    ]


@pytest.fixture
def fraud_report():
    return {
        "verdict": "FRAUD",
        "fraud_probability": 0.87,
        "confidence": "HIGH",
        "top_risk_signals": [
            {"feature": "newbalanceOrig",
             "observation": "Origin account drained to zero",
             "impact": "raises risk"},
        ],
        "matched_typology": "money_mule_patterns",
        "recommended_action": "AUTO_DECLINE",
        "rationale": "High model score combined with full balance drain.",
    }


@pytest.fixture
def legit_report():
    return {
        "verdict": "LEGIT",
        "fraud_probability": 0.02,
        "confidence": "HIGH",
        "top_risk_signals": [],
        "matched_typology": "none",
        "recommended_action": "ALLOW",
        "rationale": "No risk signals. Normal merchant payment profile.",
    }


@pytest.fixture(autouse=True)
def _reset_dispatch_state():
    """Guarantee every test starts with dispatch.last_report = None."""
    agent.dispatch.last_report = None
    yield
    agent.dispatch.last_report = None


# ---------------------------------------------------------------------------
# 1. dispatch() unit tests
# ---------------------------------------------------------------------------

class TestDispatch:
    """Unit tests for the dispatch() tool router."""

    def test_predict_and_explain_routing(self, sample_transaction, sample_explanation):
        """predict_and_explain must call explain_transaction with the tx dict."""
        with patch("agent.explain_transaction",
                   return_value=sample_explanation) as mock_explain:
            result = agent.dispatch(
                "predict_and_explain",
                {"transaction": sample_transaction},
            )

        mock_explain.assert_called_once_with(sample_transaction)
        # Gemini version: dispatch returns a dict, not a JSON string.
        assert result == sample_explanation

    def test_retrieve_context_routing(self, sample_retrieval):
        """retrieve_context must call retrieve() with the provided query string."""
        with patch("agent.retrieve", return_value=sample_retrieval) as mock_retrieve:
            result = agent.dispatch(
                "retrieve_context",
                {"query": "money mule TRANSFER drain"},
            )

        mock_retrieve.assert_called_once_with("money mule TRANSFER drain")
        assert result == sample_retrieval

    def test_finalize_report_stores_and_returns(self, fraud_report):
        """finalize_report must store the report and return a success envelope."""
        result = agent.dispatch("finalize_report", fraud_report)

        # Side effect: the report is stashed on the dispatch function itself.
        assert agent.dispatch.last_report == fraud_report

        # Return value: a dict envelope that echoes the submission.
        assert result["status"] == "report_submitted"
        assert result["report"] == fraud_report

    def test_unknown_tool_returns_error_dict(self):
        """An unknown tool name must return an error dict instead of raising."""
        result = agent.dispatch("not_a_real_tool", {"foo": "bar"})
        assert "error" in result
        assert "not_a_real_tool" in result["error"]


# ---------------------------------------------------------------------------
# 2. run_agent() tests with the Gemini client mocked
# ---------------------------------------------------------------------------

class TestRunAgent:
    """Full-loop tests of run_agent() with every external boundary mocked."""

    def test_happy_path_fraud(
        self,
        sample_transaction,
        sample_explanation,
        sample_retrieval,
        fraud_report,
    ):
        """Fraud path: predict → retrieve → finalize → text; verdict FRAUD."""
        responses = [
            tool_call_response("predict_and_explain",
                               {"transaction": sample_transaction}),
            tool_call_response("retrieve_context",
                               {"query": "balance drain to zero"}),
            tool_call_response("finalize_report", fraud_report),
            end_turn_response("Report submitted."),
        ]
        with patch("agent.client.models.generate_content",
                   side_effect=responses) as mock_generate, \
             patch("agent.explain_transaction", return_value=sample_explanation), \
             patch("agent.retrieve", return_value=sample_retrieval):
            text, report = agent.run_agent(sample_transaction)

        assert isinstance(text, str) and text
        assert report is not None
        assert report["verdict"] == "FRAUD"
        assert report["recommended_action"] == "AUTO_DECLINE"
        assert mock_generate.call_count == 4

    def test_happy_path_legit(
        self,
        sample_transaction,
        sample_explanation,
        sample_retrieval,
        legit_report,
    ):
        """Legit path: same flow, verdict LEGIT and recommended_action ALLOW."""
        responses = [
            tool_call_response("predict_and_explain",
                               {"transaction": sample_transaction}),
            tool_call_response("retrieve_context",
                               {"query": "normal merchant payment"}),
            tool_call_response("finalize_report", legit_report),
            end_turn_response("All clear."),
        ]
        with patch("agent.client.models.generate_content", side_effect=responses), \
             patch("agent.explain_transaction", return_value=sample_explanation), \
             patch("agent.retrieve", return_value=sample_retrieval):
            text, report = agent.run_agent(sample_transaction)

        assert report is not None
        assert report["verdict"] == "LEGIT"
        assert report["recommended_action"] == "ALLOW"

    def test_max_iterations_safety_rail(
        self,
        sample_transaction,
        sample_explanation,
    ):
        """If the model never stops calling tools, the loop must exit with a fallback."""
        stuck = tool_call_response(
            "predict_and_explain",
            {"transaction": sample_transaction},
        )
        with patch("agent.client.models.generate_content",
                   side_effect=[stuck] * 10) as mock_generate, \
             patch("agent.explain_transaction", return_value=sample_explanation), \
             patch("agent.retrieve", return_value=[]):
            text, report = agent.run_agent(sample_transaction)

        assert "maximum iterations" in text.lower()
        assert report is None
        # Exactly max_iterations (5) API calls, then the loop exits.
        assert mock_generate.call_count == 5

    def test_last_report_resets_between_runs(
        self,
        sample_transaction,
        sample_explanation,
        sample_retrieval,
        fraud_report,
    ):
        """dispatch.last_report from run 1 must not bleed into run 2."""
        run1 = [
            tool_call_response("predict_and_explain",
                               {"transaction": sample_transaction}),
            tool_call_response("retrieve_context", {"query": "x"}),
            tool_call_response("finalize_report", fraud_report),
            end_turn_response(),
        ]
        run2 = [
            tool_call_response("predict_and_explain",
                               {"transaction": sample_transaction}),
            end_turn_response("Not enough evidence to finalize."),
        ]

        with patch("agent.client.models.generate_content",
                   side_effect=run1 + run2), \
             patch("agent.explain_transaction", return_value=sample_explanation), \
             patch("agent.retrieve", return_value=sample_retrieval):
            _, report1 = agent.run_agent(sample_transaction)
            _, report2 = agent.run_agent(sample_transaction)

        assert report1 is not None and report1["verdict"] == "FRAUD"
        # The critical assertion: run 2 must not inherit run 1's stored report.
        assert report2 is None
        assert agent.dispatch.last_report is None

    def test_unknown_tool_does_not_crash(self, sample_transaction):
        """An unrecognized tool name from the model must not raise."""
        responses = [
            tool_call_response("made_up_tool", {"foo": "bar"}),
            end_turn_response("Could not use that tool, stopping."),
        ]
        with patch("agent.client.models.generate_content",
                   side_effect=responses) as mock_generate, \
             patch("agent.explain_transaction") as mock_explain, \
             patch("agent.retrieve") as mock_retrieve:
            text, report = agent.run_agent(sample_transaction)

        assert isinstance(text, str) and text
        assert report is None
        # The real tool functions must not have been called.
        mock_explain.assert_not_called()
        mock_retrieve.assert_not_called()
        assert mock_generate.call_count == 2


# ---------------------------------------------------------------------------
# 3. Placeholder live integration test (skipped by default)
# ---------------------------------------------------------------------------

@pytest.mark.skip(reason="requires live Gemini API key and model files")
def test_integration_real_agent():
    """Smoke-test run_agent() end-to-end against the real Gemini API. Unskip manually."""
    transaction = {
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
    result = agent.run_agent(transaction)

    assert isinstance(result, tuple) and len(result) == 2
    text, report = result
    assert isinstance(text, str) and text
    assert report is None or (isinstance(report, dict) and "verdict" in report)