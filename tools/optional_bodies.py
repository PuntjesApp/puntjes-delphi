"""Adds an overload with no body to each client method whose request body the spec does not mark required.

mopenapi makes every body a required Payload argument, also when the spec says `required` is false or absent.
The overload sends the request with no body, so a call without a payload compiles and works as before.
generate.sh runs this after mopenapi. A generated shape it does not know stops the script.
"""
import json
import re
import sys
from pathlib import Path

PAYLOAD = r',\n    Payload, (?:result, TypeInfo\(\w+\), (TypeInfo\(\w+\))|\{dummy:\}self, TypeInfo\(\w+\), nil)'
METHODS = ('get', 'put', 'post', 'delete', 'options', 'head', 'patch', 'trace')


def optional_bodies(spec):
    found = []
    for path, operations in spec['paths'].items():
        for method in METHODS:
            body = operations.get(method, {}).get('requestBody')
            if body is None:
                continue
            if '$ref' in body:
                body = spec['components']['requestBodies'][body['$ref'].rsplit('/', 1)[1]]
            if body.get('required') is not True:
                found.append((operations[method]['operationId'], method, path))
    return found


def without_payload(declaration, name):
    result, count = re.subn(r';\s*const Payload: \w+|const Payload: \w+;\s*|const Payload: \w+', '', declaration)
    if count != 1:
        raise ValueError(f'{name}: the declaration has no single "const Payload" parameter.')
    return re.sub(r'\(\s+', '(', result)


def one(pattern, text, name, what):
    matches = list(re.finditer(pattern, text, re.M | re.S))
    if len(matches) != 1:
        raise ValueError(f'{name}: found {len(matches)} {what}, expected 1.')
    return matches[0]


def overload(text, operation_id, method, path):
    name = operation_id[0].upper() + operation_id[1:]
    split = text.index('\nimplementation\n')
    interface, implementation = text[:split], text[split:]

    comment = one(rf'^    // {re.escape(operation_id)} \[{method}\] {re.escape(path)}$', interface, operation_id,
                  'operation comments')
    declaration = one(rf'^    (function|procedure) {name}\([^)]*\)(: \w+)?;$', interface[comment.end():], name,
                      'declarations')
    end = comment.end() + declaration.end()
    short = without_payload(declaration.group(0), name)
    interface = (f'{interface[:end]} overload;\n    // The same call with no request body.\n{short} overload;'
                 f'{interface[end:]}')

    body = one(rf'^(function|procedure) TPuntjesClient\.{name}\([^)]*\)(: \w+)?;\nbegin\n.*?\nend;\n',
               implementation, name, 'implementations')
    call, count = re.subn(PAYLOAD, lambda m: f',\n    result, {m.group(1)}' if m.group(1) else '', body.group(0))
    if count != 1:
        raise ValueError(f'{name}: the Request call does not pass the Payload as mopenapi 2.4 does.')
    header, rest = call.split('\nbegin\n', 1)
    copy = f'{without_payload(header, name)}\nbegin\n{rest}'
    implementation = f'{implementation[:body.end()]}\n{copy}{implementation[body.end():]}'
    return interface + implementation


def make_optional(text, spec):
    for operation in optional_bodies(spec):
        text = overload(text, *operation)
    return text


if __name__ == '__main__':
    spec_path, unit_path = sys.argv[1:3]
    unit = Path(unit_path)
    unit.write_text(make_optional(unit.read_text(), json.loads(Path(spec_path).read_text())))
