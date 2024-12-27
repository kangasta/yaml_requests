NO_PLAN = 251
'''Exit code for `NoPlanError`.'''
INVALID_PLAN = 252
'''Exit code for `InvalidPlanError`.'''
INTERRUPTED = 253
'''Exit code for `InterruptedError`.'''
UNKNOWN_ERROR = 254
'''Exit code for unknown errors.'''


UNKNOWN_ERROR_MSG = (
    'Caught unexpected error, see traceback and description below. '
    'If this seems like a bug to you, please consider creating a issue in '
    f'https://github.com/kangasta/yaml_requests/issues.\n'
)


class YamlRequestsError(Exception):
    '''Base class for `yaml_requests` errors.'''

    def __init__(self, message, exit_code):
        super().__init__(message)
        self.exit_code = exit_code
        '''Exit code for the error.'''


class NoPlanError(YamlRequestsError):
    '''No plan file was provided or provided file was not found.'''

    def __init__(self, path=None):
        if not path:
            super().__init__('No requests plan file provided.', NO_PLAN)
        else:
            super().__init__(
                f'Did not find plan file in {", ".join(path)}.', NO_PLAN)


class InvalidPlanError(YamlRequestsError):
    '''Parsing the plan file failed.'''

    def __init__(self, message):
        super().__init__(message, INVALID_PLAN)


class LoadingPlanDependencyFailedError(InvalidPlanError):
    '''Failed to load a plan dependency. For example, parsing a variable file
    failed.'''

    def __init__(self, message):
        super().__init__(message)


class InterruptedError(YamlRequestsError):
    '''The execution was interrupted by the user.'''

    def __init__(self):
        super().__init__('', INTERRUPTED)
