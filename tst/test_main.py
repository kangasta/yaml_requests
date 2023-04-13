from contextlib import redirect_stdout
from io import StringIO
from multiprocessing import Process, set_start_method
import platform
from requests import get
from time import sleep

from unittest import TestCase
from unittest.mock import patch

from yaml_requests import main, run, __version__
from yaml_requests.logger import RequestLogger

from server.api import app
from _utils import plan_path

# Use fork to start target API. TODO: check for alternative fix
if platform.system() != 'Linux':
    set_start_method('fork')

NO_PLAN = 251
INVALID_PLAN = 252

class TestConsole:
    def __init__(self):
        self.content = ''

    def print_mock_implementation(self, *args, **kwargs):
        self.content += ' '.join(str(a) for a in args) + '\n'

class StartsWith(str):
    def __eq__(self, other):
        return other.startswith(self)

class MainTest(TestCase):
    @patch('builtins.print')
    def test_main_version(self, print_mock):
        console = TestConsole()
        print_mock.side_effect = console.print_mock_implementation

        with patch('sys.argv', ['pullnrun', '--version']):
            code = main()

        self.assertEqual(code, 0)

        self.assertIn(__version__, console.content)

    @patch('builtins.print')
    def test_main_exit_codes(self, print_mock):
        for args, exit_code in [
            ([], NO_PLAN),
            (['file_not_found'], NO_PLAN),
            ([plan_path('invalid_extension.py')], INVALID_PLAN),
            ([plan_path('invalid_plan.yml')], INVALID_PLAN),
            ([plan_path('build_queue.yml'), '--variable', 'no_value'], INVALID_PLAN),
        ]:
            with patch('sys.argv', ['yaml_requests', *args]):
                code = main()

            self.assertEqual(code, exit_code)

    @patch('builtins.print')
    def test_main_minimal(self, print_mock):
        for extension in ['yml', 'json']:
            with self.subTest(extension=extension):
                with patch('sys.argv', ['yaml_requests', plan_path(f'minimal_plan.{extension}')]):
                    code = main()

                self.assertEqual(code, 0)

    @patch('builtins.print')
    def test_main_skipped(self, print_mock):
        with patch('sys.argv', ['yaml_requests', plan_path('skipped.yml')]):
            code = main()

        self.assertEqual(code, 1)

    @patch('builtins.print')
    def test_main_ignore_errors(self, print_mock):
        with patch('sys.argv', ['yaml_requests', plan_path('invalid_url.yml')]):
            code = main()

        self.assertEqual(code, 3)

    @patch('builtins.print')
    @patch('yaml_requests._main.Plan', side_effect=RuntimeError)
    def test_main_unkown_error(self, plan_mock, print_mock):
        with patch('sys.argv', ['yaml_requests', plan_path('build_queue.yml')]):
            code = main()

        self.assertEqual(code, 254) # Unkown error


class IntegrationTest(TestCase):
    @classmethod
    def setUpClass(self):
        self._server = Process(target=app.run)
        self._server.start()

        ready = False
        while not ready:
            try:
                response = get('http://localhost:5000/queue')
                response.raise_for_status()
                ready = True
            except:
                sleep(1)

    @classmethod
    def tearDownClass(self):
        self._server.terminate()
        self._server.join()

    def test_plan_succeeds(self):
        for plan in [
            'use_session_defaults.yml',
            'build_queue.yml',
            'repeat_while.yml',
        ]:
            with self.subTest(plan=plan, function='main'):
                with redirect_stdout(StringIO()) as f:
                    with patch('sys.argv', ['yaml_requests', '--no-animation', '--no-colors', plan_path(plan)]):
                        code = main()

                self.assertEqual(code, 0)
            
            with self.subTest(plan=plan, function='run'):
                code = run(plan_path(plan), RequestLogger())

    def test_main_multiple_outputs(self):
        with redirect_stdout(StringIO()) as f:
            with patch('sys.argv', ['yaml_requests', '--no-animation', '--no-colors', plan_path('print_text_and_headers.yml')]):
                code = main()

        self.assertEqual(code, 0)
        output = f.getvalue()

        self.assertIn('Content-Type: text/html', output)
        self.assertIn('<title>Test target for yaml_requests</title>', output)
