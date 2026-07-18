"""Pruebas del motor matematico de Equilibrio de Nash."""

from __future__ import annotations

import numpy as np
import pytest

from sge.config import DefenseConfig
from sge.game_theory import (
    build_payoff_matrices,
    mixed_nash_2x2,
    solve_for_request,
    suspicion_score,
)
from sge.models import RequestFeatures


def test_matching_pennies_mixed_equilibrium():
    """Matching pennies: el equilibrio mixto es (0.5, 0.5) para ambos jugadores."""
    A = np.array([[1.0, -1.0], [-1.0, 1.0]])   # jugador fila
    B = np.array([[-1.0, 1.0], [1.0, -1.0]])   # jugador columna (juego suma cero)
    eq = mixed_nash_2x2(A, B)
    assert eq.kind == "mixed"
    assert eq.p_green == pytest.approx(0.5, abs=1e-6)
    assert eq.q_light == pytest.approx(0.5, abs=1e-6)


def test_probabilities_are_valid_distributions():
    """Las estrategias del equilibrio deben ser distribuciones de probabilidad."""
    config = DefenseConfig()
    features = RequestFeatures(ip_frequency=20.0, payload_size=3000,
                              user_agent_anomaly=1.0, payload_anomaly=0.9)
    eq = solve_for_request(features, config, serverless_cold=False)
    for prob in (eq.p_green, eq.p_active, eq.q_light, eq.q_advanced):
        assert 0.0 - 1e-9 <= prob <= 1.0 + 1e-9
    assert eq.p_green + eq.p_active == pytest.approx(1.0)
    assert eq.q_light + eq.q_advanced == pytest.approx(1.0)


def test_pure_dominant_strategy_equilibrium():
    """Con una estrategia estrictamente dominante se obtiene un equilibrio puro."""
    # El defensor prefiere fila 0 siempre; el atacante columna 0 siempre.
    A = np.array([[5.0, 4.0], [1.0, 0.0]])
    B = np.array([[3.0, 1.0], [2.0, 0.0]])
    eq = mixed_nash_2x2(A, B)
    assert eq.kind == "pure"
    assert eq.p_green == pytest.approx(1.0)
    assert eq.q_light == pytest.approx(1.0)


def test_higher_suspicion_lowers_green_probability():
    """Mayor sospecha => menor probabilidad de estrategia Verde (mas escalado)."""
    config = DefenseConfig()
    low = RequestFeatures(ip_frequency=1.0, payload_size=100,
                          user_agent_anomaly=0.0, payload_anomaly=0.0)
    high = RequestFeatures(ip_frequency=40.0, payload_size=4000,
                           user_agent_anomaly=1.0, payload_anomaly=1.0)
    assert suspicion_score(low, config) < suspicion_score(high, config)
    eq_low = solve_for_request(low, config, serverless_cold=False)
    eq_high = solve_for_request(high, config, serverless_cold=False)
    assert eq_high.p_green <= eq_low.p_green + 1e-9


def test_cold_start_increases_green_probability():
    """El Cold Start encarece Serverless => el defensor tiende mas a la estrategia Verde."""
    config = DefenseConfig()
    features = RequestFeatures(ip_frequency=15.0, payload_size=2000,
                              user_agent_anomaly=1.0, payload_anomaly=0.7)
    warm = solve_for_request(features, config, serverless_cold=False)
    cold = solve_for_request(features, config, serverless_cold=True)
    assert cold.p_green >= warm.p_green - 1e-9


def test_energy_costs_match_specification():
    """Costos energeticos: Edge=1, Serverless exec=15, Cold Start=25."""
    config = DefenseConfig()
    assert config.energy_edge == 1.0
    assert config.serverless_cost(cold=False) == 15.0
    assert config.serverless_cost(cold=True) == 25.0


def test_payoff_matrix_shapes():
    config = DefenseConfig()
    features = RequestFeatures(ip_frequency=10.0, payload_size=1500,
                              user_agent_anomaly=1.0, payload_anomaly=0.5)
    A, B = build_payoff_matrices(features, config, serverless_cold=False)
    assert A.shape == (2, 2)
    assert B.shape == (2, 2)


def test_nash_indifference_condition():
    """En el equilibrio mixto el atacante es indiferente entre A_L y A_M."""
    config = DefenseConfig()
    features = RequestFeatures(ip_frequency=25.0, payload_size=3500,
                              user_agent_anomaly=1.0, payload_anomaly=1.0)
    eq = solve_for_request(features, config, serverless_cold=False)
    if eq.kind == "mixed":
        d = eq.defender_strategy
        payoff_al = d @ eq.attacker_matrix[:, 0]
        payoff_am = d @ eq.attacker_matrix[:, 1]
        assert payoff_al == pytest.approx(payoff_am, abs=1e-6)
