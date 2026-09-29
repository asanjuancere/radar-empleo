"""Evaluar UNA oferta a demanda (el «botón» del radar).

Se lanza desde GitHub Actions → «Evaluar una oferta» → Run workflow, rellenando
tres casillas (título, empresa y texto de la oferta). En un minuto llega al email
una tarjeta con la nota, el encaje, el estudio de la empresa y una idea de mensaje.

IMPORTANTE: úsalo en tu copia PRIVADA del repositorio. En un repositorio público,
lo que escribes en las casillas del botón queda visible para cualquiera.
"""
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

from radar import empresa, informe, puntuar
from radar.modelo import Oferta

RAIZ = Path(__file__).resolve().parent


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--demo", action="store_true")
    args = ap.parse_args()

    o = Oferta(id="manual", fuente="manual",
               titulo=os.getenv("OFERTA_TITULO", "").strip() or "Oferta sin título",
               empresa=os.getenv("OFERTA_EMPRESA", "").strip(),
               descripcion=os.getenv("OFERTA_TEXTO", "").strip(),
               url=os.getenv("OFERTA_URL", "").strip())
    if args.demo or not os.getenv("ANTHROPIC_API_KEY"):
        from main import EvaluadorDemo
        cliente = EvaluadorDemo()
        demo = True
    else:
        import anthropic
        cliente = anthropic.Anthropic()
        demo = False

    o.evaluacion = puntuar.evaluar(cliente, o)
    if not demo and o.nota >= 5:
        o.evaluacion["estudio_empresa"] = empresa.estudio(cliente, o.empresa, o.titulo)
    coste = puntuar.coste([o.evaluacion])
    cuerpo = informe.html_una_oferta(o, coste)
    (RAIZ / "informe.html").write_text(cuerpo, encoding="utf-8")  # ignorado por git

    usuario, clave = os.getenv("GMAIL_USUARIO"), os.getenv("GMAIL_CLAVE_APP")
    if usuario and clave:
        informe.enviar_email(usuario, clave, os.getenv("EMAIL_DESTINO", usuario),
                             f"Evaluación: {o.titulo[:60]} ({o.nota}/10)", cuerpo)
        print("Evaluación enviada por email.")  # a propósito: no se imprime nada de la oferta
    else:
        print("Sin credenciales de email: informe.html generado (modo demo).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
