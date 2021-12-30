from jinja2 import __version__ as _jinja2_version
from yaml import __version__ as _pyyaml_version
from requests import __version__ as _requests_version


from .utils.args import (
    get_argparser, load_plan_file, parse_plan, parse_variables)
from ._logger import RequestLogger
from ._runner import PlanRunner
from ._version import __version__


def _print_versions():
    print(
        f'{__version__} ('
        f'jinja2={_jinja2_version}',
        f'pyyaml={_pyyaml_version}',
        f'requests={_requests_version}'
        ')')


NO_PLAN = 251
INVALID_PLAN = 252


def main():
    args = get_argparser().parse_args()
    logger = RequestLogger(animations=args.animation, colors=args.colors)

    if args.version:
        _print_versions()
        exit(0)

    if not args.plan_file:
        logger.error('No requests plan file provided.')
        exit(NO_PLAN)

    variables_override = parse_variables(args.variables)

    try:
        plan = load_plan_file(args.plan_file)
        requests, options, variables = parse_plan(
            plan, variables_override=variables_override)
    except FileNotFoundError:
        logger.error(f'Did not find plan file in {args.plan_file}.')
        exit(NO_PLAN)
    except (ValueError, AssertionError,) as error:
        logger.error(str(error))
        exit(INVALID_PLAN)

    runner = PlanRunner(plan.get('name'), options, variables, logger)
    runner.run(requests)
