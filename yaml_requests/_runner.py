from datetime import datetime
from io import StringIO
from jinja2.exceptions import TemplateError
from multiprocessing import cpu_count
from multiprocessing.pool import ThreadPool
from requests import request, Session
from requests.cookies import cookiejar_from_dict
from time import sleep

from ciou.color import bold
from ciou.progress import MessageStatus, Update
from ciou.types import ensure_list

from .error import LoadingPlanDependencyFailedError
from .utils.template import Environment
from ._request import ParsedRequest, parse_request_loop


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
    def __init__(self, plans, logger, parallel=None):
        self._plans = plans
        self._logger = logger
        self._parallel = min(len(self._plans),
                             parallel if parallel else cpu_count())

    def run(self):
        n_requests = ListCounter(3)
        n_plans = ListCounter(3)

        start = datetime.now()

        plans = ensure_list(self._plans)
        if self._parallel == 1:
            results = map(self._run_single_series, plans)
        else:
            self._logger.start()
            pool = ThreadPool(self._parallel)
            results = pool.map(self._run_single_parallel, self._plans)
            pool.close()
            self._logger.close()

        for n in results:
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

    def _run_single_series(self, plan):
        display_filename = len(self._plans) > 1
        runner = PlanRunner(plan, self._logger, display_filename)
        return runner.run()

    def _run_single_parallel(self, plan):
        out = StringIO()
        logger = self._logger.copy(target=out, log_started=False)
        runner = PlanRunner(plan, logger, True, False)

        self._logger.push(Update(
            key=plan.path,
            message=bold(runner.title),
            status=MessageStatus.STARTED,
        ))

        n = runner.run()
        status = MessageStatus.ERROR if n[FAIL] else MessageStatus.SUCCESS
        out.seek(0)

        self._logger.push(Update(
            key=plan.path,
            message=bold(runner.title),
            details=out.read(),
            status=status,
        ))

        return n


class PlanRunner:
    def __init__(self, plan, logger, display_filename=False, print_name=True):
        self._plan = plan
        self._display_filename = display_filename
        self._print_name = print_name

        self._env = Environment()
        self._prepare_session()

        try:
            for name, value in self._env.resolve_templates(
                    self._plan.variables).items():
                self._env.register(name, value)
        except TemplateError as e:
            raise LoadingPlanDependencyFailedError(
                f'Failed to load plan variables: {str(e)}')

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
    def title(self):
        return self._plan._title(self._display_filename)

    def run(self):
        n = ListCounter(3)

        repeat_index = 0 if self._has_repeat_condition() else None

        repeat_while = True

        ignore_errors = self._plan.options.ignore_errors

        while repeat_while:
            if repeat_index:
                if self._plan.options.repeat_delay:
                    sleep(self._plan.options.repeat_delay)

            self._env.register('repeat_index', repeat_index)
            self._logger.title(
                self.title if self._print_name else None,
                len(self._plan.requests),
                repeat_index=repeat_index)

            self._logger.start()

            for request_dict in self._plan.requests:
                args_loop = parse_request_loop(request_dict, self._env)
                for args in args_loop:
                    request_dict, template_env, context = args
                    skip = not ignore_errors and n[FAIL] > 0
                    request = ParsedRequest(
                        request_dict, template_env, skip, context)

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

            if not ignore_errors and n[FAIL] > 0:
                break

            repeat_while = self._check_repeat_condition()

            if self._has_repeat_condition():
                repeat_index += 1

        return n.data
