"""Checks the committed units against spec/api.json: each operation's answer and body record has the spec's fields."""
import json
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RTTI = re.compile(r"^  _(T\w+) = ((?:'[^']*'(?: \+\s*)?)+);", re.M)
OPERATION = re.compile(r"^    // (\w+) \[(\w+)\] (\S+)\n(?:    //.*\n)*    (?:function|procedure) \w+\(([^)]*)\)(?:: (\w+))?;",
                       re.M)


def records(dto):
    found = {}
    for name, text in RTTI.findall(dto):
        fields = ''.join(re.findall(r"'([^']*)'", text)).split()
        found[name] = {}
        i = 0
        while i < len(fields):
            field, kind = fields[i].split(':', 1)
            if kind == 'array':
                kind, i = f'array of {fields[i + 2]}', i + 2
            found[name][field.strip('"')] = kind
            i += 1
    return found


def resolve(spec, schema):
    while '$ref' in schema:
        schema = spec['components']['schemas'][schema['$ref'].rsplit('/', 1)[1]]
    return schema


def mismatches(spec, recs, schema, kind, where):
    schema = resolve(spec, schema)
    item = kind[len('array of '):] if kind.startswith('array of ') else kind.removesuffix('DynArray')
    if schema.get('type') == 'array' or item != kind:
        if not (schema.get('type') == 'array' and item != kind):
            return [f'{where}: the spec has {schema.get("type")}, the unit has {kind}']
        return mismatches(spec, recs, schema['items'], item, f'{where}[]')
    if not schema.get('properties'):
        return []
    fields = recs.get(kind)
    if fields is None:
        return [f'{where}: the spec has an object, the unit has {kind}']
    fields = {name: value for name, value in fields.items() if name != '_'}
    if list(fields) != list(schema['properties']):
        return [f'{where}: {kind} has {list(fields)}, the spec has {list(schema["properties"])}']
    return [problem for name, prop in schema['properties'].items()
            for problem in mismatches(spec, recs, prop, fields[name], f'{where}.{name}')]


def operations(spec, client):
    declared = {match[0]: match for match in OPERATION.findall(client)}
    for path, items in spec['paths'].items():
        for method, operation in items.items():
            yield operation, declared.get(operation['operationId'])


def problems(spec, dto, client):
    recs, found = records(dto), []
    for operation, declared in operations(spec, client):
        name = operation['operationId']
        if declared is None:
            found.append(f'{name}: no client method')
            continue
        params, result = declared[3], declared[4]
        success = [response for code, response in sorted(operation['responses'].items()) if code.startswith('2')]
        schema = success[0].get('content', {}).get('application/json', {}).get('schema') if success else None
        if schema is None:
            if result:
                found.append(f'{name}: the spec has no answer body, the method returns {result}')
        else:
            found += mismatches(spec, recs, schema, result or 'nothing', f'{name} answer')
        body = operation.get('requestBody', {}).get('content', {}).get('application/json', {}).get('schema')
        payload = re.search(r'const Payload: (\w+)', params)
        if body is not None and payload:
            found += mismatches(spec, recs, body, payload.group(1), f'{name} body')
    return found


class GeneratedRecordsTest(unittest.TestCase):
    def test_every_operation_record_has_the_spec_fields(self):
        spec = json.loads((ROOT / 'spec/api.json').read_text())
        dto = (ROOT / 'src/puntjes.dto.pas').read_text()
        client = (ROOT / 'src/puntjes.client.pas').read_text()
        self.assertEqual(problems(spec, dto, client), [])

    def test_a_wrong_answer_record_is_found(self):
        spec = {'components': {'schemas': {'Me': {'type': 'object', 'properties': {'display_name': {}}}}},
                'paths': {'/me': {'get': {'operationId': 'showMe', 'responses': {'200': {'content': {
                    'application/json': {'schema': {'type': 'object', 'properties': {
                        'data': {'$ref': '#/components/schemas/Me'}}}}}}}}}}}
        dto = "  _TWrapper = 'data:TList';\n  _TList = 'data:array of TProduct links:TLinks';\n  _TMe = 'display_name:RawUtf8';\n"
        client = '    // showMe [get] /me\n    //\n    function ShowMe(): TWrapper;\n'
        self.assertEqual(problems(spec, dto, client),
                         ["showMe answer.data: TList has ['data', 'links'], the spec has ['display_name']"])

    def test_an_array_of_scalars_matches_a_dyn_array(self):
        spec = {'components': {'schemas': {}}, 'paths': {'/ids': {'get': {'operationId': 'listIds', 'responses': {
            '200': {'content': {'application/json': {'schema': {'type': 'object', 'properties': {
                'ids': {'type': 'array', 'items': {'type': 'integer'}}}}}}}}}}}}
        client = '    // listIds [get] /ids\n    function ListIds(): TIds;\n'
        self.assertEqual(problems(spec, "  _TIds = 'ids:TIntegerDynArray';\n", client), [])
        self.assertEqual(problems(spec, "  _TIds = 'ids:integer';\n", client),
                         ['listIds answer.ids: the spec has array, the unit has integer'])

    def test_a_missing_method_is_found(self):
        spec = {'paths': {'/health': {'get': {'operationId': 'checkHealth', 'responses': {'200': {}}}}}}
        self.assertEqual(problems(spec, '', ''), ['checkHealth: no client method'])


if __name__ == '__main__':
    unittest.main()
