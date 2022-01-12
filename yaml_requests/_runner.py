from requests import request, Session

from .utils.template import Environment
from ._request import Request


class PlanRunner:
    def __init__(self, plan, logger):
        self._plan = plan
        self._env = Environment()
        self._session = Session()

        for name, value in self._plan.variables.items():
            self._env.register(name, value)

        self._logger = logger

    def _request(self, *args, **kwargs):
        if self._plan.options.session:
            return self._session.request(*args, **kwargs)
        return request(*args, **kwargs)

    def run(self):
        self._logger.title(self._plan.name, len(self._plan.requests))

        num_errors = 0

        for request_dict in self._plan.requests:
            skip = not self._plan.options.ignore_errors and num_errors > 0

            request = Request(request_dict, self._env, skip)

            if request.state is None:
                self._logger.start_request(request)
                request.send(self._request)

            self._logger.finish_request(request)

            if not request.state.ok:
                num_errors += 1

        return num_errors
