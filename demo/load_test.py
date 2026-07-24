"""Generador de trafico realista contra la pasarela SGE en vivo.

Envia peticiones HTTP reales al gateway (`demo/gateway.py`) con la mezcla tipica
80% legitimo / 15% bots / 5% ataques avanzados (mitad SQLi, mitad prompt injection),
para poblar el panel en http://localhost:8000 mientras observas las metricas.

Uso (con el gateway ya corriendo):
    python demo/load_test.py                 # 1000 peticiones a localhost:8000
    python demo/load_test.py --n 5000 --url http://127.0.0.1:9000
"""

from __future__ import annotations

import argparse
import random
import time
import urllib.request

# Distribucion de tipos de peticion (los kinds los entiende /sample del gateway).
MIX = (
    ("legit", 0.80),
    ("bot", 0.15),
    ("sqli", 0.025),
    ("prompt", 0.025),
)


def pick() -> str:
    r = random.random()
    acc = 0.0
    for kind, p in MIX:
        acc += p
        if r <= acc:
            return kind
    return "legit"


def main() -> None:
    parser = argparse.ArgumentParser(description="Carga de trafico para el demo SGE.")
    parser.add_argument("--n", type=int, default=1000, help="Numero de peticiones.")
    parser.add_argument("--url", default="http://127.0.0.1:8000", help="URL del gateway.")
    parser.add_argument("--delay", type=float, default=0.0, help="Pausa entre peticiones (s).")
    args = parser.parse_args()

    print(f"Enviando {args.n} peticiones a {args.url} ...")
    counts: dict[str, int] = {}
    for i in range(args.n):
        kind = pick()
        counts[kind] = counts.get(kind, 0) + 1
        try:
            urllib.request.urlopen(f"{args.url}/sample?kind={kind}", timeout=5).read()
        except Exception as exc:  # noqa: BLE001
            print(f"  error en peticion {i}: {exc}")
            break
        if args.delay:
            time.sleep(args.delay)
        if (i + 1) % 200 == 0:
            print(f"  {i + 1} enviadas...")

    print("Listo. Mezcla enviada:", counts)
    print(f"Abre {args.url} para ver el panel.")


if __name__ == "__main__":
    main()
