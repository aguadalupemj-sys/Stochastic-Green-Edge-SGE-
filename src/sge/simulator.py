"""Run policies against the environment and collect metrics."""

from __future__ import annotations

from dataclasses import dataclass, field

from .config import SimConfig
from .environment import GreenEdgeEnv
from .policies import Policy


@dataclass
class EpisodeResult:
    policy: str
    total_cost: float = 0.0
    grid_energy: float = 0.0
    cloud_cycles: float = 0.0
    processed_cycles: float = 0.0
    renewable_used: float = 0.0
    renewable_spilled: float = 0.0
    late_task_slots: int = 0       # sum over slots of late-task counts
    peak_backlog: float = 0.0
    slots: int = 0
    # per-slot series (handy for plotting)
    cost_series: list[float] = field(default_factory=list)
    battery_series: list[float] = field(default_factory=list)
    backlog_series: list[float] = field(default_factory=list)

    @property
    def renewable_utilization(self) -> float:
        total = self.renewable_used + self.renewable_spilled
        return self.renewable_used / total if total > 0 else 0.0

    def summary(self) -> str:
        return (
            f"{self.policy:>10} | cost={self.total_cost:9.1f} "
            f"| grid_E={self.grid_energy:8.1f} "
            f"| cloud={self.cloud_cycles:7.1f} "
            f"| late={self.late_task_slots:5d} "
            f"| renew_util={self.renewable_utilization*100:5.1f}%"
        )


class Simulator:
    def __init__(self, cfg: SimConfig):
        self.cfg = cfg.validate()

    def run(self, policy: Policy, seed: int | None = None) -> EpisodeResult:
        env = GreenEdgeEnv(self.cfg, seed=seed)
        policy.reset()
        res = EpisodeResult(policy=policy.name)

        obs = env.observe()
        while not env.done:
            action = policy.act(obs)
            cost = env.step(action)

            res.total_cost += cost.total
            res.grid_energy += cost.grid_energy
            res.cloud_cycles += action.offload_cycles
            res.processed_cycles += cost.processed_cycles
            res.renewable_used += cost.renewable_used
            res.renewable_spilled += cost.renewable_spilled
            res.late_task_slots += cost.late_tasks
            res.peak_backlog = max(res.peak_backlog, obs.backlog_cycles)
            res.slots += 1

            res.cost_series.append(cost.total)
            res.battery_series.append(env.battery)
            res.backlog_series.append(obs.backlog_cycles)

            if not env.done:
                obs = env.observe()
        return res

    def compare(self, policies: list[Policy],
                seeds: list[int] | None = None) -> dict[str, EpisodeResult]:
        """Run each policy over one or more seeds and average the totals.

        Using the *same* seeds for every policy gives a fair, paired comparison
        (identical arrival/harvest realizations).
        """
        seeds = seeds or [self.cfg.seed]
        out: dict[str, EpisodeResult] = {}
        for policy in policies:
            agg = EpisodeResult(policy=policy.name)
            last: EpisodeResult | None = None
            for s in seeds:
                r = self.run(policy, seed=s)
                agg.total_cost += r.total_cost
                agg.grid_energy += r.grid_energy
                agg.cloud_cycles += r.cloud_cycles
                agg.processed_cycles += r.processed_cycles
                agg.renewable_used += r.renewable_used
                agg.renewable_spilled += r.renewable_spilled
                agg.late_task_slots += r.late_task_slots
                agg.peak_backlog = max(agg.peak_backlog, r.peak_backlog)
                agg.slots += r.slots
                last = r
            n = len(seeds)
            agg.total_cost /= n
            agg.grid_energy /= n
            agg.cloud_cycles /= n
            agg.processed_cycles /= n
            agg.renewable_used /= n
            agg.renewable_spilled /= n
            agg.late_task_slots = int(agg.late_task_slots / n)
            # keep one representative set of series for plotting
            if last is not None:
                agg.cost_series = last.cost_series
                agg.battery_series = last.battery_series
                agg.backlog_series = last.backlog_series
            out[policy.name] = agg
        return out
