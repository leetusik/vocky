"""The ``vocky`` command-line client package.

Re-exports the root Typer ``app`` and the ``main`` console-script entry point.
Later slices add auth/projects/feedback sub-apps in :mod:`vocky.cli.app`.
"""

from vocky.cli.app import app, main

__all__ = ["app", "main"]
