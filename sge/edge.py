"""Capa Edge: Filtro Ligero + Cerebro Matematico.

Funcion de paso rapido y consumo energetico minimo (C_energy ~ 1 unidad). Extrae
metricas de la peticion HTTP (frecuencia de IP, tamano del payload, anomalia del
User-Agent) y ejecuta el motor de Teoria de Juegos para decidir, en tiempo real,
si escalar a la capa Serverless.

El filtro Edge puede mitigar por si mismo ataques LIGEROS/ruidosos (rate limiting,
User-Agent anomalo), pero NO puede detectar ataques AVANZADOS que imitan trafico
legitimo: estos requieren inspeccion profunda (Serverless).
"""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass

import numpy as np

from .config import DefenseConfig
from .game_theory import NashEquilibrium, solve_for_request, suspicion_score
from .models import DefenderAction, HttpRequest, RequestFeatures

# User-Agents considerados "normales" (navegadores comunes).
_KNOWN_GOOD_UA_TOKENS = ("mozilla", "chrome", "safari", "firefox", "edg")


@dataclass
class EdgeDecision:
    """Decision tomada por la capa Edge para una peticion."""

    features: RequestFeatures
    suspicion: float
    escalate: bool                 # True => activar Serverless (D_A)
    action: DefenderAction
    nash: NashEquilibrium | None   # None cuando el fast-path evita el calculo
    edge_blocked: bool             # True si el filtro Edge mitigo un ataque ligero
    energy_spent: float            # Energia consumida por el propio Edge


class EdgeLayer:
    """Filtro ligero que extrae metricas y ejecuta el cerebro matematico."""

    def __init__(self, config: DefenseConfig, rng: np.random.Generator | None = None) -> None:
        self._config = config
        self._rng = rng or np.random.default_rng()
        # Ventana deslizante de IPs recientes para estimar frecuencia (rate).
        self._recent_ips: deque[str] = deque(maxlen=200)
        self.total_energy: float = 0.0
        # Umbral de sospecha por debajo del cual se aplica el fast-path verde.
        self._fast_path_threshold = 0.12
        # Umbrales del filtro Edge (rate-limiting / firma de bot) para frenar
        # ataques ligeros/ruidosos sin invocar la costosa capa Serverless.
        self._edge_block_ip_frequency = 1.5


    def extract_features(self, request: HttpRequest) -> RequestFeatures:
        """Extrae metricas ligeras de la peticion (bajo costo, C_energy ~ 0)."""
        self._recent_ips.append(request.source_ip)
        ip_count = sum(1 for ip in self._recent_ips if ip == request.source_ip)
        window = max(len(self._recent_ips), 1)
        # Frecuencia relativa escalada al tamano de la ventana.
        ip_frequency = ip_count / window * 100.0

        ua = request.user_agent.lower()
        ua_anomaly = 0.0 if any(tok in ua for tok in _KNOWN_GOOD_UA_TOKENS) else 1.0

        # Anomalia estructural del payload: payloads muy grandes o con tokens de
        # inyeccion elevan la anomalia (heuristica ligera del Edge).
        size = request.payload_size
        size_anomaly = float(np.clip((size - 512) / 4096.0, 0.0, 1.0))
        # Tokens de inyeccion clasica (SQL/XSS/traversal) y de inyeccion de prompts
        # (ataques a APIs respaldadas por modelos de lenguaje).
        injection_tokens = (
            "<script", "union select", "../", "'; drop", "${", "eval(",
            "ignore previous", "ignore all previous", "disregard", "system:",
            "you are now", "act as", "jailbreak", "reveal your", "prompt:",
        )
        token_anomaly = 0.6 if any(tok in request.payload.lower() for tok in injection_tokens) else 0.0
        payload_anomaly = float(np.clip(size_anomaly + token_anomaly, 0.0, 1.0))

        return RequestFeatures(
            ip_frequency=ip_frequency,
            payload_size=size,
            user_agent_anomaly=ua_anomaly,
            payload_anomaly=payload_anomaly,
        )

    def decide(self, request: HttpRequest, serverless_cold: bool) -> EdgeDecision:
        """Extrae metricas, calcula el Equilibrio de Nash y decide si escalar.

        Returns:
            EdgeDecision con la accion elegida (GREEN o ACTIVE).
        """
        # El Edge siempre consume su costo minimo por procesar la peticion.
        self.total_energy += self._config.energy_edge

        features = self.extract_features(request)
        s = suspicion_score(features, self._config)

        # Filtro Edge (barato): un patron de bot ruidoso (User-Agent anomalo y
        # alta frecuencia de IP) se mitiga en el borde mediante rate-limiting,
        # sin gastar energia Serverless ni ejecutar el juego. Los ataques
        # avanzados imitan trafico legitimo y NO son frenados aqui.
        if features.user_agent_anomaly >= 1.0 and features.ip_frequency > self._edge_block_ip_frequency:
            return EdgeDecision(
                features=features,
                suspicion=s,
                escalate=False,
                action=DefenderAction.GREEN,
                nash=None,
                edge_blocked=True,
                energy_spent=self._config.energy_edge,
            )

        # Fast-path Verde: trafico claramente benigno no invoca el motor completo.
        if s < self._fast_path_threshold:
            return EdgeDecision(
                features=features,
                suspicion=s,
                escalate=False,
                action=DefenderAction.GREEN,
                nash=None,
                edge_blocked=False,
                energy_spent=self._config.energy_edge,
            )

        # Trafico sospechoso: se resuelve el Equilibrio de Nash en estrategias mixtas.
        nash = solve_for_request(features, self._config, serverless_cold)

        # Muestreo de la estrategia mixta del Defensor: Verde con prob. p, Activa con 1-p.
        escalate = self._rng.random() >= nash.p_green
        action = DefenderAction.ACTIVE if escalate else DefenderAction.GREEN

        return EdgeDecision(
            features=features,
            suspicion=s,
            escalate=escalate,
            action=action,
            nash=nash,
            edge_blocked=False,
            energy_spent=self._config.energy_edge,
        )
