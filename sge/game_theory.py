"""Motor matematico: Equilibrio de Nash en Estrategias Mixtas (juego 2x2).

Modela un Juego Estocastico No Cooperativo con Informacion Imperfecta entre:

    - Defensor (jugador fila): estrategias { D_V (Verde/Edge), D_A (Activa/Serverless) }.
    - Atacante (jugador columna): estrategias { A_L (Ligero), A_M (Avanzado) }.

La funcion de utilidad del Defensor es:

    U_D(a, d) = alpha * R(a, d) - beta * C_energy(d) - gamma * C_damage(a, d)

El Defensor juega D_V con probabilidad p y D_A con probabilidad 1 - p. El motor
calcula el Equilibrio de Nash mediante enumeracion de soportes: primero busca
equilibrios en estrategias puras (mejor respuesta mutua) y luego el equilibrio
completamente mixto via el principio de indiferencia. Se prioriza el equilibrio
mixto cuando es interior y valido, acorde al requisito de estrategias mixtas.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from .config import DefenseConfig
from .models import RequestFeatures

_EPS = 1e-9


@dataclass(frozen=True)
class NashEquilibrium:
    """Resultado del calculo del equilibrio.

    Attributes:
        p_green: Probabilidad de jugar la Estrategia Verde D_V (p).
        p_active: Probabilidad de jugar la Estrategia Activa D_A (1 - p).
        q_light: Probabilidad (del atacante) de un ataque ligero A_L.
        q_advanced: Probabilidad (del atacante) de un ataque avanzado A_M.
        defender_payoff: Utilidad esperada del Defensor en el equilibrio.
        attacker_payoff: Utilidad esperada del Atacante en el equilibrio.
        kind: "mixed" o "pure" segun el tipo de equilibrio hallado.
        defender_matrix: Matriz de pagos del Defensor usada (2x2).
        attacker_matrix: Matriz de pagos del Atacante usada (2x2).
    """

    p_green: float
    p_active: float
    q_light: float
    q_advanced: float
    defender_payoff: float
    attacker_payoff: float
    kind: str
    defender_matrix: np.ndarray
    attacker_matrix: np.ndarray

    @property
    def defender_strategy(self) -> np.ndarray:
        """Vector de estrategia mixta del Defensor [P(D_V), P(D_A)]."""
        return np.array([self.p_green, self.p_active])

    @property
    def attacker_strategy(self) -> np.ndarray:
        """Vector de estrategia mixta del Atacante [P(A_L), P(A_M)]."""
        return np.array([self.q_light, self.q_advanced])


def suspicion_score(features: RequestFeatures, config: DefenseConfig) -> float:
    """Colapsa las metricas del Edge en un escalar de sospecha en [0, 1].

    Combina frecuencia de IP, anomalia de User-Agent y anomalia de payload. El
    resultado modula la severidad del dano potencial y la ganancia del atacante,
    haciendo que el Equilibrio de Nash sea especifico de cada peticion (tiempo real).
    """
    # Saturacion suave de la frecuencia de IP (rate) hacia [0, 1].
    freq_component = 1.0 - np.exp(-features.ip_frequency / 6.0)
    # La inspeccion profunda (Serverless) solo aporta valor frente a amenazas a nivel
    # de payload; por eso la anomalia de payload domina la sospecha del juego. La
    # frecuencia de IP y el User-Agent los gestiona (de forma barata) el filtro Edge.
    raw = 0.15 * freq_component + 0.15 * features.user_agent_anomaly + 0.70 * features.payload_anomaly
    return float(np.clip(raw, 0.0, 1.0))


def build_payoff_matrices(
    features: RequestFeatures,
    config: DefenseConfig,
    serverless_cold: bool,
) -> tuple[np.ndarray, np.ndarray]:
    """Construye las matrices de pago (Defensor, Atacante) para una peticion sospechosa.

    Filas   = acciones del Defensor  [D_V (Verde), D_A (Activa)].
    Columnas = acciones del Atacante [A_L (Ligero), A_M (Avanzado)].

    Args:
        features: Metricas extraidas por el Edge.
        config: Parametros del modelo.
        serverless_cold: True si la funcion Serverless incurriria en Cold Start.

    Returns:
        (A_def, B_att): matrices numpy 2x2 con las utilidades del Defensor y Atacante.
    """
    s = suspicion_score(features, config)
    # La escala de riesgo nunca es nula (evita degeneracion) y crece con la sospecha.
    risk = config.suspicion_floor + (1.0 - config.suspicion_floor) * s

    c_edge = config.energy_edge
    c_srv = config.serverless_cost(serverless_cold)

    damage = config.damage_breach_base * risk
    breach_gain = config.attacker_breach_gain_base * risk

    a, b, g = config.alpha, config.beta, config.gamma

    # --- Matriz del Defensor: U_D(a, d) = a*R - b*C_energy - g*C_damage ---
    #                                A_L (ligero)                 A_M (avanzado)
    # D_V (Verde):   bloquea A_L en Edge          |  A_M EVADE -> brecha severa
    # D_A (Activa):  detecta con energia alta      |  detecta A_M (evita dano)
    A_def = np.array(
        [
            [a * config.reward_edge_block - b * c_edge,        # (D_V, A_L): mitigado en Edge
             a * 0.0 - b * c_edge - g * damage],               # (D_V, A_M): brecha
            [a * config.reward_deep_detect - b * c_srv,        # (D_A, A_L): overkill energetico
             a * config.reward_deep_detect - b * c_srv],       # (D_A, A_M): deteccion profunda
        ],
        dtype=float,
    )

    # --- Matriz del Atacante: ganancia por dano - penalizaciones - costo de ataque ---
    #                                A_L (ligero)                 A_M (avanzado)
    B_att = np.array(
        [
            [-config.attacker_penalty_light,                    # (D_V, A_L): bot bloqueado
             breach_gain - config.attacker_cost_advanced],      # (D_V, A_M): brecha exitosa
            [-config.attacker_penalty_light,                    # (D_A, A_L): bot bloqueado
             -config.attacker_penalty_advanced - config.attacker_cost_advanced],  # (D_A, A_M): detectado
        ],
        dtype=float,
    )
    return A_def, B_att


def _pure_best_responses(A_def: np.ndarray, B_att: np.ndarray) -> list[tuple[int, int]]:
    """Devuelve la lista de perfiles de estrategia pura que son Equilibrios de Nash."""
    equilibria: list[tuple[int, int]] = []
    for i in range(2):        # accion del Defensor
        for j in range(2):    # accion del Atacante
            defender_best = A_def[i, j] >= A_def[1 - i, j] - _EPS
            attacker_best = B_att[i, j] >= B_att[i, 1 - j] - _EPS
            if defender_best and attacker_best:
                equilibria.append((i, j))
    return equilibria


def _interior_mixed(A_def: np.ndarray, B_att: np.ndarray) -> tuple[float, float] | None:
    """Calcula el equilibrio completamente mixto via el principio de indiferencia.

    - p (prob. de D_V) hace al Atacante indiferente entre A_L y A_M.
    - q (prob. de A_L) hace al Defensor indiferente entre D_V y D_A.

    Returns:
        (p, q) si ambos estan en [0, 1]; en caso contrario None.
    """
    # Atacante indiferente: p*B[0,0] + (1-p)*B[1,0] == p*B[0,1] + (1-p)*B[1,1]
    denom_p = (B_att[0, 0] - B_att[1, 0]) - (B_att[0, 1] - B_att[1, 1])
    if abs(denom_p) < _EPS:
        return None
    p = (B_att[1, 1] - B_att[1, 0]) / denom_p

    # Defensor indiferente: q*A[0,0] + (1-q)*A[0,1] == q*A[1,0] + (1-q)*A[1,1]
    denom_q = (A_def[0, 0] - A_def[0, 1]) - (A_def[1, 0] - A_def[1, 1])
    if abs(denom_q) < _EPS:
        return None
    q = (A_def[1, 1] - A_def[0, 1]) / denom_q

    if -_EPS <= p <= 1 + _EPS and -_EPS <= q <= 1 + _EPS:
        return float(np.clip(p, 0.0, 1.0)), float(np.clip(q, 0.0, 1.0))
    return None


def mixed_nash_2x2(A_def: np.ndarray, B_att: np.ndarray) -> NashEquilibrium:
    """Resuelve el Equilibrio de Nash de un juego bimatriz 2x2.

    Estrategia de solucion (enumeracion de soportes):
        1. Se intenta el equilibrio interior (completamente mixto), que es el caso
           de interes para estrategias mixtas ante trafico sospechoso.
        2. Si no existe equilibrio mixto interior, se recurre a un equilibrio en
           estrategias puras (mejor respuesta mutua).

    Args:
        A_def: Matriz de pagos del Defensor (2x2). Filas = D_V, D_A.
        B_att: Matriz de pagos del Atacante (2x2). Columnas = A_L, A_M.

    Returns:
        NashEquilibrium con las probabilidades y utilidades esperadas.
    """
    A_def = np.asarray(A_def, dtype=float)
    B_att = np.asarray(B_att, dtype=float)
    if A_def.shape != (2, 2) or B_att.shape != (2, 2):
        raise ValueError("Ambas matrices deben ser 2x2.")

    interior = _interior_mixed(A_def, B_att)
    if interior is not None:
        p, q = interior
        return _build_result(A_def, B_att, p, q, kind="mixed")

    # Respaldo: equilibrio en estrategias puras.
    pures = _pure_best_responses(A_def, B_att)
    if pures:
        # Se elige el equilibrio puro mas favorable para el Defensor.
        i, j = max(pures, key=lambda ij: A_def[ij])
        p = 1.0 if i == 0 else 0.0
        q = 1.0 if j == 0 else 0.0
        return _build_result(A_def, B_att, p, q, kind="pure")

    # Caso extremo sin equilibrio detectado (no deberia ocurrir en un 2x2 finito):
    # se devuelve la estrategia maximin del Defensor.
    row_min = A_def.min(axis=1)
    i = int(np.argmax(row_min))
    p = 1.0 if i == 0 else 0.0
    return _build_result(A_def, B_att, p, 0.5, kind="pure")


def _build_result(
    A_def: np.ndarray,
    B_att: np.ndarray,
    p: float,
    q: float,
    kind: str,
) -> NashEquilibrium:
    defender_strategy = np.array([p, 1.0 - p])
    attacker_strategy = np.array([q, 1.0 - q])
    defender_payoff = float(defender_strategy @ A_def @ attacker_strategy)
    attacker_payoff = float(defender_strategy @ B_att @ attacker_strategy)
    return NashEquilibrium(
        p_green=p,
        p_active=1.0 - p,
        q_light=q,
        q_advanced=1.0 - q,
        defender_payoff=defender_payoff,
        attacker_payoff=attacker_payoff,
        kind=kind,
        defender_matrix=A_def,
        attacker_matrix=B_att,
    )


def solve_for_request(
    features: RequestFeatures,
    config: DefenseConfig,
    serverless_cold: bool,
) -> NashEquilibrium:
    """Construye las matrices de una peticion y resuelve su Equilibrio de Nash."""
    A_def, B_att = build_payoff_matrices(features, config, serverless_cold)
    return mixed_nash_2x2(A_def, B_att)
