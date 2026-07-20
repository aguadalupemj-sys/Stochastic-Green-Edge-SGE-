"""Figuras de sostenibilidad (huella de carbono) para el paper enfocado en Green Computing.

Traduce el ahorro energetico de SGE (medido en unidades relativas por la simulacion)
a emisiones de CO2 mediante el modelo estandar de contabilidad de carbono:

    E_CO2 = W (kWh) * PUE * I_grid (kgCO2/kWh)

Ancla conservadora: una inspeccion profunda tibia consume e_exec = 1 J de energia de
computo real, equivalente a C_exec = 15 unidades del modelo => 1 unidad = 1/15 J.

Uso:
    python3 paper/make_sustainability_figures.py
Salida:
    paper/figures/fig4_carbon.png   (CO2 anual por enfoque)
    paper/figures/fig5_carbon_scale.png (CO2 evitado vs volumen de trafico)
"""

from __future__ import annotations

import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt

from sge.config import DefenseConfig
from sge.simulation import generate_traffic, run_simulation

HERE = Path(__file__).resolve().parent
FIG = HERE / "figures"
FIG.mkdir(parents=True, exist_ok=True)

# --- Parametros de contabilidad de carbono (documentados en el paper) ---
J_PER_UNIT = 1.0 / 15.0          # 1 unidad de energia simulada ~ 1/15 Joule real
PUE = 1.5                        # Power Usage Effectiveness tipico de centro de datos
I_GRID = 0.475                   # kgCO2eq/kWh (media mundial de la red)
J_PER_KWH = 3.6e6               # Joules por kWh
N_MONTHLY = 1_000_000_000        # 10^9 peticiones/mes (API de gran escala)
MONTHS = 12

N_REQUESTS = 2000
SEED = 7


def units_to_annual_tonnes(units_per_request: float) -> float:
    """Convierte energia (unidades/peticion) a toneladas de CO2 al anio a escala."""
    joules_per_req = units_per_request * J_PER_UNIT
    kwh_year = joules_per_req * N_MONTHLY * MONTHS / J_PER_KWH
    kg_year = kwh_year * PUE * I_GRID
    return kg_year / 1000.0


def main() -> None:
    config = DefenseConfig()
    traffic = generate_traffic(N_REQUESTS, seed=SEED)
    r = run_simulation(traffic, config=config, seed=SEED)

    # Energia (unidades) por peticion de cada enfoque.
    adaptive_upr = r.adaptive_energy / r.total_requests
    traditional_upr = r.baseline_energy / r.total_requests
    edge_only_upr = config.energy_edge  # 1 unidad/peticion

    t_trad = units_to_annual_tonnes(traditional_upr)
    t_adap = units_to_annual_tonnes(adaptive_upr)
    t_edge = units_to_annual_tonnes(edge_only_upr)

    plt.rcParams.update({"font.size": 11, "figure.dpi": 130})

    # --- Fig 4: CO2 anual por enfoque ---
    fig, ax = plt.subplots(figsize=(5.4, 3.6))
    labels = ["Edge-only", "Adaptativo\n(Nash)", "Tradicional\n(100%)"]
    tonnes = [t_edge, t_adap, t_trad]
    colors = ["#8fbf6a", "#2e7d32", "#b23b3b"]
    bars = ax.bar(labels, tonnes, color=colors)
    ax.set_ylabel("Emisiones de CO$_2$ (toneladas/anio)")
    ax.set_title("Huella de carbono anual por enfoque\n(API de $10^9$ peticiones/mes)")
    for b, t in zip(bars, tonnes, strict=True):
        ax.text(b.get_x() + b.get_width() / 2, t, f"{t:.2f} t",
                ha="center", va="bottom", fontsize=9)
    ax.margins(y=0.18)
    # Anotacion del ahorro Adaptativo vs Tradicional.
    saved = t_trad - t_adap
    ax.annotate(
        f"-{saved:.2f} t/anio\n(-{100 * saved / t_trad:.1f}%)",
        xy=(1, t_adap), xytext=(1.05, t_trad * 0.6),
        fontsize=9, color="#1b5e20", fontweight="bold",
        arrowprops=dict(arrowstyle="->", color="#1b5e20"),
    )
    fig.tight_layout()
    fig.savefig(FIG / "fig4_carbon.png")
    plt.close(fig)

    # --- Fig 5: CO2 evitado vs volumen de trafico ---
    fig, ax = plt.subplots(figsize=(5.6, 3.4))
    volumes = [10**e for e in range(6, 11)]  # 1e6 .. 1e10 peticiones/mes
    saved_per_req = traditional_upr - adaptive_upr
    saved_tonnes = []
    for v in volumes:
        joules = saved_per_req * J_PER_UNIT * v * MONTHS
        kwh = joules / J_PER_KWH
        saved_tonnes.append(kwh * PUE * I_GRID / 1000.0)
    ax.plot(volumes, saved_tonnes, "o-", color="#2e7d32")
    ax.set_xscale("log")
    ax.set_yscale("log")
    ax.set_xlabel("Volumen de trafico (peticiones/mes)")
    ax.set_ylabel("CO$_2$ evitado (toneladas/anio)")
    ax.set_title("CO$_2$ evitado por SGE vs. escala de la API")
    ax.grid(alpha=0.3, which="both")
    fig.tight_layout()
    fig.savefig(FIG / "fig5_carbon_scale.png")
    plt.close(fig)

    print("== Huella de carbono (API de 1e9 peticiones/mes) ==")
    print(f"  Tradicional : {t_trad:.3f} t CO2/anio")
    print(f"  Adaptativo  : {t_adap:.3f} t CO2/anio")
    print(f"  Edge-only   : {t_edge:.3f} t CO2/anio")
    print(f"  AHORRO (adaptativo vs tradicional): {t_trad - t_adap:.3f} t CO2/anio "
          f"({100 * (t_trad - t_adap) / t_trad:.1f}%)")
    print("Figuras escritas: fig4_carbon.png, fig5_carbon_scale.png")


if __name__ == "__main__":
    main()
