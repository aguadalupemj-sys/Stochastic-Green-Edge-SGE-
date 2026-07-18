"""Simulacion de flujo de trafico y reporte comparativo de seguridad/energia.

Simula un flujo constante de peticiones con la mezcla especificada:
    - 80% usuarios legitimos.
    - 15% bots automaticos ruidosos (Ataque Ligero, A_L).
    - 5%  hackers dirigidos (Ataque Avanzado, A_M).

Compara el enfoque ADAPTATIVO (Teoria de Juegos + Edge) contra un enfoque
TRADICIONAL que inspecciona el 100% de las peticiones en la capa Serverless.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np

from .config import DefenseConfig
from .edge import EdgeLayer
from .models import DefenderAction, HttpRequest, TrafficClass
from .serverless import ServerlessLayer

# Distribucion de trafico requerida.
TRAFFIC_MIX = {
    TrafficClass.LEGIT: 0.80,
    TrafficClass.LIGHT_ATTACK: 0.15,
    TrafficClass.ADVANCED_ATTACK: 0.05,
}

_LEGIT_UAS = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/124.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15) Safari/17.4",
    "Mozilla/5.0 (X11; Linux x86_64) Firefox/125.0",
)
_BOT_UAS = ("curl/8.4.0", "python-requests/2.31", "Go-http-client/1.1", "sqlmap/1.7")


def generate_traffic(n: int, seed: int = 7) -> list[HttpRequest]:
    """Genera `n` peticiones HTTP con la mezcla 80/15/5 y features coherentes.

    - Legitimo: IP diversa, User-Agent de navegador, payload pequeno y limpio.
    - Ligero (bot ruidoso): pocas IPs repetidas (alta frecuencia), UA anomalo.
    - Avanzado (dirigido): UA casi normal, payload grande con tokens de inyeccion.
    """
    rng = np.random.default_rng(seed)
    classes = list(TRAFFIC_MIX.keys())
    probs = list(TRAFFIC_MIX.values())
    requests: list[HttpRequest] = []

    for _ in range(n):
        # Se muestrea por indice para no coaccionar los Enum a cadenas numpy truncadas.
        cls = classes[int(rng.choice(len(classes), p=probs))]
        if cls == TrafficClass.LEGIT:
            ip = f"203.0.{rng.integers(0, 255)}.{rng.integers(1, 255)}"
            ua = _LEGIT_UAS[rng.integers(0, len(_LEGIT_UAS))]
            payload = "GET /api/v1/resource?id=" + str(int(rng.integers(1, 9999)))
        elif cls == TrafficClass.LIGHT_ATTACK:
            # Bots ruidosos: se concentran en un puñado de IPs (alta frecuencia).
            ip = f"198.51.100.{rng.integers(1, 6)}"
            ua = _BOT_UAS[rng.integers(0, len(_BOT_UAS))]
            payload = "GET /api/v1/login?u=admin&p=" + str(int(rng.integers(1, 99)))
        else:  # ADVANCED_ATTACK
            # Dirigido y sigiloso: UA casi normal, payload malicioso y voluminoso.
            ip = f"192.0.2.{rng.integers(1, 255)}"
            ua = _LEGIT_UAS[rng.integers(0, len(_LEGIT_UAS))]
            filler = "A" * int(rng.integers(1200, 4096))
            payload = "POST /api/v1/data " + filler + " '; DROP TABLE users; --"
        requests.append(HttpRequest(source_ip=ip, user_agent=ua, payload=payload, true_class=cls))

    return requests


@dataclass
class SimulationReport:
    """Metricas agregadas de una corrida de simulacion."""

    total_requests: int = 0
    counts: dict[TrafficClass, int] = field(default_factory=dict)

    # Seguridad
    attacks_total: int = 0
    attacks_mitigated: int = 0
    advanced_total: int = 0
    advanced_mitigated: int = 0
    light_total: int = 0
    light_mitigated: int = 0
    breaches: int = 0

    # Energia
    adaptive_energy: float = 0.0
    baseline_energy: float = 0.0
    serverless_invocations: int = 0
    serverless_cold_starts: int = 0
    escalations: int = 0

    @property
    def mitigation_rate(self) -> float:
        return self.attacks_mitigated / self.attacks_total if self.attacks_total else 1.0

    @property
    def advanced_mitigation_rate(self) -> float:
        return self.advanced_mitigated / self.advanced_total if self.advanced_total else 1.0

    @property
    def energy_saved(self) -> float:
        return self.baseline_energy - self.adaptive_energy

    @property
    def energy_saved_pct(self) -> float:
        return 100.0 * self.energy_saved / self.baseline_energy if self.baseline_energy else 0.0


def run_simulation(
    requests: list[HttpRequest],
    config: DefenseConfig | None = None,
    seed: int = 42,
) -> SimulationReport:
    """Ejecuta el flujo de defensa adaptativa peticion por peticion.

    Flujo por peticion:
        1. El Edge extrae metricas y ejecuta el motor de Nash (si es sospechosa).
        2. Estrategia Verde (D_V): solo Edge. Mitiga ataques LIGEROS; los AVANZADOS
           EVADEN (brecha).
        3. Estrategia Activa (D_A): escala a Serverless (inspeccion profunda) que
           mitiga cualquier ataque, con costo energetico (y posible Cold Start).
    """
    config = config or DefenseConfig()
    rng = np.random.default_rng(seed)
    edge = EdgeLayer(config, rng=rng)
    serverless = ServerlessLayer(config)

    report = SimulationReport(total_requests=len(requests))
    report.counts = {cls: 0 for cls in TrafficClass}

    for step, request in enumerate(requests):
        report.counts[request.true_class] += 1
        is_attack = request.true_class in (TrafficClass.LIGHT_ATTACK, TrafficClass.ADVANCED_ATTACK)
        if is_attack:
            report.attacks_total += 1
        if request.true_class == TrafficClass.ADVANCED_ATTACK:
            report.advanced_total += 1
        elif request.true_class == TrafficClass.LIGHT_ATTACK:
            report.light_total += 1

        cold = serverless.is_cold(step)
        decision = edge.decide(request, serverless_cold=cold)

        if decision.action == DefenderAction.ACTIVE:
            report.escalations += 1
            result = serverless.inspect(request, step)
            if result.threat_detected:
                report.attacks_mitigated += 1
                if request.true_class == TrafficClass.ADVANCED_ATTACK:
                    report.advanced_mitigated += 1
                elif request.true_class == TrafficClass.LIGHT_ATTACK:
                    report.light_mitigated += 1
        else:
            # Estrategia Verde: el filtro Edge frena ataques ligeros/ruidosos,
            # pero los ataques avanzados evaden la capa Edge (brecha).
            if request.true_class == TrafficClass.LIGHT_ATTACK:
                report.attacks_mitigated += 1
                report.light_mitigated += 1
            elif request.true_class == TrafficClass.ADVANCED_ATTACK:
                report.breaches += 1

    report.adaptive_energy = edge.total_energy + serverless.total_energy
    report.serverless_invocations = serverless.invocations
    report.serverless_cold_starts = serverless.cold_starts

    # --- Enfoque TRADICIONAL: inspeccion profunda del 100% del trafico ---
    report.baseline_energy = _baseline_energy(len(requests), config)

    return report


def _baseline_energy(n: int, config: DefenseConfig) -> float:
    """Energia del enfoque tradicional (Serverless en el 100% de las peticiones).

    La primera invocacion es Cold Start; el resto se asume warm por el flujo constante.
    """
    if n <= 0:
        return 0.0
    return config.energy_serverless_cold_start + (n - 1) * config.energy_serverless_exec


def format_report(report: SimulationReport) -> str:
    """Genera el reporte final en consola (texto)."""
    lines: list[str] = []
    lines.append("=" * 68)
    lines.append("  DEFENSA ADAPTATIVA EDGE + TEORIA DE JUEGOS  (Stochastic Green Edge)")
    lines.append("=" * 68)
    lines.append("")
    lines.append(f"  Peticiones totales simuladas : {report.total_requests}")
    lines.append(
        "  Mezcla de trafico            : "
        f"{report.counts.get(TrafficClass.LEGIT, 0)} legitimo | "
        f"{report.counts.get(TrafficClass.LIGHT_ATTACK, 0)} bots (A_L) | "
        f"{report.counts.get(TrafficClass.ADVANCED_ATTACK, 0)} avanzado (A_M)"
    )
    lines.append("")
    lines.append("  --- SEGURIDAD (Mitigacion de amenazas) ---")
    lines.append(
        f"  Tasa de mitigacion global    : {report.mitigation_rate * 100:6.2f}%  "
        f"({report.attacks_mitigated}/{report.attacks_total} ataques)"
    )
    lines.append(
        f"  Mitigacion ataques avanzados : {report.advanced_mitigation_rate * 100:6.2f}%  "
        f"({report.advanced_mitigated}/{report.advanced_total})"
    )
    lines.append(
        f"  Mitigacion ataques ligeros   : "
        f"{(report.light_mitigated / report.light_total * 100) if report.light_total else 100.0:6.2f}%  "
        f"({report.light_mitigated}/{report.light_total})"
    )
    lines.append(f"  Brechas (A_M evadido)        : {report.breaches}")
    lines.append("")
    lines.append("  --- SUSTENTABILIDAD (Green Computing) ---")
    lines.append(
        f"  Escalados a Serverless       : {report.escalations} "
        f"(de {report.total_requests} peticiones)"
    )
    lines.append(
        f"  Invocaciones Serverless      : {report.serverless_invocations} "
        f"({report.serverless_cold_starts} Cold Starts)"
    )
    lines.append(f"  Energia ADAPTATIVA (Joules)  : {report.adaptive_energy:10.1f}")
    lines.append(f"  Energia TRADICIONAL (Joules) : {report.baseline_energy:10.1f}")
    lines.append(
        f"  Energia AHORRADA (Joules)    : {report.energy_saved:10.1f}  "
        f"({report.energy_saved_pct:.2f}% menos)"
    )
    lines.append("")
    lines.append("=" * 68)
    lines.append(
        "  Conclusion: el equilibrio de Nash concentra la energia costosa "
    )
    lines.append(
        "  (Serverless) en el trafico sospechoso, manteniendo alta mitigacion "
    )
    lines.append(
        "  de ataques avanzados con una fraccion de la energia tradicional."
    )
    lines.append("=" * 68)
    return "\n".join(lines)
