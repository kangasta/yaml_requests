from argparse import ArgumentParser
import json
import yaml


def get_argparser():
    parser = ArgumentParser()
    parser.add_argument(
        'plan_file',
        type=str,
        nargs='?',
        help='Load requests plan from JSON or YAML file.')
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
