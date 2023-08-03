from importlib.metadata import version
__version__ = version('yaml_requests')

from ._main import execute, main, run
