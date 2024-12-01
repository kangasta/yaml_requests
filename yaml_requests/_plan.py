from copy import deepcopy
from os import path
from pathlib import Path

from ciou.types import ensure_list

from .error import (
    InvalidPlanError,
    LoadingPlanDependencyFailedError,
)
from .utils.args import load_json_or_yaml_file


class PlanOptions:
    def __init__(self, plan_dict, options_override=None):
        if options_override is None:
            options_override = {}

        self._options = {**plan_dict.get('options', {}), **options_override}

        self.session = self._options.get('session', False)
        self.ignore_errors = self._options.get('ignore_errors')
        self.repeat_while = self._options.get('repeat_while')
        self.repeat_delay = self._options.get('repeat_delay')


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


class Plan:
    def __init__(
            self,
            plan_dict,
            options_override=None,
            variables_override=None):
        if variables_override is None:
            variables_override = {}

        self._plan = deepcopy(plan_dict)

        self.name = self._plan.pop('name', None)
        self.path = self._plan.pop('path', None)
        self.options = PlanOptions(self._plan, options_override)
        self.variable_files = _resolve_variable_files(
            self._plan.get('variable_files'), self.path)
        self.variables = {
            **self._plan.get('variables', {}),
            **_load_variable_files(self.variable_files),
            **variables_override
        }
        self.requests = self._plan.get('requests')

        if not self.requests or not isinstance(self.requests, list):
            raise AssertionError('Plan must contain requests array.')

    def title(self, display_filename=False):
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
                Plan(
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
