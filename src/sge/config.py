"""Configuration for the Stochastic Green Edge simulator.

All physical quantities use simple, self-consistent units so the prototype
stays readable. Tune these to match a real deployment later.

Units
-----
- energy:   "energy units" (think Wh scaled). Battery, harvest and demand share it.
- compute:  "cycles" per task; CPU capacity is cycles/slot.
- time:     discrete slots (e.g. 1 slot = 5 minutes).
- cost:     abstract cost units combined by the weights below.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class SimConfig:
    # ----- horizon -----
    horizon: int = 288            # number of time slots (288 * 5min = 24h)
    slots_per_day: int = 288      # used to build the diurnal renewable curve
    seed: int = 7                 # master RNG seed (reproducibility)

    # ----- workload (stochastic task arrivals) -----
    arrival_rate: float = 5.0     # mean tasks/slot (Poisson); near CPU capacity
                                  # so scheduling/energy decisions actually matter
    task_cycles_mean: float = 1.0 # mean compute demand per task (cycles)
    task_deadline_slots: int = 6  # slots before a queued task is "late"

    # ----- edge node compute -----
    cpu_capacity: float = 6.0     # cycles processable locally per slot
    energy_per_cycle: float = 1.0 # energy to process one cycle locally

    # ----- renewable source (stochastic, diurnal) -----
    solar_peak: float = 10.0      # peak harvest at solar noon (energy/slot)
    solar_noise: float = 0.35     # multiplicative noise std (clouds)

    # ----- battery -----
    battery_capacity: float = 60.0
    battery_init: float = 20.0
    battery_efficiency: float = 0.95  # round-trip-ish charge efficiency

    # ----- grid + cloud offload -----
    grid_carbon: float = 1.0      # carbon per unit of grid energy bought
    grid_price: float = 1.0       # monetary price per unit of grid energy
    cloud_cost_per_cycle: float = 0.6  # rental fee to offload one cycle to cloud
    cloud_latency: float = 1.0    # latency penalty per offloaded cycle

    # ----- cost weights (the objective the policy minimizes) -----
    w_latency: float = 1.0        # weight on queueing/latency (backlog + late)
    w_grid: float = 1.5           # weight on grid energy (price + carbon)
    w_cloud: float = 1.0          # weight on cloud rental

    # ----- Lyapunov controller -----
    lyapunov_V: float = 20.0      # penalty weight (cost vs. stability tradeoff)
    battery_target: float = 30.0  # perturbation / desired battery operating point

    def validate(self) -> "SimConfig":
        assert self.horizon > 0
        assert self.cpu_capacity > 0
        assert 0.0 < self.battery_efficiency <= 1.0
        assert self.battery_init <= self.battery_capacity
        return self
