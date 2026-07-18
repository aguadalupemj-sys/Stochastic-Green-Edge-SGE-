"""Pruebas de la simulacion de trafico y del reporte comparativo."""

from __future__ import annotations

from sge.config import DefenseConfig
from sge.models import TrafficClass
from sge.simulation import generate_traffic, run_simulation


def test_traffic_mix_is_approximately_80_15_5():
    traffic = generate_traffic(5000, seed=3)
    counts = {cls: 0 for cls in TrafficClass}
    for req in traffic:
        counts[req.true_class] += 1
    total = len(traffic)
    assert 0.75 <= counts[TrafficClass.LEGIT] / total <= 0.85
    assert 0.11 <= counts[TrafficClass.LIGHT_ATTACK] / total <= 0.19
    assert 0.02 <= counts[TrafficClass.ADVANCED_ATTACK] / total <= 0.08


def test_adaptive_saves_energy_vs_baseline():
    traffic = generate_traffic(2000, seed=7)
    report = run_simulation(traffic, config=DefenseConfig(), seed=7)
    assert report.adaptive_energy < report.baseline_energy
    assert report.energy_saved > 0
    assert report.energy_saved_pct > 0


def test_high_advanced_mitigation_rate():
    """La defensa adaptativa debe mitigar la mayoria de los ataques avanzados."""
    traffic = generate_traffic(3000, seed=11)
    report = run_simulation(traffic, config=DefenseConfig(), seed=11)
    assert report.advanced_total > 0
    assert report.advanced_mitigation_rate >= 0.6


def test_light_attacks_fully_mitigated_by_edge_or_serverless():
    """Los ataques ligeros siempre son mitigados (Edge los frena o Serverless los inspecciona)."""
    traffic = generate_traffic(2000, seed=5)
    report = run_simulation(traffic, config=DefenseConfig(), seed=5)
    assert report.light_mitigated == report.light_total


def test_report_totals_are_consistent():
    traffic = generate_traffic(1500, seed=9)
    report = run_simulation(traffic, config=DefenseConfig(), seed=9)
    assert report.total_requests == 1500
    assert report.attacks_total == report.light_total + report.advanced_total
    assert report.attacks_mitigated + report.breaches == report.attacks_total
