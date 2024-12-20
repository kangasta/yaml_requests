import json
import os
import yaml

from jinja2.exceptions import UndefinedError

from unittest import TestCase

from yaml_requests.utils.template import Environment

TST_DIR = os.path.dirname(os.path.realpath(__file__))
with open(os.path.join(TST_DIR, 'template_test_data.yml'), 'r') as f:
    TEST_DATA = yaml.load(f, Loader=yaml.SafeLoader)


def wrap(i):
    return '{{' + i + '}}'


class TemplateTest(TestCase):
    def test_template(self):
        env = Environment()
        for key, value in TEST_DATA.get('vars').items():
            env.register(key, value)

        for test in TEST_DATA.get('tests'):
            in_ = test.get('in')
            with self.subTest(**{'in': in_}):
                out = test.get('out')

                r = env.resolve_templates(in_)
                self.assertEqual(r, out)

    def test_open(self):
        env = Environment()
        path = json.dumps(os.path.join(TST_DIR, "test_template.py"))
        f = env.resolve_templates(wrap(f' open({path}) '))
        f.read()
        f.close()

    def test_lookup_file(self):
        env = Environment(path=__file__)

        path = json.dumps(os.path.join(TST_DIR, "file_lookup_test_data.txt"))
        content = env.resolve_templates(wrap(f' lookup("file", {path})'))
        self.assertEqual(content, "Thu Nov 28 00:05:47 EET 2024")

        content = env.resolve_templates(wrap(f' lookup("file", "file_lookup_test_data.txt")'))
        self.assertEqual(content, "Thu Nov 28 00:05:47 EET 2024")

    def test_lookup_env(self):
        env = Environment(path=__file__)

        os.environ['CITY'] = 'Rovaniemi'
        value = env.resolve_templates(wrap(' lookup("env", "CITY")'))
        self.assertEqual(value, 'Rovaniemi')

        value = env.resolve_templates(wrap(' lookup("env", "COUNTRY")'))
        self.assertEqual(value, None)


    def test_context(self):
        env = Environment()
        value = env.resolve_templates('{{ item }}', dict(item='foo'))
        self.assertEqual(value, 'foo')

    def test_undefined(self):
        env = Environment()
        with self.assertRaises(UndefinedError):
            env.resolve_templates('{{ undefined_var }}')
