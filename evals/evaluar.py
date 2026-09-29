"""Evals: ¿la IA puntúa las ofertas como las puntuaría yo?

Es la parte que convierte un "script con IA" en un sistema medible.
1. Yo puntúo a mano un conjunto de ofertas (etiquetas.csv).
2. Este script las pasa por el mismo evaluador que usa el radar.
3. Compara ambas notas y calcula:
   - Error medio absoluto (MAE): cuántos puntos se desvía de media.
   - % de acierto a ±2 puntos.
   - Acierto en la decisión que importa: ¿aplicar (nota ≥ 7) o no?
   - Falsos negativos: ofertas que yo aplicaría y la IA descartaría (lo más grave:
     son oportunidades perdidas).
Cada cambio de prompt o de modelo se valida con esto antes de darlo por bueno.

Uso: python evals/evaluar.py [--modelo claude-haiku-4-5-20251001]
"""
from __future__ import annotations

import argparse
import csv
import json
import sys
from datetime import datetime
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))

from radar import puntuar  # noqa: E402
from radar.modelo import Oferta  # noqa: E402


def metricas(pares: list[tuple[int, int]], umbral: int = 7) -> dict:
    n = len(pares)
    if not n:
        return {}
    mae = sum(abs(h - ia) for h, ia in pares) / n
    cerca = sum(abs(h - ia) <= 2 for h, ia in pares) / n
    decision = sum((h >= umbral) == (ia >= umbral) for h, ia in pares) / n
    fn = sum(h >= umbral and ia < umbral for h, ia in pares)
    fp = sum(h < umbral and ia >= umbral for h, ia in pares)
    return {"n": n, "mae": round(mae, 2), "acierto_2pts": round(cerca, 2),
            "acierto_decision": round(decision, 2), "falsos_negativos": fn, "falsos_positivos": fp}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--modelo", default=puntuar.MODELO)
    args = ap.parse_args()

    ofertas = {o["id"]: Oferta(**o) for o in json.loads((RAIZ / "evals/ofertas_ejemplo.json").read_text(encoding="utf-8"))}
    etiquetas = [r for r in csv.DictReader((RAIZ / "evals/etiquetas.csv").open(encoding="utf-8")) if r["nota_humana"].strip()]
    if not etiquetas:
        print("Primero rellena nota_humana en evals/etiquetas.csv")
        return 1

    import anthropic
    cliente = anthropic.Anthropic()
    pares, filas, evs = [], [], []
    for r in etiquetas:
        o = ofertas[r["id"]]
        ev = puntuar.evaluar(cliente, o, modelo=args.modelo)
        evs.append(ev)
        h, ia = int(r["nota_humana"]), int(ev["puntuacion"])
        pares.append((h, ia))
        filas.append(f"| {o.titulo[:45]} | {o.empresa[:25]} | {h} | {ia} | {'✅' if abs(h-ia) <= 2 else '⚠️'} |")

    m = metricas(pares)
    informe = [
        f"# Resultados del eval · {datetime.now():%Y-%m-%d} · `{args.modelo}`", "",
        f"- Ofertas evaluadas: **{m['n']}**",
        f"- Error medio: **{m['mae']} puntos**",
        f"- Acierto a ±2 puntos: **{m['acierto_2pts']:.0%}**",
        f"- Acierto en la decisión aplicar/no aplicar: **{m['acierto_decision']:.0%}**",
        f"- Falsos negativos (buenas que descartaría): **{m['falsos_negativos']}**",
        f"- Falsos positivos: **{m['falsos_positivos']}**",
        f"- Coste del eval: {puntuar.coste(evs, args.modelo)} $", "",
        "| Oferta | Empresa | Yo | IA | |", "|---|---|---|---|---|", *filas,
    ]
    (RAIZ / "evals/resultados.md").write_text("\n".join(informe) + "\n", encoding="utf-8")
    print("\n".join(informe))
    return 0


if __name__ == "__main__":
    sys.exit(main())
