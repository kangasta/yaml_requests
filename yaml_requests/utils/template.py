import json
from os import getenv, path
from pathlib import Path

from jinja2.exceptions import TemplateError
from jinja2.nativetypes import NativeEnvironment as _J2_NativeEnvironment
from jinja2 import StrictUndefined


class TemplateDependencyError(TemplateError):
    def __init__(self, message):
        super().__init__(message)


def to_json_filter(value):
    str(value)  # Raises UndefinedError if value is StrictUndefined
    return json.dumps(value)


class Environment(_J2_NativeEnvironment):
    def __init__(self, *args, **kwargs):
        self.path = kwargs.pop('path', None)
        kwargs = {
            'undefined': StrictUndefined,
            **kwargs,
        }

        super().__init__(*args, **kwargs)

        self.globals['lookup'] = self.lookup
        self.globals['open'] = self.open
        self.filters['to_json'] = to_json_filter

    def register(self, name, value):
        self.globals[name] = value

    def open(self, src, mode='rb'):
        paths = [src]
        if self.path:
            paths.append(
                path.join(path.dirname(path.realpath(self.path)), Path(src)))

        for i in paths:
            try:
                return open(i, mode)
            except FileNotFoundError:
                pass

        raise TemplateDependencyError(
            f'File {src} not found from {" or ".join(paths)}')

    def _lookup_file(self, src):
        f = self.open(src, "r")
        content = f.read()
        f.close()
        return content

    def lookup(self, value, src):
        if value == 'env':
            return getenv(src)
        elif value == 'file':
            return self._lookup_file(src)

        raise ValueError(f'Unknown lookup source: {value}')

    def get(self, name):
        return self.globals.get(name)

    def _contains_template(self, str_in):
        has_start = self.variable_start_string in str_in
        has_end = self.variable_end_string in str_in
        return has_start and has_end

    def _is_template(self, str_in):
        start_eq = str_in.startswith(self.variable_start_string)
        end_eq = str_in.endswith(self.variable_end_string)
        single_start_eq = str_in.count(self.variable_start_string) == 1
        return start_eq and single_start_eq and end_eq

    def _resolve_string(self, str_in, context=None) -> any:
        if not self._contains_template(str_in):
            return str_in

        inputs = [str_in]
        if self._is_template(str_in):
            # If input is a template, append to_json filter to maintain
            # original data type. This requires wrapping template expression
            # from user in parentheses to avoid issues with operator
            # predendence.
            with_to_json = str_in.replace('{{', '{{ (')
            with_to_json = with_to_json.replace('}}', ') | to_json }}')
            inputs = [with_to_json, *inputs]

        errors = []
        for i in inputs:
            template = self.from_string(i)
            try:
                rendered = template.render(**(context or {}))
            except TypeError as e:
                # If rendering fails, try to render without to_json filter.
                # This is the case, for example, when using the open filter.
                errors.append(str(e))
                continue

            if 'to_json' in i:
                try:
                    loaded = json.loads(rendered)
                    if isinstance(loaded, dict):
                        return rendered
                    return loaded
                except Exception:
                    pass

            return rendered

        raise TypeError(
            'Failed to render template. (' +
            ', '.join(f'- {e}' for e in errors) +
            ')'
        )

    def _resolve_dict(self, item, context) -> dict:
        return {key: self.resolve_templates(value, context)
                for key, value in item.items()}

    def _resolve_list(self, item, context) -> list:
        return [self.resolve_templates(i, context) for i in item]

    def resolve_templates(self, item, context=None) -> any:
        if isinstance(item, str):
            return self._resolve_string(item, context)
        elif isinstance(item, list):
            return self._resolve_list(item, context)
        elif isinstance(item, dict):
            return self._resolve_dict(item, context)
        else:
            return item

    def resolve_expression(self, expr, context=None):
        return self.compile_expression(expr)(**(context or {}))
