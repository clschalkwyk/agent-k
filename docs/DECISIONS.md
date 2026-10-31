# Architecture Decision Record (ADR) log

## ADR-001 — XRPL only for hackathon (accepted)
Use XRPL Testnet for settlement; no BOT Chain. Reason: concentrate on sponsor-aligned Agentic Finance demonstration, reduce integration risk. Revisit only after the MVP.

## ADR-002 — Two DDD bounded domains (accepted)
Procurement (A) and Fulfilment (B), connected by versioned HTTP contracts. No shared persistence or direct database access. B owns rights, quotes, execution and independent payment validation.

## ADR-003 — Synthetic data only (accepted)
No real medical/patient datasets or credentials. Mock providers supply realistic metadata and restrictions; actual statistical code runs on synthetic fixtures.

## ADR-004 — Policy outside LLM (accepted)
LLM may parse goals/rank datasets; machine-readable rules and trusted backend enforce rights, budgets and payment validation.

## ADR-005 — No simulated payments represented as real (accepted)
Use a genuine XRPL Testnet transaction in demo. Confirm whether RLUSD is realistically usable on testnet; otherwise use XRP and label it accurately.

## ADR-006 — Trust and failure semantics (accepted)
The demo is a coordinated trusted workflow, not atomic payment-for-delivery or cryptographically proven computation. Processor verifies actual ledger status before executing. Handle retries and failures without duplicate payments.

## ADR-007 — Infrastructure deliberately minimal (proposed)
Python FastAPI services, React/Vite web, SQLite and Docker Compose. No queue, Kubernetes, cross-chain bridge or live patient integrations for the MVP.

## ADR-008 — Shared API 0.1.0 freeze (proposed in contract PR)

OpenAPI 3.1 at `contracts/openapi.yaml` owns wire shapes; `docs/API-CONTRACT.md` owns runtime invariants. Keep all nine draft routes and the A/B boundary. Choose one quote-binding memo format, closed input objects, authenticated human-only mandate creation, quote-bound mandates with cumulative request reservations, independent B verification, globally unique payment/quote claims and durable POST idempotency. Payment evidence is output-only; incoming jobs carry an untrusted hash/network reference. Synthetic XRP fixtures are not wallet configuration or proof of asset readiness. Issued assets remain gated on explicit verification. Merge establishes the stage-0 contract freeze; later breaking changes require joint review/versioning.
