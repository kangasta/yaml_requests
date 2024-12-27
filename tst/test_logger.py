from io import StringIO
import json
from unittest import TestCase
from unittest.mock import MagicMock, patch
import yaml

from requests import RequestException

from yaml_requests.utils.template import Environment
from yaml_requests.logger import ConsoleLogger, RequestLogger
from yaml_requests._request import ParsedRequest

from _utils import get_sent_mock_request, SIMPLE_REQUEST, RESPONSE_JSON, REQUEST_WITH_ASSERT

TEXT = '\r- Get queued items'
FORMATTED_TEXT = '\r\033[1m- Get queued items\033[22m'

class ConsoleLoggerTest(TestCase):
    def test_response_output(self):
        logger = ConsoleLogger(False, False)
        _env = Environment()
        _env.globals["foo"] = "bar"
        for output, expected in [
            ('unknown', '\n? Unknown output entry [unknown], expected one of [headers, request_headers, request_body, response_headers, response_body, text, json, variables, yml, yaml]\n'),
            (
                'request_body',
                '\n> ' + json.dumps(json.loads(SIMPLE_REQUEST['body']), indent=2).rstrip(' \n').replace('\n', '\n> ') + '\n'
            ),
            (
                'request_headers',
                '\n> Accept: */*\n> Content-Type: application/json\n'
            ),
            (
                'json',
                '\n< ' + json.dumps(RESPONSE_JSON, indent=2).rstrip(' \n').replace('\n', '\n< ') + '\n'
            ),
            (
                'response_body',
                '\n< ' + json.dumps(RESPONSE_JSON, indent=2).rstrip(' \n').replace('\n', '\n< ') + '\n'
            ),
            (
                'response_headers',
                '\n< Content-Type: application/json\n< Server: MockResponse/0.0\n'
            ),
            (
                'variables',
                '\nfoo: bar\n'
            ),
            (
                'yml',
                '\n< ' + yaml.dump(RESPONSE_JSON, default_flow_style=False).rstrip(' \n').replace('\n', '\n  < ') + '\n'
            ),
            (
                'yaml',
                '\n< ' + yaml.dump(RESPONSE_JSON, default_flow_style=False).rstrip(' \n').replace('\n', '\n< ') + '\n'
            ),
        ]:
            with self.subTest(output=output):
                request = get_sent_mock_request({
                    **SIMPLE_REQUEST,
                    'output': output
                }, _env)

                self.assertEqual(logger._response_text(request), expected)

    def test_response_output_handles_error(self):
        logger = ConsoleLogger(False, False)
        content = '{not json}'

        for output, expected in [
            ('text', f'\n< {content}\n'),
            ('json', ''),
            ('yaml', '')
        ]:
            request = get_sent_mock_request({
                **SIMPLE_REQUEST,
                'output': output
            },content=content)
            self.assertEqual(logger._response_text(request), expected)

    @patch('sys.stdout', new_callable=StringIO)
    def test_log_errored_request_with_asserts(self, out):
        logger = ConsoleLogger(False, False)
        logger.start()

        request = ParsedRequest(REQUEST_WITH_ASSERT, Environment())
        request_mock = MagicMock(side_effect=RequestException)

        request.send(request_mock)
        logger.finish_request(request)

        logger.close()

class RequestLoggerTest(TestCase):
    def test_log_errored_request_with_asserts(self):
        logger = RequestLogger()
        request = ParsedRequest(REQUEST_WITH_ASSERT, Environment())

        logger.start_request(request)
        self.assertIsNone(logger.requests[0].state)

        request_mock = MagicMock(side_effect=RequestException)
        request.send(request_mock)
        logger.finish_request(request)

        self.assertFalse(logger.requests[0].state.ok)
