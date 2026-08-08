"""Scheduling / energy policies.

A policy maps an ``Observation`` to an ``Action``. This is the core place
where *theory* becomes *algorithm*. We ship three references:

  - ``GreedyBaseline``   : run everything you can locally, buy grid on deficit.
  - ``ThresholdPolicy``  : offload/charge based on simple queue/battery rules.
  - ``LyapunovPolicy``   : online drift-plus-penalty controller (no forecasts).

All policies share the same interface so they are directly comparable in the
simulator.
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from .config import SimConfig
from .environment import Action, Observation


class Policy(ABC):
    name: str = "policy"

    @abstractmethod
    def act(self, obs: Observation) -> Action:  # pragma: no cover - interface
        ...

    def reset(self) -> None:
        """Clear any internal state between episodes."""
        pass


class GreedyBaseline(Policy):
    """Myopic: process as much as the CPU allows; never offload; never
    pre-buy grid energy (deficits are covered by emergency grid).

    This is the "do the obvious thing" strawman to beat.
    """
    name = "greedy"

    def act(self, obs: Observation) -> Action:
        local = min(obs.cfg.cpu_capacity, obs.backlog_cycles)
        return Action(local_cycles=local, offload_cycles=0.0, grid_buy=0.0)


class ThresholdPolicy(Policy):
    """Heuristic with two knobs:

      - if the queue is backed up beyond the CPU, offload the overflow to cloud;
      - opportunistically charge the battery from cheap/abundant renewable.
    """
    name = "threshold"

    def __init__(self, offload_backlog_factor: float = 2.0):
        self.offload_backlog_factor = offload_backlog_factor

    def act(self, obs: Observation) -> Action:
        cfg = obs.cfg
        local = min(cfg.cpu_capacity, obs.backlog_cycles)
        overflow = obs.backlog_cycles - local
        offload = 0.0
        if overflow > self.offload_backlog_factor * cfg.cpu_capacity:
            offload = overflow - self.offload_backlog_factor * cfg.cpu_capacity

        # Charge battery when the sun is strong and the battery is low.
        grid_buy = 0.0
        if obs.harvest > cfg.cpu_capacity * cfg.energy_per_cycle and \
                obs.battery < 0.5 * cfg.battery_capacity:
            grid_buy = 0.0  # renewable surplus already charges the battery
        return Action(local_cycles=local, offload_cycles=offload, grid_buy=grid_buy)


class LyapunovPolicy(Policy):
    """Online drift-plus-penalty controller.

    Idea (Neely-style stochastic network optimization): keep two virtual
    queues stable while greedily minimizing a penalty each slot.

      - Data queue  Q  = backlog of cycles (must stay bounded => throughput).
      - Battery queue X = (battery - target); we keep the battery near a target
        operating point using a perturbation, so it neither empties nor saturates.

    Each slot we choose the action minimizing:

        V * penalty(action)  +  drift_terms(action)

    where ``penalty`` is the real per-slot cost (grid + cloud) and the drift
    terms push work out of the data queue and steer the battery to target.
    No forecasts of future harvest/arrivals are required: decisions use only
    the *current* observation, which is what makes this practical.
    """
    name = "lyapunov"

    def __init__(self, V: float | None = None):
        self.V = V  # override cfg.lyapunov_V if provided

    def act(self, obs: Observation) -> Action:
        cfg = obs.cfg
        V = cfg.lyapunov_V if self.V is None else self.V

        Q = obs.backlog_cycles                 # data queue backlog
        X = obs.battery - cfg.battery_target   # battery deviation from target

        # ---- decide LOCAL compute ----
        # Draining the queue reduces drift by ~Q per cycle. The cost of a local
        # cycle is its energy: free if covered by renewable/battery, else grid.
        # Marginal grid cost per local cycle (only when we must buy):
        renew_cycles = obs.harvest / cfg.energy_per_cycle
        batt_cycles = max(0.0, obs.battery) / cfg.energy_per_cycle
        free_cycles = renew_cycles + batt_cycles

        local_cap = min(cfg.cpu_capacity, Q)
        # Serve "free" cycles as long as they reduce drift (Q>0). Serving from
        # the battery is discouraged when the battery is below target (X<0).
        local = 0.0
        # 1) cycles fully covered by renewable are almost always worth it.
        local += min(local_cap, renew_cycles)
        remaining_cap = local_cap - local
        # 2) battery cycles: worth it if drift gain V-less term beats steering.
        #    Draining battery increases -X pressure by ~ energy_per_cycle * (-X)/... ;
        #    approximate: run battery cycles while Q outweighs battery deficit push.
        if remaining_cap > 0 and Q > 0:
            # weight: prefer draining queue (Q) vs. keeping battery near target.
            batt_pressure = max(0.0, -X)  # how far below target we are
            if Q >= batt_pressure:
                local += min(remaining_cap, batt_cycles)
                remaining_cap = local_cap - local
        # 3) grid-powered local cycles: only if queue drift beats grid penalty.
        grid_unit_cost = (cfg.grid_price + cfg.grid_carbon) * 0.5 * cfg.w_grid
        if remaining_cap > 0 and Q > V * grid_unit_cost:
            local += remaining_cap
            remaining_cap = 0.0

        local = min(local, local_cap)

        # ---- decide OFFLOAD (cloud) ----
        # Offloading a cycle removes ~Q of drift at penalty V*cloud_cost/cycle.
        remaining_backlog = Q - local
        offload = 0.0
        cloud_unit = cfg.cloud_cost_per_cycle * cfg.w_cloud
        if remaining_backlog > 0 and Q > V * cloud_unit:
            offload = remaining_backlog  # relieve everything the drift justifies

        # ---- decide GRID pre-buy to steer the battery to target ----
        # If the battery is below target (X<0), buying now stabilizes X; the
        # drift-plus-penalty tradeoff buys only when the deficit outweighs V*cost.
        grid_buy = 0.0
        if X < 0 and (-X) > V * grid_unit_cost:
            room = cfg.battery_capacity - obs.battery
            grid_buy = min(room, -X)

        return Action(local_cycles=local, offload_cycles=offload, grid_buy=grid_buy)


REGISTRY: dict[str, type[Policy]] = {
    GreedyBaseline.name: GreedyBaseline,
    ThresholdPolicy.name: ThresholdPolicy,
    LyapunovPolicy.name: LyapunovPolicy,
}


def make_policy(name: str) -> Policy:
    if name not in REGISTRY:
        raise KeyError(f"unknown policy '{name}'. available: {list(REGISTRY)}")
    return REGISTRY[name]()
