"""Salida: el resumen diario por email y las métricas públicas.

Privacidad: el repositorio es público, así que NO se publican las ofertas ni mis
notas (se vería qué busco y dónde). Solo se guardan métricas
agregadas (cuántas ofertas, cuántas buenas, coste). El detalle llega a mi email.
"""
from __future__ import annotations

import csv
import html
import smtplib
from datetime import datetime
from email.mime.text import MIMEText
from pathlib import Path

from .modelo import Oferta

COLOR = {"aplicar hoy": "#157a4a", "aplicar": "#2f5bea", "dudosa": "#a55a00", "descartar": "#8a8f98"}


def html_resumen(ofertas: list[Oferta], coste_usd: float) -> str:
    e = html.escape
    buenas = [o for o in ofertas if o.nota >= 7]
    filas = []
    for o in sorted(ofertas, key=lambda x: -x.nota):
        ev = o.evaluacion
        if o.nota < 5:
            continue
        aviso = "" if ev.get("info_suficiente", True) else " <i>(solo título: nota orientativa)</i>"
        encaje = "".join(f"<li>✓ {e(x)}</li>" for x in ev.get("encaje", []))
        carencias = "".join(f"<li>✗ {e(x)}</li>" for x in ev.get("carencias", []))
        filas.append(f"""
<div style="border:1px solid #e2e5ea;border-radius:10px;padding:14px 16px;margin:0 0 12px">
  <div style="font-size:13px;color:{COLOR.get(ev.get('veredicto'), '#555')};font-weight:700">
    {o.nota}/10 · {e(ev.get('veredicto', '').upper())} · entrevista {e(ev.get('probabilidad_entrevista', ''))}</div>
  <div style="font-size:16px;font-weight:700;margin:4px 0"><a href="{e(o.url)}" style="color:#14171c">{e(o.titulo)}</a></div>
  <div style="color:#5d6570;font-size:14px">{e(o.empresa)} · {e(o.ubicacion)} {('· ' + e(o.salario)) if o.salario else ''} · {e(o.fuente)}</div>
  <p style="margin:8px 0;font-size:14px">{e(ev.get('motivo', ''))}{aviso}</p>
  <ul style="margin:0 0 8px;padding-left:0;list-style:none;font-size:13px">{encaje}{carencias}</ul>
  <div style="font-size:13px;background:#f0f2f5;border-radius:8px;padding:8px 10px">💬 {e(ev.get('argumento_carta', ''))}</div>
</div>""")
    cuerpo = "".join(filas) or "<p>Hoy no hay ofertas con nota 5 o más.</p>"
    return f"""<div style="font-family:Arial,sans-serif;max-width:640px;margin:auto;color:#14171c">
<h2 style="margin:0 0 4px">Radar de empleo · {datetime.now():%d/%m/%Y}</h2>
<p style="color:#5d6570;margin:0 0 16px">{len(ofertas)} ofertas nuevas analizadas · <b>{len(buenas)} con nota ≥ 7</b> · coste {coste_usd:.3f} $</p>
{cuerpo}</div>"""


def enviar_email(usuario: str, clave_app: str, destino: str, asunto: str, cuerpo_html: str) -> None:
    msg = MIMEText(cuerpo_html, "html", "utf-8")
    msg["Subject"], msg["From"], msg["To"] = asunto, usuario, destino
    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as s:
        s.login(usuario, clave_app)
        s.send_message(msg)


def guardar_metricas(ruta: Path, ofertas: list[Oferta], coste_usd: float) -> None:
    nueva = not ruta.exists()
    with ruta.open("a", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        if nueva:
            w.writerow(["fecha", "ofertas_nuevas", "linkedin", "adzuna", "descartadas_por_reglas",
                        "nota_media", "nota_7_o_mas", "coste_usd"])
        notas = [o.nota for o in ofertas if o.nota >= 0]
        w.writerow([
            datetime.now().strftime("%Y-%m-%d"), len(ofertas),
            sum(o.fuente == "linkedin" for o in ofertas), sum(o.fuente == "adzuna" for o in ofertas),
            sum(bool(o.evaluacion.get("por_reglas")) for o in ofertas),
            round(sum(notas) / len(notas), 2) if notas else "", sum(n >= 7 for n in notas), coste_usd,
        ])
