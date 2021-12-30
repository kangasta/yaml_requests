from requests import request, Session
from requests.exceptions import RequestException
from .utils.template import Environment

METHODS = ('GET', 'OPTIONS', 'HEAD', 'POST', 'PUT', 'PATCH', 'DELETE',)


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

        for request in requests:
            processed_request = self._env.resolve_templates(request)
            method, params = _parse_method_and_params(processed_request)
            self._logger.start(processed_request.get('name'), method, params)

            try:
                response = self._request(method, **params)
            except RequestException as error:
                self._logger.finish(processed_request.get(
                    'name'), method, params, error=str(error))

                if self._options.get('raise_for_status'):
                    break
                else:
                    continue

            self._env.register('response', response)

            self._logger.finish(
                processed_request.get('name'),
                method,
                params,
                response)

            if self._options.get('raise_for_status') and not response.ok:
                break
