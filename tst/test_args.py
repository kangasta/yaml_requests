import os
from unittest import TestCase

from yaml_requests.utils.args import get_argparser, load_plan_file, parse_plan, parse_variables

TST_DIR = os.path.dirname(os.path.realpath(__file__))

class ArgsTest(TestCase):
    def test_parse_variables(self):
        args = get_argparser().parse_args(
            ['-v', 'base_url:https://google.com', '-v', 'user:ci'])
        vars = parse_variables(args.variables)
        self.assertDictEqual(
            vars, dict(base_url='https://google.com', user='ci'))

    def test_parse_empty_variables(self):
        args = get_argparser().parse_args([])
        vars = parse_variables(args.variables)
        self.assertDictEqual(vars, {})

    def test_invalid_variable(self):
        with self.assertRaises(ValueError):
            parse_variables(['no_separator'])

    def test_parse_invalid_plan(self):
        plan = load_plan_file(f'{TST_DIR}/invalid_plan.yml')
        with self.assertRaises(AssertionError):
            parse_plan(plan)

    def test_parse_valid_plan(self):
        for plan_file in ['minimal_plan.yml', 'full_plan.yml']:
            plan = load_plan_file(f'{TST_DIR}/{plan_file}')
            parse_plan(plan)

    def test_parse_plan_overrides(self):
        options_override = dict(session=False)
        variables_override = dict(hostname='github.com')

        for plan_file in ['minimal_plan.yml', 'full_plan.yml']:
            plan = load_plan_file(f'{TST_DIR}/{plan_file}')
            _, options, variables = parse_plan(
                plan,
                options_override=options_override,
                variables_override=variables_override)

            self.assertDictEqual(options_override, options)
            self.assertDictEqual(variables_override, variables)
