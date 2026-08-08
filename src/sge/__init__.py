"""Stochastic Green Edge (SGE) prototype.

A small, dependency-free discrete-time simulator for green (renewable-powered)
edge computing. It lets you turn the *theory* of stochastic energy/workload
optimization into runnable experiments:

  - a stochastic environment (renewable harvest, task arrivals),
  - an edge node with a battery, a CPU, and a link to the cloud/grid,
  - pluggable scheduling/energy *policies* (greedy baseline, threshold,
    and a Lyapunov drift-plus-penalty online controller),
  - a cost model + metrics to compare policies on equal footing.

Everything runs on the Python standard library so you can iterate fast.
See ``scripts/run_demo.py`` for an end-to-end comparison.
"""

from .config import SimConfig
from .environment import GreenEdgeEnv
from .simulator import Simulator, EpisodeResult
from . import policies

__all__ = [
    "SimConfig",
    "GreenEdgeEnv",
    "Simulator",
    "EpisodeResult",
    "policies",
]
