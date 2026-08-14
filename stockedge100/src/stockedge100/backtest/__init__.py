"""Stage 2 backtest engine.

The engine's job is not to produce good numbers. It is to produce numbers that are wrong in no way
anybody has thought of yet, and to fail loudly the moment one of them would be.

Every rule it applies — costs, rounding directions, execution timing, corporate actions — was sealed
in ``config/stage2_cost_model.json`` and ``config/stage2_engine_spec.json`` before this package
contained a single line of code. :mod:`stockedge100.backtest.config` refuses to load either file if
its bytes have drifted from the digest recorded in ``governance/STAGE_2_PREREGISTRATION.json``.
"""
