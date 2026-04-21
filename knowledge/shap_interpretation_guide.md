# Interpreting SHAP Values for Fraud Investigations

## What SHAP values represent
SHAP (SHapley Additive exPlanations) assigns each feature a contribution score
for a specific prediction. The score answers: "how much did this feature push
the fraud probability up or down, compared to the average prediction?"

- **Positive SHAP value** → feature raised the fraud probability for this transaction.
- **Negative SHAP value** → feature lowered the fraud probability.
- **Magnitude** → how strongly. A SHAP of +0.45 is a much stronger signal than +0.03.

## How to read a SHAP output in plain language

Given a feature output like:
  feature: V14, value: -4.2, shap_contribution: +0.38, direction: raises risk

Plain-language translation:
  "Feature V14 had an unusually low value for this transaction (-4.2),
   and this pushed the fraud probability up significantly (+0.38).
   This is one of the strongest risk signals in this prediction."

## Translating into an investigator report
When writing a report, lead with the top 2–3 features by absolute SHAP magnitude.
For each, state:
1. What the feature value was.
2. Whether it raised or lowered risk.
3. How strongly (large / moderate / small contribution).

Avoid saying "the model gave it a SHAP of X" — instead say
"this transaction showed an unusually high amount relative to account history,
which was the strongest factor driving the fraud flag."

## Important caveats to communicate

**SHAP explains the model, not ground truth.**
A high fraud probability with strong SHAP signals means the model is confident
and the features are driving that confidence — it does not guarantee the
transaction is actually fraudulent. Human review remains essential.

**Correlated features can split attribution.**
If two features carry similar information (e.g., V1 and V3 are both
PCA-transformed spending patterns), their SHAP values may each appear moderate
even though together they represent a strong signal. Look at the combined
picture, not individual scores in isolation.

**PCA-anonymized features limit narrative depth.**
On datasets like ULB (V1–V28), SHAP tells you which latent components matter
but not what those components mean in business terms. In production with raw
features (amount, merchant category, velocity, device fingerprint), SHAP
explanations become directly actionable for investigators.