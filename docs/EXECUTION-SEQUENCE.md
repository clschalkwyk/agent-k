# Agent K — End-to-end execution sequence and recovery

**Status:** Implementation reference aligned with [OpenAPI 0.1.0](../contracts/openapi.yaml) and [runtime contract rules](API-CONTRACT.md).
**Reading order:** First see the [DDD context map](DDD-CONTEXT-MAP.md) for who owns what. This sequence shows **when** the components interact.

## 1. Exact workflow across the two bounded contexts

```mermaid
sequenceDiagram
    autonumber
    actor U as Researcher
    participant A as Dev A: Procurement
    participant AS as A: Durable store + signer
    participant B as Dev B: Fulfilment API
    participant BS as B: Quote + job store
    participant X as XRPL Testnet
    participant W as B: Research executor

    U->>A: POST /v1/research-requests
    A->>AS: Persist request (DRAFT)
    A-->>U: 201 ResearchRequest
    U->>A: POST /v1/plans (request_id)
    A->>B: GET /v1/offerings (filters)
    B-->>A: 200 OfferingList
    loop Each candidate offering
        A->>B: POST /v1/rights/evaluate
        B-->>A: 200 RightsDecision (allowed / denied)
    end
    A->>AS: Persist plan (PLANNED), rank allowed offers
    A-->>U: 201 Plan and rejected-offer reasons
    A->>B: POST /v1/quotes for selected eligible offering
    B->>BS: Recheck rights; persist immutable quote + reference
    B-->>A: 201 Quote (price, destination, memo reference, expiry)
    U->>A: POST /v1/mandates (human approval)
    A->>AS: Bind mandate to quote, asset, caps and expiry
    A-->>U: 201 Mandate (APPROVED)

    A->>AS: Recheck caps; atomically reserve spend + network fee
    alt Mandate/quote expired or over budget
        AS-->>A: Reject BEFORE signing
        A-->>U: Refused; no payment created
    else Mandate valid
        A->>AS: Sign and persist exact transaction identity
        A->>X: Submit signed XRPL Payment
        alt Validated and tesSUCCESS
            X-->>A: Validated TX hash and metadata
            A->>AS: Persist PAYMENT_VALIDATED
            opt A crashes or HTTP response is lost
                A->>AS: On restart load persisted signed TX/hash
                A->>X: Reconcile status; DO NOT sign a second payment
                X-->>A: Previously validated outcome
            end

            A->>B: POST /v1/jobs (JobCreate + payment_reference)
            B->>BS: Atomic intake; reserve quote, job, TX claims
            B-->>A: 202 Job RECEIVED (NOT payment proof)
            B->>BS: Job -> VERIFYING
            B->>X: Fetch TX using B-owned pinned RPC
            X-->>B: Validated TX + metadata
            B->>B: Check payer, destination, memo, asset, delivered_amount, time, rights
            alt Valid payment and eligible rights
                B->>BS: Job -> AUTHORIZED
                B->>BS: Job -> RUNNING
                B->>W: Execute approved synthetic analysis
                alt Processing succeeds
                    W-->>B: Statistics, dataset/code/output hashes
                    B->>BS: Save result + provenance; Job -> COMPLETED
                    A->>B: GET /v1/jobs/{job_id}
                    B-->>A: 200 COMPLETED
                    A->>B: GET /v1/jobs/{job_id}/result
                    B-->>A: 200 Result + Provenance
                    A-->>U: Display statistics, payment TX and evidence
                else Processing fails
                    W-->>B: Execution error
                    B->>BS: Job -> FAILED with PROCESSING_FAILED
                    A->>B: GET /v1/jobs/{job_id}
                    B-->>A: 200 FAILED + Error
                    A-->>U: Processing failed; reconciliation required
                end
            else B cannot reach trusted XRPL RPC temporarily
                B->>BS: Stay VERIFYING; retry read; no computation
                A->>B: GET /v1/jobs/{job_id}
                B-->>A: 200 Job VERIFYING
            else Mismatch, replay, or policy revoked
                B->>BS: Job -> REJECTED with reason code
                A->>B: GET /v1/jobs/{job_id}
                B-->>A: 200 REJECTED + Error
                A-->>U: Show failure; payment may already have settled
            end
        else Pending or XRPL RPC timed out
            A->>AS: Preserve pending transaction + budget reservation
            A->>X: Reconcile persisted TX/hash before any retry
            A-->>U: PAYMENT_PENDING; no new signing
        else Definitive transaction failure
            A->>AS: Record PAYMENT_FAILED; release only after confirmed failure
            A-->>U: Payment failed; no job submitted
        end
    end
```

**Diagram notes:** The `B cannot reach RPC`, `mismatch/replay`, and `processor fails` branches represent different outcomes of validation/execution, not concurrent events. In implementation the processor failure branch occurs *after* successful verification and entry to `RUNNING`. The canonical status values and API response codes are from OpenAPI, not invented by the diagram.

The diagram uses a single logical `Dev A: Procurement` participant for the UI/API/orchestrator and one `Dev B: Fulfilment API` participant for B's internal application actions. The detailed subcomponent ownership is in the context map.

## 2. State model — owned independently

| Milestone | A: ResearchStatus | B: Job.status | Ownership / meaning |
|---|---|---|---|
| User submits objective | `DRAFT` | — | A stores request |
| Matching and permission evaluation completed | `PLANNED` | — | A stores plan; B supplies decisions |
| Human approves quote-specific mandate | `APPROVED` | — | A controls spend |
| Signed payment pending validation | `PAYMENT_PENDING` | — | A never blindly resubmits |
| Ledger settlement verified by A | `PAYMENT_VALIDATED` | — | Still not proof of B acceptance |
| A submits job | `PROCESSING` (or projected pending fulfilment) | `RECEIVED` → `VERIFYING` | B's 202 only confirms intake |
| B independently authorises | `PROCESSING` | `AUTHORIZED` → `RUNNING` | B enforces rights, price, payment |
| B returns output and provenance | `COMPLETED` | `COMPLETED` | A presents B's result |
| Rejected or failed | `REJECTED` / `PAYMENT_FAILED` / `PROCESSING_FAILED` / `EXPIRED` | `REJECTED` / `FAILED` | Distinct lifecycle failure states |

Use the exact status enum in `contracts/openapi.yaml`. `PROCESSING` on A is an application-level projection of fulfilment, **not** B's execution state.

## 3. Failure-recovery contract (must survive a restart)

| Failure window | Correct recovery | Owning developer |
|---|---|---|
| Policy denied or mandate exceeds budget | Do not sign; explain reason | A + B policy |
| HTTP timeout after payment submission | Persisted signed TX/hash is reconciled against XRPL; never sign another without proven non-inclusion/failure | A |
| A crashes after ledger payment, before `POST /v1/jobs` | Rebuild from durable state; send **same** `job_id`, `quote_id`, payment reference and idempotency key | A |
| `POST /v1/jobs` response lost | Retry same payload and ID. B must return original accepted response, not run twice | A + B |
| B's XRPL RPC unavailable | Keep `VERIFYING`; retry lookup. No job execution until verified | B |
| Fake/unvalidated/wrong-issuer/wrong-destination/partial payment | Reject with machine-readable error; no processing | B |
| One TX presented for a second job or quote | Atomic uniqueness check → `PAYMENT_REPLAY` or `JOB_ALREADY_EXISTS` | B |
| Rights revoked after quote/payment | Reject execution and show exception to human; no automatic refund claim | B + A display |
| Processing fails after a valid payment | Mark `FAILED`; preserve payment claim and evidence; operator reconciliation required | B, surfaced by A |

**Invariant:** Money may have moved even when execution fails. This is a **trusted saga with explicit exception handling**, not atomic delivery-versus-payment.

## 4. Contract-level checkpoints for both developers

- HTTP POST requests use `Idempotency-Key` and authenticated principals. Correlate with `request_id`, `quote_id`, `job_id` and `xrpl_tx_hash`.
- A validates the immutable quote and mandate immediately before signing; B independently checks the same immutable quote against ledger facts.
- In the frozen API, the reference is `payment_reference: {network, xrpl_tx_hash}`, **not** `paid: true` or a duplicate `xrpl_tx_hash` at top level.
- B's quote reference is bound to a single XRPL payment memo per [API-CONTRACT.md](API-CONTRACT.md#quote-binding-and-expiry); no destination-tag fallback in v0.1.
- B must validate actual `delivered_amount` and the exact asset identity. Testnet XRP-only demo is sufficient while RLUSD issuer/trustline configuration is unresolved.
- `POST /v1/jobs` 202 means `RECEIVED`, never `AUTHORIZED`; A polls `GET /v1/jobs/{job_id}` until completion/rejection/failure.
- A may query `GET /v1/jobs/{job_id}/result` only once B reports `COMPLETED`; the result includes reproducibility hashes and verified ledger evidence.
- There is **no onchain patient data**, no production medical rights attestation and no third-party scientific execution proof in this MVP.

## 5. Minimum joint sign-off

1. A can complete discovery/rights/quote/mandate against B's real HTTP service.
2. A sends **one genuine XRPL Testnet payment** under the approved quote.
3. B verifies the payment using its own configured RPC, then produces actual statistics on synthetic data.
4. A crash/restart or HTTP timeout does not trigger duplicate signing, payment or execution.
5. B denies wrong-asset, unvalidated, reused or unauthorized payments, visibly and predictably.

See [contract tests](../contracts/README.md) and [MVP acceptance tests](DEMO.md).
