#!/usr/bin/env python3
"""End-to-end demo: compare policies on the Stochastic Green Edge simulator.

Usage:
    python scripts/run_demo.py                # default config, 5 seeds
    python scripts/run_demo.py --seeds 20     # more Monte-Carlo runs
    python scripts/run_demo.py --plot out.png # save a plot (needs matplotlib)

Runs each policy over the *same* stochastic realizations (paired seeds) so the
comparison is fair, then prints a metrics table.
"""

from __future__ import annotations

import argparse
import os
import sys

# make ``src`` importable when run from the repo root
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from sge import SimConfig, Simulator  # noqa: E402
from sge.policies import GreedyBaseline, ThresholdPolicy, LyapunovPolicy  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--seeds", type=int, default=5,
                    help="number of Monte-Carlo seeds to average over")
    ap.add_argument("--horizon", type=int, default=None,
                    help="override number of time slots")
    ap.add_argument("--V", type=float, default=None,
                    help="override Lyapunov penalty weight V")
    ap.add_argument("--plot", type=str, default=None,
                    help="path to save a comparison plot (requires matplotlib)")
    args = ap.parse_args()

    cfg = SimConfig()
    if args.horizon:
        cfg.horizon = args.horizon
    if args.V is not None:
        cfg.lyapunov_V = args.V

    sim = Simulator(cfg)
    policies = [GreedyBaseline(), ThresholdPolicy(), LyapunovPolicy()]
    seeds = list(range(1, args.seeds + 1))

    results = sim.compare(policies, seeds=seeds)

    print(f"\nStochastic Green Edge — {args.seeds} seed(s), "
          f"horizon={cfg.horizon} slots\n" + "-" * 78)
    for name in ("greedy", "threshold", "lyapunov"):
        print(results[name].summary())
    print("-" * 78)

    base = results["greedy"].total_cost
    best = min(results.values(), key=lambda r: r.total_cost)
    if base > 0:
        improvement = 100.0 * (base - best.total_cost) / base
        print(f"best policy: '{best.policy}'  "
              f"({improvement:.1f}% lower cost than greedy baseline)\n")

    if args.plot:
        _plot(results, args.plot)
    return 0


def _plot(results, path: str) -> None:
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except Exception as exc:  # pragma: no cover
        print(f"[plot skipped] matplotlib not available: {exc}")
        return

    fig, axes = plt.subplots(3, 1, figsize=(9, 9), sharex=True)
    for name, r in results.items():
        axes[0].plot(r.backlog_series, label=name)
        axes[1].plot(r.battery_series, label=name)
        axes[2].plot(_cumsum(r.cost_series), label=name)
    axes[0].set_ylabel("backlog (cycles)")
    axes[1].set_ylabel("battery")
    axes[2].set_ylabel("cumulative cost")
    axes[2].set_xlabel("time slot")
    for ax in axes:
        ax.legend()
        ax.grid(alpha=0.3)
    fig.suptitle("Stochastic Green Edge — policy comparison")
    fig.tight_layout()
    fig.savefig(path, dpi=120)
    print(f"saved plot to {path}")


def _cumsum(xs):
    out, s = [], 0.0
    for x in xs:
        s += x
        out.append(s)
    return out


if __name__ == "__main__":
    raise SystemExit(main())
