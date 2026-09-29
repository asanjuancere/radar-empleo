"""Radar de empleo con IA — orquestador.

Se ejecuta cada mañana en GitHub Actions (o a mano en local):
  1. Recoge ofertas nuevas (alertas de LinkedIn por email + API de Adzuna)
  2. Quita las ya vistas otros días
  3. Claude las puntúa con mi rúbrica
  4. Me envía un resumen por email y guarda métricas agregadas

Uso:
  python main.py                 # ejecución real (usa variables de entorno)
  python main.py --demo          # sin claves: datos de ejemplo y evaluador simulado
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from pathlib import Path

from radar import adzuna, empresa, informe, linkedin_email, mercado, puntuar
from radar.modelo import Oferta

RAIZ = Path(__file__).resolve().parent
VISTOS = RAIZ / "datos" / "vistos.json"
METRICAS = RAIZ / "datos" / "metricas.csv"
HABILIDADES = RAIZ / "datos" / "habilidades.csv"
MERCADO = RAIZ / "datos" / "MERCADO.md"
CONSULTAS_ADZUNA = os.getenv("CONSULTAS_ADZUNA", "automatización IA|AI automation|n8n").split("|")


def huella(id_: str) -> str:
    """Guardamos una huella del id, no el id: el repo es público y no quiero
    que se pueda saber a qué ofertas exactas estoy mirando."""
    return hashlib.sha256(id_.encode()).hexdigest()[:16]


def cargar_vistos() -> set[str]:
    return set(json.loads(VISTOS.read_text())) if VISTOS.exists() else set()


def guardar_vistos(v: set[str]) -> None:
    VISTOS.parent.mkdir(exist_ok=True)
    VISTOS.write_text(json.dumps(sorted(v), indent=0))


def recoger() -> list[Oferta]:
    ofertas: list[Oferta] = []
    if os.getenv("GMAIL_USUARIO") and os.getenv("GMAIL_CLAVE_APP"):
        li = linkedin_email.leer_alertas(os.environ["GMAIL_USUARIO"], os.environ["GMAIL_CLAVE_APP"])
        print(f"LinkedIn (alertas por email): {len(li)} ofertas")
        ofertas += li
    if os.getenv("ADZUNA_APP_ID") and os.getenv("ADZUNA_APP_KEY"):
        az = adzuna.buscar(os.environ["ADZUNA_APP_ID"], os.environ["ADZUNA_APP_KEY"], CONSULTAS_ADZUNA)
        print(f"Adzuna: {len(az)} ofertas")
        ofertas += az
    return ofertas


class EvaluadorDemo:
    """Imita a Claude sin gastar: sirve para probar el flujo completo sin claves."""

    class messages:
        @staticmethod
        def create(**kw):
            txt = kw["messages"][0]["content"].lower()
            claves = ["ia", "ai", "automat", "agente", "claude", "n8n", "no-code", "low-code"]
            n = min(10, 3 + sum(k in txt for k in claves))
            from types import SimpleNamespace as NS
            ev = {"puntuacion": n, "veredicto": "aplicar" if n >= 7 else "dudosa" if n >= 5 else "descartar",
                  "motivo": "(demo) Nota calculada por palabras clave, no por IA.",
                  "encaje": ["(demo)"], "carencias": [], "probabilidad_entrevista": "media",
                  "argumento_carta": "(demo)", "info_suficiente": True,
                  "habilidades": [h for h in ["n8n", "Zapier", "Python", "Power Automate", "Copilot Studio", "Claude"] if h.lower() in txt],
                  "nivel": "senior" if "senior" in txt else "junior" if "junior" in txt else "no indicado"}
            return NS(content=[NS(type="tool_use", input=ev)],
                      usage=NS(input_tokens=0, output_tokens=0, cache_read_input_tokens=0, cache_creation_input_tokens=0))


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--demo", action="store_true", help="datos de ejemplo, sin claves ni coste")
    ap.add_argument("--sin-email", action="store_true")
    args = ap.parse_args()

    if args.demo:
        ofertas = [Oferta(**o) for o in json.loads((RAIZ / "evals" / "ofertas_ejemplo.json").read_text(encoding="utf-8"))]
        cliente = EvaluadorDemo()
    else:
        import anthropic
        ofertas = recoger()
        cliente = anthropic.Anthropic()  # lee ANTHROPIC_API_KEY

    vistos = set() if args.demo else cargar_vistos()
    nuevas = [o for o in ofertas if huella(o.id) not in vistos]
    print(f"Nuevas (no vistas antes): {len(nuevas)}")

    evaluaciones = []
    for o in nuevas:
        try:
            o.evaluacion = puntuar.evaluar(cliente, o)
            if not args.demo and o.nota >= 7:
                o.evaluacion["estudio_empresa"] = empresa.estudio(cliente, o.empresa, o.titulo)
            evaluaciones.append(o.evaluacion)
            if args.demo:  # en ejecuciones reales NO se imprime nada de las ofertas (los registros pueden ser públicos)
                print(f"  {o.nota:>2}/10  {o.titulo[:60]} — {o.empresa}")
        except Exception as e:  # una oferta rara no debe tumbar toda la ejecución
            print(f"  ERROR evaluando una oferta: {type(e).__name__}", file=sys.stderr)

    coste = puntuar.coste(evaluaciones)
    cuerpo = informe.html_resumen(nuevas, coste)
    (RAIZ / "informe.html").write_text(cuerpo, encoding="utf-8")  # ignorado por git
    print(f"Coste estimado: {coste} $ · informe.html generado")

    filas = mercado.registros(nuevas, huella)
    if args.demo:
        ranking, n = mercado.top(filas, 5)
        print(f"Mercado (demo, {n} ofertas): " + ", ".join(f"{h} ({c})" for h, c, _ in ranking))
    else:
        mercado.guardar(HABILIDADES, filas)
        mercado.escribir_informe(HABILIDADES, MERCADO)
        guardar_vistos(vistos | {huella(o.id) for o in nuevas})
        informe.guardar_metricas(METRICAS, nuevas, coste)
        buenas = sum(o.nota >= 7 for o in nuevas)
        if not args.sin_email and os.getenv("GMAIL_USUARIO"):
            informe.enviar_email(os.environ["GMAIL_USUARIO"], os.environ["GMAIL_CLAVE_APP"],
                                 os.getenv("EMAIL_DESTINO", os.environ["GMAIL_USUARIO"]),
                                 f"🎯 Radar: {buenas} ofertas buenas hoy", cuerpo)
            print("Email enviado")
    return 0


if __name__ == "__main__":
    sys.exit(main())
