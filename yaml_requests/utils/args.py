from argparse import ArgumentParser
import json
import os
import yaml

from ciou.types import ensure_list


def get_argparser():
    parser = ArgumentParser()
    parser.add_argument(
        'plan_file',
        type=str,
        nargs='*',
        help='Load requests plan from JSON or YAML file.')
    parser.add_argument(
        '--parallel',
        type=int,
        help='Limit number of parallel executions.')
    parser.add_argument(
        '-v', '--variable',
        action='append',
        dest='variables',
        metavar='NAME:VALUE',
        help=(
            'Define a variable to be used in the requests. '
            'To set multiple variables, use this argument multiple times'))
    parser.add_argument(
        '--no-animation',
        dest='animation',
        action='store_false',
        help='Disable progress animations in console output.')
    parser.add_argument(
        '--no-colors',
        dest='colors',
        action='store_false',
        help='Disable colors in console output.')
    parser.add_argument(
        '--version',
        action='store_true',
        help='Print version information.')

    return parser


def has_known_extension(path):
    for extension in ('.json', '.yaml', '.yml',):
        if path.endswith(extension):
            return True

    return False


def load_plan_files(paths, in_directory=False):
    plans = []

    paths = ensure_list(paths)
    if in_directory:
        paths = sorted(paths)

    for path in paths:
        if os.path.isdir(path):
            plans.extend(load_plan_files((os.path.join(path, i)
                         for i in os.listdir(path)), in_directory=True))
        elif has_known_extension(path) or not in_directory:
            plans.append(load_plan_file(path))

    return plans


def load_plan_file(filename):
    if not filename:
        raise ValueError('No input file given.')

    with open(filename, 'r') as f:
        if filename.endswith('.json'):
            plan = json.load(f)
        elif filename.endswith('.yaml') or filename.endswith('.yml'):
            plan = yaml.load(f, Loader=yaml.SafeLoader)
        else:
            raise ValueError(
                'Failed to recognize file type. '
                'File extension must be json, yaml, or yml.')

    plan['path'] = filename
    return plan


def parse_variables(raw_variables):
    variables = {}

    if not raw_variables:
        return variables

    for raw_variable in raw_variables:
        try:
            key, value = raw_variable.split(':', maxsplit=1)
            variables[key] = value
        except ValueError:
            raise ValueError(
                f'Variable definition "{raw_variable}" has invalid format. '
                'Variables should be defined as NAME:VALUE strings.')

    return variables
