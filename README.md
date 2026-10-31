# Agent K — Autonomous Research Data Brokerage

**W3Node 2026 · Agentic Finance / XRPL · Two-developer MVP**

Agent K turns a research objective and a delegated budget into a traceable workflow: discover candidate datasets, evaluate scientific fit and usage rights, select a provider, purchase permitted access using **XRPL Testnet**, run an actual analysis on **synthetic data**, and deliver results with payment and provenance evidence.

> **Mission:** Research request → discovery → rights evaluation → quote → human approval → XRPL payment → independently verified fulfilment → reproducible result.

## Scope / truthfulness

- **XRPL only.** No BOT Chain or EVM contracts in this MVP.
- **Synthetic datasets and mocked commercial catalogues**; no patient records or genuine medical-data licences.
- **Actual XRPL Testnet settlement** is required for the demo; never imply testnet funds have cash value.
- A policy check is an evaluation of machine-readable declared terms, **not** proof of patient consent or regulatory compliance.
- A validated XRPL transaction proves payment, **not** delivery or scientific correctness.
- The execution service must reject unauthorised or unpaid jobs; an LLM must never control wallet signing policy.

## Developer ownership

| Developer A — Procurement | Developer B — Fulfilment |
| --- | --- |
| Research-request UI and schema | Provider/dataset catalogue |
| Research planning / broker agent | Search and dataset suitability metadata |
| Spending mandate and approval | Deterministic rights engine |
| XRPL wallet, payment, reconciliation | Quotes, job intake and payment verification |
| End-to-end orchestrator and dashboard | Statistical processing and provenance |

**Boundary:** A owns the purchase decision and submitting payment. B owns offering eligibility, service delivery, and **independent payment verification**. Neither service trusts a caller-supplied `paid: true`.

## Planning and execution

- [Architecture and bounded contexts](docs/ARCHITECTURE.md)
- [Execution strategy and two-developer milestones](docs/EXECUTION.md)
- [OpenAPI 3.1 contract](contracts/openapi.yaml)
- [Contract fixtures and independent test suites](contracts/README.md)
- [HTTP runtime rules and state transitions](docs/API-CONTRACT.md)
- [Demo script and acceptance checklist](docs/DEMO.md)
- [Engineering decisions](docs/DECISIONS.md)

## Proposed repository shape

```text
apps/web/                  # A: research UI
services/procurement/      # A: planning, mandate, XRPL
services/fulfilment/       # B: catalogue, policy, execution
contracts/                 # shared OpenAPI / JSON Schema
fixtures/synthetic/        # B: synthetic demo datasets
tests/e2e/                 # joint happy path and failure paths
docs/                      # product and technical agreements
```

Suggested stack: React/TypeScript UI, Python FastAPI services, Pydantic/OpenAPI contracts, SQLite, pandas/SciPy, and `xrpl-py`. These are proposals, not dependencies already installed.

## Definition of done

A judge can submit one research objective, see three candidate offerings (including an ineligible one), approve a bounded purchase, watch a **validated XRPL Testnet payment**, and receive a computed statistical result plus an auditable provenance manifest.

**Build rule:** one finished vertical slice beats ten mocked features. Details live in `docs/EXECUTION.md`.
