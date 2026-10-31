# API contract 0.1.0

[`../contracts/openapi.yaml`](../contracts/openapi.yaml) is the normative wire contract (OpenAPI 3.1 / JSON Schema 2020-12). This document supplies normative runtime rules that JSON Schema cannot enforce. Merge this contract PR as the stage-0 freeze before implementing services. Changes to endpoints, required fields or semantics require a contract PR reviewed by both owners; breaking changes require a new API major version.

## Ownership and routes

| Owner | Routes | Trust boundary |
|---|---|---|
| A: Procurement | `POST /v1/research-requests`, `/v1/plans`, `/v1/mandates` | Stored requests, recommendations, authenticated human mandate approval; signing remains internal |
| B: Fulfilment | `GET /v1/offerings`, `POST /v1/rights/evaluate`, `/v1/quotes`, `/v1/jobs`, `GET /v1/jobs/{job_id}`, `/v1/jobs/{job_id}/result` | Own catalogue/policies/prices; independently fetch and verify payment before execution |

Each service exposes only its own routes. Configure separate base URLs; no deployed server URL is assumed. Bearer credentials are deployment-configured and scoped to a principal/role. Require HTTPS outside loopback. Authorise every object ID against the principal; possession of a quote ID or transaction hash grants no access. B binds quotes to the authenticated caller and payer; its local snapshot is authoritative, not A's database. A must resolve B quotes through its trusted client/storage, not accept caller-supplied quote bodies. A human principal may create a mandate; agent/service principals may not. Approval identity/time are server-produced. No public signing or approval-bypass endpoint exists.

## Wire rules and draft changes

- Closed objects reject unknown fields, including `paid`, `validated`, wallet secrets and client-supplied prices/approval identities. All times are UTC `Z`; IDs are opaque, bounded strings. UUIDs are not required.
- Money uses positive decimal strings. XRP `value` is in XRP units (at most six decimal places), converted exactly to integer drops; no binary floats. Issued assets use a ledger currency code AND issuer; a display label such as RLUSD is not a ledger currency identifier. The supported issued-decimal subset is deliberately narrow; additionally check <=16 significant digits and exact serialization at runtime. No implicit FX or issuer substitution.
- Draft flat `xrpl_tx_hash` becomes `payment_reference: {network, xrpl_tx_hash}`. Never accept validation evidence in job creation. The PaymentEvidence schema is B-produced output only.
- Analysis parameters and variable selection are explicit and bound into quotes. For the MVP, `variables` must contain `bmi` and the chosen biomarker, and be covered by the offering. Extra variables must also be covered. `aggregate_analysis` means two BMI groups with a two-sided Mann–Whitney U test; no caller-supplied code/SQL or arbitrary parameters.
- Rights evaluation returns HTTP 200 for both allow and deny, with matching boolean/code. Quote creation re-evaluates B's policy and returns 403 RIGHTS_DENIED when ineligible. A prior allow decision never substitutes for rechecking.
- Catalogue purpose is a suitability hint, not an authorisation filter: all three fixture offers remain discoverable so an incompatible one can be explained. Variable filter requires coverage. Complete MVP catalogue has at most 100 entries; no pagination or silent truncation.

## Quote binding and expiry

B creates an immutable quote including request, payer, provider, offering, dataset version/hash, variable selection, purpose, operation, parameters, allowed rights decision, exact price/asset, destination, network and timestamps. Every nested identifier/purpose/operation/policy version must match the snapshot. `reference == quote_id` and must be unique within B. Only configured, checksum-valid, non-reserved accounts may be used at runtime.

`terms_hash` is lowercase SHA-256 of UTF-8 RFC 8785 canonical JSON of the entire Quote object with only its top-level `terms_hash` omitted. Do not hash YAML, pretty-printed JSON, or a mutable catalogue row. Snapshot hashes are independently recomputable; they do not prove scientific correctness.

For this MVP choose **memo binding only** (no destination-tag alternative): one memo with `MemoType` equal to uppercase hex UTF-8 `agent-k/quote/v1`, and `MemoData` equal to uppercase hex UTF-8 of `reference`. Reject missing, malformed, duplicate or conflicting quote-binding memos. No patient information, purpose or research text goes on ledger. A receiver requiring a destination tag is unsupported for this contract version and must fail configuration checks.

Quote creation < expiry; B must receive the first job attempt before expiry and establish validated payment with ledger close time >= quote creation and < expiry. Rights are rechecked before authorisation/execution; a revoked policy denies execution even after payment. A retry of an already accepted identical job returns the original intake response even after expiry. A rejected-before-admission attempt can retry only while quote/payment remain eligible. If payment is late or service delivery fails, expose the failure and reconcile manually; never imply atomic payment-for-compute or automatic refund.

## Spending controls (A, before signing)

A binds the mandate to one request and one immutable quote. Its human approval endpoint validates ownership, current quote, purpose/parameters, provider allowlist, exact asset, expiry and limits. `per_purchase_limit <= total_limit <= request.max_budget` using exact arithmetic and the same asset identity. Quote price must fit all three limits. Mandate expiry must be in the future and no later than quote expiry. Reject unconfigured assets, unknown providers and agents attempting human approval.

The trusted signer repeats these checks immediately before signing, including current expiry and principal/wallet mapping. Atomically reserve quote price against both the mandate and the request's cumulative budget across *all* mandates; already spent + reserved + proposed spend must fit. A new mandate cannot reset a request budget. Quote-bound mandate permits one purchase. Separately reserve network fees in integer XRP drops, checking actual fee <= `max_network_fee_drops` and funded balance/reserves. Do not conflate XRP fees with an issued-token budget.

Persist transaction identity before submission; retries reuse/reconcile the same signed transaction. Unknown/pending transactions retain reservations. Release only when failure/non-inclusion is established by ledger reconciliation. Never sign a replacement merely because the HTTP/RPC request timed out. No keys in HTTP bodies, logs or LLM prompts.

## Payment controls (B, independently)

The HTTP payment reference is only a lookup key. B fetches ledger facts using its **own pinned Testnet RPC**; it must never use caller-supplied ledger facts, RPC URLs, status flags or Procurement's verification decision.

Before AUTHORIZED or any statistical execution, require all of:

1. Trusted configured Testnet source, exact requested hash, `validated=true`, `TransactionType=Payment`, metadata `TransactionResult=tesSUCCESS`, and a positive validated ledger index/close time.
2. Expected payer, destination and unique decoded quote memo match B's snapshot; validate address checksums/configuration.
3. Actual metadata `delivered_amount` matches the quote numerically and by exact currency/issuer. Reject missing or `unavailable` metadata. Never trust transaction `Amount` as delivered value. MVP rejects partial-payment flags and cross-currency/path payments altogether (including SendMax/Paths); still inspect delivered amount for every payment.
4. Time window, current rights and all job fields match the immutable quote. Recompute/verify stored terms integrity before using it.
5. Atomic uniqueness of `(network, xrpl_tx_hash)`, quote_id and job_id; one payment/quote funds one logical job, including concurrent submissions. Scope payment/quote uniqueness globally in B, not per caller. Reserve them in the same durable transaction as job admission. Retain accepted claims through failure; do not allow a crash to buy a second execution.

Unknown or unvalidated receipts cannot run. Temporary RPC failure stays VERIFYING or yields 503 DEPENDENCY_UNAVAILABLE without execution. A terminal verification failure is REJECTED with a structured error. No Mainnet fallback. Receiving 202 is not proof of payment or authorisation.

## Idempotency and errors

All POSTs require `Idempotency-Key`, including rights evaluation. Scope key by authenticated principal + HTTP method + normalised route. Store a fingerprint of canonical request JSON and the initial terminal HTTP response (status/body); reserve the key atomically before effects. Same key + same payload returns the same status/body; same key + different payload returns 409 IDEMPOTENCY_CONFLICT. Correlation response headers may reflect the current attempt. Concurrent identical calls wait for the original or return 409 IDEMPOTENCY_CONFLICT with `retryable=true`, never duplicate effects. Do not store transient failures before resource admission as final outcomes; retry those with the same key. Preserve accepted operations and uniqueness records for the life of the MVP data; no time-based eviction that permits duplicate spending or execution.

Job identity additionally protects retries with a *different* key: identical job_id, quote_id and payload owned by the same principal returns the original 202 intake body; changed payload/job ID for a consumed quote returns 409 JOB_ALREADY_EXISTS; transaction used by another quote/job returns 409 PAYMENT_REPLAY (check replay first when both apply). Accepted pending jobs retry through GET polling; retrying POST returns the original intake, not current status. Transport/auth/schema failures occur before admission. Synchronous admission errors use the documented HTTP status; asynchronous verifier/executor errors use the same Error object in Job.error.

| HTTP | Codes |
|---|---|
| 400 | INVALID_REQUEST (malformed JSON, missing key/header) |
| 401 | UNAUTHENTICATED |
| 403 | FORBIDDEN, RIGHTS_DENIED, PROVIDER_NOT_ALLOWED |
| 404 | NOT_FOUND (also hide inaccessible resources) |
| 409 | IDEMPOTENCY_CONFLICT, JOB_ALREADY_EXISTS, PAYMENT_REPLAY, PAYMENT_UNVALIDATED, RESULT_NOT_READY |
| 410 | QUOTE_EXPIRED, MANDATE_EXPIRED |
| 422 | INVALID_REQUEST (schema/semantic validation), OVER_BUDGET, PAYMENT_MISMATCH |
| 500 | INTERNAL_ERROR, PROCESSING_FAILED |
| 503 | ASSET_NOT_CONFIGURED, DEPENDENCY_UNAVAILABLE |

Every response carries `X-Correlation-ID`; every error includes code, safe message, matching correlation_id and retryable. Pending/not-ready/transient dependency errors may be retryable; rights denial, mismatch, replay, expired quotes, exhausted budgets and terminal processing failures are not. Retryable never authorises a new payment. Do not expose credentials, tracebacks or patient data. Get-result returns 409 while pending, 403 RIGHTS_DENIED for a denied job, the corresponding verification error status for other rejections, and 500 PROCESSING_FAILED after execution failure.

## State and result semantics

A: `DRAFT -> PLANNED -> APPROVED -> PAYMENT_PENDING -> PAYMENT_VALIDATED -> PROCESSING -> COMPLETED`; explicit terminal failures `REJECTED`, `PAYMENT_FAILED`, `PROCESSING_FAILED`, `EXPIRED`. Only validated ledger finality advances PAYMENT_PENDING. A reports completion only after B's completed result.

B: `RECEIVED -> VERIFYING -> AUTHORIZED -> RUNNING -> COMPLETED`; verification may end REJECTED, execution may end FAILED. No backwards transition or terminal-to-completed rewrite. Crashes resume the same durable job, never a new purchase. On completion persist result and status atomically. Only COMPLETED has result_path; only REJECTED/FAILED has error. Result path's job ID must equal the job's ID. updated_at >= created_at; provenance completed_at >= started_at.

Results contain synthetic markers, two distinct group summaries, sample counts, nonnegative quartiles with q1 <= median <= q3, test statistic, p-value [0,1], excluded row count and versioned reproducibility metadata. BMI >= threshold is obese. Exclude rows missing BMI or the chosen marker; fail if either group is empty. Report median and linearly interpolated quartiles. Mann–Whitney U uses the non-obese group first, exact method when no ties and min group size <=8, otherwise asymptotic with tie/continuity correction; pin library/code version in the implementation. hsCRP uses mg/L and VCAM-1 ng/mL. No raw row export. All provenance links must match the quote/job and verified payment. Hash exact CSV bytes for dataset_hash, implementation artifact bytes for code_hash, and RFC 8785 canonical AnalysisResult JSON for output_hash. Fixture code_hash/ledger evidence are synthetic, not an implemented processor or payment proof.

## Configuration gate: still unverified

No asset issuer, usable wallet, funded balance, trustline, RPC endpoint or live transaction has been verified by this PR. The examples use XRP and reserved account sentinels for **offline validation only**. Never sign/send to them. Issued-money schema support does not assert RLUSD availability.

Before enabling quotes/signing, both owners independently record and verify: pinned Testnet RPC/network, checksum-valid non-reserved payer/receiver, funded balances/reserves, exact asset code/issuer if issued, issuer account state and relevant authorised/unfrozen trustlines/balances, receiver flags (including destination-tag requirements), and a genuine validated transfer observed by both services. If any check is unknown, fail closed with ASSET_NOT_CONFIGURED/DEPENDENCY_UNAVAILABLE. Verify XRP fallback explicitly and label it XRP. Keep secrets outside the repo; record non-secret evidence and check time separately.

## Tests and references

Run [the contract suite](../contracts/README.md) independently of either service. Offline schema/fixture tests do **not** prove runtime security, XRPL settlement or scientific execution. The adapter safety suite must run against each implementation, with controlled RPC/signing/execution dependencies, before accepting the relevant scenarios from `docs/DEMO.md`.

Primary references: [OpenAPI 3.1](https://spec.openapis.org/oas/v3.1.0), [XRPL payment metadata](https://xrpl.org/docs/references/protocol/transactions/metadata), [robust payment monitoring](https://xrpl.org/docs/concepts/payment-types/robustly-monitoring-for-payments), [Payment transaction](https://xrpl.org/docs/references/protocol/transactions/types/payment), [RFC 8785 canonical JSON](https://www.rfc-editor.org/rfc/rfc8785).
