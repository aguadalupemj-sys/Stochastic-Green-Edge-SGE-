"""Estructuras de datos del dominio: peticiones HTTP, metricas y acciones del juego."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class TrafficClass(str, Enum):
    """Etiqueta REAL (ground truth) de una peticion. Solo se usa para evaluacion.

    El sistema de defensa NUNCA observa esta etiqueta (informacion imperfecta);
    unicamente infiere sospecha a partir de metricas del Edge.
    """

    LEGIT = "legit"                # Usuario legitimo
    LIGHT_ATTACK = "light_attack"  # Bot automatico ruidoso (Ataque Ligero, A_L)
    ADVANCED_ATTACK = "advanced_attack"  # Hacker dirigido (Ataque Avanzado, A_M)


class DefenderAction(str, Enum):
    """Acciones puras del Defensor."""

    GREEN = "D_V"   # Estrategia Verde: solo Edge (energia minima)
    ACTIVE = "D_A"  # Estrategia Activa: escalar a Serverless (inspeccion profunda)


class AttackerAction(str, Enum):
    """Acciones puras del Atacante."""

    LIGHT = "A_L"     # Ataque ligero / ruidoso
    ADVANCED = "A_M"  # Ataque avanzado / dirigido


@dataclass
class RequestFeatures:
    """Metricas ligeras extraidas por la capa Edge a partir de la peticion HTTP.

    Attributes:
        ip_frequency: Frecuencia relativa de la IP origen en la ventana reciente [0, inf).
        payload_size: Tamano del payload en bytes.
        user_agent_anomaly: Anomalia del User-Agent en [0, 1] (0 = normal, 1 = anomalo).
        payload_anomaly: Anomalia estructural del payload en [0, 1].
    """

    ip_frequency: float
    payload_size: int
    user_agent_anomaly: float
    payload_anomaly: float


@dataclass
class HttpRequest:
    """Peticion HTTP simulada."""

    source_ip: str
    user_agent: str
    payload: str
    true_class: TrafficClass = field(default=TrafficClass.LEGIT)

    @property
    def payload_size(self) -> int:
        return len(self.payload.encode("utf-8"))
