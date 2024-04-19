from contextlib import redirect_stdout
from io import StringIO
from multiprocessing import Process, set_start_method
import platform
from requests import get
from time import sleep

from unittest import TestCase
from unittest.mock import patch

from ciou.snapshot import rewind_and_read, snapshot, REPLACE_DURATION, REPLACE_TIMESTAMP, REPLACE_UUID

from yaml_requests import main, run, __version__
from yaml_requests.logger import RequestLogger

from server.api import start
from _utils import plan_path


REPLACE = [REPLACE_TIMESTAMP, REPLACE_DURATION, REPLACE_UUID]

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
    maxDiff = None

    @patch('builtins.print')
    def test_main_version(self, print_mock):
        console = TestConsole()
        print_mock.side_effect = console.print_mock_implementation

        with patch('sys.argv', ['pullnrun', '--version']):
            code = main()

        self.assertEqual(code, 0)

        self.assertIn(__version__, console.content)

    def test_main_exit_codes(self):
        for key, args, exit_code in [
            ('empty_agrs', [], NO_PLAN),
            ('file_not_found', ['file_not_found'], NO_PLAN),
            ('invalid_extension', [plan_path('invalid_extension.py')], INVALID_PLAN),
            ('invalid_plan', [plan_path('invalid_plan.yml')], INVALID_PLAN),
            ('invalid_variable', [plan_path('build_queue.yml'), '--variable', 'no_value'], INVALID_PLAN),
        ]:
            with self.subTest(key=key, function='main'):
                with redirect_stdout(StringIO()) as f:
                    with patch('sys.argv', ['yaml_requests', *args]):
                        code = main()

                    if platform.system() != "Windows":
                        actual = rewind_and_read(f)
                        self.assertEqual(*snapshot(key, actual, replace=REPLACE))

                self.assertEqual(code, exit_code)

    @patch('builtins.print')
    def test_main_minimal(self, print_mock):
        for extension in ['yml', 'json']:
            with self.subTest(extension=extension):
                with patch('sys.argv', ['yaml_requests', plan_path(f'minimal_plan.{extension}')]):
                    code = main()

                self.assertEqual(code, 0)

    def test_main_skipped(self):
        with redirect_stdout(StringIO()) as f:
            with patch('sys.argv', ['yaml_requests', '--no-animation', plan_path('skipped.yml')]):
                code = main()

            if platform.system() != "Windows":
                actual = rewind_and_read(f)
                self.assertEqual(*snapshot('skipped', actual, replace=REPLACE))

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
    maxDiff = None

    @classmethod
    def setUpClass(self):
        self._server = Process(target=start)
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
                    with patch('sys.argv', ['yaml_requests', '--no-animation', plan_path(plan)]):
                        code = main()

                    if platform.system() != "Windows":
                        actual = rewind_and_read(f)
                        key = plan.split('.')[0]
                        self.assertEqual(*snapshot(key, actual, replace=REPLACE))

                self.assertEqual(code, 0)

            with self.subTest(plan=plan, function='run'):
                code = run(plan_path(plan), RequestLogger())
                self.assertEqual(code, 0)

    def test_accessing_request_data(self):
        logger = RequestLogger()
        code = run(plan_path('full_plan.yml'), logger)
        self.assertEqual(code, 0)

        reqs = logger.requests
        self.assertEqual(len(reqs), 2)
        self.assertEqual(reqs[0].response.url, 'https://www.google.com/')

    def test_run_override_variables(self):
        logger = RequestLogger()
        code = run(plan_path('full_plan.yml'), logger, dict(hostname='duckduckgo.com'))
        self.assertEqual(code, 0)

        reqs = logger.requests
        self.assertEqual(len(reqs), 2)
        self.assertEqual(reqs[0].response.url, 'https://duckduckgo.com/')


    def test_main_multiple_outputs(self):
        with redirect_stdout(StringIO()) as f:
            with patch('sys.argv', ['yaml_requests', '--no-animation', '--no-colors', plan_path('print_text_and_headers.yml')]):
                code = main()

        self.assertEqual(code, 0)
        output = f.getvalue()

        self.assertIn('Content-Type: text/html', output)
        self.assertIn('<title>Test target for yaml_requests</title>', output)
