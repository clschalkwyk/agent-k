# API contract v0.1 — freeze before feature work

HTTP JSON over local services. Version prefix `/v1`; OpenAPI schema belongs in `contracts/openapi.yaml` once implementation starts. All IDs opaque strings, money as **decimal strings**, times ISO 8601 UTC, hashes full length. These are **draft contract examples**, not production endpoints.

## Core requests
A owns `POST /v1/research-requests`, `POST /v1/plans`, `POST /v1/mandates`.
B owns:

| Method | Endpoint | Purpose |
|---|---|---|
| GET | `/v1/offerings?variable=vcam1&purpose=academic_research` | Discover candidate offerings |
| POST | `/v1/rights/evaluate` | Deterministic eligibility check |
| POST | `/v1/quotes` | Bind offered resource, terms, price, destination and expiry |
| POST | `/v1/jobs` | Authorised, paid execution request (idempotent) |
| GET | `/v1/jobs/{job_id}` | State, errors, result pointers |
| GET | `/v1/jobs/{job_id}/result` | Analysis and provenance |

## Illustrative objects

```json
{
  "research_request": {
    "request_id": "req-001",
    "question": "Compare inflammatory biomarker distributions by obesity group",
    "variables": ["bmi", "vcam1"],
    "purpose": "academic_research",
    "operation": "aggregate_analysis",
    "max_budget": {"currency": "RLUSD", "value": "20.00"}
  },
  "provider_offer": {
    "offer_id": "offer-002",
    "provider_id": "provider-b",
    "dataset_id": "synthetic-cohort-b",
    "dataset_version": "v1",
    "variable_coverage": ["bmi", "vcam1"],
    "usage_policy_version": "policy-2",
    "supported_operations": ["aggregate_analysis"]
  }
}
```

```json
{
  "quote_id": "quote-001",
  "offer_id": "offer-002",
  "operation": "aggregate_analysis",
  "purpose": "academic_research",
  "price": {
    "currency": "RLUSD",
    "issuer": "<verified-testnet-issuer-address>",
    "value": "3.50"
  },
  "destination": "<provider-xrpl-address>",
  "expires_at": "2026-11-14T12:00:00Z",
  "reference": "quote-001",
  "terms_hash": "<sha256>"
}
```

**Production-like nuance:** use a stable quote-binding method supported by XRPL (memo or destination tag plus server-side mapping). Never trust a user-supplied identifier without checking the validated transaction and preventing replay. Quoted issuer and destination must be configured and pinned.

```json
{
  "job_id": "job-001",
  "quote_id": "quote-001",
  "offer_id": "offer-002",
  "operation": "aggregate_analysis",
  "purpose": "academic_research",
  "parameters": {"obese_bmi_threshold": 30},
  "xrpl_tx_hash": "<validated-transaction-hash>"
}
```

## Status
- A research job: `DRAFT -> PLANNED -> APPROVED -> PAYMENT_PENDING -> PAYMENT_VALIDATED -> PROCESSING -> COMPLETED`.
- Error states: `REJECTED`, `PAYMENT_FAILED`, `PROCESSING_FAILED`, `EXPIRED`; do not silently convert into success.
- B processing: `RECEIVED -> VERIFYING -> AUTHORIZED -> RUNNING -> COMPLETED` or `REJECTED/FAILED`.
- Cross-service correlation: `request_id`, `quote_id`, `job_id`, `xrpl_tx_hash`, `Idempotency-Key`.

## Errors
Use machine-readable codes `RIGHTS_DENIED`, `QUOTE_EXPIRED`, `OVER_BUDGET`, `PAYMENT_UNVALIDATED`, `PAYMENT_MISMATCH`, `PAYMENT_REPLAY`, `JOB_ALREADY_EXISTS`, `PROCESSING_FAILED`. Return a human-readable explanation and correlation ID.

## Payment safety
Do not assume RLUSD testnet liquidity or faucet availability; confirm supported asset and trustline before coding. If RLUSD testnet is unavailable, demo with XRP and call it **XRP**, not RLUSD. Avoid floating-point money calculations; XRPL XRP amount is in integer drops and issued tokens have XRPL decimal semantics.
