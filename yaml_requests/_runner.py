from datetime import datetime, timedelta
from requests import request, Session
from requests.cookies import cookiejar_from_dict

from ciou.types import ensure_list

from .utils.template import Environment
from ._request import Request


PASS = 0
FAIL = 1
TOTAL = 2


class ListCounter:
    def __init__(self, input):
        if isinstance(input, list):
            self._data = list(input)
        else:
            self._data = [0] * input

    def increment(self, position):
        self._data[position] += 1

    def __getitem__(self, i):
        return self._data[i]

    @property
    def data(self):
        return list(self._data)

    def __add__(self, other):
        if isinstance(other, list):
            other = ListCounter(other)
        return ListCounter([sum(i) for i in zip(self.data, other.data)])


class PlansRunner:
    def __init__(self, plans, logger):
        self._plans = plans
        self._logger = logger

    def run(self):
        n_requests = ListCounter(3)
        n_plans = ListCounter(3)

        start = datetime.now()

        for plan in ensure_list(self._plans):
            display_filename = len(self._plans) > 1
            runner = PlanRunner(plan, self._logger, display_filename)
            n = runner.run()
            n_requests += n
            n_plans.increment(FAIL if n[FAIL] else PASS)
            n_plans.increment(TOTAL)

        elapsed = (datetime.now() - start).total_seconds()

        summary = [
            ('Plans', n_plans.data),
            ('Requests', n_requests.data),
            ('Elapsed', f'{elapsed:.3f} s')
        ]
        if n_plans[TOTAL] == 1:
            summary = summary[1:]
        self._logger.summary(summary)

        return n_requests[FAIL]


class PlanRunner:
    def __init__(self, plan, logger, display_filename=False):
        self._plan = plan
        self._display_filename = display_filename

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

    @property
    def _title(self):
        name = self._plan.name
        if not self._display_filename:
            return name

        path = self._plan.path
        if name and path:
            return f'{name} ({path})'

        return path or name

    def run(self):
        n = ListCounter(3)

        repeat_index = 0 if self._has_repeat_condition() else None

        break_repeat = False
        repeat_while = True

        ignore_errors = self._plan.options.ignore_errors

        while repeat_while and not break_repeat:
            self._env.register('repeat_index', repeat_index)
            self._logger.title(
                self._title,
                len(self._plan.requests),
                repeat_index=repeat_index)

            self._logger.start()

            for request_dict in self._plan.requests:
                skip = not ignore_errors and n[FAIL] > 0

                request = Request(request_dict, self._env, skip)

                if request.state is None:
                    self._logger.start_request(request)
                    request.send(self._request)

                self._logger.finish_request(request)

                if not request.state.ok:
                    n.increment(FAIL)
                elif request.response is not None:
                    n.increment(PASS)
                n.increment(TOTAL)

            self._logger.close()

            break_repeat = not ignore_errors and n[FAIL] > 0
            repeat_while = (
                True if repeat_index == 0 else self._check_repeat_condition())

            if self._has_repeat_condition():
                repeat_index += 1

        return n.data
