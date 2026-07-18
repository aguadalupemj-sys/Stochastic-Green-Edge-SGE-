"""Experimentos reproducibles para el paper SGE.

Genera los datos y figuras que respaldan la evaluacion empirica:
    1. Comparacion Adaptativo (Nash) vs Tradicional (100% inspeccion) vs
       Edge-only (0% inspeccion) agregada sobre multiples semillas.
    2. Frontera de compromiso seguridad-energia (Pareto) al variar el incentivo
       de brecha del adversario.
    3. Respuesta dinamica: probabilidad de escalado 1-p vs sospecha.

Uso:
    python3 paper/run_experiments.py
Salida:
    paper/results.json  y  paper/figures/*.png
"""

from __future__ import annotations

import json
import statistics
import sys
from dataclasses import replace
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt

from sge.config import DefenseConfig
from sge.game_theory import solve_for_request, suspicion_score
from sge.models import RequestFeatures
from sge.simulation import generate_traffic, run_simulation

HERE = Path(__file__).resolve().parent
FIG = HERE / "figures"
FIG.mkdir(parents=True, exist_ok=True)

N_REQUESTS = 2000
HEADLINE_SEED = 7
SEEDS = list(range(20))


def _mean_std(xs):
    return statistics.mean(xs), (statistics.pstdev(xs) if len(xs) > 1 else 0.0)


def experiment_comparison(config: DefenseConfig) -> dict:
    """Compara los tres enfoques sobre SEEDS semillas."""
    adaptive = {"global": [], "advanced": [], "energy": [], "saved_pct": []}
    for seed in SEEDS:
        traffic = generate_traffic(N_REQUESTS, seed=seed)
        r = run_simulation(traffic, config=config, seed=seed)
        adaptive["global"].append(r.mitigation_rate * 100)
        adaptive["advanced"].append(r.advanced_mitigation_rate * 100)
        adaptive["energy"].append(r.adaptive_energy)
        adaptive["saved_pct"].append(r.energy_saved_pct)

    # Referencias analiticas (deterministas dada la mezcla de trafico).
    sample = run_simulation(generate_traffic(N_REQUESTS, seed=0), config=config, seed=0)
    n = sample.total_requests
    light, advanced = sample.light_total, sample.advanced_total
    attacks = light + advanced

    traditional = {
        "global": 100.0,
        "advanced": 100.0,
        "energy": sample.baseline_energy,
    }
    edge_only = {
        "global": light / attacks * 100,
        "advanced": 0.0,
        "energy": n * config.energy_edge,
    }

    # Corrida "titular" reproducible (semilla 7) reportada en el texto.
    hl = run_simulation(generate_traffic(N_REQUESTS, seed=HEADLINE_SEED),
                        config=config, seed=HEADLINE_SEED)
    headline = {
        "seed": HEADLINE_SEED,
        "n_requests": hl.total_requests,
        "global": hl.mitigation_rate * 100,
        "advanced": hl.advanced_mitigation_rate * 100,
        "advanced_frac": [hl.advanced_mitigated, hl.advanced_total],
        "light": (hl.light_mitigated / hl.light_total * 100) if hl.light_total else 100.0,
        "light_frac": [hl.light_mitigated, hl.light_total],
        "adaptive_energy": hl.adaptive_energy,
        "baseline_energy": hl.baseline_energy,
        "energy_saved": hl.energy_saved,
        "energy_saved_pct": hl.energy_saved_pct,
        "escalations": hl.escalations,
        "serverless_invocations": hl.serverless_invocations,
        "cold_starts": hl.serverless_cold_starts,
        "counts": {
            "legit": hl.counts[[c for c in hl.counts if c.value == "legit"][0]],
            "light": hl.light_total,
            "advanced": hl.advanced_total,
        },
    }

    return {
        "n_requests": N_REQUESTS,
        "n_seeds": len(SEEDS),
        "headline": headline,
        "adaptive": {k: _mean_std(v) for k, v in adaptive.items()},
        "adaptive_advanced_min": min(adaptive["advanced"]),
        "adaptive_advanced_max": max(adaptive["advanced"]),
        "traditional": traditional,
        "edge_only": edge_only,
    }


def experiment_pareto(config: DefenseConfig) -> dict:
    """Frontera seguridad-energia variando el incentivo de brecha del adversario."""
    gains = [40, 70, 100, 140, 180, 220, 280, 340, 420, 500]
    points = []
    for g in gains:
        cfg = replace(config, attacker_breach_gain_base=float(g), damage_breach_base=float(g))
        adv, eng = [], []
        for seed in SEEDS[:10]:
            r = run_simulation(generate_traffic(N_REQUESTS, seed=seed), config=cfg, seed=seed)
            adv.append(r.advanced_mitigation_rate * 100)
            eng.append(r.adaptive_energy)
        points.append({"gain": g, "advanced": _mean_std(adv)[0], "energy": _mean_std(eng)[0]})
    return {"points": points}


def experiment_response(config: DefenseConfig) -> dict:
    """Probabilidad de escalado (1 - p) en funcion de la anomalia de payload."""
    xs, ys = [], []
    for i in range(0, 101):
        pa = i / 100.0
        feats = RequestFeatures(
            ip_frequency=0.5, payload_size=800,
            user_agent_anomaly=0.0, payload_anomaly=pa,
        )
        eq = solve_for_request(feats, config, serverless_cold=False)
        xs.append(suspicion_score(feats, config))
        ys.append(eq.p_active * 100)
    return {"suspicion": xs, "escalation_pct": ys}


def nash_example(config: DefenseConfig) -> dict:
    """Ejemplo resuelto del equilibrio para una peticion muy sospechosa."""
    feats = RequestFeatures(
        ip_frequency=0.5, payload_size=2500,
        user_agent_anomaly=0.0, payload_anomaly=1.0,
    )
    eq = solve_for_request(feats, config, serverless_cold=False)
    return {
        "suspicion": suspicion_score(feats, config),
        "defender_matrix": eq.defender_matrix.tolist(),
        "attacker_matrix": eq.attacker_matrix.tolist(),
        "p_green": eq.p_green,
        "p_active": eq.p_active,
        "q_light": eq.q_light,
        "q_advanced": eq.q_advanced,
        "defender_payoff": eq.defender_payoff,
        "kind": eq.kind,
    }


def make_figures(comp: dict, pareto: dict, resp: dict) -> None:
    """Genera las tres figuras del paper en paper/figures/."""
    plt.rcParams.update({"font.size": 11, "figure.dpi": 130})

    # Fig 1: energia por enfoque.
    fig, ax = plt.subplots(figsize=(5.2, 3.4))
    labels = ["Edge-only", "Adaptativo\n(Nash)", "Tradicional\n(100%)"]
    energies = [
        comp["edge_only"]["energy"],
        comp["headline"]["adaptive_energy"],
        comp["traditional"]["energy"],
    ]
    colors = ["#8fbf6a", "#2e7d32", "#b23b3b"]
    bars = ax.bar(labels, energies, color=colors)
    ax.set_ylabel("Energia (Joules simulados)")
    ax.set_title("Consumo energetico por enfoque")
    for b, e in zip(bars, energies, strict=True):
        ax.text(b.get_x() + b.get_width() / 2, e, f"{e:,.0f}", ha="center", va="bottom", fontsize=9)
    ax.margins(y=0.15)
    fig.tight_layout()
    fig.savefig(FIG / "fig1_energy.png")
    plt.close(fig)

    # Fig 2: Pareto seguridad-energia.
    fig, ax = plt.subplots(figsize=(5.6, 3.8))
    ex = [p["energy"] for p in pareto["points"]]
    ey = [p["advanced"] for p in pareto["points"]]
    ax.plot(ex, ey, "o-", color="#2e7d32", label="Adaptativo (Nash)")
    for p in pareto["points"]:
        ax.annotate(
            str(p["gain"]), (p["energy"], p["advanced"]), fontsize=7,
            textcoords="offset points", xytext=(4, 4),
        )
    ax.scatter(
        [comp["traditional"]["energy"]], [comp["traditional"]["advanced"]],
        color="#b23b3b", marker="s", s=70, label="Tradicional (100%)", zorder=5,
    )
    ax.scatter(
        [comp["edge_only"]["energy"]], [comp["edge_only"]["advanced"]],
        color="#8fbf6a", marker="^", s=70, label="Edge-only", zorder=5,
    )
    ax.set_xlabel("Energia (Joules simulados)")
    ax.set_ylabel("Mitigacion de ataques avanzados (%)")
    ax.set_title("Frontera de compromiso seguridad-energia")
    ax.legend(loc="lower right", fontsize=9)
    ax.grid(alpha=0.3)
    fig.tight_layout()
    fig.savefig(FIG / "fig2_pareto.png")
    plt.close(fig)

    # Fig 3: respuesta dinamica.
    fig, ax = plt.subplots(figsize=(5.6, 3.4))
    ax.plot(resp["suspicion"], resp["escalation_pct"], color="#1565c0")
    ax.set_xlabel("Puntuacion de sospecha  s")
    ax.set_ylabel("Prob. de escalado a Serverless  1 - p  (%)")
    ax.set_title("Respuesta del Equilibrio de Nash a la sospecha")
    ax.grid(alpha=0.3)
    fig.tight_layout()
    fig.savefig(FIG / "fig3_response.png")
    plt.close(fig)


def main() -> None:
    config = DefenseConfig()
    comp = experiment_comparison(config)
    pareto = experiment_pareto(config)
    resp = experiment_response(config)
    nash = nash_example(config)
    make_figures(comp, pareto, resp)
    results = {"comparison": comp, "pareto": pareto, "nash_example": nash}
    (HERE / "results.json").write_text(json.dumps(results, indent=2), encoding="utf-8")

    h = comp["headline"]
    c = h["counts"]
    lf, af = h["light_frac"], h["advanced_frac"]
    print(f"== Corrida titular (semilla {h['seed']}, {h['n_requests']} peticiones) ==")
    print(f"  Trafico     : {c['legit']} legitimo | {c['light']} bots | {c['advanced']} avanzado")
    print(f"  Mit. global : {h['global']:.2f}%")
    print(f"  Ligeros     : {h['light']:.0f}% ({lf[0]}/{lf[1]})")
    print(f"  Avanzados   : {h['advanced']:.2f}% ({af[0]}/{af[1]})")
    print(f"  Energia     : adapt={h['adaptive_energy']:.0f} J  trad={h['baseline_energy']:.0f} J  "
          f"ahorro={h['energy_saved_pct']:.2f}%")
    print(f"  Escalados   : {h['escalations']} (cold starts {h['cold_starts']})")
    a = comp["adaptive"]
    lo, hi = comp["adaptive_advanced_min"], comp["adaptive_advanced_max"]
    print(f"== Robustez (media sobre {comp['n_seeds']} semillas) ==")
    print(f"  avanzados: {a['advanced'][0]:.2f}+-{a['advanced'][1]:.2f}% (rango {lo:.1f}-{hi:.1f}%)")
    print(
        f"Adaptativo   : global={a['global'][0]:.2f}+-{a['global'][1]:.2f}%  "
        f"avanzado={a['advanced'][0]:.2f}+-{a['advanced'][1]:.2f}%  "
        f"energia={a['energy'][0]:.0f}  ahorro={a['saved_pct'][0]:.2f}%"
    )
    print(f"Tradicional  : global=100%  avanzado=100%  energia={comp['traditional']['energy']:.0f}")
    print(
        f"Edge-only    : global={comp['edge_only']['global']:.2f}%  avanzado=0%  "
        f"energia={comp['edge_only']['energy']:.0f}"
    )
    print("Figuras y results.json escritos en paper/")


if __name__ == "__main__":
    main()
