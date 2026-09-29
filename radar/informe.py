"""Salida: el resumen diario por email y las métricas públicas.

Privacidad: el repositorio es público, así que NO se publican las ofertas ni mis
notas (se vería qué busco y dónde). Solo se guardan métricas
agregadas (cuántas ofertas, cuántas buenas, coste). El detalle llega a mi email.

Diseño del email: mismos colores y tipografía que mi web (verde sobrio sobre
crema, títulos con serif). Los emails no cargan fuentes web, así que se usan
Georgia (títulos) y Arial (texto), que existen en cualquier programa de correo.
"""
from __future__ import annotations

import csv
import html
import smtplib
import urllib.parse
from datetime import datetime
from email.mime.text import MIMEText
from pathlib import Path

from .modelo import Oferta

# Paleta (la misma que la web)
FONDO, TARJETA, TINTA, VERDE = "#f6f3ee", "#fffdf9", "#1f2a24", "#2f4a3a"
APAGADO, BORDE = "#6b6f68", "#e4ded3"
COLOR_NOTA = {"aplicar hoy": "#2f4a3a", "aplicar": "#4a6b58", "dudosa": "#a0722a", "descartar": "#8a8f98"}
SERIF, SANS = "Georgia,'Times New Roman',serif", "Arial,Helvetica,sans-serif"


def _q(texto: str) -> str:
    return urllib.parse.quote_plus(texto)


def _enlace(url: str, texto: str) -> str:
    return (f'<a href="{html.escape(url)}" style="color:{VERDE};text-decoration:none;'
            f'border-bottom:1px solid {VERDE};font-size:13px">{html.escape(texto)}</a>')


def _lista(titulo: str, items: list[str], signo: str) -> str:
    if not items:
        return ""
    e = html.escape
    lis = "".join(f'<div style="margin:0 0 4px">{signo} {e(x)}</div>' for x in items)
    return (f'<div style="font-size:12px;letter-spacing:.06em;text-transform:uppercase;color:{APAGADO};'
            f'margin:12px 0 6px">{titulo}</div><div style="font-size:14px;line-height:1.5;color:{TINTA}">{lis}</div>')


def tarjeta(o: Oferta) -> str:
    """Una oferta = una tarjeta: nota, resumen, encaje, carencias, mensaje y enlaces."""
    e = html.escape
    ev = o.evaluacion
    veredicto = ev.get("veredicto", "")
    color = COLOR_NOTA.get(veredicto, APAGADO)
    aviso = "" if ev.get("info_suficiente", True) else f' <span style="color:{APAGADO}">(solo título: nota orientativa)</span>'
    meta = " · ".join(x for x in [e(o.empresa), e(o.ubicacion), e(o.salario), e(o.fuente)] if x)
    enlaces = []
    if o.url:
        enlaces.append(_enlace(o.url, "Ver oferta"))
    if o.empresa:
        enlaces.append(_enlace(f"https://www.glassdoor.es/Search/results.htm?keyword={_q(o.empresa)}", "Opiniones en Glassdoor"))
        enlaces.append(_enlace(f"https://www.linkedin.com/search/results/companies/?keywords={_q(o.empresa)}", "Empresa en LinkedIn"))
    estudio = ev.get("estudio_empresa", "")
    bloque_estudio = ""
    if estudio:
        bloque_estudio = (f'<div style="margin:14px 0 0;padding:12px 14px;background:{FONDO};border-radius:8px;'
                          f'font-size:13px;line-height:1.55;color:{TINTA}"><b style="color:{VERDE}">Sobre la empresa</b><br>'
                          f'{e(estudio).replace(chr(10), "<br>")}</div>')
    mensaje = ev.get("argumento_carta", "")
    bloque_msg = ""
    if mensaje:
        bloque_msg = (f'<div style="margin:14px 0 0;padding:12px 14px;border-left:3px solid {VERDE};background:{FONDO};'
                      f'font-size:14px;line-height:1.55;font-style:italic;color:{TINTA}">'
                      f'<span style="font-style:normal;font-size:12px;letter-spacing:.06em;text-transform:uppercase;'
                      f'color:{APAGADO}">Idea para el mensaje</span><br>{e(mensaje)}</div>')
    return f"""
<div style="background:{TARJETA};border:1px solid {BORDE};border-radius:14px;padding:22px 24px;margin:0 0 16px">
  <table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="border-collapse:collapse"><tr>
    <td style="vertical-align:top">
      <div style="font-family:{SANS};font-size:12px;letter-spacing:.06em;text-transform:uppercase;color:{color};font-weight:700">
        {e(veredicto)} · entrevista {e(ev.get('probabilidad_entrevista', ''))}</div>
      <div style="font-family:{SERIF};font-size:21px;line-height:1.25;color:{TINTA};margin:6px 0 4px">{e(o.titulo)}</div>
      <div style="font-family:{SANS};font-size:13px;color:{APAGADO}">{meta}</div>
    </td>
    <td width="64" style="vertical-align:top;text-align:right">
      <div style="font-family:{SERIF};font-size:30px;color:{color};line-height:1">{o.nota}<span style="font-size:14px;color:{APAGADO}">/10</span></div>
    </td>
  </tr></table>
  <div style="font-family:{SANS}">
    <p style="margin:14px 0 0;font-size:14px;line-height:1.55;color:{TINTA}">{e(ev.get('motivo', ''))}{aviso}</p>
    {_lista('Encaja', ev.get('encaje', []), '✓')}
    {_lista('Ojo con', ev.get('carencias', []), '–')}
    {bloque_msg}
    {bloque_estudio}
    <div style="margin:16px 0 0">{'&nbsp;&nbsp;·&nbsp;&nbsp;'.join(enlaces)}</div>
  </div>
</div>"""


def marco(titulo: str, subtitulo: str, cuerpo: str, pie: str = "") -> str:
    return f"""<div style="background:{FONDO};padding:28px 12px">
<div style="max-width:640px;margin:0 auto;font-family:{SANS};color:{TINTA}">
  <div style="font-family:{SERIF};font-size:28px;color:{TINTA};margin:0 0 4px">{html.escape(titulo)}</div>
  <div style="font-size:14px;color:{APAGADO};margin:0 0 22px">{subtitulo}</div>
  {cuerpo}
  <div style="font-size:12px;color:{APAGADO};margin:18px 0 0;text-align:center">{pie}</div>
</div></div>"""


def html_resumen(ofertas: list[Oferta], coste_usd: float) -> str:
    buenas = [o for o in ofertas if o.nota >= 7]
    tarjetas = "".join(tarjeta(o) for o in sorted(ofertas, key=lambda x: -x.nota) if o.nota >= 5)
    cuerpo = tarjetas or f'<p style="color:{APAGADO}">Hoy no hay ofertas con nota 5 o más.</p>'
    sub = f"{datetime.now():%d/%m/%Y} · {len(ofertas)} ofertas analizadas · <b style=\"color:{VERDE}\">{len(buenas)} con nota 7 o más</b>"
    return marco("Radar de empleo", sub, cuerpo, f"Coste de hoy: {coste_usd:.3f} $ · Notas de la IA según tu rúbrica; la decisión es tuya.")


def html_una_oferta(o: Oferta, coste_usd: float = 0.0) -> str:
    return marco("Evaluación de una oferta", f"{datetime.now():%d/%m/%Y}", tarjeta(o),
                 f"Coste: {coste_usd:.3f} $ · Nota orientativa de la IA; la decisión es tuya.")


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
