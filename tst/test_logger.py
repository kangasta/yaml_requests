from contextlib import redirect_stdout
from io import StringIO
import json
from os import terminal_size
from textwrap import indent
from unittest import TestCase
from unittest.mock import MagicMock, patch
import yaml

from requests import RequestException

from yaml_requests.utils.template import Environment
from yaml_requests.logger import ConsoleLogger, RequestLogger
from yaml_requests.logger._console import _fit_to_width
from yaml_requests._request import Request

from _utils import get_sent_mock_request, SIMPLE_REQUEST, RESPONSE_JSON, REQUEST_WITH_ASSERT

TEXT = '\r- Get queued items'
FORMATTED_TEXT = '\r\033[1m- Get queued items\033[22m'

class ConsoleLoggerTest(TestCase):
    @patch('yaml_requests.logger._console.get_terminal_size')
    def test_fit_to_width_no_truncate(self, get_width_mock):
        get_width_mock.return_value = terminal_size((18, 3))
        self.assertEqual(_fit_to_width(TEXT), TEXT)
        self.assertEqual(_fit_to_width(FORMATTED_TEXT), FORMATTED_TEXT)

    @patch('yaml_requests.logger._console.get_terminal_size')
    def test_fit_to_width_no_truncate(self, get_width_mock):
        get_width_mock.return_value = terminal_size((16, 3))
        self.assertEqual(
            _fit_to_width(TEXT),
            f'{TEXT[:15]}…')
        self.assertEqual(
            _fit_to_width(FORMATTED_TEXT),
            f'{FORMATTED_TEXT[:19]}\033[0m…')

    def test_response_output(self):
        logger = ConsoleLogger(False, False)
        for output, expected in [
            ('unknown', '\n  ? Unknown output entry [unknown], expected one of [headers, request_headers, request_body, response_headers, response_body, text, json, yml, yaml]\n'),
            (
                'request_body',
                '\n  > ' + json.dumps(json.loads(SIMPLE_REQUEST['body']), indent=2).rstrip(' \n').replace('\n', '\n  > ') + '\n'
            ),
            (
                'request_headers',
                '\n  > Accept: */*\n  > Content-Type: application/json\n'
            ),
            (
                'json',
                '\n  < ' + json.dumps(RESPONSE_JSON, indent=2).rstrip(' \n').replace('\n', '\n  < ') + '\n'
            ),
            (
                'response_body',
                '\n  < ' + json.dumps(RESPONSE_JSON, indent=2).rstrip(' \n').replace('\n', '\n  < ') + '\n'
            ),
            (
                'response_headers',
                '\n  < Content-Type: application/json\n  < Server: MockResponse/0.0\n'
            ),
            (
                'yml',
                '\n  < ' + yaml.dump(RESPONSE_JSON, default_flow_style=False).rstrip(' \n').replace('\n', '\n  < ') + '\n'
            ),
            (
                'yaml',
                '\n  < ' + yaml.dump(RESPONSE_JSON, default_flow_style=False).rstrip(' \n').replace('\n', '\n  < ') + '\n'
            ),
        ]:
            request = get_sent_mock_request({
                **SIMPLE_REQUEST,
                'output': output
            })

            self.assertEqual(logger._response_text(request), expected)

    def test_response_output_handles_error(self):
        logger = ConsoleLogger(False, False)
        content = '{not json}'

        for output, expected in [
            ('text', f'\n  < {content}\n'),
            ('json', ''),
            ('yaml', '')
        ]:
            request = get_sent_mock_request({
                **SIMPLE_REQUEST,
                'output': output
            },content=content)
            self.assertEqual(logger._response_text(request), expected)

    def test_log_errored_request_with_asserts(self):
        logger = ConsoleLogger(False, False)
        request = Request(REQUEST_WITH_ASSERT, Environment())
        request_mock = MagicMock(side_effect=RequestException)

        request.send(request_mock)
        with redirect_stdout(StringIO()):
            logger.finish_request(request)

class RequestLoggerTest(TestCase):
    def test_log_errored_request_with_asserts(self):
        logger = RequestLogger()
        request = Request(REQUEST_WITH_ASSERT, Environment())

        logger.start_request(request)
        self.assertIsNone(logger.requests[0].state)

        request_mock = MagicMock(side_effect=RequestException)
        request.send(request_mock)
        logger.finish_request(request)

        self.assertFalse(logger.requests[0].state.ok)
