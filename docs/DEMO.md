# Demo and acceptance tests

## 90-second judging path
1. **0–15s:** Submit scientific research question, constraints and maximum spend.
2. **15–30s:** Show three discovered synthetic offerings; one rejected due to commercial/research-use mismatch.
3. **30–45s:** Display selected quote and delegated spending mandate.
4. **45–65s:** Agent pays with XRPL Testnet; validated transaction appears with destination and amount.
5. **65–80s:** Provider verifies payment and executes a real synthetic-cohort statistical analysis.
6. **80–90s:** Show actual results, dataset/code hashes, policy decision and XRPL transaction evidence.

## Acceptance scenarios
| ID | Given | When | Then |
|---|---|---|---|
| AT-01 | Three offerings | Broker queries | All offerings discoverable, with suitability metadata |
| AT-02 | Prohibited usage policy | Rights evaluation | Denied with deterministic code |
| AT-03 | Price exceeds mandate | Broker requests payment | No signature/payment; rejection displayed |
| AT-04 | Valid approved quote | Broker submits testnet payment | Validated TX, matching quote and receiver |
| AT-05 | Fake or pending TX | B receives job | No execution |
| AT-06 | Same TX for second job | B receives another job | Replay denied |
| AT-07 | Correct paid, authorised job | B executes | Reproducible statistics and manifest returned |
| AT-08 | Wrong asset issuer/destination/amount | B verifies | Payment mismatch denied |
| AT-09 | Processing crashes | A polls job | Explicit failure; no false completed status |

## Demo evidence
- XRPL testnet explorer link for genuine payment.
- Provider rights evaluation decision and version.
- SHA-256 source data hash and algorithm version.
- Job ID, output hash, timestamps and cost.
- Clear **SYNTHETIC DATA / TESTNET** markings.

**Avoid claims:** verified patient consent, production clinical compliance, trustless compute proof or real-money settlement.
