class ScrapydError(Exception):
    """Base class for exceptions from within this package"""


class MissingRequiredArgument(ScrapydError):
    """Raised if a required argument is missing"""


class RunnerError(ScrapydError):
    """Raised if the runner returns an error code"""
