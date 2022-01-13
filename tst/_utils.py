import json
import os

from yaml_requests.utils.template import Environment
from yaml_requests._request import Request

RESPONSE_JSON = dict(message='Mock respose text content')
SIMPLE_REQUEST = dict(
    get=dict(url='http://localhost:5000'),
)
REQUEST_WITH_ASSERT = {
    'get': dict(url='http://localhost:5000'),
    'assert': 'var == 3'
}
TST_DIR = os.path.dirname(os.path.realpath(__file__))

class MockResponse:
    def __init__(self, ok=True, content=None):
        self.ok = ok
        self._content = content or json.dumps(RESPONSE_JSON)

    def __call__(self, *args, **kwargs):
        return self

    @property
    def text(self):
        return self._content

    def json(self):
        return json.loads(self._content)

def get_sent_mock_request(request_dict=None, template_env=None, ok=True, content=None):
    req = Request(request_dict or SIMPLE_REQUEST, template_env or Environment())
    req.send(MockResponse(ok, content))
    return req

def plan_path(plan_name):
    return f'{TST_DIR}/plans/{plan_name}'
