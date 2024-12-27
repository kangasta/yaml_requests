from copy import deepcopy
from unittest import TestCase

from jinja2.exceptions import TemplateError

from yaml_requests.utils.template import Environment
from yaml_requests._request import ParsedAssertion, ParsedRequest, RequestState, parse_request_loop

from _utils import MockResponse, REQUEST_WITH_ASSERT

class RequestStateTest(TestCase):
    def test_init_with_unknown_state_raises(self):
        with self.assertRaises(ValueError):
            RequestState('UNKNOWN')

    def test_request_state_equality(self):
        self.assertEqual(RequestState(RequestState.ERROR), RequestState.ERROR)
        self.assertEqual(RequestState(RequestState.ERROR), RequestState(RequestState.ERROR))

        self.assertNotEqual(RequestState(RequestState.ERROR), RequestState.SUCCESS)
        self.assertNotEqual(RequestState(RequestState.SUCCESS), RequestState(RequestState.ERROR))

class AssertionTest(TestCase):
    def test_ok_raises_if_not_executed(self):
        assertion = ParsedAssertion('var is undefined')
        self.assertEqual(assertion.name, 'var is undefined')
        with self.assertRaises(RuntimeError):
            assertion.ok

    def test_execute_raises_on_error(self):
        env = Environment()
        assertion = ParsedAssertion('var == 3')
        with self.assertRaises(TemplateError):
            assertion.execute(env)
        self.assertFalse(assertion.ok)

REQUEST_WITH_VARIABLE = dict(
    name='Get {{ url }}',
    get=dict(url='{{ url }}')
)

REQUEST_WITH_METHOD_AND_PARAMS = dict(
    name='With method and params',
    method='get',
    params=dict(url='{{ url }}')
)

REQUEST_WITH_LOOP = dict(
    name='Get item',
    get=dict(url='http://localhost:5000/items/{{ item }}'),
    loop=[1,2,3]
)

REQUEST_WITOUT_METHOD = dict(
    name='HTTP method missing'
)


class RequestTest(TestCase):
    def test_init_sets_error_when_template_processing_fails(self):
        env = Environment()

        req = ParsedRequest(REQUEST_WITH_VARIABLE, env)
        self.assertEqual(req.state, RequestState.ERROR)

        req = ParsedRequest(REQUEST_WITH_VARIABLE, env, context=dict(url='http://localhost:5000'))
        self.assertIsNone(req.state)

        env.register('url','http://localhost:5000')
        req = ParsedRequest(REQUEST_WITH_VARIABLE, env)
        self.assertIsNone(req.state)

    def test_init_parses_method_and_params(self):
        env = Environment()
        env.register('url','http://localhost:5000')

        req = ParsedRequest(REQUEST_WITH_METHOD_AND_PARAMS, env)
        self.assertIsNone(req.state)
        self.assertEqual(req.method, 'GET')
        self.assertEqual(req.params['url'], 'http://localhost:5000')

        request_dict = deepcopy(REQUEST_WITH_METHOD_AND_PARAMS)
        request_dict.pop('method')
        req = ParsedRequest(REQUEST_WITOUT_METHOD, env)
        self.assertEqual(req.state, RequestState.ERROR)

    def test_init_sets_error_when_no_http_method(self):
        env = Environment()

        req = ParsedRequest(REQUEST_WITOUT_METHOD, env)
        self.assertEqual(req.state, RequestState.ERROR)

    def test_init_sets_error_when_multiple_http_methods(self):
        env = Environment()
        env.register('url','http://localhost:5000')

        req = ParsedRequest({**REQUEST_WITH_METHOD_AND_PARAMS, **REQUEST_WITH_VARIABLE}, env)
        self.assertEqual(req.state, RequestState.ERROR)

    def test_send_invalid_does_not_raise(self):
        env = Environment()

        req = ParsedRequest(REQUEST_WITOUT_METHOD, env)
        self.assertEqual(req.state, RequestState.ERROR)

        req.send(lambda: None)
        self.assertIsNone(req.response)

    def test_send_sets_status(self):
        env = Environment()
        env.register('url','http://localhost:5000')

        for raise_for_status, response_ok, expected in [
            (None, False, RequestState.FAILURE),
            (None, True, RequestState.SUCCESS),
            (True, False, RequestState.FAILURE),
            (True, True, RequestState.SUCCESS),
            (False, False, RequestState.NOT_RAISED),
            (False, True, RequestState.SUCCESS),
        ]:
            if raise_for_status is not None:
                request_dict = {
                    **REQUEST_WITH_VARIABLE,
                    'raise_for_status': raise_for_status}
            else:
                request_dict = REQUEST_WITH_VARIABLE

            req = ParsedRequest(request_dict, env)
            req.send(MockResponse(response_ok))
            self.assertEqual(
                req.state,
                expected,
                msg=f'{raise_for_status}, {response_ok} => {str(req.state)}')

    def test_assertions_from_str(self):
        env = Environment()

        req = ParsedRequest(REQUEST_WITH_ASSERT, env)
        self.assertIsInstance(req.assertions, list)
        self.assertEqual(len(req.assertions), 1)

        req.send(MockResponse(True))
        self.assertEqual(req.state, RequestState.ERROR)

    def test_failed_assertion_set_failure_state(self):
        env = Environment()
        env.register('var', 5)

        req = ParsedRequest(REQUEST_WITH_ASSERT, env)
        req.send(MockResponse(True))
        self.assertEqual(req.state, RequestState.FAILURE)

    def test_parse_request_loop(self):
        env = Environment()
        args_loop = parse_request_loop(REQUEST_WITH_LOOP, env)
        self.assertEqual(len(args_loop), 3)

        for i, args in enumerate(args_loop):
            request_dict, template_env, context = args
            req = ParsedRequest(request_dict, template_env, False, context)
            self.assertEqual(req.params['url'], f'http://localhost:5000/items/{i+1}')
