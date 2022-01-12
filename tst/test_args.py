import os
from unittest import TestCase

from yaml_requests.utils.args import get_argparser, parse_variables


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
