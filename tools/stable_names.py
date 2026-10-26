"""Moves each inline object schema of the spec into components/schemas, under a name from its operation or component.

mopenapi 2.4 names an inline object after its field names and tries 19 numbered names when that name is taken.
The 21st different `{data: ...}` answer gets the 20th one's record, so its method decodes the answer into the wrong
record and reports no error. A record with a schema name never takes that path.
As in mopenapi, a schema with properties is a record; a union or a nullable array is a variant, so it stays inline.
A string enum gets the same kind of name as its format, which mopenapi reads as the type name instead of TEnumN.
generate.sh runs this before mopenapi. A shape it cannot name stops the script.
"""
import copy
import json
import re
import sys
from pathlib import Path

METHODS = ('get', 'put', 'post', 'delete', 'options', 'head', 'patch', 'trace')
LONGEST = 70


def pascal(name):
    return ''.join(part[:1].upper() + part[1:] for part in re.split(r'[^A-Za-z0-9]+', name))


def is_record(schema):
    return bool(schema.get('properties'))


def inline_objects(node):
    if isinstance(node, dict):
        return ('$ref' not in node and is_record(node)) or any(inline_objects(value) for value in node.values())
    return isinstance(node, list) and any(inline_objects(value) for value in node)


class Namer:
    def __init__(self, spec):
        self.schemas = spec['components']['schemas']

    def fields(self, schema, name):
        if inline_objects(schema.get('allOf')):
            raise ValueError(f'{name}: mopenapi merges an inline object inside allOf under a name from its fields.')
        for field, value in schema.get('properties', {}).items():
            schema['properties'][field] = self.place(value, name + pascal(field))

    def place(self, schema, name):
        if '$ref' in schema:
            return schema
        if schema.get('type') == 'array' and 'items' in schema:
            schema['items'] = self.place(schema['items'], name + 'Item')
            return schema
        if schema.get('type') == 'string' and 'enum' in schema:
            schema.setdefault('format', name)
            return schema
        if not is_record(schema):
            self.fields(schema, name)
            return schema
        if name in self.schemas:
            raise ValueError(f'{name}: the spec already has a schema with this name.')
        if len(name) > LONGEST:
            raise ValueError(f'{name}: mopenapi numbers a type name longer than {LONGEST} characters.')
        self.schemas[name] = schema
        self.fields(schema, name)
        return {'$ref': f'#/components/schemas/{name}'}

    def operation(self, operation, where):
        if 'operationId' not in operation:
            raise ValueError(f'{where}: no operationId to name its records after.')
        name = pascal(operation['operationId'])
        for parameter in operation.get('parameters', []):
            if 'schema' in parameter:
                parameter['schema'] = self.place(parameter['schema'], name + pascal(parameter['name']))
        answers = {}
        for code, response in operation.get('responses', {}).items():
            content = response.get('content', {}).get('application/json', {})
            if 'schema' not in content:
                continue
            if not code.startswith('2'):
                if inline_objects(content['schema']):
                    raise ValueError(f'{name}: the {code} answer has an inline object.')
                continue
            answers[code] = content
        if len({json.dumps(content['schema'], sort_keys=True) for content in answers.values()}) > 1:
            raise ValueError(f'{name}: the success answers {sorted(answers)} differ, and a method returns one record.')
        placed = None
        for content in answers.values():
            placed = placed or self.place(content['schema'], f'{name}Response')
            content['schema'] = placed
        body = operation.get('requestBody', {}).get('content', {}).get('application/json', {})
        if 'schema' in body:
            body['schema'] = self.place(body['schema'], f'{name}Request')


def stable_names(spec):
    spec = copy.deepcopy(spec)
    namer = Namer(spec)
    for name, schema in list(namer.schemas.items()):
        namer.fields(schema, name)
    for name, response in spec['components'].get('responses', {}).items():
        if inline_objects(response):
            raise ValueError(f'{name}: the shared answer has an inline object.')
    for path, items in spec['paths'].items():
        for method in METHODS:
            if method in items:
                namer.operation(items[method], f'{method} {path}')
    return spec


if __name__ == '__main__':
    source, target = sys.argv[1:3]
    Path(target).write_text(json.dumps(stable_names(json.loads(Path(source).read_text())), indent=2))
