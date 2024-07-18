class ScrapydError(Exception):
    """Base class for exceptions from within this package"""


class DirectoryTraversalError(ScrapydError):
    """Raised if the resolved path is outside the expected directory"""


class RunnerError(ScrapydError):
    """Raised if the runner returns an error code"""
