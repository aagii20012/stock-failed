"""The engine's failure vocabulary.

Each class names one way a backtest can lie. They are separate types rather than one generic error
because a test must be able to assert that a *specific* defect was caught: an assertion that "some
exception was raised" would pass for the wrong reason as readily as the right one.

Every one of these is fatal. Nothing in this package catches an engine error and continues — an
engine that logs a broken invariant and carries on is exactly the engine Gate 2 exists to reject.
"""

from __future__ import annotations


class BacktestError(RuntimeError):
    """Base class for every engine failure."""


class LookAheadError(BacktestError):
    """Information was requested that was not available at the simulated decision time."""


class FillTimingError(BacktestError):
    """A fill was attempted at or before its own decision session."""


class DuplicateOrderError(BacktestError):
    """The same order was admitted twice, or two live orders exist for one symbol on one session."""


class CorporateActionError(BacktestError):
    """A split or dividend was applied in a way that does not conserve value."""


class DelistingError(BacktestError):
    """A position survived the final session of its own price series."""


class InvariantViolation(BacktestError):
    """A cash, exposure, ordering, or sign invariant failed."""


class DataIntegrityHalt(BacktestError):
    """Stale data ran longer than the sealed limit; the run stops rather than guessing."""


class WindowViolation(BacktestError):
    """A session outside the authorized research window was requested."""


class ConfigViolation(BacktestError):
    """A sealed configuration file has drifted, or is being used outside its declared scope."""
