import unittest

from tools.optional_bodies import make_optional

UNIT = """interface
type
  TPuntjesClient = class
  public
    // verifyRedemption [post] /redemptions/{code}/verify
    //
    // Params:
    // - [path] Code (required)
    // - [body] Payload  (required)
    function VerifyRedemption(const Code: variant;
      const Payload: TVerifyRedemptionData): TDtoPuntjes49;

    // registerCustomer [post] /customers
    function RegisterCustomer(const Payload: TCreateCustomerData): TDtoPuntjes4;

    // touchProduct [patch] /products/{externalId}
    procedure TouchProduct(const ExternalId: variant;
      const Payload: TTouchData; Force: boolean = false);

    // redeemReward [post] /redemptions
    function RedeemReward(const Payload: TRedeemRewardData): TDtoPuntjes45;
  end;

implementation

function TPuntjesClient.VerifyRedemption(const Code: variant;
  const Payload: TVerifyRedemptionData): TDtoPuntjes49;
begin
  fClient.Request('POST', '/redemptions/%/verify', [Code], [], [],
    Payload, result, TypeInfo(TVerifyRedemptionData), TypeInfo(TDtoPuntjes49), OnError4);
end;

function TPuntjesClient.RegisterCustomer(
  const Payload: TCreateCustomerData): TDtoPuntjes4;
begin
  fClient.Request('POST', '/customers', [], [], [],
    Payload, result, TypeInfo(TCreateCustomerData), TypeInfo(TDtoPuntjes4), OnError2);
end;

procedure TPuntjesClient.TouchProduct(const ExternalId: variant;
  const Payload: TTouchData; Force: boolean);
begin
  fClient.Request('PATCH', '/products/%', [ExternalId], [
    'force', Force], [],
    Payload, {dummy:}self, TypeInfo(TTouchData), nil, OnError9);
end;

function TPuntjesClient.RedeemReward(
  const Payload: TRedeemRewardData): TDtoPuntjes45;
begin
  fClient.Request('POST', '/redemptions', [], [], [],
    Payload, result, TypeInfo(TRedeemRewardData), TypeInfo(TDtoPuntjes45), OnError5);
end;

end.
"""


def body(required=None):
    return {'content': {'application/json': {}}} if required is None else {'required': required, 'content': {}}


SPEC = {'paths': {
    '/redemptions/{code}/verify': {'post': {'operationId': 'verifyRedemption', 'requestBody': body()}},
    '/customers': {'post': {'operationId': 'registerCustomer', 'requestBody': body(False)}},
    '/products/{externalId}': {'patch': {'operationId': 'touchProduct', 'requestBody': {'$ref': '#/components/requestBodies/Touch'}}},
    '/redemptions': {'post': {'operationId': 'redeemReward', 'requestBody': body(True)}, 'get': {'operationId': 'x'}},
}, 'components': {'requestBodies': {'Touch': body()}}}


class MakeOptionalTest(unittest.TestCase):
    def setUp(self):
        self.out = make_optional(UNIT, SPEC)

    def test_adds_an_overload_without_the_body_for_each_optional_body(self):
        self.assertIn('    function VerifyRedemption(const Code: variant;\n'
                      '      const Payload: TVerifyRedemptionData): TDtoPuntjes49; overload;\n'
                      '    // The same call with no request body.\n'
                      '    function VerifyRedemption(const Code: variant): TDtoPuntjes49; overload;\n', self.out)
        self.assertIn('    function RegisterCustomer(): TDtoPuntjes4; overload;\n', self.out)
        self.assertIn('    procedure TouchProduct(const ExternalId: variant; Force: boolean = false); overload;\n',
                      self.out)

    def test_the_overload_sends_no_body(self):
        self.assertIn("function TPuntjesClient.VerifyRedemption(const Code: variant): TDtoPuntjes49;\nbegin\n"
                      "  fClient.Request('POST', '/redemptions/%/verify', [Code], [], [],\n"
                      "    result, TypeInfo(TDtoPuntjes49), OnError4);\nend;\n", self.out)
        self.assertIn("procedure TPuntjesClient.TouchProduct(const ExternalId: variant; Force: boolean);\nbegin\n"
                      "  fClient.Request('PATCH', '/products/%', [ExternalId], [\n    'force', Force], [], OnError9);\n"
                      "end;\n", self.out)

    def test_keeps_the_call_with_the_body(self):
        self.assertEqual(self.out.count('Payload, result, TypeInfo(TVerifyRedemptionData)'), 1)

    def test_leaves_a_required_body_alone(self):
        self.assertEqual(self.out.count('RedeemReward('), UNIT.count('RedeemReward('))

    def test_fails_when_the_generated_shape_is_not_the_expected_one(self):
        with self.assertRaisesRegex(ValueError, 'VerifyRedemption'):
            make_optional(UNIT.replace('    Payload, result, TypeInfo(TVerifyRedemptionData)', '    Payload2'), SPEC)
        with self.assertRaisesRegex(ValueError, 'registerCustomer'):
            make_optional(UNIT.replace('    // registerCustomer [post] /customers\n', ''), SPEC)


if __name__ == '__main__':
    unittest.main()
