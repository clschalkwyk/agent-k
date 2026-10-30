# Execution strategy — 2 developers / 48-hour MVP

## Non-negotiable critical path
**Request → offers → rights decision → quote → approval → validated XRPL payment → independent verification → real analysis → manifest.**

## Ownership and deliverables
| Stream | Dev A: Procurement | Dev B: Fulfilment |
|---|---|---|
| Build | Request UI, plans, mandate, XRPL integration, orchestration | Fixtures, catalogue, rights, quotes, payment verifier, executor, provenance |
| Unit proof | Reject over-limit or unauthorized spend before signing | Reject incompatible use, unpaid/replayed jobs |
| Mock for parallelism | Mock B search/quote/job APIs | Mock A request and payment proof |
| Final proof | Validated transaction with correct destination/value | Executes only after verifying the same transaction independently |

### Stage 0 — first 2 hours (together)
- Agree question, 3 synthetic offerings, one allowed and one denied licence, one analysis.
- Pin XRPL network, funded Testnet wallets, and confirmed payment asset.
- Freeze `docs/API-CONTRACT.md` and sample fixtures; create OpenAPI spec before implementation diverges.
- Assign branch ownership: `feat/procurement` (A), `feat/fulfilment` (B). PR into main; small, frequent merges.

### Stage 1 — hours 2–12 (parallel)
- **A:** UI request, plan from mock offers, mandate validator, wallet balance and standalone payment test.
- **B:** dataset registry, deterministic licence policy, quote endpoint, synthetic CSV, standalone SciPy/pandas analysis.
- Integration check: A can query B's real catalogue and rights response.

### Stage 2 — hours 12–24 (parallel)
- **A:** signing isolated from LLM, validated payment handling, durable status and idempotency.
- **B:** XRPL transaction verifier, quote matching, paid job API, deterministic result + manifest.
- Integration check: one testnet payment can unlock exactly one job.

### Stage 3 — hours 24–36 (join)
- Complete end-to-end vertical slice on clean Docker Compose startup.
- Validate network rejection, expired quote, bad issuer, wrong destination, policy denial.
- Render researcher-friendly budget, source selection, status, TX explorer and result.

### Stage 4 — hours 36–48 (stabilise)
- Freeze new features. Fix race/retry bugs, clean logs, record backup demo.
- Validate all P0 scenarios and rehearse live 90-second demo.
- Test from a fresh clone; no undocumented manual steps.

## P0 checklist
- [ ] Three synthetic offerings with different rights/prices.
- [ ] One policy-denied provider; deterministic reason shown.
- [ ] Budget, per-transaction cap and expiry checked before signing.
- [ ] Human approves mandate; agent performs payment without a second manual signature **only within mandate**.
- [ ] One real validated XRPL Testnet transfer.
- [ ] Fulfilment independently verifies payment and replay protection.
- [ ] Real statistical calculation using synthetic data.
- [ ] Manifest contains dataset version/hash, code version, result hash, quote, payment and purpose.
- [ ] Clean startup, coherent UI, repeatable demo.

## Cut order when behind
1. Cut provider negotiation and external discovery (retain 3 mock catalogue offers).
2. Cut complex multi-analysis and animated UI (retain 1 real analysis).
3. Cut x402/MPP (retain direct XRPL transfer and validated receipt).
4. Cut autonomous multi-step reasoning (retain structured deterministic planner).
**Never cut:** independent payment validation, one genuine transaction, actual computation, rights rejection.

## Risks
- Testnet faucet/issued-asset availability: prove wallet settlement on day 0.
- Third-party API instability: keep deterministic local providers.
- Schema drift: version and contract-test every endpoint.
- LLM hallucinated rights: rules engine decides, not prompt text.
- Refund/processing failure: report honestly; no fake atomic escrow claims.
