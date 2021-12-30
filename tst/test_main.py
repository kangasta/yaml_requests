import json
import os
import yaml

from unittest import TestCase
from unittest.mock import patch

from yaml_requests import main, __version__

NO_PLAN = 251
INVALID_PLAN = 252
TST_DIR = os.path.dirname(os.path.realpath(__file__))

class TestConsole:
    def __init__(self):
        self.content = ''

    def print_mock_implementation(self, *args, **kwargs):
        self.content += ' '.join(str(a) for a in args) + '\n'

class TestExit(Exception):
    def __init__(self, exit_code):
        super().__init__()
        self.exit_code = exit_code

def exit_mock_implementation(exit_code):
    raise TestExit(exit_code)

class StartsWith(str):
    def __eq__(self, other):
        return other.startswith(self)

class MainTest(TestCase):
    @patch('builtins.exit', side_effect=exit_mock_implementation)
    @patch('builtins.print')
    def test_main_version(self, print_mock, exit_mock):
        console = TestConsole()
        print_mock.side_effect = console.print_mock_implementation

        with self.assertRaises(TestExit) as raised:
            with patch('sys.argv', ['pullnrun', '--version']):
                main()

        self.assertEqual(0, raised.exception.exit_code)

        self.assertIn(__version__, console.content)

    @patch('builtins.exit', side_effect=exit_mock_implementation)
    @patch('builtins.print')
    def test_main_exit_codes(self, print_mock, exit_mock):
        for args, exit_code in [
            ([], NO_PLAN),
            (['file_not_found'], NO_PLAN),
            ([f'{TST_DIR}/test_main.py'], INVALID_PLAN),
            ([f'{TST_DIR}/invalid_plan.yml'], INVALID_PLAN),
        ]:
            with self.assertRaises(TestExit):
                with patch('sys.argv', ['yaml_requests', *args]):
                    main()

            exit_mock.assert_called_with(exit_code)

    @patch('builtins.print')
    def test_main_minimal(self, print_mock):
        for extension in ['yml', 'json']:
            with patch('sys.argv', ['yaml_requests', f'{TST_DIR}/minimal_plan.{extension}']):
                main()
