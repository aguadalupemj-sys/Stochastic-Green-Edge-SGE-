"""Capa Serverless: Inspeccion Profunda con costo energetico y Cold Start.

Funcion robusta que realiza sanitizacion exhaustiva y validacion criptografica del
payload. Permanece inactiva a menos que el motor de Teoria de Juegos decida
activarla (Estrategia Activa D_A). Modela el fenomeno de Cold Start: la primera
invocacion (o tras un periodo de inactividad) es mas costosa energeticamente.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass

from .config import DefenseConfig
from .models import HttpRequest, TrafficClass


@dataclass
class DeepInspectionResult:
    """Resultado de la inspeccion profunda."""

    threat_detected: bool
    energy_spent: float
    cold_start: bool
    integrity_hash: str


class ServerlessLayer:
    """Simula una funcion Serverless con estado de calentamiento (warm/cold)."""

    def __init__(self, config: DefenseConfig) -> None:
        self._config = config
        self._last_invocation_step: int | None = None
        self.total_energy: float = 0.0
        self.invocations: int = 0
        self.cold_starts: int = 0

    def is_cold(self, step: int) -> bool:
        """Determina si la proxima invocacion en `step` incurriria en Cold Start."""
        if self._last_invocation_step is None:
            return True
        return (step - self._last_invocation_step) > self._config.serverless_warm_ttl

    def inspect(self, request: HttpRequest, step: int) -> DeepInspectionResult:
        """Ejecuta la inspeccion profunda del payload.

        La sanitizacion profunda detecta de forma fiable tanto ataques ligeros como
        avanzados (a diferencia del Edge, que solo frena los ligeros/ruidosos).
        """
        cold = self.is_cold(step)
        energy = self._config.serverless_cost(cold)

        self.total_energy += energy
        self.invocations += 1
        if cold:
            self.cold_starts += 1
        self._last_invocation_step = step

        # Validacion criptografica simulada (integridad del payload).
        integrity_hash = hashlib.sha256(request.payload.encode("utf-8")).hexdigest()

        # Sanitizacion exhaustiva: cualquier clase de ataque es detectada aqui.
        threat = request.true_class in (
            TrafficClass.LIGHT_ATTACK,
            TrafficClass.ADVANCED_ATTACK,
        )
        return DeepInspectionResult(
            threat_detected=threat,
            energy_spent=energy,
            cold_start=cold,
            integrity_hash=integrity_hash,
        )
