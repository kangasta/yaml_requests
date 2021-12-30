import json

from jinja2 import Environment as _J2_Environment, StrictUndefined


def to_json_filter(value):
    str(value)  # Raises UndefinedError if value is StrictUndefined
    return json.dumps(value)


class Environment(_J2_Environment):
    def __init__(self, *args, **kwargs):
        kwargs = {
            'undefined': StrictUndefined,
            **kwargs,
        }

        super().__init__(*args, **kwargs)

        self.filters['to_json'] = to_json_filter

    def register(self, name, value):
        self.globals[name] = value

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

    def _resolve_string(self, str_in):
        if not self._contains_template(str_in):
            return str_in

        if self._is_template(str_in):
            str_in = str_in.replace('}}', ' | to_json }}')
        template = self.from_string(str_in)
        rendered = template.render()

        if 'to_json' in str_in:
            try:
                return json.loads(rendered)
            except Exception:
                pass

        return rendered

    def _resolve_dict(self, item):
        return {key: self.resolve_templates(value)
                for key, value in item.items()}

    def _resolve_list(self, item):
        return [self.resolve_templates(i) for i in item]

    def resolve_templates(self, item):
        if isinstance(item, str):
            return self._resolve_string(item)
        elif isinstance(item, list):
            return self._resolve_list(item)
        elif isinstance(item, dict):
            return self._resolve_dict(item)
        else:
            return item

    def resolve_expression(self, expr):
        return self.compile_expression(expr)()
