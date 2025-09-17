"""
Rich logging configuration for Scrapyd.

This module provides enhanced logging with rich formatting for terminal output.
It integrates with both Python's standard logging and Twisted's logging system.
"""

import logging
import sys
from typing import Optional

from rich.console import Console
from rich.logging import RichHandler
from rich.text import Text
from twisted.logger import Logger, LogLevel, globalLogBeginner
from twisted.python import log as twistedLog


class RichTwistedLogObserver:
    """Custom Twisted log observer that uses Rich for formatting."""

    def __init__(self, console: Optional[Console] = None):
        self.console = console or Console(stderr=True)
        self.level_colors = {
            LogLevel.debug: "dim white",
            LogLevel.info: "blue",
            LogLevel.warn: "yellow",
            LogLevel.error: "red",
            LogLevel.critical: "bold red",
        }

    def __call__(self, event):
        """Process a Twisted log event."""
        # Skip if not meant for terminal output
        if not sys.stderr.isatty():
            return

        level = event.get("log_level", LogLevel.info)
        message = event.get("log_format", "")

        # Handle formatted messages
        if "log_format" in event:
            try:
                message = event["log_format"].format(**event)
            except (KeyError, ValueError):
                # Fallback to string representation if formatting fails
                message = str(event.get("log_format", ""))

        # Create rich-formatted message
        level_name = level.name.upper()
        level_color = self.level_colors.get(level, "white")

        # Get logger name from system or namespace
        logger_name = event.get("log_namespace", "scrapyd")
        if logger_name.startswith("scrapyd."):
            logger_name = logger_name[8:]  # Remove 'scrapyd.' prefix

        # Format the log message
        timestamp = Text.from_markup("[dim]" +
                                   event.get("log_time", "").strftime("%Y-%m-%d %H:%M:%S")
                                   if event.get("log_time") else "" + "[/dim]")

        level_text = Text(f"[{level_name}]", style=level_color)
        logger_text = Text(f"{logger_name}:", style="cyan")
        message_text = Text(message, style="white")

        # Combine parts
        if timestamp:
            full_message = Text.assemble(timestamp, " ", level_text, " ", logger_text, " ", message_text)
        else:
            full_message = Text.assemble(level_text, " ", logger_text, " ", message_text)

        self.console.print(full_message)


def setup_rich_logging(console: Optional[Console] = None, enable_twisted: bool = True,
                      enable_standard: bool = True) -> Console:
    """
    Set up rich logging for both Twisted and standard Python logging.

    Args:
        console: Rich console instance to use. If None, creates a new one.
        enable_twisted: Whether to set up Twisted logging with Rich.
        enable_standard: Whether to set up Python logging with Rich.

    Returns:
        The console instance used for logging.
    """
    if console is None:
        console = Console(stderr=True)

    # Set up standard Python logging with Rich
    if enable_standard:
        rich_handler = RichHandler(
            console=console,
            show_time=True,
            show_path=True,
            show_level=True,
            markup=True,
            rich_tracebacks=True,
            tracebacks_show_locals=True,
        )
        rich_handler.setFormatter(logging.Formatter(
            fmt="[%(name)s] %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S"
        ))

        # Configure root logger
        root_logger = logging.getLogger()

        # Remove existing handlers to avoid duplicate output
        for handler in root_logger.handlers[:]:
            root_logger.removeHandler(handler)

        root_logger.addHandler(rich_handler)
        root_logger.setLevel(logging.INFO)

        # Configure scrapyd loggers
        for logger_name in ["scrapyd", "scrapy"]:
            logger = logging.getLogger(logger_name)
            logger.setLevel(logging.INFO)

    # Set up Twisted logging with Rich
    if enable_twisted:
        rich_observer = RichTwistedLogObserver(console)

        # Begin logging with our rich observer
        globalLogBeginner.beginLoggingTo([rich_observer])

        # Also redirect Twisted's log to our observer
        twistedLog.addObserver(rich_observer)

    return console


def get_rich_logger(name: str) -> logging.Logger:
    """
    Get a logger configured to use Rich formatting.

    Args:
        name: Logger name

    Returns:
        Configured logger instance
    """
    return logging.getLogger(name)


def get_twisted_logger(namespace: str = "scrapyd") -> Logger:
    """
    Get a Twisted logger with the specified namespace.

    Args:
        namespace: Logger namespace

    Returns:
        Twisted Logger instance
    """
    return Logger(namespace=namespace)