from copy import deepcopy
from dataclasses import dataclass
from os import path
from pathlib import Path

from ciou.types import ensure_list

from .error import (
    InvalidPlanError,
    LoadingPlanDependencyFailedError,
)
from ._request import Request
from .utils.args import load_json_or_yaml_file


@dataclass
class PlanOptions:
    '''Options for controlling the execution of the plan.'''

    session: bool = False
    '''Use session to keep cookies between requests.'''
    ignore_errors: bool = None
    '''Continue executing requests even if one of them fails.'''
    repeat_while: str = None
    '''Expression that determines if the plan should be repeated.'''
    repeat_delay: int = None
    '''Time to sleep in seconds before repeating the plan.'''

    @classmethod
    def _from_dict(cls, options_dict=None, options_override=None):
        if options_dict is None:
            options_dict = {}

        if options_override is None:
            options_override = {}

        return cls(**{**options_dict, **options_override})


def _resolve_variable_files(variable_files, plan_path=None):
    if not variable_files:
        return []

    resolved = []
    for f in variable_files:
        paths = [f]
        if path.isfile(f):
            resolved.append(f)
            continue

        if plan_path:
            plan_relative = path.join(
                path.dirname(path.realpath(plan_path)), Path(f))
            paths.append(plan_relative)
            if path.isfile(plan_relative):
                resolved.append(plan_relative)
                continue

        raise LoadingPlanDependencyFailedError(
            f'Failed to resolve variable file {f}: '
            f'File {f} not found from {" or ".join(paths)}.')

    return resolved


def _load_variable_files(files):
    variables = {}

    if not files:
        return variables

    for f in files:
        try:
            data = load_json_or_yaml_file(f)
        except Exception as e:
            raise LoadingPlanDependencyFailedError(
                f'Failed to load variable file {f}: {str(e)}')
        if not isinstance(data, dict):
            raise LoadingPlanDependencyFailedError(
                f'Failed to load variable file {f}: '
                'The top level data-type in variable file must be an object.')
        variables = {**variables, **data}

    return variables


@dataclass
class Plan:
    '''A plan that contains requests to be executed consecutively.'''

    name: str
    '''Human readable description for the plan.'''
    path: str
    '''Path to the plan file.'''
    options: PlanOptions
    '''Options for controlling the execution of the plan. See `PlanOptions`
    for details.'''
    variable_files: list[str]
    '''List of paths to variable files.'''
    variables: dict
    '''Variables to be used in the plan.'''
    requests: list[Request]
    '''List of requests to be executed.'''

    @classmethod
    def _from_dict(
            cls,
            input_dict,
            options_override=None,
            variables_override=None):
        if variables_override is None:
            variables_override = {}

        plan_dict = deepcopy(input_dict)

        path = plan_dict.pop('path', None)
        variable_files = _resolve_variable_files(
            plan_dict.get('variable_files'), path)
        variables = {
            **plan_dict.get('variables', {}),
            **_load_variable_files(variable_files),
            **variables_override
        }

        requests = plan_dict.get('requests')
        if not requests or not isinstance(requests, list):
            raise AssertionError('Plan must contain requests array.')

        return cls(
            name=plan_dict.pop('name', None),
            path=path,
            options=PlanOptions._from_dict(
                plan_dict.get('options'), options_override),
            variable_files=variable_files,
            variables=variables,
            requests=requests
        )

    def _title(self, display_filename=False):
        if not display_filename:
            return self.name

        if self.name and self.path:
            return f'{self.name} ({self.path})'

        return self.path or self.name


class InvalidPlan:
    def __init__(self, path, plan_dict, error):
        self.path = path
        self.plan_dict = plan_dict
        self.error = error


def build_plans(
    plan_dicts, paths, variables_override
) -> tuple[list[Plan], list[InvalidPlan]]:
    plans = []
    invalid_plans = {}

    paths = ensure_list(paths)

    for plan_dict in plan_dicts:
        plan_path = plan_dict['path']

        try:
            plans.append(
                Plan._from_dict(
                    plan_dict,
                    variables_override=variables_override))
        except (ValueError, AssertionError,) as error:
            invalid_plans[path.realpath(plan_path)] = InvalidPlan(
                plan_path,
                plan_dict,
                InvalidPlanError(str(error))
            )

    # Ignore InvalidPlanError if the plan that caused it is a variable file
    # used by other plan unless the file was explicitly defined by the user.
    if invalid_plans:
        abs_paths = [path.realpath(i) for i in paths]
        for plan in plans:
            for variable_file in plan.variable_files:
                abs_variable_file = path.realpath(variable_file)
                if (abs_variable_file not in abs_paths and
                        abs_variable_file in invalid_plans):
                    invalid_plans.pop(abs_variable_file)

    return plans, list(invalid_plans.values())
