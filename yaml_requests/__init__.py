"""
.. include:: ../README.md
    :start-after: <!-- Start docs include -->
    :end-before: <!-- End docs include -->

## API Reference
"""

from importlib.metadata import version
__version__ = version('yaml_requests')

from ._main import execute, main, run
from ._plan import Plan, PlanOptions
from ._request import Assertion, Request, RequestOptions


# Hide dataclass constructors from documentation.
for i in (Plan, PlanOptions, Assertion, Request, RequestOptions):
    i.__init__.__doc__ = '@private'


__all__ = [
    'error',
    'Plan',
    'PlanOptions',
    'Request',
    'RequestOptions',
    'Assertion',
]
