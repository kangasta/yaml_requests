from os import system
import platform
from traceback import print_exc

from jinja2 import __version__ as _jinja2_version
from yaml import __version__ as _pyyaml_version
from requests import __version__ as _requests_version

from .utils.args import get_argparser, load_plan_file, parse_variables
from ._logger import RequestLogger
from ._plan import Plan
from ._runner import PlanRunner
from ._version import __version__


UNKNOWN_ERROR_MSG = (
    'Caught unexpected error, see traceback and description below. '
    'If this seems like a bug to you, please consider creating a issue in '
    'https://github.com/kangasta/yaml_requests/issues.\n'
)


def _print_versions():
    print(
        f'{__version__} ('
        f'jinja2={_jinja2_version}',
        f'pyyaml={_pyyaml_version}',
        f'requests={_requests_version}'
        ')')


NO_PLAN = 251
INVALID_PLAN = 252
INTERRUPTED = 253
UNKNOWN_ERROR = 254


def main():
    # On windows, run shell command to enable ANSI code support
    if platform.system() == 'Windows':
        system('')

    args = get_argparser().parse_args()
    logger = RequestLogger(animations=args.animation, colors=args.colors)

    try:
        if args.version:
            _print_versions()
            return 0

        if not args.plan_file:
            logger.error('No requests plan file provided.')
            return NO_PLAN

        variables_override = parse_variables(args.variables)

        try:
            plan_dict = load_plan_file(args.plan_file)
            plan = Plan(plan_dict, variables_override=variables_override)
        except FileNotFoundError:
            logger.error(f'Did not find plan file in {args.plan_file}.')
            return NO_PLAN
        except (ValueError, AssertionError,) as error:
            logger.error(str(error))
            return INVALID_PLAN

        runner = PlanRunner(plan, logger)
        num_errors = runner.run()
        return min(num_errors, 250)
    except KeyboardInterrupt:
        logger.stop_progress_animation()
        return INTERRUPTED
    except BaseException:
        logger.stop_progress_animation()
        logger.error(UNKNOWN_ERROR_MSG)
        print_exc()
        return UNKNOWN_ERROR
