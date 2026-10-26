import unittest

from tools.enum_members import enum_members

DTO = """unit puntjes.dto;
interface
type
  TUpdateProductDataStatus = (
    updNone, updActive, updInactive);
  TUpsertProductDataStatus = (
    upd2None, upd2Active, upd2Inactive);
  TShowStatisticsPeriod = (
    sspNone, ssp7d);
const
  _TUpsertProductDataStatus: array[TUpsertProductDataStatus] of RawUtf8 = (
    '', 'active', 'inactive');
implementation
end.
"""
CLIENT = """unit puntjes.client;
interface
    function ShowStatistics(const Period: TShowStatisticsPeriod = sspNone): TShowStatisticsResponse;
implementation
end.
"""


class EnumMembersTest(unittest.TestCase):
    def test_prefixes_each_member_with_its_own_type_name(self):
        dto = enum_members({'dto': DTO})['dto']

        self.assertIn('    updateProductDataStatusNone, updateProductDataStatusActive, updateProductDataStatusInactive);',
                      dto)
        self.assertIn('    upsertProductDataStatusNone, upsertProductDataStatusActive, upsertProductDataStatusInactive);',
                      dto)
        self.assertIn('    showStatisticsPeriodNone, showStatisticsPeriod7d);', dto)

    def test_keeps_the_text_of_each_value(self):
        self.assertIn("    '', 'active', 'inactive');", enum_members({'dto': DTO})['dto'])

    def test_renames_a_member_where_another_unit_uses_it(self):
        client = enum_members({'dto': DTO, 'client': CLIENT})['client']

        self.assertIn('const Period: TShowStatisticsPeriod = showStatisticsPeriodNone)', client)

    def test_wraps_a_long_list_at_120_characters(self):
        values = ', '.join(f'llePart{k}' for k in range(12))
        dto = enum_members({'dto': f'type\n  TListLedgerEntriesType = (\n    lleNone, {values});\n'})['dto']

        self.assertTrue(all(len(line) <= 120 for line in dto.splitlines()))
        self.assertIn('listLedgerEntriesTypePart11);', dto)

    def test_stops_when_a_new_member_name_is_taken(self):
        with self.assertRaisesRegex(ValueError, 'showStatisticsPeriodNone'):
            enum_members({'dto': DTO.replace('implementation\n', 'implementation\nvar showStatisticsPeriodNone: integer;\n')})


if __name__ == '__main__':
    unittest.main()
