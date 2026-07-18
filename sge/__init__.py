"""Stochastic Green Edge (SGE).

Prototipo de Defensa Adaptativa para APIs basada en el Borde (Edge) y Teoria de
Juegos. El paquete implementa un Juego Estocastico No Cooperativo con Informacion
Imperfecta para equilibrar seguridad y sustentabilidad (Green Computing).

Modulos principales:
    - config:        Parametros ponderables del modelo (alpha, beta, gamma, costos).
    - models:        Estructuras de datos (peticiones, acciones, metricas).
    - game_theory:   Motor matematico del Equilibrio de Nash en estrategias mixtas.
    - edge:          Capa Edge (filtro ligero + cerebro matematico).
    - serverless:    Capa Serverless (inspeccion profunda con costo/Cold Start).
    - simulation:    Simulacion de trafico y reporte comparativo.
"""

from .config import DefenseConfig
from .game_theory import NashEquilibrium, build_payoff_matrices, mixed_nash_2x2
from .models import (
    AttackerAction,
    DefenderAction,
    HttpRequest,
    RequestFeatures,
    TrafficClass,
)

__all__ = [
    "DefenseConfig",
    "NashEquilibrium",
    "mixed_nash_2x2",
    "build_payoff_matrices",
    "AttackerAction",
    "DefenderAction",
    "HttpRequest",
    "RequestFeatures",
    "TrafficClass",
]
