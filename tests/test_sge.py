"""Unit tests for the Stochastic Green Edge prototype.

Run with:  python -m pytest -q   (or)   python tests/test_sge.py
These use only the standard library so they run without extra installs.
"""

from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from sge import SimConfig, Simulator, GreenEdgeEnv  # noqa: E402
from sge.environment import Action  # noqa: E402
from sge.policies import GreedyBaseline, ThresholdPolicy, LyapunovPolicy  # noqa: E402
from sge.stochastic import poisson  # noqa: E402
import random  # noqa: E402


def test_poisson_mean_is_reasonable():
    rng = random.Random(0)
    lam = 3.0
    samples = [poisson(rng, lam) for _ in range(20000)]
    mean = sum(samples) / len(samples)
    assert abs(mean - lam) < 0.15, mean


def test_battery_stays_within_bounds():
    cfg = SimConfig(horizon=200)
    env = GreenEdgeEnv(cfg)
    pol = LyapunovPolicy()
    obs = env.observe()
    while not env.done:
        env.step(pol.act(obs))
        assert -1e-6 <= env.battery <= cfg.battery_capacity + 1e-6
        if not env.done:
            obs = env.observe()


def test_costs_are_non_negative():
    cfg = SimConfig(horizon=100)
    env = GreenEdgeEnv(cfg)
    obs = env.observe()
    while not env.done:
        cost = env.step(Action(local_cycles=cfg.cpu_capacity))
        assert cost.total >= 0.0
        assert cost.grid_energy >= 0.0
        if not env.done:
            obs = env.observe()


def test_reproducible_given_seed():
    cfg = SimConfig(horizon=150)
    sim = Simulator(cfg)
    a = sim.run(GreedyBaseline(), seed=42).total_cost
    b = sim.run(GreedyBaseline(), seed=42).total_cost
    assert a == b


def test_lyapunov_beats_greedy_on_cost():
    """The whole point of the theory: the online controller should not be
    worse than the myopic baseline on total cost (usually clearly better)."""
    cfg = SimConfig(horizon=288)
    sim = Simulator(cfg)
    seeds = list(range(1, 8))
    res = sim.compare([GreedyBaseline(), ThresholdPolicy(), LyapunovPolicy()],
                      seeds=seeds)
    assert res["lyapunov"].total_cost <= res["greedy"].total_cost * 1.001


def _run_all():
    fns = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    for fn in fns:
        fn()
        print(f"ok  {fn.__name__}")
    print(f"\n{len(fns)} tests passed")


if __name__ == "__main__":
    _run_all()
