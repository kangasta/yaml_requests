import json

from yaml_requests.utils.template import Environment
from yaml_requests._request import Request

SIMPLE_REQUEST = dict(
    get=dict(url='http://localhost:5000'),
)

RESPONSE_JSON = dict(message='Mock respose text content')

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
