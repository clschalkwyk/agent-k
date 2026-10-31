# Shared contract development kit

`openapi.yaml` is the frozen-wire proposal for API 0.1.0; merge through the normal PR review. [Runtime rules](../docs/API-CONTRACT.md) are normative alongside schemas. Neither service imports the other service or shares its database.

## Offline tests: either developer, no services or wallets

From the repository root, Python 3.12:

```sh
python -m venv .venv
. .venv/bin/activate
python -m pip install -r contracts/requirements.txt
python -m pytest -q tests/contracts/test_schema.py
```

CI runs the same command. It validates OpenAPI structure, all local references, every HTTP example, shared fixtures, error mappings, owner/auth/key metadata, required fields and adversarial schema mutations. `jsonschema` uses Draft 2020-12 **with format checking enabled**; merely checking a date regex is insufficient.

For either a consumer mock or a provider payload:

```sh
python contracts/validate_payload.py JobCreate /path/to/job.json
```

Exit 0 = schema-valid; nonzero = invalid. Use `ResearchRequestCreate`, `Offering`, `UsageRights`, `Quote`, `PaymentReference`, `Job`, `Result`, etc. Validate response bodies too. Unknown fields are rejected. This is a wire validator, not a rights, wallet or ledger verifier.

`fixtures/objects.json` maps schema names to reusable values. `fixtures/synthetic-cohort.csv` provides four explicitly synthetic rows. Three offerings have different prices; one permits commercial research only. Quote/dataset/output hashes are recomputed and checked. The result's exact two-sided Mann–Whitney U value is illustrative for the four rows; service implementation must reproduce it using pinned statistical code. Fixture code hash, ledger index and transaction hash are deliberate test values, not payment or runtime evidence.

The two `r...` account values are XRPL reserved account **sentinels**. They satisfy lexical shape but must be rejected by runtime configuration. They are not funded wallets, destinations or issuers. No issued-asset issuer address is provided. Never submit transactions using fixture accounts. JSON Schema cannot verify address checksum, issuer availability, funded balances, ownership, cross-field equalities, chronological ordering, atomicity or ledger finality.

## Implementation safety suites: independent streams

The 46 vectors in `fixtures/safety-cases.json` are acceptance inputs, not a replacement implementation. Each owner supplies a small adapter wrapping their *real* service/domain handlers with controlled dependencies. There is intentionally no built-in mock that makes these tests green without implementing safety controls.

```sh
# A: human approvals, atomic budget reservation, trusted signer and reconciliation
AGENT_K_STREAM=procurement AGENT_K_ADAPTER=your_tests.contract_adapter:make_adapter \
  python -m pytest -q tests/contracts/test_service_safety.py

# B: HTTP admission, own RPC verifier, quote/policy store, replay guard, executor
AGENT_K_STREAM=fulfilment AGENT_K_ADAPTER=your_tests.contract_adapter:make_adapter \
  python -m pytest -q tests/contracts/test_service_safety.py
```

Put the adapter module on PYTHONPATH, or install the owning package. Explicit safety-suite invocation without both variables fails collection instead of silently skipping P0 tests. The default offline CI selects only `test_schema.py`; add the appropriate safety invocation to each service's CI when its adapter exists. Do not use an unconditional repository-wide pytest command until a stream/adapter is supplied.

Adapter interface (test-only):

```python
class Adapter:
    def run_case(self, case: dict, fixtures: dict) -> dict:
        # Reset independent stores, inject deterministic clock/RPC/policy/spy ports,
        # apply case['given'], call real handlers, then report observed effects.
        ...

def make_adapter():
    return Adapter()
```

The runner removes `expected` before invoking your adapter. Do not branch on case ID or return canned outcomes. Record signature, submitted-payment, ledger-fetch, execution and job-insert counters at actual dependency boundaries. Map HTTP errors or terminal Job.error codes into `code`; positive signing uses `SPEND_AUTHORIZED`, completed execution uses `COMPLETED`. These two positive labels are **test outcomes**, not HTTP error codes. Multi-call cases report the last/conflicting outcome and cumulative effects. Verify no execution on rejected payment even when the RPC or executor is slow. Each case resets state; use barriers/parallel calls for concurrency cases, not sequential retries.

### Baseline world and override semantics

- Clock `2026-11-14T11:01:00Z`; ledger close time `2026-11-14T11:00:30Z`. Seed request/quote/mandate from objects.json; rights permitted, configured asset XRP, configuration verified, human owner `human-001`, policy current, no existing claims/spend/reservations, fee 10 drops, sufficient balance/reserves.
- Replace reserved address sentinels with locally generated checksum-valid **offline test accounts** consistently across quote, mandate ownership and mocked RPC; never use a live wallet. Recompute quote terms hash after legitimate setup changes. B's mock RPC returns Payment, requested hash, Testnet, validated=true, tesSUCCESS, ledger_index 12345, baseline close time, exact quote payer/destination/delivered amount and one correctly encoded quote memo. No partial-payment flag, SendMax, Paths or destination tag.
- The only ledger facts come through B's injected RPC client; `procurement_claims_valid` must have no effect on that client. `extra_http_fields` are sent to real HTTP/schema admission. For admitted valid cases drain the worker through completion. For unvalidated/transient verification, stop after one verification attempt and report its error/remaining gate with zero executions.
- `per_purchase_limit`, `total_limit`, `request_budget`, `request_spent`, `request_reserved`, `reserved`, `fee_drops` are exact decimal/drops strings. `reserved` applies to the mandate; request_* applies cumulatively across mandates. `provider_allowlist`, `now`, `principal_role`, `principal`, `configuration_verified` replace their corresponding trusted-state values. In `authorize_spend`, limits/reservations represent stored state at signer time (even if inconsistent due to revocation/change); signer must recheck, not rely on approval validation.
- `budget_asset` changes mandate asset only. `quote_asset=issued-test-asset` sets quote/mandate/delivered currency to a generic issued test asset with a locally generated **offline** issuer; `delivered_issuer` then swaps only RPC issuer to another local test identity. These symbolic names are not wire currency codes or real issuer addresses. `delivered_asset`, `destination`, `payer` swap only the corresponding RPC fact to a distinct test identity/asset.
- Other ledger overrides: `validated`, `transaction_result`, `transaction_type`, `ledger_network`, `returned_hash`, `ledger_close_time`, `delivered_value`, `transaction_amount`, `delivered_amount`, `omit_delivered_amount`, `partial_payment`, `memo_reference`, `duplicate_binding_memo`, `has_sendmax`, `has_paths`, `rpc_available`. Build the raw RPC response or raise dependency failure at B's RPC boundary, not by supplying HTTP evidence.
- `rights_allowed=false` revokes current B policy; `tx_claimed_by` and `quote_claimed_by` seed durable uniqueness records for another job. `job_bmi_threshold` changes only incoming job parameters. `tampered_terms_hash` corrupts stored quote integrity without recomputing the hash. `processor_crashes` raises from the real execution port after authorization. `omit_idempotency_key` removes that HTTP header.

### Actions

| Action | Required exercise |
|---|---|
| authorize_spend | Invoke A's trusted signing path with stored mandate; count signatures at signing port |
| approve_mandate | Invoke A's human-only POST with indicated principal role |
| retry_payment | Seed previously submitted unknown transaction; invoke retry, reconcile through RPC, count **new** signatures/submissions (zero) |
| concurrent_spend | Two concurrent attempts for the same quote; one signature/submission only |
| verify_and_execute | Invoke B job admission and worker; independent RPC lookup then controlled executor |
| submit_job | Exercise B HTTP authentication/schema/idempotency admission |
| repeat_job | Two POSTs; mutate parameters for changed payload, keep or change key as specified; drain worker; compare initial HTTP status/bodies for identical retries |
| concurrent_jobs | Two valid quotes and different jobs race for one transaction; fixture claim should be made at admission so loser returns PAYMENT_REPLAY and only one job is created/executed |

For concurrent_jobs, bind the mocked ledger payment to the first quote and coordinate both admissions before verification so claim order is deterministic; this tests durable duplicate funding prevention, not a timing lottery. Effects are cumulative per scenario. The signature and execution counts are always asserted; extra expected counters/status/result flags must also be observed. A processing crash counts one execution attempt, FAILED, no result.

These tests cover the contract-relevant portions of AT-02 through AT-09. They cannot certify a live Testnet payment (AT-04), production authentication/configuration, scientific validity or recovery durability by themselves. Exercise real persistence races/restarts and the genuine Testnet demo as separate integration acceptance work.
