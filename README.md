# fraud-detection-agent-demo

An end-to-end fraud investigation demo built with XGBoost, SHAP, RAG, and Gemini API. A Streamlit app accepts a transaction, scores it with a trained classifier, explains the prediction with SHAP, retrieves relevant fraud typology from a local knowledge base, and produces a structured investigator report via a Gemini-powered agent.

---

## Architecture

```
Transaction input
      │
      ▼
┌─────────────┐     ┌──────────────────┐     ┌─────────────────────┐
│  XGBoost    │────▶│  SHAP explainer  │────▶│                     │
│  classifier │     │  (top features)  │     │   Gemini agent      │
└─────────────┘     └──────────────────┘     │   (tool use loop)   │──▶ Report
                                             │                     │
┌─────────────┐     ┌──────────────────┐     │                     │
│  Markdown   │────▶│  FAISS vector    │────▶│                     │
│  knowledge  │     │  store (RAG)     │     └─────────────────────┘
│  base       │     └──────────────────┘
└─────────────┘
```

The agent has three tools:
- `predict_and_explain` — scores the transaction and returns SHAP attributions
- `retrieve_context` — retrieves relevant docs from the knowledge base
- `finalize_report` — commits to a structured verdict with recommended action

---

## Stack

| Layer | Technology |
|---|---|
| Classifier | XGBoost |
| Explainability | SHAP TreeExplainer |
| Embeddings | `sentence-transformers/all-MiniLM-L6-v2` |
| Vector store | FAISS (`IndexFlatIP`) |
| Agent | Gemini `Gemini 2.0 Flash` |
| UI | Streamlit + Plotly |
| Dataset | PaySim (simulated mobile money transactions) |

---


## Setup

### 1. Clone and create environment

```bash
git clone https://github.com/ZoeCD/fraud-detection-agent-demo
cd fraud-detection-agent
```

### 2. Install uv

If you don't have uv installed:

```bash
# macOS / Linux
curl -LsSf https://astral.sh/uv/install.sh | sh

# Windows
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
```

Verify the install: `uv --version`

### 3. Create the environment and install dependencies

```bash
uv sync
```

This reads `pyproject.toml`, creates a `.venv` automatically, and installs
all dependencies in one step. No need to activate the environment manually
for most commands — prefix them with `uv run` instead.

### 4. Set your API key

Create a `.env` file in the project root:

```
GOOGLE_API_KEY=sk-ant-your-key-here
```

> ⚠️ Make sure `.env` is listed in `.gitignore` before committing anything.

---

## Usage

### Step 1 — Get the dataset

Download the PaySim dataset from Kaggle:  [kaggle.com/datasets/ealaxi/paysim1](https://www.kaggle.com/datasets/ealaxi/paysim1).


### Step 2 — Train the model

```bash
uv run python src/train.py
```

Saves `xgb_model.joblib` and `feature_order.joblib` to `models/`.
Expected AUC-PR: ~0.90+ on PaySim. If it's under 0.75, check class balance handling.


### Step 3 — Build the FAISS index

```bash
uv run python src/rag.py
```

Reads all `.md` files from `knowledge/`, encodes them, and writes
`faiss.index` and `docs.pkl` to `knowledge/`.

### Step 4 — Run the app

```bash
uv run streamlit run src/app.py
```

Opens at `http://localhost:8501`.

---

## Running tests

The test suite uses mocked API call.
```bash
uv run pytest src/test_agent.py -v
```

There is an integration test (that gets skipped for now) that does require an API key. To run it, remove the `@pytest.mark.skip` decorator in `test_agent.py`.
