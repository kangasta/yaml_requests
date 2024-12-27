from copy import deepcopy
from dataclasses import dataclass
from jinja2.exceptions import TemplateError
from requests.exceptions import RequestException
from typing import Union
from uuid import uuid4

from ciou.types import ensure_list

from .utils.template import Environment


METHODS = ('GET', 'OPTIONS', 'HEAD', 'POST', 'PUT', 'PATCH', 'DELETE',)
EARLIER_ERRORS_SKIP = 'Request skipped due to earlier error.'
NO_HTTP_METHOD = (
    'Request definition should contain exactly one HTTP method as '
    'a main level dict key or as main level method and params keys.')
METHOD_OR_PARAMS_MISSING = (
    'When using method and params fields to define the request, both method '
    'and params must be defined.')


class RequestState:
    SUCCESS = 'SUCCESS'
    NOT_RAISED = 'NOT-RAISED'
    FAILURE = 'FAILURE'
    ERROR = 'ERROR'
    SKIPPED = 'SKIPPED'

    def __init__(self, state, message=None):
        states = (
            self.SUCCESS,
            self.NOT_RAISED,
            self.FAILURE,
            self.ERROR,
            self.SKIPPED)

        if state not in states:
            raise ValueError(
                'Unknown state.'
                f'State must be {", ".join(states[:-1])} or {states[-1]}.')

        self.state = state
        self.message = message

    def __eq__(self, other):
        if isinstance(other, RequestState):
            return self.state == other.state

        return self.state == other

    def __str__(self):
        return self.state

    @property
    def ok(self):
        return self.state in (self.SUCCESS, self.NOT_RAISED, self.SKIPPED)


@dataclass
class Assertion:
    '''An assertion to execute after the request is sent. The assertion is
    considered successful if the expression evaluates to `True`.

    For example:

    ```yaml
    - name: Response is not empty
      expression: response.json() | length
    ```
    '''

    name: str
    '''Human readable description for the assertion.'''
    expression: str
    '''Expression to evaluate.'''


class ParsedAssertion(Assertion):
    def __init__(self, raw_assertion):
        self._ok = None
        if isinstance(raw_assertion, dict):
            super().__init__(
                name=raw_assertion.get('name'),
                expression=raw_assertion.get('expression'),
            )
        else:
            super().__init__(
                name=raw_assertion,
                expression=raw_assertion,
            )

    @property
    def executed(self):
        return self._ok is not None

    @property
    def ok(self):
        if self._ok is None:
            raise RuntimeError('ParsedAssertion has not been executed yet.')
        return self._ok

    def execute(self, template_env, context=None):
        try:
            self._ok = bool(
                template_env.resolve_expression(
                    self.expression, context))
        except BaseException:
            self._ok = False
            raise

        return self._ok


@dataclass
class Request:
    '''A Request to send.'''

    name: str
    '''Human readable description for the request.'''
    method: str
    '''HTTP method to use.

    Can also be defined as a main level dict key with `params` as the value.
    For example:

    ```yaml
    - name: Get index page
      get:
        url: http://localhost:8080
    ```'''
    params: dict
    '''Parameters to pass to the `requests.request` function.

    Can also be defined as a main level dict value with the HTTP `method` as
    the key. See `method` for details.'''
    loop: str
    '''Loop over the given list of items.'''
    assertions: list[Union[Assertion, str]]
    '''List of assertions to execute after the request is sent.

    Can also be defined with `assert` key.'''
    register: str = None
    '''Register the response object as a variable with the given name.'''
    raise_for_status: bool = True
    '''Raise an exception if the response status code is not ok.'''
    output: str = None
    '''Output the given properties of the response, e.g. `response_json`.'''

    def _parse_options(self, request_dict):
        self.register = request_dict.get('register')
        self.raise_for_status = request_dict.get('raise_for_status', True)
        self.output = request_dict.get('output')


class ParsedRequest(Request):
    def __init__(
            self,
            request_dict: dict,
            template_env: Environment,
            skip=False,
            context: dict = None):
        self._raw = deepcopy(request_dict)
        self._processed = None
        self._template_env = template_env
        self.context = context

        self.id = f'request-{uuid4()}'
        self.state = None
        self.response = None

        self._parse_assertions()

        if skip:
            self._set_state(RequestState.SKIPPED, EARLIER_ERRORS_SKIP)
        else:
            self._process_templates()

        self.name = self._request.pop('name', None)
        self._parse_method_and_params()
        self._parse_options(self._request)

    @property
    def _request(self):
        return self._processed or self._raw

    def _set_state(self, state, message=None):
        self.state = RequestState(state, message)

    def _process_templates(self):
        try:
            self._processed = self._template_env.resolve_templates(
                self._request, self.context)
        except TemplateError as error:
            message = f'Failed to resolve templates: {str(error)}'
            self._set_state(RequestState.ERROR, message=message)

    def _parse_method_and_params(self):
        method_keys = [
            key for key in self._request.keys() if key.upper() in METHODS]

        method = self._request.get('method')
        params = self._request.get('params')
        if method and params:
            self.method = method.upper()
            self.params = params
            if len(method_keys) > 0:
                self._set_state(
                    RequestState.ERROR,
                    NO_HTTP_METHOD)
            return
        if method or params:
            self._set_state(
                RequestState.ERROR,
                METHOD_OR_PARAMS_MISSING)
            return

        if not method_keys or len(method_keys) > 1:
            self._set_state(
                RequestState.ERROR,
                NO_HTTP_METHOD)
            return

        self.method = method_keys[0].upper()
        self.params = self._request.pop(method_keys[0])

    def _parse_assertions(self):
        raw_assertions = self._request.pop('assertions', [])
        if not raw_assertions:
            raw_assertions = self._request.pop('assert', [])

        raw_assertions = ensure_list(raw_assertions)
        self.assertions = [
            ParsedAssertion(raw_assertion) for raw_assertion in raw_assertions]

    def send(self, request_function):
        if self.state is not None:
            return

        try:
            self.response = request_function(self.method, **self.params)
        except RequestException as error:
            self._set_state(RequestState.ERROR, str(error))
            return

        self._template_env.register('response', self.response)
        if self.register:
            self._template_env.register(self.register, self.response)

        if not self.response.ok:
            if self.raise_for_status:
                self._set_state(RequestState.FAILURE)
            else:
                self._set_state(RequestState.NOT_RAISED)
        else:
            self._set_state(RequestState.SUCCESS)

        for assertion in self.assertions:
            try:
                ok = assertion.execute(self._template_env, self.context)
                if not ok:
                    self._set_state(RequestState.FAILURE)
            except BaseException as error:
                self._set_state(RequestState.ERROR, message=str(error))


def parse_request_loop(request_dict: dict,
                       template_env: Environment) -> list[tuple[dict,
                                                                Environment,
                                                                dict]]:
    raw_loop = request_dict.get('loop')
    if not raw_loop:
        return [(request_dict, template_env, None,)]

    loop = template_env.resolve_templates(raw_loop)
    if not isinstance(loop, list):
        raise AssertionError(
            f'Expected loop to be a list, got {type(loop).__name__}.')

    return [(request_dict, template_env, dict(item=i),)
            for i in loop]
