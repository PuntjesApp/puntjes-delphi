import unittest

from tools.api_surface import announced, check, surface

UNIT = """unit puntjes.client;
interface
uses sysutils, puntjes.dto;
type
  // A comment that names function Fake(): integer;
  TEnumPuntjes3 = (
    ep3None, ep3Active, ep3Archived);
  TVerifyRedemptionResponse = packed record
    Data: TRedemptionVerificationData;
  end;
  TBulkUpsertProductsRequest = packed record
    Products: TCreateProductDataDynArray;
  end;
  TVerifyRedemptionData = packed record
    Branch: variant;
    IdempotencyKey: variant;
  end;
  PVerifyRedemptionData = ^TVerifyRedemptionData;
  EErrorResponse = class(EJsonClient)
  protected
    fError: TErrorResponse;
  public
    constructor CreateResp(const Format: RawUtf8;
      const Resp: TJsonResponse); override;
  end;
  TPuntjesClient = class
  private
    fClient: IJsonClient;
    procedure OnError1(const Sender: IJsonClient;
      const Response: TJsonResponse);
  public
    constructor Create(const aClient: IJsonClient);
    { VerifyRedemption [post] }
    function VerifyRedemption(const Code: variant): TVerifyRedemptionResponse;
    function BulkUpsertProducts(
      const Payload: TBulkUpsertProductsRequest): TVerifyRedemptionResponse;
    property JsonClient: IJsonClient
      read fClient write fClient;
  end;
const
  _TEnumPuntjes3: array[TEnumPuntjes3] of RawUtf8 = (
    '', 'active', 'archived');
implementation
function TPuntjesClient.VerifyRedemption(const Code: variant): TVerifyRedemptionResponse;
begin
end;
end.
"""


def changed(old, new):
    return surface({'u': UNIT}) - surface({'u': UNIT.replace(old, new)})


class SurfaceTest(unittest.TestCase):
    def test_lists_public_members_and_skips_private_comments_and_implementation(self):
        lines = surface({'u': UNIT})
        self.assertIn('u: TPuntjesClient.VerifyRedemption: function VerifyRedemption(const Code: variant): '
                      'TVerifyRedemptionResponse', lines)
        self.assertIn('u: TPuntjesClient.JsonClient: property JsonClient: IJsonClient read fClient write fClient',
                      lines)
        self.assertFalse([line for line in lines if 'OnError1' in line or 'fClient:' in line or 'Fake' in line])
        self.assertEqual(len([line for line in lines if '.VerifyRedemption:' in line]), 1)
        self.assertIn('u: EErrorResponse.CreateResp: constructor CreateResp(const Format: RawUtf8; '
                      'const Resp: TJsonResponse); override', lines)
        self.assertIn('u: EErrorResponse: EErrorResponse = class(EJsonClient)', lines)

    def test_a_changed_signature_is_a_removal(self):
        self.assertEqual(changed('(const Code: variant): TVerifyRedemptionResponse;',
                                 '(const Code: variant;\n      const Payload: TVerifyRedemptionData): TVerifyRedemptionResponse;'),
                         {'u: TPuntjesClient.VerifyRedemption: function VerifyRedemption(const Code: variant): '
                          'TVerifyRedemptionResponse'})

    def test_a_removed_method_field_or_type_is_a_removal(self):
        self.assertTrue(changed('    property JsonClient', '    property OtherName'))
        self.assertTrue(changed('    IdempotencyKey: variant;\n', ''))
        self.assertTrue(changed('  PVerifyRedemptionData = ^TVerifyRedemptionData;\n', ''))

    def test_an_added_field_method_or_appended_enum_value_is_no_removal(self):
        self.assertFalse(changed('    IdempotencyKey: variant;\n', '    IdempotencyKey: variant;\n    Id: integer;\n'))
        self.assertFalse(changed('  public\n', '  public\n    function ListBranches(): TVerifyRedemptionResponse;\n'))
        self.assertFalse(changed("ep3Archived);", "ep3Archived, ep3Draft);").union(
            changed("'archived');", "'archived', 'draft');")))

    def test_an_inserted_enum_value_moves_the_ones_after_it(self):
        self.assertEqual(changed('ep3None, ep3Active', 'ep3None, ep3Draft, ep3Active'),
                         {'u: TEnumPuntjes3[1]: ep3Active', 'u: TEnumPuntjes3[2]: ep3Archived'})

    def test_an_overload_directive_or_an_added_overload_is_no_removal(self):
        self.assertFalse(changed('(const Code: variant): TVerifyRedemptionResponse;',
                                 '(const Code: variant): TVerifyRedemptionResponse; overload;\n'
                                 '    function VerifyRedemption(): TVerifyRedemptionResponse; overload;'))

    def test_a_renamed_answer_or_body_type_is_a_removal(self):
        self.assertTrue(changed('TVerifyRedemptionResponse', 'TVerifyRedemptionAnswer'))
        self.assertTrue(changed('TBulkUpsertProductsRequest', 'TBulkUpsertProductsBody'))


class AnnouncedTest(unittest.TestCase):
    def test_a_bang_or_a_breaking_change_footer_announces_a_break(self):
        self.assertTrue(announced('feat!: regenerate from puntjes-openapi v3.0.0'))
        self.assertTrue(announced('fix(client)!: rename a method'))
        self.assertTrue(announced('feat: regenerate\n\nBREAKING CHANGE: VerifyRedemption takes a body'))
        self.assertFalse(announced('feat: regenerate from puntjes-openapi v2.2.0'))
        self.assertFalse(announced('docs: explain why feat!: is needed'))


class CheckTest(unittest.TestCase):
    def run_check(self, new, is_announced):
        out, err = [], []
        code = check({'u': UNIT}, {'u': new}, is_announced, 'v0.3.0', out.append, err.append)
        return code, '\n'.join(out), '\n'.join(err)

    def test_an_unannounced_removal_fails_and_says_how_to_retitle(self):
        code, _, err = self.run_check(UNIT.replace('    property JsonClient', '    property OtherName'), False)
        self.assertEqual(code, 1)
        self.assertIn('TPuntjesClient.JsonClient', err)
        self.assertIn('feat!:', err)

    def test_an_announced_removal_passes(self):
        self.assertEqual(self.run_check(UNIT.replace('    property JsonClient', '    property X'), True)[0], 0)

    def test_no_removal_passes(self):
        self.assertEqual(self.run_check(UNIT, False)[0], 0)


if __name__ == '__main__':
    unittest.main()
