import json
import os

from yaml_requests.utils.template import Environment
from yaml_requests._request import ParsedRequest

RESPONSE_JSON = dict(message='Mock respose text content')
SIMPLE_REQUEST = dict(
    get=dict(url='http://localhost:5000'),
    headers={
        "Accept": "*/*",
        "Content-Type": 'application/json',
    },
    body=json.dumps(dict(key="value")),
)
REQUEST_WITH_ASSERT = {
    'get': dict(url='http://localhost:5000'),
    'assert': 'var == 3'
}
TST_DIR = os.path.dirname(os.path.realpath(__file__))

class MockRequest:
    def __init__(self, body=None, headers=None, **kwargs):
        self.body = body
        self.headers = headers

class MockResponse:
    def __init__(self, ok=True, content=None, request=None):
        self.ok = ok
        self.request = MockRequest(**(request or SIMPLE_REQUEST))
        self._content = content or json.dumps(RESPONSE_JSON)

    def __call__(self, *args, **kwargs):
        return self

    @property
    def headers(self):
        return {
            "Content-Type": "application/json",
            "Server": "MockResponse/0.0",
        }

    @property
    def text(self):
        return self._content

    def json(self):
        return json.loads(self._content)

def get_sent_mock_request(request_dict=None, template_env=None, ok=True, content=None):
    req = ParsedRequest(request_dict or SIMPLE_REQUEST, template_env or Environment())
    req.send(MockResponse(ok, content, request_dict))
    return req

def plan_path(plan_name):
    return os.path.join(TST_DIR, 'plans', plan_name)
