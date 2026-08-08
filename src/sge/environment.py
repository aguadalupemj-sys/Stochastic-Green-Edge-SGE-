"""The Green Edge environment: one edge node powered by renewables + battery + grid.

Discrete-time dynamics per slot ``t``:

  1. Stochastic arrivals add tasks (cycles) to the queue; harvest is realized.
  2. The *policy* chooses an ``Action`` (how many cycles to run locally, how
     many to offload to the cloud, and how much grid energy to buy).
  3. The environment enforces energy/compute feasibility, updates the battery
     and the task queue, and returns the per-slot cost breakdown.

The energy dispatch rule (fixed, so policies stay comparable):
  - Local compute is served first by *renewable + purchased grid* energy.
  - Any remaining deficit is covered by the battery, then by emergency grid.
  - Any surplus (renewable/bought over demand) charges the battery (with loss);
    energy beyond battery capacity is spilled.
"""

from __future__ import annotations

import random
from dataclasses import dataclass, field

from .config import SimConfig
from .stochastic import WorkloadProcess, RenewableProcess, Task


@dataclass
class Action:
    """A policy decision for one slot."""
    local_cycles: float = 0.0   # cycles to process on the edge CPU
    offload_cycles: float = 0.0  # cycles to send to the cloud
    grid_buy: float = 0.0       # energy proactively bought from the grid


@dataclass
class Observation:
    """What a policy can see before deciding (fully observable prototype)."""
    slot: int
    backlog_cycles: float       # total remaining cycles queued
    num_tasks: int
    oldest_age: int             # slots the oldest queued task has waited
    battery: float
    harvest: float              # renewable available this slot
    cfg: SimConfig


@dataclass
class SlotCost:
    """Per-slot cost breakdown (all non-negative)."""
    latency: float = 0.0
    grid: float = 0.0
    cloud: float = 0.0
    # bookkeeping (not part of the objective, useful for analysis)
    grid_energy: float = 0.0
    renewable_used: float = 0.0
    renewable_spilled: float = 0.0
    late_tasks: int = 0
    processed_cycles: float = 0.0

    @property
    def total(self) -> float:
        return self.latency + self.grid + self.cloud


class GreenEdgeEnv:
    """Stateful simulation of a single green edge node."""

    def __init__(self, cfg: SimConfig, seed: int | None = None):
        self.cfg = cfg.validate()
        self.seed = cfg.seed if seed is None else seed
        self.reset()

    # ------------------------------------------------------------------ setup
    def reset(self) -> Observation:
        rng = random.Random(self.seed)
        # independent streams so policy-side randomness never perturbs the world
        self._workload = WorkloadProcess(
            random.Random(rng.random() * 1e9),
            self.cfg.arrival_rate, self.cfg.task_cycles_mean,
            self.cfg.task_deadline_slots)
        self._renewable = RenewableProcess(
            random.Random(rng.random() * 1e9),
            self.cfg.slots_per_day, self.cfg.solar_peak, self.cfg.solar_noise)

        self.slot = 0
        self.battery = self.cfg.battery_init
        self.queue: list[Task] = []
        self._harvest = 0.0
        self._advance_world()  # realize arrivals + harvest for slot 0
        return self.observe()

    # --------------------------------------------------------------- dynamics
    def _advance_world(self) -> None:
        """Realize the stochastic inputs for the current slot."""
        self.queue.extend(self._workload.arrivals(self.slot))
        self._harvest = self._renewable.harvest(self.slot)

    def observe(self) -> Observation:
        backlog = sum(t.cycles for t in self.queue)
        oldest_age = 0
        if self.queue:
            oldest_age = self.slot - min(t.arrival_slot for t in self.queue)
        return Observation(
            slot=self.slot,
            backlog_cycles=backlog,
            num_tasks=len(self.queue),
            oldest_age=oldest_age,
            battery=self.battery,
            harvest=self._harvest,
            cfg=self.cfg,
        )

    def _process(self, cycles: float) -> float:
        """Remove up to ``cycles`` of work from the FIFO queue. Returns done."""
        remaining = cycles
        done = 0.0
        while remaining > 1e-9 and self.queue:
            task = self.queue[0]
            take = min(task.cycles, remaining)
            task.cycles -= take
            remaining -= take
            done += take
            if task.cycles <= 1e-9:
                self.queue.pop(0)
        return done

    def step(self, action: Action) -> SlotCost:
        cfg = self.cfg
        cost = SlotCost()

        # --- clamp the action to what is physically possible ---
        backlog = sum(t.cycles for t in self.queue)
        local = max(0.0, min(action.local_cycles, cfg.cpu_capacity, backlog))
        offload = max(0.0, min(action.offload_cycles, backlog - local))
        grid_buy = max(0.0, action.grid_buy)

        # --- compute: local first (FIFO), then the offloaded portion ---
        cost.processed_cycles = self._process(local)
        self._process(offload)  # cloud handles these instantly for this prototype

        # --- energy dispatch for the local compute ---
        demand_e = cost.processed_cycles * cfg.energy_per_cycle
        inflow = self._harvest + grid_buy
        cost.renewable_used = min(self._harvest, demand_e)

        if inflow >= demand_e:
            surplus = inflow - demand_e
            # charge battery with round-trip loss; spill the rest
            room = cfg.battery_capacity - self.battery
            stored = min(room, surplus * cfg.battery_efficiency)
            self.battery += stored
            cost.renewable_spilled = max(0.0, surplus - stored / cfg.battery_efficiency)
            grid_energy = grid_buy
        else:
            deficit = demand_e - inflow
            from_batt = min(self.battery, deficit)
            self.battery -= from_batt
            emergency = deficit - from_batt  # forced grid purchase
            grid_energy = grid_buy + emergency
            cost.renewable_spilled = 0.0

        cost.grid_energy = grid_energy

        # --- cost model ---
        cost.grid = grid_energy * (cfg.grid_price + cfg.grid_carbon) * 0.5 * cfg.w_grid
        cost.cloud = offload * cfg.cloud_cost_per_cycle * cfg.w_cloud

        # latency: backlog carried over + explicit lateness penalty
        remaining_backlog = sum(t.cycles for t in self.queue)
        late = sum(1 for t in self.queue if self.slot >= t.deadline_slot)
        cost.late_tasks = late
        cost.latency = cfg.w_latency * (remaining_backlog + late)

        # --- advance time and realize the next slot's stochastic inputs ---
        self.slot += 1
        if self.slot < cfg.horizon:
            self._advance_world()
        return cost

    @property
    def done(self) -> bool:
        return self.slot >= self.cfg.horizon
