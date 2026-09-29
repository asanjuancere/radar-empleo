"""Inteligencia de mercado: qué piden las ofertas de IA y automatización en Madrid.

Además de puntuar ofertas para mí, el radar apunta qué herramientas y habilidades
aparecen en cada una. Con las semanas sale un resumen (datos/MERCADO.md) que me
dice qué conviene aprender y poner en el CV.

Reglas de honestidad y privacidad:
- Solo cuentan las ofertas con descripción completa (las alertas de LinkedIn
  traen solo el título: sus "habilidades" serían adivinanzas).
- Solo se guarda una huella de la oferta, la fecha, la habilidad y el nivel.
  Nada de empresas, títulos ni enlaces: el repositorio es público.
"""
from __future__ import annotations

import csv
from collections import Counter
from datetime import date, datetime, timedelta
from pathlib import Path

from .modelo import Oferta

# Sinónimos habituales -> nombre único (para que "MS Power Automate" y "Power Automate" cuenten igual)
ALIAS = {
    "ms power automate": "Power Automate", "microsoft power automate": "Power Automate",
    "power platform": "Power Platform", "microsoft power platform": "Power Platform",
    "copilot studio": "Copilot Studio", "microsoft copilot studio": "Copilot Studio",
    "llm": "LLMs", "llms": "LLMs", "modelos de lenguaje": "LLMs", "api de llm": "API de LLMs",
    "apis de llm": "API de LLMs", "llm apis": "API de LLMs", "openai api": "API de LLMs",
    "agentes": "Agentes de IA", "agentes de ia": "Agentes de IA", "ai agents": "Agentes de IA",
    "agentic ai": "Agentes de IA", "prompt engineering": "Prompt engineering", "prompting": "Prompt engineering",
    "no-code": "No-code/Low-code", "low-code": "No-code/Low-code", "low-code/no-code": "No-code/Low-code",
    "no-code/low-code": "No-code/Low-code", "powerbi": "Power BI", "power bi": "Power BI",
    "python": "Python", "javascript": "JavaScript", "sql": "SQL", "n8n": "n8n", "zapier": "Zapier",
    "make": "Make", "rpa": "RPA", "uipath": "UiPath", "azure": "Azure", "aws": "AWS",
    "apis rest": "APIs REST", "api rest": "APIs REST", "rest apis": "APIs REST", "function calling": "Function calling",
}


def normalizar(habilidad: str) -> str:
    h = " ".join(habilidad.split()).strip(" .,;")
    return ALIAS.get(h.lower(), h)


def registros(ofertas: list[Oferta], huella, hoy: date | None = None) -> list[tuple]:
    """Filas (fecha, huella, habilidad, nivel) de las ofertas con información suficiente."""
    hoy = hoy or date.today()
    filas = []
    for o in ofertas:
        ev = o.evaluacion
        if not ev or ev.get("por_reglas") or not ev.get("info_suficiente", True):
            continue
        # Set: una oferta cuenta una habilidad una sola vez aunque la repita
        for h in sorted({normalizar(x) for x in ev.get("habilidades", []) if x.strip()}):
            filas.append((hoy.isoformat(), huella(o.id), h, ev.get("nivel", "no indicado")))
    return filas


def guardar(ruta: Path, filas: list[tuple]) -> None:
    if not filas:
        return
    ruta.parent.mkdir(exist_ok=True)
    nueva = not ruta.exists()
    with ruta.open("a", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        if nueva:
            w.writerow(["fecha", "oferta", "habilidad", "nivel"])
        w.writerows(filas)


def top(filas: list[tuple], n: int = 15) -> tuple[list[tuple[str, int, float]], int]:
    """Devuelve ([(habilidad, apariciones, % de ofertas)], nº de ofertas con datos)."""
    ofertas = {f[1] for f in filas}
    cuenta = Counter(f[2] for f in filas)
    total = len(ofertas) or 1
    return [(h, c, c / total) for h, c in cuenta.most_common(n)], len(ofertas)


def leer(ruta: Path, dias: int = 30, hoy: date | None = None) -> list[tuple]:
    if not ruta.exists():
        return []
    hoy = hoy or date.today()
    limite = hoy - timedelta(days=dias)
    with ruta.open(encoding="utf-8") as f:
        filas = [tuple(r) for r in list(csv.reader(f))[1:]]
    return [f for f in filas if datetime.strptime(f[0], "%Y-%m-%d").date() >= limite]


def escribir_informe(ruta_csv: Path, ruta_md: Path, dias: int = 30) -> str:
    filas = leer(ruta_csv, dias)
    ranking, n = top(filas)
    lineas = [f"# Qué piden las ofertas de IA y automatización en Madrid", "",
              f"Últimos {dias} días · **{n} ofertas** con descripción completa · actualizado {date.today():%d/%m/%Y}", ""]
    if n < 20:
        lineas += [f"> Aviso: con solo {n} ofertas los porcentajes son orientativos. "
                   "Se vuelven fiables a partir de unas 50.", ""]
    if ranking:
        lineas += ["| # | Habilidad o herramienta | Ofertas | % |", "|---|---|---|---|"]
        lineas += [f"| {i} | {h} | {c} | {p:.0%} |" for i, (h, c, p) in enumerate(ranking, 1)]
    else:
        lineas.append("Todavía no hay datos suficientes.")
    lineas += ["", "Metodología: la IA extrae las habilidades de cada descripción; una oferta cuenta "
               "cada habilidad una sola vez; las alertas de LinkedIn (solo título) no se cuentan. "
               "No se guarda empresa, título ni enlace de ninguna oferta."]
    texto = "\n".join(lineas) + "\n"
    ruta_md.write_text(texto, encoding="utf-8")
    return texto
