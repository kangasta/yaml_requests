NO_PLAN = 251
INVALID_PLAN = 252
INTERRUPTED = 253
UNKNOWN_ERROR = 254


UNKNOWN_ERROR_MSG = (
    'Caught unexpected error, see traceback and description below. '
    'If this seems like a bug to you, please consider creating a issue in '
    f'https://github.com/kangasta/yaml_requests/issues.\n'
)


class YamlRequestsError(Exception):
    def __init__(self, message, exit_code):
        super().__init__(message)
        self.exit_code = exit_code


class NoPlanError(YamlRequestsError):
    def __init__(self, path=None):
        if not path:
            super().__init__('No requests plan file provided.', NO_PLAN)
        else:
            super().__init__(
                f'Did not find plan file in {", ".join(path)}.', NO_PLAN)


class InvalidPlanError(YamlRequestsError):
    def __init__(self, message):
        super().__init__(message, INVALID_PLAN)


class InterruptedError(YamlRequestsError):
    def __init__(self):
        super().__init__('', INTERRUPTED)
