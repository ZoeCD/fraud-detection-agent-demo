"""
Fraud detection demo — Streamlit UI.

What this shows end-to-end:
  1. Paste a raw PaySim row (no manual preprocessing).
  2. XGBoost scores it + SHAP explains the top feature contributions.
  3. Gemini agent calls predict_and_explain, retrieves knowledge-base context,
     and submits a structured investigator report.

Run: uv run streamlit run src/app.py
"""

import json
import sys
from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st
from google.genai import errors as genai_errors

# Make sibling modules (explain, rag, agent) importable regardless of cwd.
sys.path.insert(0, str(Path(__file__).parent))

from explain import explain_transaction  # noqa: E402
from agent import run_agent  # noqa: E402


# ---------------------------------------------------------------------------
# Preset transactions — pick-list for the demo
# ---------------------------------------------------------------------------
EXAMPLES = {
    "Likely fraud — balance-drain TRANSFER": {
        "step": 1,
        "type": "TRANSFER",
        "amount": 181.0,
        "nameOrig": "C1305486145",
        "oldbalanceOrg": 181.0,
        "newbalanceOrig": 0.0,
        "nameDest": "C553264065",
        "oldbalanceDest": 0.0,
        "newbalanceDest": 0.0,
    },
    "Likely legit — small PAYMENT to merchant": {
        "step": 1,
        "type": "PAYMENT",
        "amount": 9839.64,
        "nameOrig": "C1231006815",
        "oldbalanceOrg": 170136.0,
        "newbalanceOrig": 160296.36,
        "nameDest": "M1979787155",
        "oldbalanceDest": 0.0,
        "newbalanceDest": 0.0,
    }, 
    "Edge case — mid-size CASH_OUT, partial drain": {
        "step": 200,
        "type": "CASH_OUT",
        "amount": 5000.0,
        "nameOrig": "C840083671",
        "oldbalanceOrg": 8500.0,
        "newbalanceOrig": 3500.0,
        "nameDest": "C38997010",
        "oldbalanceDest": 15000.0,
        "newbalanceDest": 20000.0,
    },
}


# ---------------------------------------------------------------------------
# Page setup
# ---------------------------------------------------------------------------
st.set_page_config(
    page_title="Fraud Agent",
    layout="wide",
)

st.title("Fraud Detection Agent")
st.caption(
    "Paste a PaySim transaction. The XGBoost model scores it, SHAP explains "
    "the top features, and the Gemini-powered agent writes an investigator "
    "report grounded in a small knowledge base (FAISS + MiniLM)."
)

with st.sidebar:
    st.header("About")
    st.caption(
        "Demo prototype."
    )
    st.markdown("---")
    st.header("Try a preset")
    preset_name = st.selectbox(
        "Preset",
        options=list(EXAMPLES.keys()),
        label_visibility="collapsed",
    )


# ---------------------------------------------------------------------------
# Input
# ---------------------------------------------------------------------------
chosen = EXAMPLES[preset_name]

# Key depends on preset so switching presets resets the textarea contents.
tx_text = st.text_area(
    "Transaction (JSON)",
    value=json.dumps(chosen, indent=2),
    height=300,
    key=f"tx_input_{preset_name}",
    help="Paste any row from data/PS_*.csv, minus isFraud and isFlaggedFraud.",
)

run_clicked = st.button("Investigate", type="primary")


# ---------------------------------------------------------------------------
# Pipeline
# ---------------------------------------------------------------------------
if run_clicked:
    # --- Parse ---
    try:
        tx = json.loads(tx_text)
    except json.JSONDecodeError as e:
        st.error(f"Invalid JSON: {e}")
        st.stop()

    # --- XGBoost + SHAP ---
    with st.spinner("Scoring with XGBoost and computing SHAP values..."):
        try:
            exp = explain_transaction(tx)
        except KeyError as e:
            st.error(
                f"Missing required field: {e}. "
                "The transaction needs all PaySim columns "
                "(step, type, amount, nameOrig, oldbalanceOrg, newbalanceOrig, "
                "nameDest, oldbalanceDest, newbalanceDest)."
            )
            st.stop()
        except FileNotFoundError as e:
            st.error(
                f"Model artifact missing: {e}. "
                "Run `uv run python src/train.py` first."
            )
            st.stop()

    st.markdown("## Model output")

    col_metric, col_chart = st.columns([1, 2])

    with col_metric:
        verdict_color = "red" if exp["prediction"] == "FRAUD" else "green"
        st.markdown(f"### Verdict\n:{verdict_color}[**{exp['prediction']}**]")
        st.metric("Fraud probability", f"{exp['fraud_probability']:.2%}")
        st.caption(
            "Threshold 0.5. In production you would tune this by cost-of-mistake: "
            "false declines vs. missed fraud."
        )

    with col_chart:
        top = pd.DataFrame(exp["top_features"]).sort_values("shap_contribution")
        max_abs = max(abs(top["shap_contribution"]))
        fig = px.bar(
            top,
            x="shap_contribution",
            y="feature",
            orientation="h",
            color="shap_contribution",
            color_continuous_scale="RdBu_r",
            range_color=[-max_abs, max_abs],
            title="Top SHAP feature contributions",
            hover_data={"value": ":.2f", "direction": True},
        )
        fig.update_layout(showlegend=False, height=360, coloraxis_showscale=False)
        st.plotly_chart(fig, use_container_width=True)

    # --- Agent ---
    st.markdown("---")
    st.markdown("## Agent investigation")

    with st.spinner("Agent is investigating (calling Gemini + retrieving context)..."):
        try:
            final_text, report_dict = run_agent(tx)
        except genai_errors.APIError as e:
            st.error(
                f"Gemini API error: {e}\n\n"
                "Free-tier quotas reset per minute — wait ~60s and retry. "
                "If this persists, swap MODEL in agent.py to 'gemini-2.0-flash'."
            )
            st.stop()
        except Exception as e:
            # Catch-all so a mid-demo bug shows a readable message instead of a traceback.
            st.error(f"Unexpected error during agent run: {type(e).__name__}: {e}")
            st.stop()

    # --- Structured report ---
    if report_dict:
        verdict_color = {
            "FRAUD": "red",
            "LEGIT": "green",
            "UNCERTAIN": "orange",
        }.get(report_dict["verdict"], "gray")

        c1, c2, c3 = st.columns(3)
        c1.markdown(f"**Verdict**\n\n:{verdict_color}[**{report_dict['verdict']}**]")
        c2.metric("Confidence", report_dict["confidence"])
        c3.metric("Recommended action", report_dict["recommended_action"].replace("_", " "))

        st.markdown(f"**Matched typology:** `{report_dict['matched_typology']}`")
        st.markdown(f"**Rationale:** {report_dict['rationale']}")

        signals = report_dict.get("top_risk_signals") or []
        if signals:
            st.markdown("**Top risk signals**")
            for signal in signals:
                arrow = "↑" if signal["impact"] == "raises risk" else "↓"
                st.markdown(
                    f"- `{signal['feature']}` {arrow} *{signal['impact']}* — "
                    f"{signal['observation']}"
                )

        with st.expander("Structured report (raw JSON)"):
            st.json(report_dict)
    else:
        st.warning(
            "Agent did not submit a structured report. "
            "This usually means it hit max_iterations — check the narrative below."
        )

    if final_text:
        with st.expander("Agent narrative", expanded=True):
            st.markdown(final_text)