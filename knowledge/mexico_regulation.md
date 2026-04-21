# Financial Regulation Context — Mexico

## Key regulatory bodies

**CNBV (Comisión Nacional Bancaria y de Valores)**
The primary prudential regulator for banks and financial institutions in Mexico.
Oversees licensing, risk management standards, and anti-fraud controls.
Neobanks and fintech institutions operating under a banking license fall
under CNBV jurisdiction.

**Condusef (Comisión Nacional para la Protección y Defensa de los Usuarios
de Servicios Financieros)**
Consumer protection body. Handles user complaints related to unauthorized
transactions, fraud, and disputed charges. Institutions are generally required
to respond to Condusef complaints within defined windows and may face sanctions
for non-compliance.

**LFPIORPI (Ley Federal para la Prevención e Identificación de Operaciones
con Recursos de Procedencia Ilícita)**
Mexico's primary anti-money laundering law. Establishes obligations for
"vulnerable activities" — including financial institutions — to identify
customers, monitor operations, and report suspicious activity to the FIU
(Unidad de Inteligencia Financiera, UIF).

## Suspicious operation reporting
Financial institutions in Mexico are generally required to file suspicious
operation reports (Reportes de Operaciones Sospechosas, ROS) with the UIF
when transactions show indicators of money laundering or illicit origin.
Reporting windows and thresholds are defined by regulation and vary by
institution type — consult current CNBV/UIF circulars for specifics.

## Relevant fraud obligations
- Institutions must have documented fraud prevention and detection controls.
- Unauthorized transaction claims by users generally trigger an investigation
  obligation, with provisional credit rules depending on the institution type.
- PII and transaction data handling must comply with LFPDPPP
  (Mexico's federal data protection law) — relevant when passing transaction
  data to external systems or LLM APIs.

## Note on LLM usage and data privacy
Sending raw customer PII (name, card number, CURP) to external API providers
may conflict with data localization or consent requirements. In production,
tokenize or anonymize sensitive fields before passing transactions to any
external model or API.