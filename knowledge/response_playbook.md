# Fraud Response Playbook — Triage Levels

## Decision framework
Every flagged transaction should result in one of four actions.
The decision depends on fraud probability, confidence of explanation,
transaction amount, and account context.

## Triage levels

**AUTO-DECLINE**
Triggered when: fraud probability is high (e.g., >0.85) AND strong SHAP signals
are present AND the transaction matches a known high-risk pattern
(BIN attack, rapid card testing, bust-out velocity).
Action: Decline immediately. No step-up offered. Log for investigation.
User communication: generic decline message to avoid tipping off attacker.

**STEP-UP AUTHENTICATION**
Triggered when: fraud probability is moderate-to-high (e.g., 0.55–0.85)
OR a strong signal is present but account history is otherwise clean
OR a high-value transaction comes from a new device or location.
Action: Pause transaction. Request OTP, biometric, or security question.
If step-up passes → allow and log. If step-up fails or times out → decline
and escalate to manual review.

**MANUAL REVIEW**
Triggered when: probability is ambiguous (e.g., 0.35–0.55), or signals
are contradictory, or the account profile is unusual enough that
automated rules are unreliable (e.g., synthetic identity suspicion,
money mule fan-out pattern).
Action: Hold transaction (if reversible). Route to fraud analyst queue
with agent-generated report. SLA: typically 24–48 hours for non-urgent cases.

**ALLOW (with logging)**
Triggered when: fraud probability is low (<0.35) AND no high-risk pattern
is detected AND transaction is consistent with account history.
Action: Approve. Log prediction and SHAP snapshot for model monitoring.
Do not silently allow — every scored transaction should leave an audit trail.

## General guidance
- Thresholds above are illustrative. Production thresholds should be calibrated
  against your institution's risk appetite, chargeback rate, and false positive cost.
- False positives have real cost: declined legitimate transactions damage
  user trust and generate Condusef complaints.
- Document the rationale for every manual review decision — required for
  regulatory audit trails and model governance.