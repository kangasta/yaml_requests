from contextlib import redirect_stdout
from io import StringIO
from multiprocessing import Process, set_start_method
import platform
from requests import get
from time import sleep

from unittest import TestCase
from unittest.mock import patch

from yaml_requests import main, __version__

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
            ([plan_path('invalid_extension.py')], INVALID_PLAN),
            ([plan_path('invalid_plan.yml')], INVALID_PLAN),
        ]:
            with self.assertRaises(TestExit):
                with patch('sys.argv', ['yaml_requests', *args]):
                    main()

            exit_mock.assert_called_with(exit_code)

    @patch('builtins.exit', side_effect=exit_mock_implementation)
    @patch('builtins.print')
    def test_main_minimal(self, print_mock, exit_mock):
        for extension in ['yml', 'json']:
            with self.subTest(extension=extension):
                with self.assertRaises(TestExit):
                    with patch('sys.argv', ['yaml_requests', plan_path(f'minimal_plan.{extension}')]):
                        main()

                exit_mock.assert_called_with(0)

    @patch('builtins.exit', side_effect=exit_mock_implementation)
    @patch('builtins.print')
    def test_main_skipped(self, print_mock, exit_mock):
        with self.assertRaises(TestExit):
            with patch('sys.argv', ['yaml_requests', plan_path('skipped.yml')]):
                main()

        exit_mock.assert_called_with(1)

    @patch('builtins.exit', side_effect=exit_mock_implementation)
    @patch('builtins.print')
    def test_main_ignore_errors(self, print_mock, exit_mock):
        with self.assertRaises(TestExit):
            with patch('sys.argv', ['yaml_requests', plan_path('invalid_url.yml')]):
                main()

        exit_mock.assert_called_with(3)

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

    @patch('builtins.exit', side_effect=exit_mock_implementation)
    @patch('builtins.print')
    def test_main_build_queue(self, print_mock, exit_mock):
        with self.assertRaises(TestExit):
            with patch('sys.argv', ['yaml_requests', plan_path('build_queue.yml')]):
                main()

        exit_mock.assert_called_with(0)

    @patch('builtins.exit', side_effect=exit_mock_implementation)
    def test_main_multiple_outputs(self, exit_mock):
        with self.assertRaises(TestExit):
            with redirect_stdout(StringIO()) as f:
                with patch('sys.argv', ['yaml_requests', '--no-animation', '--no-colors', plan_path('print_text_and_headers.yml')]):
                    main()

        output = f.getvalue()

        self.assertIn('Content-Type: text/html', output)
        self.assertIn('<title>Test target for yaml_requests</title>', output)
        exit_mock.assert_called_with(0)
