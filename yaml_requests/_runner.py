from requests import request, Session

from .utils.template import Environment
from ._request import Request


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

        for request_dict in requests:
            skip = not self._options.get('ignore_errors') and num_errors > 0

            request = Request(request_dict, self._env, skip)

            if request.state is None:
                self._logger.start_request(request)
                request.send(self._request)

            self._logger.finish_request(request)

            if not request.state.ok:
                num_errors += 1

        return num_errors
