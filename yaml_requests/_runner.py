from requests import request, Session
from requests.cookies import cookiejar_from_dict

from .utils.template import Environment
from ._request import Request


class PlanRunner:
    def __init__(self, plan, logger):
        self._plan = plan
        self._env = Environment()
        self._prepare_session()

        for name, value in self._env.resolve_templates(
                self._plan.variables).items():
            self._env.register(name, value)

        self._logger = logger

    def _prepare_session(self):
        session_option = self._plan.options.session
        if not session_option:
            self._session = None
            return

        self._session = Session()

        if isinstance(session_option, dict):
            session_dict = self._env.resolve_templates(session_option)
            self._session.headers.update(session_dict.get('headers', {}))
            self._session.cookies.update(
                cookiejar_from_dict(
                    session_dict.get(
                        'cookies', {})))

    def _request(self, *args, **kwargs):
        if self._plan.options.session:
            return self._session.request(*args, **kwargs)
        return request(*args, **kwargs)

    def _has_repeat_condition(self):
        return bool(self._plan.options.repeat_while)

    def _check_repeat_condition(self):
        repeat_while = self._plan.options.repeat_while
        if isinstance(repeat_while, str):
            return bool(self._env.resolve_expression(repeat_while))

        return bool(repeat_while)

    def run(self):
        num_errors = 0
        repeat_index = 0 if self._has_repeat_condition() else None

        break_repeat = False
        repeat_while = True

        ignore_errors = self._plan.options.ignore_errors

        while repeat_while and not break_repeat:
            self._env.register('repeat_index', repeat_index)
            self._logger.title(
                self._plan.name,
                len(self._plan.requests),
                repeat_index=repeat_index)

            for request_dict in self._plan.requests:
                skip = not ignore_errors and num_errors > 0

                request = Request(request_dict, self._env, skip)

                if request.state is None:
                    self._logger.start_request(request)
                    request.send(self._request)

                self._logger.finish_request(request)

                if not request.state.ok:
                    num_errors += 1

            break_repeat = not ignore_errors and num_errors > 0
            repeat_while = (
                True if repeat_index == 0 else self._check_repeat_condition())

            if self._has_repeat_condition():
                repeat_index += 1

        return num_errors
