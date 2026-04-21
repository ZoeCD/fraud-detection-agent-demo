# Transaction Velocity Patterns

## What it is
Velocity refers to the rate at which transactions occur on an account or
across a network of accounts within a defined time window. Fraudsters operate
under time pressure — they need to move funds before detection — so abnormally
high velocity is one of the most reliable cross-pattern fraud signals.

## Why velocity matters
Legitimate users have organic, irregular transaction rhythms. Fraudsters,
especially those using automated tools or executing a bust-out, generate
transaction bursts that fall far outside normal behavioral bounds.
High velocity alone is not proof of fraud, but combined with other signals
(account age, balance drain, unusual transaction type) it significantly
raises risk.

## Key velocity patterns

**Single-account burst**
An account that is normally quiet suddenly initiates multiple transactions
within minutes. Especially suspicious when the account is new or has a
thin transaction history.
Signals: high transaction count in a short window, all of the same type
(e.g., repeated TRANSFER or CASH_OUT), amounts that together approach
the full account balance.

**Sequential drain**
A series of transactions that progressively reduce the account balance
to zero, each just below a round number or threshold.
Signals: decreasing oldbalanceOrg across sequential transactions,
newbalanceOrig approaching zero, consistent transaction type.

**Fan-out velocity**
One account receives a large inbound transfer and immediately distributes
it to multiple destination accounts in quick succession.
Signals: multiple outbound transactions within minutes of a single
inbound, destination accounts are new or have zero prior balance.

**Cross-account relay**
Funds move through a chain of accounts rapidly — A → B → C → cash out —
each hop occurring within a short window to layer the trail.
Signals: destination account of one transaction becomes origin of the next,
timestamps clustered tightly, balance fully transferred at each hop.

## Velocity signals in PaySim-style data
- Multiple transactions sharing the same step (time unit) on one account
- newbalanceDest immediately becoming the origin of another transaction
  in the same or next step
- TRANSFER followed by CASH_OUT on the destination within one or two steps
- Accounts that appear only during a burst window and go silent afterward

## Caveats
- High velocity during known high-activity periods (payroll receipt,
  bill payment cycles) can be legitimate. Account history and transaction
  type context matter.
- Velocity features are most powerful when computed at inference time
  from recent transaction history — a single transaction record without
  history limits how much velocity can be inferred.
- In this demo context, velocity signals must be inferred from the
  features available in the transaction record rather than computed
  from a live transaction log.