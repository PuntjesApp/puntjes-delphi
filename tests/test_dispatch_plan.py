import unittest

from tools.dispatch_plan import dispatch_plan

URL = 'https://raw.githubusercontent.com/PuntjesApp/puntjes-openapi/v1.1.0/api.json'


def plan(*args):
    lines = []
    code = dispatch_plan(list(args), lines.append, lambda line: None)
    return code, dict(line.split('=', 1) for line in lines)


class DispatchPlanTest(unittest.TestCase):
    def test_a_minor_is_a_feat_that_merges_itself(self):
        self.assertEqual(plan('v1.1.0', 'minor', URL, 'main@abc1234'), (0, {
            'skip': 'false', 'commit_type': 'feat', 'auto_merge': 'true', 'branch': 'regenerate/v1.1.0', 'close': '',
        }))

    def test_a_major_is_breaking_and_waits_for_a_person(self):
        _, p = plan('v1.1.0', 'major', URL, 'main@abc1234')
        self.assertEqual([p['commit_type'], p['auto_merge']], ['feat!', 'false'])

    def test_a_patch_is_a_fix(self):
        self.assertEqual(plan('v1.1.0', 'patch', URL, 'main@abc1234')[1]['commit_type'], 'fix')

    def test_skips_the_tag_already_in_source(self):
        self.assertEqual(plan('v1.1.0', 'minor', URL, 'v1.1.0')[1]['skip'], 'true')

    def test_refuses_a_url_outside_puntjes_openapi_or_for_another_tag(self):
        self.assertEqual(plan('v1.1.0', 'minor', 'https://example.com/api.json', 'x')[0], 1)
        other = 'https://raw.githubusercontent.com/PuntjesApp/puntjes-openapi/v9.9.9/api.json'
        self.assertEqual(plan('v1.1.0', 'minor', other, 'x')[0], 1)

    def test_refuses_an_unknown_level_or_tag(self):
        self.assertEqual(plan('v1.1.0', 'huge', URL, 'x')[0], 1)
        self.assertEqual(plan('v1.1.0;rm', 'minor', URL, 'x')[0], 1)

    def test_skips_a_tag_older_than_source(self):
        self.assertEqual(plan('v1.1.0', 'minor', URL, 'v1.2.0')[1]['skip'], 'true')

    def test_compares_versions_by_number_not_by_text(self):
        newer = 'https://raw.githubusercontent.com/PuntjesApp/puntjes-openapi/v1.10.0/api.json'
        self.assertEqual(plan('v1.10.0', 'minor', newer, 'v1.9.0')[1]['skip'], 'false')
        self.assertEqual(plan('v1.9.0', 'minor', newer.replace('v1.10.0', 'v1.9.0'), 'v1.10.0')[1]['skip'], 'true')

    def test_skips_the_older_tag_when_a_pr_for_a_newer_tag_is_open(self):
        _, p = plan('v1.1.0', 'minor', URL, 'main@abc1234', 'regenerate/v1.0.0\nregenerate/v1.2.0')
        self.assertEqual([p['skip'], p['close']], ['true', ''])

    def test_closes_the_open_prs_for_older_tags(self):
        _, p = plan('v1.1.0', 'minor', URL, 'v1.0.0',
                    'regenerate/v1.0.1\nregenerate/v1.1.0\nfeature/x\nregenerate/v0.9.0\nregenerate/v1.0.2;rm')
        self.assertEqual([p['skip'], p['close']], ['false', 'regenerate/v1.0.1 regenerate/v0.9.0'])

    def test_a_closed_open_major_makes_the_new_pr_a_major(self):
        _, p = plan('v1.1.0', 'patch', URL, 'v1.0.0', 'regenerate/v1.0.5 feat!: regenerate from puntjes-openapi v1.0.5')
        self.assertEqual([p['close'], p['commit_type'], p['auto_merge']], ['regenerate/v1.0.5', 'feat!', 'false'])

    def test_a_closed_open_minor_keeps_the_new_level(self):
        _, p = plan('v1.1.0', 'patch', URL, 'v1.0.0', 'regenerate/v1.0.5 feat: regenerate from puntjes-openapi v1.0.5')
        self.assertEqual([p['close'], p['commit_type'], p['auto_merge']], ['regenerate/v1.0.5', 'fix', 'true'])

    def test_a_lower_major_in_source_makes_a_major(self):
        url = 'https://raw.githubusercontent.com/PuntjesApp/puntjes-openapi/v2.0.1/api.json'
        _, p = plan('v2.0.1', 'patch', url, 'v1.9.0')
        self.assertEqual([p['commit_type'], p['auto_merge']], ['feat!', 'false'])

    def test_a_source_that_is_not_a_tag_keeps_the_level(self):
        _, p = plan('v1.1.0', 'patch', URL, 'main@abc1234')
        self.assertEqual([p['commit_type'], p['auto_merge']], ['fix', 'true'])

    def test_reads_source_with_the_newline_the_workflow_writes(self):
        self.assertEqual(plan('v1.1.0', 'minor', URL, 'v1.1.0\n')[1]['skip'], 'true')
