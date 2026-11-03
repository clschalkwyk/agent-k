"""Run with AGENT_K_STREAM and AGENT_K_ADAPTER; see contracts/README.md.

No built-in passing mock: results must come from a developer's implementation.
"""
import importlib
import json
import os
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
CASES = json.loads((ROOT/'contracts/fixtures/safety-cases.json').read_text())
STREAM = os.environ.get('AGENT_K_STREAM')
ADAPTER = os.environ.get('AGENT_K_ADAPTER')
# Explicit invocation must fail if setup is missing, rather than silently skip P0 checks.
if STREAM not in ('procurement', 'fulfilment') or not ADAPTER:
    raise pytest.UsageError('Set AGENT_K_STREAM=procurement|fulfilment and AGENT_K_ADAPTER=module:factory; for offline tests select test_schema.py')

@pytest.fixture
def adapter():
    module, factory = ADAPTER.split(':', 1)
    return getattr(importlib.import_module(module), factory)()

@pytest.mark.parametrize('case', [c for c in CASES if c['stream'] == STREAM], ids=lambda c: c['id'])
def test_implementation_safety(adapter, case):
    fixtures = json.loads((ROOT/'contracts/fixtures/objects.json').read_text())
    # Do not expose the expected result to the implementation adapter.
    observed = adapter.run_case({k:v for k,v in case.items() if k != 'expected'}, fixtures)
    assert isinstance(observed, dict), 'Adapter must return observed outcomes and spy counters'
    for key, expected in case['expected'].items():
        assert key in observed, f'Missing observation: {key}'
        assert observed[key] == expected, f'{case["id"]}: {key}'
