from os import system
import platform
from traceback import print_exc

from jinja2 import __version__ as _jinja2_version
from yaml import __version__ as _pyyaml_version
from requests import __version__ as _requests_version

from . import __version__
from .utils.args import get_argparser, load_plan_files, parse_variables
from .logger import ConsoleLogger
from ._plan import build_plans
from ._runner import PlansRunner
from .error import (
    NoPlanError,
    InterruptedError,
    InvalidPlanError,
    YamlRequestsError,
    INVALID_PLAN,
    UNKNOWN_ERROR,
    UNKNOWN_ERROR_MSG,
)


def _print_versions():
    print(
        f'{__version__} ('
        f'jinja2={_jinja2_version}',
        f'pyyaml={_pyyaml_version}',
        f'requests={_requests_version}'
        ')')


def main():
    '''Run the application.

    Returns:
        int: Exit code
    '''

    # On windows, run shell command to enable ANSI code support
    if platform.system() == 'Windows':
        system('')

    args = get_argparser().parse_args()

    if args.version:
        _print_versions()
        return 0

    logger = ConsoleLogger(animations=args.animation, colors=args.colors)

    try:
        variables_override = parse_variables(args.variables)
    except ValueError as error:
        logger.error(str(error))
        return INVALID_PLAN

    try:
        num_errors = run(
            args.plan_file,
            logger,
            variables_override,
            args.parallel)
        return min(num_errors, 250)
    except YamlRequestsError as error:
        logger.error(str(error))
        return error.exit_code
    except BaseException:
        logger.close()
        logger.error(UNKNOWN_ERROR_MSG)
        print_exc()
        return UNKNOWN_ERROR


def execute():
    '''Run the application and exit with suitable exit code.

    This is the entrypoint of the application.
    '''
    code = main()
    exit(code)


def run(plan_path, logger, variables_override=None, parallel=None):
    try:
        if not plan_path:
            raise NoPlanError()

        try:
            plan_dicts = load_plan_files(plan_path)
            plans, invalid_plans = build_plans(
                plan_dicts, plan_path, variables_override)
        except FileNotFoundError:
            raise NoPlanError(plan_path)
        except (ValueError, AssertionError,) as error:
            raise InvalidPlanError(str(error))

        if invalid_plans:
            logger.skipped_plan(plans, invalid_plans)
            raise InvalidPlanError('')

        runner = PlansRunner(plans, logger, parallel)
        return runner.run()
    except KeyboardInterrupt:
        logger.close()
        raise InterruptedError()
