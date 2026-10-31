"""Offline consumer/provider wire compatibility. No service or ledger required."""
import copy
import hashlib
import json
from pathlib import Path

import pytest
import yaml
from jsonschema import Draft202012Validator, FormatChecker, ValidationError
from openapi_spec_validator import validate as validate_openapi

ROOT = Path(__file__).resolve().parents[2]
SPEC = yaml.safe_load((ROOT / 'contracts/openapi.yaml').read_text())
FIXTURES = json.loads((ROOT / 'contracts/fixtures/objects.json').read_text())

def validator(schema):
    # Root components make local refs resolvable without network resolution.
    return Draft202012Validator(
        {**schema, 'components': SPEC['components']}, format_checker=FormatChecker())

def validate(name, value):
    validator({'$ref': '#/components/schemas/' + name}).validate(value)

def operations():
    for path, item in SPEC['paths'].items():
        for method, op in item.items():
            yield path, method, op

def resolve(ref):
    assert ref.startswith('#/'), 'Contract must be self-contained'
    node = SPEC
    for part in ref[2:].split('/'):
        node = node[part.replace('~1', '/').replace('~0', '~')]
    return node

def test_openapi_and_all_json_schemas():
    validate_openapi(SPEC)
    for schema in SPEC['components']['schemas'].values():
        Draft202012Validator.check_schema(schema)

def test_every_reference_resolves():
    def walk(node):
        if isinstance(node, dict):
            if '$ref' in node:
                resolve(node['$ref'])
            for value in node.values():
                walk(value)
        elif isinstance(node, list):
            for value in node:
                walk(value)
    walk(SPEC)

@pytest.mark.parametrize('name', FIXTURES)
def test_shared_fixtures(name):
    validate(name, FIXTURES[name])

def test_all_http_examples_and_error_status_codes():
    for _, method, op in operations():
        if method == 'post':
            body = op['requestBody']['content']['application/json']
            validator(body['schema']).validate(body['example'])
        for response in op['responses'].values():
            response = resolve(response['$ref']) if '$ref' in response else response
            body = response['content']['application/json']
            validator(body['schema']).validate(body['example'])
            assert 'X-Correlation-ID' in response['headers']

def test_endpoint_ownership_auth_and_idempotency():
    assert len(list(operations())) == 9
    ids = []
    for path, method, op in operations():
        ids.append(op['operationId'])
        expected = 'Procurement' if path in ['/v1/research-requests', '/v1/plans', '/v1/mandates'] else 'Fulfilment'
        assert op['x-owner'] == expected
        assert op.get('security', SPEC['security']) == [{'BearerAuth': []}]
        params = [resolve(p['$ref']) if '$ref' in p else p for p in op['parameters']]
        if method == 'post':
            assert any(p['name'] == 'Idempotency-Key' and p['required'] for p in params)
        if '{job_id}' in path:
            assert any(p['name'] == 'job_id' and p['in'] == 'path' and p['required'] for p in params)
    assert len(ids) == len(set(ids))

@pytest.mark.parametrize('value', [0, 3.5, '0', '0.000000', '-1', '+1', '1e3', '01', '1.', '.5', '0.0000001', 'NaN', ' 1'])
def test_reject_invalid_xrp_money(value):
    with pytest.raises(ValidationError):
        validate('Money', {'currency': 'XRP', 'value': value})

@pytest.mark.parametrize('value', ['0.000001', '1', '3.500000', '99999999999.999999'])
def test_accept_exact_xrp_money(value):
    validate('Money', {'currency': 'XRP', 'value': value})

@pytest.mark.parametrize('payload', [
    {'currency':'XRP','value':'1','issuer':'rrrrrrrrrrrrrrrrrrrrBZbvji'},
    {'currency':'USD','value':'1'},
    {'currency':'RLUSD','value':'1','issuer':'rrrrrrrrrrrrrrrrrrrrBZbvji'},
    {'currency':'0'*40,'value':'1','issuer':'rrrrrrrrrrrrrrrrrrrrBZbvji'},
    {'currency':'USD','value':'1','issuer':'<verified-testnet-issuer-address>'},
])
def test_reject_ambiguous_assets(payload):
    with pytest.raises(ValidationError):
        validate('Money', payload)

@pytest.mark.parametrize('name,field,value', [
    ('JobCreate','paid',True), ('JobCreate','validated',True),
    ('JobCreate','price',{'currency':'XRP','value':'1'}),
    ('PaymentReference','validated',True), ('PaymentReference','network','mainnet'),
    ('PaymentReference','xrpl_tx_hash','fake'),
    ('QuoteCreate','price',{'currency':'XRP','value':'1'}),
    ('QuoteCreate','destination','attacker'), ('QuoteCreate','rights_decision',{'allowed':True}),
    ('MandateCreate','approved_by','agent'), ('MandateCreate','status','APPROVED'),
    ('MandateCreate','wallet_seed','secret'),
    ('RightsDecision','code','RIGHTS_DENIED'),
    ('ResearchRequestCreate','variables',['bmi','bmi']),
    ('ResearchRequestCreate','max_budget',{'currency':'XRP','value':20}),
    ('Quote','expires_at','2026-11-14T12:00:00+02:00'),
    ('Quote','expires_at','2026-02-30T12:00:00Z'),
    ('Quote','terms_hash','short'),
    ('Result','synthetic',False), ('Result','network','mainnet'),
])
def test_security_and_validation_mutations(name, field, value):
    body = copy.deepcopy(FIXTURES[name]); body[field] = value
    with pytest.raises(ValidationError):
        validate(name, body)

@pytest.mark.parametrize('name', ['JobCreate','QuoteCreate','MandateCreate','ResearchRequestCreate'])
def test_required_write_fields(name):
    for field in SPEC['components']['schemas'][name]['required']:
        body = copy.deepcopy(FIXTURES[name]); del body[field]
        with pytest.raises(ValidationError):
            validate(name, body)

def test_job_state_shapes():
    for status in ['RECEIVED','VERIFYING','AUTHORIZED','RUNNING','COMPLETED','REJECTED','FAILED']:
        job = {**FIXTURES['Job'], 'status':status}
        if status == 'COMPLETED':
            with pytest.raises(ValidationError): validate('Job', job)
            job['result_path'] = '/v1/jobs/job-001/result'
        if status in ['REJECTED','FAILED']:
            with pytest.raises(ValidationError): validate('Job', job)
            job['error'] = FIXTURES['Error']
        validate('Job', job)
        bad = {**job, 'error':FIXTURES['Error']} if status not in ['REJECTED','FAILED'] else {**job, 'result_path':'/v1/jobs/job-001/result'}
        with pytest.raises(ValidationError): validate('Job', bad)

def test_fixture_links_and_hashes():
    f = FIXTURES
    q = f['Quote']; job = f['JobCreate']; p = f['Provenance']
    for key in ['request_id','quote_id','offer_id','purpose','operation','parameters']:
        assert job[key] == q[key] == p[key]
    assert q['reference'] == q['quote_id'] == p['payment']['reference']
    assert q['rights_decision']['allowed']
    assert q['rights_decision'] == p['rights_decision']
    assert q['price'] == p['payment']['delivered_amount']
    assert q['payer'] == p['payment']['payer']
    assert q['destination'] == p['payment']['destination']
    assert f['Result']['provenance'] == p
    digest = hashlib.sha256((ROOT/'contracts/fixtures/synthetic-cohort.csv').read_bytes()).hexdigest()
    assert q['dataset_hash'] == p['dataset_hash'] == digest
    # These fixtures contain only RFC8785-compatible simple numbers and ASCII keys.
    def digest_json(value):
        return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=False).encode()).hexdigest()
    assert q['terms_hash'] == digest_json({k:v for k,v in q.items() if k != 'terms_hash'})
    assert p['terms_hash'] == q['terms_hash']
    assert p['output_hash'] == digest_json(f['AnalysisResult'])
    assert len(f['OfferingList']['items']) == 3
    assert any('academic_research' not in o['rights']['allowed_purposes'] for o in f['OfferingList']['items'])

def test_safety_vectors_cover_both_owners_and_required_gates():
    cases = json.loads((ROOT/'contracts/fixtures/safety-cases.json').read_text())
    assert len({c['id'] for c in cases}) == len(cases)
    for stream in ['procurement','fulfilment']:
        assert any(c['stream'] == stream for c in cases)
    for code in ['OVER_BUDGET','RIGHTS_DENIED','QUOTE_EXPIRED','PAYMENT_UNVALIDATED','PAYMENT_MISMATCH','PAYMENT_REPLAY','IDEMPOTENCY_CONFLICT','PROCESSING_FAILED']:
        assert any(c['expected']['code'] == code for c in cases)
    for case in cases:
        expected = case['expected']
        assert expected['signatures'] >= 0 and expected['executions'] >= 0
        if case['stream'] == 'fulfilment':
            assert expected['signatures'] == 0
        if case['stream'] == 'procurement':
            assert expected['executions'] == 0
