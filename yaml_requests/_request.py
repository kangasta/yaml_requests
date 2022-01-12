from copy import deepcopy
from jinja2.exceptions import TemplateError
from requests.exceptions import RequestException


METHODS = ('GET', 'OPTIONS', 'HEAD', 'POST', 'PUT', 'PATCH', 'DELETE',)
EARLIER_ERRORS_SKIP = 'Request skipped due to earlier error.'
NO_HTTP_METHOD = (
    'Request definition should contain exactly one HTTP method as '
    'a main level dict key.')


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


class RequestOptions:
    def __init__(self, request_dict):
        self.register = request_dict.get('register')
        self.raise_for_status = request_dict.get('raise_for_status', True)
        self.output = request_dict.get('output')


class Assertion:
    def __init__(self, raw_assertion):
        self._ok = None
        if isinstance(raw_assertion, dict):
            self.name = raw_assertion.get('name')
            self.expression = raw_assertion.get('expression')
        else:
            self.name = raw_assertion
            self.expression = raw_assertion

    @property
    def ok(self):
        if self._ok is None:
            raise RuntimeError('Assertion has not been executed yet.')
        return self._ok

    def execute(self, template_env):
        try:
            self._ok = bool(template_env.resolve_expression(self.expression))
        except BaseException:
            self._ok = False
            raise

        return self._ok


class Request:
    def __init__(self, request_dict, template_env, skip=False):
        self._raw = deepcopy(request_dict)
        self._processed = None
        self._template_env = template_env

        self.state = None
        self.response = None

        self._parse_assertions()

        if skip:
            self._set_state(RequestState.SKIPPED, EARLIER_ERRORS_SKIP)
        else:
            self._process_templates()

        self.name = self._request.pop('name', None)
        self._parse_method_and_params()
        self.options = RequestOptions(self._request)

    @property
    def _request(self):
        return self._processed or self._raw

    def _set_state(self, state, message=None):
        self.state = RequestState(state, message)

    def _process_templates(self):
        try:
            self._processed = self._template_env.resolve_templates(
                self._request)
        except TemplateError as error:
            self._set_state(RequestState.ERROR, message=str(error))

    def _parse_method_and_params(self):
        method_keys = [
            key for key in self._request.keys() if key.upper() in METHODS]
        if not method_keys or len(method_keys) > 1:
            self._set_state(
                RequestState.ERROR,
                NO_HTTP_METHOD)
            return

        self.method = method_keys[0].upper()
        self.params = self._request.pop(method_keys[0])

    def _parse_assertions(self):
        raw_assertions = self._request.pop('assert', [])
        if not isinstance(raw_assertions, list):
            raw_assertions = [raw_assertions]

        self.assertions = [
            Assertion(raw_assertion) for raw_assertion in raw_assertions]

    def send(self, request_function):
        if self.state is not None:
            return

        try:
            self.response = request_function(self.method, **self.params)
        except RequestException as error:
            self._set_state(RequestState.ERROR, str(error))
            return

        self._template_env.register('response', self.response)
        if self.options.register:
            self._template_env.register(self.options.register, self.response)

        if not self.response.ok:
            if self.options.raise_for_status:
                self._set_state(RequestState.FAILURE)
            else:
                self._set_state(RequestState.NOT_RAISED)
        else:
            self._set_state(RequestState.SUCCESS)

        for assertion in self.assertions:
            try:
                ok = assertion.execute(self._template_env)
                if not ok:
                    self._set_state(RequestState.FAILURE)
            except BaseException as error:
                self._set_state(RequestState.ERROR, message=str(error))
