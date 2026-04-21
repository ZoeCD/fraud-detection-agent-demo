# Money Mule Patterns

## What it is
A money mule account is used to receive and quickly forward stolen funds,
creating distance between the original fraud and the final destination.
Mules are sometimes recruited (job scams, romance scams, "work from home" offers)
and may not know they are facilitating fraud.

## Transaction-level signals

**Rapid in/out**
Funds arrive and are forwarded within minutes to hours — the account is used
as a relay, not for spending. Account balance stays near zero between events.

**Round-number amounts**
Fraudsters often move round numbers ($500, $1,000, $5,000) to simplify accounting
across multiple mule hops. Legitimate P2P transfers tend to be irregular amounts.

**Structuring (smurfing)**
Breaking a large transfer into multiple smaller ones to stay below reporting thresholds.

**Fan-out pattern**
One incoming transfer is split immediately into several outgoing transfers
to different accounts — characteristic of layering in money laundering.

## Account-level signals
- Recently opened account (days to weeks old) receiving large transfers
- No organic spending activity — no retail, subscriptions, or food purchases
- Recipient accounts are also new or have thin histories
- Multiple inbound transfers from different originators on the same day

## Recruited mule indicators
- Account owner responds to step-up auth (unlike synthetic identities) but
  cannot explain the source of funds when contacted
- Transaction narrative fields contain job-related references
  ("payment for task", "commission", "project fee")

## Response guidance
High fan-out velocity + new account + round amounts → escalate to manual review
and consider temporary hold pending AML review. Document for Condusef reporting
if the pattern meets suspicious operation criteria.