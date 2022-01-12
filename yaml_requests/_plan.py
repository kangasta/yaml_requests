from copy import deepcopy


class PlanOptions:
    def __init__(self, plan_dict, options_override=None):
        if options_override is None:
            options_override = {}

        self._options = {**plan_dict.get('options', {}), **options_override}

        self.session = self._options.get('session', False)
        self.ignore_errors = self._options.get('ignore_errors')


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
        self.options = PlanOptions(self._plan, options_override)
        self.variables = {
            **self._plan.get('variables', {}), **variables_override}
        self.requests = self._plan.get('requests')

        if not self.requests or not isinstance(self.requests, list):
            raise AssertionError('Plan must contain requests array.')
