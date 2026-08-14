"""Stage 3 strategy families — Gate 3, ``development_admissibility``.

Everything in this package is downstream of a seal. ``config/stage3_strategy_protocol.json`` and
``config/stage3_gate_criteria.json`` were written and hashed into
``governance/STAGE_3_PREREGISTRATION.json`` before any file in this directory existed. No symbol,
lookback, threshold, entry rule, exit rule, or benchmark is written as a literal here; each is read
back out of the sealed protocol at load time, and :mod:`stockedge100.strategies.config` refuses to
load a file whose digest has drifted.

Constitution §8 bounds what may be here: strategy families are tested **independently**, no machine
learning is authorized for Generation 1, and combining strategies is prohibited until each component
has an independent verdict. There is accordingly no ensemble, no meta-model, no fitted parameter,
and no cross-candidate comparison anywhere in this package.
"""
