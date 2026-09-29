"""Estudio rápido de la empresa de cada oferta buena.

Usa la búsqueda web de la API de Claude: busca información pública y la resume
en pocas líneas citando de dónde sale. No entra en Glassdoor ni en LinkedIn (sus
condiciones lo prohíben); en el email se añade un enlace para mirarlo a mano.
Si algo falla, devuelve texto vacío: un fallo aquí nunca debe romper el radar.
"""
from __future__ import annotations

PROMPT = (
    "Investiga en fuentes públicas la empresa «{empresa}» (oferta: «{puesto}») y resume en "
    "máximo 5 líneas: a qué se dedica, tamaño aproximado, noticias recientes relevantes "
    "(despidos, expansión, resultados) y lo que digan de ella empleados o antiguos empleados "
    "en fuentes fiables, citando la fuente entre paréntesis. No inventes nada: si no hay "
    "datos públicos suficientes, dilo. Responde en español, sin introducción."
)


def estudio(cliente, empresa: str, puesto: str, modelo: str = "claude-sonnet-5") -> str:
    if not empresa.strip():
        return ""
    try:
        r = cliente.messages.create(
            model=modelo,
            max_tokens=700,
            tools=[{"type": "web_search_20250305", "name": "web_search", "max_uses": 3}],
            messages=[{"role": "user", "content": PROMPT.format(empresa=empresa, puesto=puesto)}],
        )
        texto = "".join(b.text for b in r.content if getattr(b, "type", "") == "text").strip()
        return texto
    except Exception:
        return ""
