import os
import yaml

from jinja2.exceptions import UndefinedError

from unittest import TestCase

from yaml_requests.utils.template import Environment

TST_DIR = os.path.dirname(os.path.realpath(__file__))
with open(f'{TST_DIR}/template_test_data.yml', 'r') as f:
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
        f = env.resolve_templates(wrap(f' open("{TST_DIR}/test_template.py") '))
        print(f"***** {f}")
        f.read()
        f.close()

    def test_lookup(self):
        env = Environment(path=__file__)

        content = env.resolve_templates(wrap(f' lookup("file", "{TST_DIR}/file_lookup_test_data.txt")'))
        self.assertEqual(content, "Thu Nov 28 00:05:47 EET 2024")

        content = env.resolve_templates(wrap(f' lookup("file", "file_lookup_test_data.txt")'))
        self.assertEqual(content, "Thu Nov 28 00:05:47 EET 2024")

        os.environ['CITY'] = 'Rovaniemi'
        value = env.resolve_templates(wrap(' lookup("env", "CITY")'))
        self.assertEqual(value, 'Rovaniemi')

    def test_context(self):
        env = Environment()
        value = env.resolve_templates('{{ item }}', dict(item='foo'))
        self.assertEqual(value, 'foo')

    def test_undefined(self):
        env = Environment()
        with self.assertRaises(UndefinedError):
            env.resolve_templates('{{ undefined_var }}')
