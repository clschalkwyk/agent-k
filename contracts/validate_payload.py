"""Usage: python contracts/validate_payload.py JobCreate path/to/payload.json"""
import argparse
import json
from pathlib import Path
import sys
import yaml
from jsonschema import Draft202012Validator, FormatChecker


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('schema')
    parser.add_argument('payload', type=Path)
    args = parser.parse_args()
    spec = yaml.safe_load(Path(__file__).with_name('openapi.yaml').read_text())
    if args.schema not in spec['components']['schemas']:
        parser.error('Unknown schema: ' + args.schema)
    value = json.loads(args.payload.read_text())
    schema = {'$ref': '#/components/schemas/' + args.schema, 'components': spec['components']}
    errors = list(Draft202012Validator(schema, format_checker=FormatChecker()).iter_errors(value))
    for error in errors:
        print(f'{list(error.absolute_path)}: {error.message}', file=sys.stderr)
    return int(bool(errors))


if __name__ == '__main__':
    raise SystemExit(main())
