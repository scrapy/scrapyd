class ScrapydError(Exception):
    """Base class for exceptions from within this package"""


class ConfigError(ScrapydError):
    """Raised if a configuration error prevents Scrapyd from starting"""


class InvalidUsernameError(ConfigError):
    """Raised if the username contains a colon"""

    def __init__(self):
        super().__init__(
            "The `username` option contains illegal character ':'. Check and update the Scrapyd configuration file."
        )


class BadEggError(ScrapydError):
    """Raised if the egg is invalid"""


class DirectoryTraversalError(ScrapydError):
    """Raised if the resolved path is outside the expected directory"""


class ProjectNotFoundError(ScrapydError):
    """Raised if a project isn't found in an IEggStorage implementation"""


class EggNotFoundError(ScrapydError):
    """Raised if an egg isn't found in an IEggStorage implementation"""


class RunnerError(ScrapydError):
    """Raised if the runner returns an error code"""
