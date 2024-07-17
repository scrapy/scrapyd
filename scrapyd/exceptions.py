class ScrapydError(Exception):
    """Base class for exceptions from within this package"""


class RunnerError(ScrapydError):
    """Raised if the runner returns an error code"""
