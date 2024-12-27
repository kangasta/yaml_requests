import os
from unittest import TestCase, runner

from yaml_requests.utils.args import load_plan_file
from yaml_requests._plan import Plan
from yaml_requests._runner import PlanRunner
from yaml_requests.logger import ConsoleLogger

from _utils import plan_path

class PlanTest(TestCase):
    def test_parse_invalid_plan(self):
        plan_dict = load_plan_file(plan_path('invalid_plan.yml'))
        with self.assertRaises(AssertionError):
            Plan._from_dict(plan_dict)

    def test_parse_valid_plan(self):
        for plan_file in ['minimal_plan.yml', 'full_plan.yml']:
            with self.subTest(plan=plan_file):
                plan_dict = load_plan_file(plan_path(plan_file))
                Plan._from_dict(plan_dict)

    def test_parse_plan_overrides(self):
        options_override = dict(session=False)
        variables_override = dict(hostname='github.com', name='test')

        for plan_file in ['minimal_plan.yml', 'full_plan.yml']:
            with self.subTest(plan=plan_file):
                plan_dict = load_plan_file(plan_path(plan_file))
                plan = Plan._from_dict(
                    plan_dict,
                    options_override=options_override,
                    variables_override=variables_override)

                self.assertEqual(options_override.get('session'), plan.options.session)
                self.assertDictEqual(variables_override, plan.variables)

    def test_parse_session_options(self):
        plan_dict = load_plan_file(plan_path('integration/use_session_defaults.yml'))
        plan = Plan._from_dict(plan_dict)
        runner = PlanRunner(plan, ConsoleLogger(False, False))
        session = runner._session

        self.assertEqual(session.headers.get('TEST-HEADER'), 'header-value')
        self.assertEqual(session.cookies.get('test-cookie'), 'cookie-value')
