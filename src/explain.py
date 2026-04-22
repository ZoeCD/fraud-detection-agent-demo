import shap, joblib, numpy as np, pandas as pd
from pathlib import Path


ROOT = Path(__file__).parent.parent

model = joblib.load(ROOT / "models" / "xgb_model.joblib")
feature_order = joblib.load(ROOT / "models" / "feature_order.joblib")
explainer = shap.TreeExplainer(model)  # fast on tree models
OHE = joblib.load(ROOT / "models" / "type_encoder.joblib")


def preprocess_transaction(raw_tx: dict) -> dict:
    """Convert a raw PaySim-style row into model-ready features.
    """
    tx = dict(raw_tx)  # don't mutate the caller's dict

    # Derive merchant flag from nameDest if it hasn't been derived yet.
    if "nameDest" in tx and "dest_is_merchant" not in tx:
        tx["dest_is_merchant"] = int(str(tx["nameDest"]).startswith("M"))

    # Drop columns the model never consumes (identifiers + labels).
    for col in ("isFraud", "isFlaggedFraud", "isFlaggedFraud", "nameOrig", "nameDest"):
        tx.pop(col, None)

    # One-hot encode `type` using the fitted encoder from training.
    if "type" in tx and isinstance(tx["type"], str):
        raw_type = tx.pop("type")
        encoded = OHE.transform([[raw_type]])[0]
        for col, val in zip(OHE.get_feature_names_out(["type"]), encoded):
            tx[col] = int(val)

    return tx


def explain_transaction(tx: dict, top_k: int = 5) -> dict:
    tx = preprocess_transaction(tx)
    X = pd.DataFrame([tx])[feature_order]
    proba = float(model.predict_proba(X)[0, 1])
    shap_values = explainer.shap_values(X)[0]        # shape: (n_features,)
    contribs = sorted(
        zip(feature_order, X.iloc[0].values, shap_values),
        key=lambda t: abs(t[2]), reverse=True,
    )[:top_k]
    return {
        "fraud_probability": proba,
        "prediction": "FRAUD" if proba > 0.5 else "LEGIT",
        "top_features": [
            {"feature": f, "value": float(v), "shap_contribution": float(s),
             "direction": "raises risk" if s > 0 else "lowers risk"}
            for f, v, s in contribs
        ],
    }