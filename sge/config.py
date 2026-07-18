"""Parametrizacion del modelo de defensa adaptativa.

Todos los pesos y costos de la funcion de utilidad del Defensor son configurables
aqui. Los costos energeticos siguen la especificacion (unidades relativas de
Joules/ciclos): Edge = 1, Serverless (ejecucion) = 15, Serverless (Cold Start) = 25.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class DefenseConfig:
    """Configuracion del juego estocastico de defensa.

    Attributes:
        alpha: Peso de la Recompensa R(a, d) por deteccion / trafico legitimo eficiente.
        beta: Peso del Costo energetico C_energy(d) (sustentabilidad / Green Computing).
        gamma: Peso de la Penalizacion por dano C_damage(a, d) (severidad de brecha).

        energy_edge: Costo energetico de la Estrategia Verde (Edge). = 1 unidad.
        energy_serverless_exec: Costo energetico de ejecucion Serverless (warm). = 15.
        energy_serverless_cold_start: Costo energetico Serverless con Cold Start. = 25.

        reward_edge_block: Recompensa por mitigar un ataque ligero en el Edge.
        reward_deep_detect: Recompensa por deteccion via inspeccion profunda.
        reward_legit_green: Recompensa por servir trafico legitimo con energia minima.

        damage_breach_base: Penalizacion base severa si un ataque avanzado (A_M) evade
            la seguridad por quedarse en la capa Edge (D_V). Se escala por sospecha.

        attacker_breach_gain_base: Ganancia base del atacante ante una brecha exitosa.
        attacker_cost_advanced: Costo/esfuerzo de montar un ataque avanzado (A_M).
        attacker_penalty_light: Penalizacion al atacante cuando un ataque ligero es
            detectado (bot ruidoso bloqueado).
        attacker_penalty_advanced: Penalizacion al atacante cuando un ataque avanzado
            es detectado por la inspeccion profunda.

        serverless_warm_ttl: Numero de pasos de simulacion durante los cuales la
            funcion Serverless permanece "tibia" (warm) tras una invocacion.
        suspicion_floor: Escala minima de sospecha para no anular por completo el
            riesgo de dano (evita matrices degeneradas).
    """

    # --- Pesos de ponderacion de la funcion de utilidad U_D = a*R - b*C_e - g*C_d ---
    alpha: float = 1.0
    beta: float = 1.0
    gamma: float = 1.0

    # --- Costos energeticos (Joules/ciclos relativos) ---
    energy_edge: float = 1.0
    energy_serverless_exec: float = 15.0
    energy_serverless_cold_start: float = 25.0

    # --- Recompensas R(a, d) ---
    reward_edge_block: float = 10.0
    reward_deep_detect: float = 12.0
    reward_legit_green: float = 8.0

    # --- Penalizacion de dano C_damage(a, d) ---
    damage_breach_base: float = 140.0

    # --- Utilidad del atacante (juego no cooperativo) ---
    attacker_breach_gain_base: float = 200.0
    attacker_cost_advanced: float = 20.0
    attacker_penalty_light: float = 5.0
    attacker_penalty_advanced: float = 15.0

    # --- Dinamica de la capa Serverless ---
    serverless_warm_ttl: int = 12
    suspicion_floor: float = 0.15

    def serverless_cost(self, cold: bool) -> float:
        """Costo energetico Serverless segun estado (Cold Start vs warm)."""
        return self.energy_serverless_cold_start if cold else self.energy_serverless_exec
