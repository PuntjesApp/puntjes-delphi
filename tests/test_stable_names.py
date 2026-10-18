import unittest

from tools.stable_names import stable_names

DATA = {'type': 'object', 'properties': {'display_name': {'type': 'string'}}}


def operation(responses, body=None, operation_id='showMe'):
    found = {'operationId': operation_id, 'responses': {
        code: {'content': {'application/json': {'schema': schema}}} for code, schema in responses.items()}}
    if body is not None:
        found['requestBody'] = {'required': True, 'content': {'application/json': {'schema': body}}}
    return found


def spec(paths, schemas=None):
    return {'paths': paths, 'components': {'schemas': schemas or {}}}


def ref(name):
    return {'$ref': f'#/components/schemas/{name}'}


class StableNamesTest(unittest.TestCase):
    def test_names_an_inline_answer_and_its_inline_fields_after_the_operation(self):
        page = {'type': 'object', 'properties': {'data': {'type': 'array', 'items': DATA}, 'total': {'type': 'integer'}}}
        answer = {'type': 'object', 'properties': {'data': page}, 'required': ['data']}
        result = stable_names(spec({'/me': {'get': operation({'200': answer})}}))

        schema = result['paths']['/me']['get']['responses']['200']['content']['application/json']['schema']
        self.assertEqual(schema, ref('ShowMeResponse'))
        schemas = result['components']['schemas']
        self.assertEqual(schemas['ShowMeResponse'], {'type': 'object', 'properties': {'data': ref('ShowMeResponseData')},
                                                     'required': ['data']})
        self.assertEqual(schemas['ShowMeResponseData']['properties']['data'],
                         {'type': 'array', 'items': ref('ShowMeResponseDataDataItem')})
        self.assertEqual(schemas['ShowMeResponseDataDataItem'], DATA)

    def test_names_an_inline_request_body_and_keeps_its_required_flag(self):
        body = {'type': 'object', 'properties': {'products': {'type': 'array', 'items': ref('Product')}}}
        result = stable_names(spec({'/products/batch': {'post': operation({'200': ref('Result')}, body,
                                                                          'bulkUpsertProducts')}}))

        request = result['paths']['/products/batch']['post']['requestBody']
        self.assertEqual(request['content']['application/json']['schema'], ref('BulkUpsertProductsRequest'))
        self.assertIs(request['required'], True)
        self.assertEqual(result['components']['schemas']['BulkUpsertProductsRequest'], body)

    def test_names_an_inline_field_of_a_component(self):
        error = {'type': 'object', 'properties': {'error': {'type': 'object', 'properties': {'code': {}}}}}
        result = stable_names(spec({}, {'ErrorResponse': error}))

        self.assertEqual(result['components']['schemas']['ErrorResponse']['properties']['error'],
                         ref('ErrorResponseError'))
        self.assertEqual(result['components']['schemas']['ErrorResponseError'], {'type': 'object',
                                                                                 'properties': {'code': {}}})

    def test_leaves_a_reference_a_scalar_and_an_object_with_no_fields_as_they_are(self):
        answer = {'type': 'object', 'properties': {'data': ref('Me'), 'meta': {'type': 'object'}, 'n': {'type': 'integer'}}}
        result = stable_names(spec({'/me': {'get': operation({'200': answer})}}))

        self.assertEqual(result['components']['schemas']['ShowMeResponse'], answer)

    def test_names_a_nullable_inline_object_as_mopenapi_makes_it_a_record(self):
        nullable = dict(DATA, type=['object', 'null'])
        result = stable_names(spec({'/me': {'get': operation({'200': {'type': 'object', 'properties': {
            'data': nullable}}})}}))

        self.assertEqual(result['components']['schemas']['ShowMeResponseData'], nullable)

    def test_leaves_an_object_inside_a_union_or_a_nullable_array_inline_as_mopenapi_makes_it_a_variant(self):
        answer = {'type': 'object', 'properties': {'one': {'oneOf': [DATA, {'type': 'null'}]},
                                                   'lines': {'type': ['array', 'null'], 'items': DATA}}}
        result = stable_names(spec({'/me': {'get': operation({'200': answer})}}))

        self.assertEqual(result['components']['schemas']['ShowMeResponse'], answer)
        self.assertEqual(sorted(result['components']['schemas']), ['ShowMeResponse'])

    def test_gives_two_equal_success_answers_one_name(self):
        answer = {'type': 'object', 'properties': {'data': ref('Product')}}
        result = stable_names(spec({'/products/{id}': {'put': operation({'200': answer, '201': answer},
                                                                        operation_id='upsertProduct')}}))

        responses = result['paths']['/products/{id}']['put']['responses']
        self.assertEqual([r['content']['application/json']['schema'] for r in responses.values()],
                         [ref('UpsertProductResponse')] * 2)

    def test_does_not_change_its_input(self):
        source = spec({'/me': {'get': operation({'200': DATA})}})
        stable_names(source)
        self.assertEqual(source['paths']['/me']['get']['responses']['200']['content']['application/json']['schema'], DATA)

    def test_stops_on_a_shape_it_cannot_name(self):
        merged = {'type': 'object', 'properties': {'x': {'allOf': [DATA, ref('Me')]}}}
        cases = {
            'two success answers that differ': spec({'/me': {'get': operation({'200': DATA, '201': ref('Me')})}}),
            'no operationId': spec({'/me': {'get': {'responses': {}}}}),
            'a name the spec already has': spec({'/me': {'get': operation({'200': DATA})}}, {'ShowMeResponse': DATA}),
            'an inline object in allOf': spec({'/me': {'get': operation({'200': merged})}}),
            'an inline object in an error answer': spec({'/me': {'get': operation({'200': ref('Me'), '404': DATA})}}),
            'an inline object in a shared answer': {'paths': {}, 'components': {'schemas': {}, 'responses': {
                'Error404': {'content': {'application/json': {'schema': DATA}}}}}},
            'a name too long for mopenapi': spec({'/x': {'get': operation({'200': DATA}, operation_id='x' * 70)}}),
        }
        for case, source in cases.items():
            with self.subTest(case), self.assertRaises(ValueError):
                stable_names(source)


if __name__ == '__main__':
    unittest.main()
