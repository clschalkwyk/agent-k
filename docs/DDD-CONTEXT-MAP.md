# Agent K — DDD context map (XRPL-only)

**Status:** Implementation reference, aligned to [OpenAPI 0.1.0](../contracts/openapi.yaml) and [normative runtime rules](API-CONTRACT.md).
**Owners:** Developer A — Procurement; Developer B — Fulfilment.
**Purpose:** Show domain ownership, trusted infrastructure, and *which* interfaces cross the developer boundary. This is a **context/component map**, not a call-order diagram.

## 1. Bounded contexts and integration topology

\`\`\`mermaid
flowchart LR
  USER(["Researcher"])

  subgraph A["Developer A — PROCUREMENT bounded context"]
    direction TB
    UI["Research Web UI"]
    AAPI["Research API<br/>requests · plans · mandates"]
    PLAN["Research Planner<br/>selection and explanation"]
    ORCH["Workflow Orchestrator<br/>state and reconciliation"]
    MANDATE["Spending Mandate<br/>trusted policy and signer"]
    APORT["Fulfilment client / ACL<br/>OpenAPI DTO translation"]
    ADB[("Procurement store<br/>request · plan · mandate · payment")]
    UI --> AAPI
    AAPI --> PLAN
    AAPI --> ORCH
    PLAN --> APORT
    ORCH --> APORT
    ORCH --> MANDATE
    ORCH --> ADB
    MANDATE --> ADB
  end

  subgraph B["Developer B — FULFILMENT bounded context"]
    direction TB
    BAPI["Fulfilment API<br/>only public entrypoint"]
    CAT["Offerings Catalogue"]
    RIGHTS["Rights Policy Engine"]
    QUOTE["Quote Service"]
    JOB["Job / Execution Service"]
    VERIFY["XRPL Payment Verifier"]
    EXEC["Synthetic Research Executor"]
    PROV["Provenance Builder"]
    BDB[("Fulfilment store<br/>offers · policy · quote · job · payment claim")]
    DATA[("Synthetic dataset fixtures")]
    BAPI --> CAT
    BAPI --> RIGHTS
    BAPI --> QUOTE
    BAPI --> JOB
    QUOTE --> RIGHTS
    QUOTE --> BDB
    JOB --> VERIFY
    JOB --> EXEC
    JOB --> BDB
    EXEC --> DATA
    EXEC --> PROV
    PROV --> BDB
  end

  XRPL[("XRPL Testnet<br/>shared external ledger")]

  USER -->|"C1: research and approval"| UI
  APORT <-->|"C2 / C3 / C4 / C6 / C9<br/>versioned HTTP JSON"| BAPI
  MANDATE -->|"C5: signed Payment via XRPL RPC"| XRPL
  VERIFY -->|"C7: independent validated-tx lookup"| XRPL
  BAPI -->|"C9: result DTO and provenance"| APORT

  classDef a fill:#173b61,color:#ffffff,stroke:#4c95ce
  classDef b fill:#155c50,color:#ffffff,stroke:#39b29d
  classDef ext fill:#594087,color:#ffffff,stroke:#b6a2e6
  class AAPI,PLAN,ORCH,MANDATE,APORT,ADB,UI a
  class BAPI,CAT,RIGHTS,QUOTE,JOB,VERIFY,EXEC,PROV,BDB,DATA b
  class XRPL ext
\`\`\`

> **Boundary rule:** all cross-domain communication goes through B's versioned Fulfilment API. The XRPL ledger is not a third bounded context, not a message bus and not a shared service database. Both developers independently integrate with it.

### Domain responsibility and language

| Procurement (A) | Fulfilment (B) | Contract translation |
|---|---|---|
| \`ResearchRequest\` | \`Offering\` / coverage | A converts goal/variables to catalogue filters and an evaluated offer |
| \`ProcurementPlan\` | \`RightsDecision\` | B evaluates declared rights; A may rank only eligible offerings |
| \`SpendingMandate\` | \`Quote\` | A approves *buying*; B declares *price, terms and provider eligibility* |
| \`PaymentInstruction\` / \`PaymentReference\` | \`PaymentEvidence\` | A sends only lookup reference; B independently reads XRPL and derives evidence |
| \`ResearchMission\` (orchestrated state) | \`Job\` (execution state) | Correlate via \`request_id\`, \`quote_id\`, \`job_id\` |
| Dashboard projection | \`Result\` / \`Provenance\` | B produces evidence; A presents it |

There is **no shared aggregate named Job** across the two domains. A owns its own mission state; B owns its own processing job. Each context may use its own persistence and internal models.

## 2. Wire contracts crossing A ↔ B

All operations below terminate at **B's single external service boundary**; subcomponents are B-internal.

| ID | Caller → implementer | Interconnect | API / data contract |
|---|---|---|---|
| C1 | Researcher → A | HTTPS/JSON | \`POST /v1/research-requests\`, \`POST /v1/plans\`, \`POST /v1/mandates\` |
| C2 | A → B | HTTP GET | \`GET /v1/offerings\` → \`OfferingList\` |
| C3 | A → B | HTTP POST | \`POST /v1/rights/evaluate\` → \`RightsDecision\` (\`allowed\` true/false) |
| C4 | A → B | HTTP POST | \`POST /v1/quotes\` → immutable \`Quote\`, including price, network, payer, destination, reference and terms hash |
| C5 | A → XRPL | signed transaction over RPC | XRP or properly configured issued-token \`Payment\`; A stores signed TX/hash before submit |
| C6 | A → B | HTTP POST | \`POST /v1/jobs\` with \`JobCreate\` and \`payment_reference\`; HTTP 202 means intake only |
| C7 | B → XRPL | **read-only** RPC | Fetch independent validated transaction + metadata; verify quote binding and delivered amount |
| C8 | B Job → B Executor | internal function or worker command | Approved execution specification and immutable dataset/code identity, **not public API** |
| C9 | A → B | HTTP GET | \`GET /v1/jobs/{job_id}\` and \`GET /v1/jobs/{job_id}/result\` → \`Job\`, \`Result\` |
| C10 | A → Researcher | HTTPS/JSON | UI projection of state, result and proofs; no direct B database access |

**OpenAPI is normative for payload shapes and response codes**: [\`contracts/openapi.yaml\`](../contracts/openapi.yaml). The table above is an ownership index, not a competing API definition. All POSTs carry \`Idempotency-Key\`; authenticated object access and correlation handling follow [API-CONTRACT.md](API-CONTRACT.md).

## 3. Cross-context invariants

1. **Quote is the commercial boundary.** B alone issues an immutable, quote-bound offer. A never supplies its own price, service policy, or payment destination.
2. **Mandate != data licence.** A can approve spending only. B evaluates whether the requested use/operation is permitted and rechecks at admission/execution.
3. **Payment is out-of-band ledger infrastructure.** A signs/submits; B independently verifies using its own pinned Testnet RPC, never accepting \`paid: true\` or A's RPC response.
4. **Quote ↔ transaction binding.** Follow the existing [memo binding convention](API-CONTRACT.md#quote-binding-and-expiry), exact currency/issuer and delivered amount; no raw patient/research content on XRPL.
5. **No double purchase or double execution.** A persists signed transaction identity and reservations; B atomically binds \`quote_id\` + \`job_id\` + \`xrpl_tx_hash\` with replay protection.
6. **Execution authority is local to B.** B denies unpaid, out-of-policy, expired or mismatched jobs. A cannot bypass B by invoking the processor directly.
7. **No atomic payment-for-service guarantee.** Processing failures after payment require explicit exception handling; the demo does not implement generic trustless escrow or automatic refunds.

## 4. Developer handover tests

**Dev A's mock:** B endpoints returning offers, rights allow/deny, immutable quote, job state, and result. A demonstrates UI → mandate → one actual Testnet Payment → recovery without duplicate signing.

**Dev B's mock:** standalone HTTP client (no A service) able to discover offers, evaluate rights, issue a quote, and submit a job with a **genuinely validated Testnet transaction**. B demonstrates independent ledger verification, exact-quote matching, replay rejection, real synthetic statistical result and provenance.

**Joint integration:** a single happy path and a negative path work from a clean checkout. See [execution sequence](EXECUTION-SEQUENCE.md) and [acceptance tests](DEMO.md).
