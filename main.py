"""Punto de entrada: simula el flujo de trafico y muestra el reporte final.

Uso:
    python main.py                 # 2000 peticiones, semilla por defecto
    python main.py --requests 5000 --seed 123
    python main.py --demo-nash     # muestra el calculo del Nash para una peticion
"""

from __future__ import annotations

import argparse

from sge.config import DefenseConfig
from sge.edge import EdgeLayer
from sge.game_theory import solve_for_request, suspicion_score
from sge.models import HttpRequest, TrafficClass
from sge.simulation import format_report, generate_traffic, run_simulation


def _demo_nash(config: DefenseConfig) -> None:
    """Muestra el calculo del Equilibrio de Nash para una peticion avanzada sospechosa."""
    edge = EdgeLayer(config)
    request = HttpRequest(
        source_ip="192.0.2.55",
        user_agent="Mozilla/5.0 (Windows NT 10.0) Chrome/124.0",
        payload="POST /api/v1/data " + "A" * 2000 + " '; DROP TABLE users; --",
        true_class=TrafficClass.ADVANCED_ATTACK,
    )
    features = edge.extract_features(request)
    s = suspicion_score(features, config)
    nash = solve_for_request(features, config, serverless_cold=False)

    print("--- DEMO: Equilibrio de Nash para una peticion sospechosa (A_M) ---")
    print(f"Metricas Edge   : ip_freq={features.ip_frequency:.2f}, "
          f"ua_anom={features.user_agent_anomaly:.1f}, "
          f"payload_anom={features.payload_anomaly:.2f}")
    print(f"Sospecha (s)    : {s:.3f}")
    print("Matriz Defensor U_D (filas D_V,D_A | cols A_L,A_M):")
    print(nash.defender_matrix)
    print("Matriz Atacante U_A:")
    print(nash.attacker_matrix)
    print(f"Tipo equilibrio : {nash.kind}")
    print(f"Estrategia Defensor: P(D_V)={nash.p_green:.3f}  P(D_A)={nash.p_active:.3f}")
    print(f"Estrategia Atacante: P(A_L)={nash.q_light:.3f}  P(A_M)={nash.q_advanced:.3f}")
    print(f"Utilidad esperada Defensor: {nash.defender_payoff:.3f}")
    print()


def main() -> None:
    parser = argparse.ArgumentParser(description="Simulacion SGE (Defensa Adaptativa Edge + Nash).")
    parser.add_argument("--requests", type=int, default=2000, help="Numero de peticiones a simular.")
    parser.add_argument("--seed", type=int, default=7, help="Semilla del generador de trafico.")
    parser.add_argument("--demo-nash", action="store_true", help="Muestra el calculo del Nash de ejemplo.")
    args = parser.parse_args()

    config = DefenseConfig()

    if args.demo_nash:
        _demo_nash(config)

    traffic = generate_traffic(args.requests, seed=args.seed)
    report = run_simulation(traffic, config=config, seed=args.seed)
    print(format_report(report))


if __name__ == "__main__":
    main()
