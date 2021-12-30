from requests import request, Session
from requests.exceptions import RequestException
from .utils.template import Environment

METHODS = ('GET', 'OPTIONS', 'HEAD', 'POST', 'PUT', 'PATCH', 'DELETE',)
EARLIER_ERRORS_SKIP = 'Request skipped due to earlier error.'
NO_RAISE_FOR_STATUS = 'raise_for_status was set to False.'


def _parse_method_and_params(request):
    method_keys = [key for key in request.keys() if key.upper() in METHODS]
    if not method_keys or len(method_keys) > 1:
        raise AssertionError(
            'Request definition should contain exactly one HTTP method as '
            'a main level dict key.')

    method = method_keys[0].upper()
    params = request.get(method_keys[0])

    return (method, params,)


class PlanRunner:
    def __init__(self, name, options, variables, logger):
        self._name = name
        self._options = options
        self._env = Environment()
        self._session = Session()

        for name, value in variables.items():
            self._env.register(name, value)

        self._logger = logger

    def _request(self, *args, **kwargs):
        if self._options.get('session'):
            return self._session.request(*args, **kwargs)
        return request(*args, **kwargs)

    def run(self, requests):
        self._logger.title(self._name, len(requests))

        num_errors = 0

        for request in requests:
            processed_request = self._env.resolve_templates(request)
            method, params = _parse_method_and_params(processed_request)
            self._logger.start(processed_request.get('name'), method, params)

            if not self._options.get('ignore_errors') and num_errors > 0:
                self._logger.finish(
                    processed_request.get('name'),
                    method,
                    params,
                    message=EARLIER_ERRORS_SKIP,
                    message_type='SKIPPED')
                continue

            try:
                response = self._request(method, **params)
            except RequestException as error:
                self._logger.finish(
                    processed_request.get('name'),
                    method,
                    params,
                    message=str(error),
                    message_type='ERROR')

                num_errors += 1
                continue

            self._env.register('response', response)

            message_dict = dict()
            if not response.ok:
                if processed_request.get('raise_for_status', True):
                    num_errors += 1
                else:
                    message_dict = dict(
                        message_type='NOT-RAISED',
                        message=NO_RAISE_FOR_STATUS)

            self._logger.finish(
                processed_request.get('name'),
                method,
                params,
                response,
                **message_dict)

        return num_errors
