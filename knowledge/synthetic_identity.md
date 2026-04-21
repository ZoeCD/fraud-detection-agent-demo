# Synthetic Identity Fraud

## What it is
An attacker constructs a fictional person by combining real and fabricated data —
typically a real SSN (often belonging to a child, elderly person, or recent immigrant
who rarely checks credit) with a fake name, address, and date of birth.
In the Mexican context, a real CURP or RFC may be used with falsified supporting data.

## How it builds up (the slow burn)
Synthetic identities are patient. The typical lifecycle:

1. **Seeding** — attacker opens a low-limit account or applies for a small credit line.
   Initial applications are often rejected; attacker keeps trying across institutions.
2. **Nurturing** — account is used lightly and paid on time for months or years
   to build a credit/behavior history. The account looks clean.
3. **Bust-out** — attacker maxes out all available credit or withdraws all funds
   in a short window, then disappears. No real person exists to collect from.

## Signals at account opening
- Identity documents that pass validation but have no prior credit or banking history
- Address is a mail drop, virtual office, or does not match public records
- Phone number is a VoIP or recently registered prepaid
- Multiple applications with slightly varied personal data (name spelling, DOB off by one)

## Signals at bust-out phase
- Sudden spike in transaction volume after a long quiet period
- Multiple high-value transactions in a short window
- Transfers to accounts with no prior relationship
- No response to step-up authentication (no real person is watching)

## Why it matters for a neobank
Mobile-first onboarding (selfie + ID scan) reduces but does not eliminate synthetic
identity risk. Liveness detection helps; behavioral biometrics during onboarding
add another layer. The bust-out loss is typically total — no chargeback recovery.