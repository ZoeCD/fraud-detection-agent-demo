# Account Takeover (ATO)

## What it is
An attacker gains unauthorized access to a legitimate user's account and
exploits the trusted standing of that account — bypassing card-not-present
checks because the account appears authentic.

## Typical attack chain
1. **Credential acquisition** — phishing, data breach dumps, or credential stuffing
   (automated login attempts using username/password pairs from other breaches).
2. **Access confirmation** — attacker logs in, often from a new device or foreign IP.
3. **Account modification** — changes email, phone number, or notification settings
   to delay victim detection.
4. **Monetization** — high-value purchase, P2P transfer to mule account,
   card addition, or withdrawal.

## Behavioral signals
- Login from a new device or IP immediately before a high-value transaction
- Password or contact-info change shortly before a transaction
- Unusual transaction time (e.g., 3 AM local time for the account)
- Transaction type or merchant category never seen in account history
- Multiple failed logins followed by success (stuffing hit)
- Geolocation jump: account used in CDMX, then Miami 10 minutes later

## Why it's hard to detect
The card credentials are legitimate. Behavioral and device signals matter more
than the transaction itself. Models trained only on transaction features
may underweight session-level context.

## Recommended response
Step-up authentication (OTP, biometric confirmation) before allowing
high-value or profile-change actions. Flag for manual review if step-up
is not completed or if device is new + amount is high.