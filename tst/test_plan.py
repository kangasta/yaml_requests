import os
from unittest import TestCase

from yaml_requests.utils.args import load_plan_file
from yaml_requests._plan import Plan

from _utils import plan_path

class PlanTest(TestCase):
    def test_parse_invalid_plan(self):
        plan_dict = load_plan_file(plan_path('invalid_plan.yml'))
        with self.assertRaises(AssertionError):
            Plan(plan_dict)

    def test_parse_valid_plan(self):
        for plan_file in ['minimal_plan.yml', 'full_plan.yml']:
            plan_dict = load_plan_file(plan_path(plan_file))
            Plan(plan_dict)

    def test_parse_plan_overrides(self):
        options_override = dict(session=False)
        variables_override = dict(hostname='github.com')

        for plan_file in ['minimal_plan.yml', 'full_plan.yml']:
            plan_dict = load_plan_file(plan_path(plan_file))
            plan = Plan(
                plan_dict,
                options_override=options_override,
                variables_override=variables_override)

            self.assertEqual(options_override.get('session'), plan.options.session)
            self.assertDictEqual(variables_override, plan.variables)
