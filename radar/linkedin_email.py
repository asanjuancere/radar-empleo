"""Fuente 1: alertas de empleo de LinkedIn que llegan por email.

Por qué por email y no leyendo LinkedIn directamente:
LinkedIn prohíbe el acceso automatizado (robots.txt y condiciones de uso) y puede
bloquear la cuenta. Las alertas por email son el canal oficial: LinkedIn nos
manda las ofertas y nosotros solo leemos nuestro propio correo.

Cómo funciona:
1. Se conecta al buzón por IMAP con una "contraseña de aplicación" de Google.
2. Busca los emails de alertas de LinkedIn de los últimos días.
3. Saca de cada email los enlaces /jobs/view/<id> y el texto que los rodea
   (título, empresa y ubicación).
"""
from __future__ import annotations

import email
import imaplib
import re
from datetime import date, timedelta
from email.header import decode_header, make_header
from html.parser import HTMLParser

from .modelo import Oferta

REMITENTES = ["jobalerts-noreply@linkedin.com", "jobs-listings@linkedin.com"]
RE_JOB = re.compile(r"linkedin\.com/(?:comm/)?jobs/view/(\d+)")
# Líneas que aparecen en las alertas pero no son datos de la oferta
RUIDO = re.compile(
    r"^(ver empleo|view job|solicitud sencilla|easy apply|promocionado|promoted|"
    r"nuevo|new|actively recruiting|contratando activamente|\d+ (conexiones?|connections?)|"
    r"hace .*|.* ago|ver todos los empleos|see all jobs)$",
    re.I,
)


class _Lector(HTMLParser):
    """Convierte el HTML del email en una lista de trozos de texto,
    marcando qué trozos están dentro de un enlace a una oferta."""

    def __init__(self):
        super().__init__()
        self.trozos: list[tuple[str, str | None]] = []  # (texto, job_id o None)
        self._job: str | None = None
        self._ignorar = 0

    def handle_starttag(self, tag, attrs):
        if tag in ("style", "script"):
            self._ignorar += 1
        if tag == "a":
            m = RE_JOB.search(dict(attrs).get("href", "") or "")
            self._job = m.group(1) if m else None

    def handle_endtag(self, tag):
        if tag in ("style", "script"):
            self._ignorar -= 1
        if tag == "a":
            self._job = None

    def handle_data(self, data):
        t = " ".join(data.split())
        if t and not self._ignorar:
            self.trozos.append((t, self._job))


def extraer_ofertas_html(html: str) -> list[Oferta]:
    """Saca las ofertas de un email de alerta. Función pura: fácil de probar."""
    lector = _Lector()
    lector.feed(html)
    trozos = lector.trozos
    ofertas: dict[str, Oferta] = {}
    for i, (texto, job) in enumerate(trozos):
        if not job or job in ofertas or RUIDO.match(texto) or len(texto) < 4:
            continue
        # El primer texto útil dentro del enlace es el título.
        # Los dos siguientes textos útiles suelen ser empresa y ubicación.
        siguientes = []
        for t, j in trozos[i + 1 : i + 8]:
            if j == job and t == texto:
                continue
            if RUIDO.match(t) or (j and j != job):
                if j and j != job:
                    break
                continue
            siguientes.append(t)
            if len(siguientes) == 2:
                break
        empresa = siguientes[0] if siguientes else ""
        ubicacion = siguientes[1] if len(siguientes) > 1 else ""
        # A veces viene "Empresa · Ubicación" en una sola línea
        if "·" in empresa and not ubicacion:
            empresa, ubicacion = [p.strip() for p in empresa.split("·", 1)]
        ofertas[job] = Oferta(
            id=f"linkedin:{job}",
            fuente="linkedin",
            titulo=texto,
            empresa=empresa,
            ubicacion=ubicacion,
            url=f"https://www.linkedin.com/jobs/view/{job}/",
        )
    return list(ofertas.values())


def _cuerpo_html(msg: email.message.Message) -> str:
    for parte in msg.walk():
        if parte.get_content_type() == "text/html":
            return parte.get_payload(decode=True).decode(parte.get_content_charset() or "utf-8", "replace")
    return ""


def leer_alertas(usuario: str, clave_app: str, dias: int = 2) -> list[Oferta]:
    """Lee el buzón y devuelve todas las ofertas de las alertas recientes."""
    desde = (date.today() - timedelta(days=dias)).strftime("%d-%b-%Y")
    ofertas: dict[str, Oferta] = {}
    with imaplib.IMAP4_SSL("imap.gmail.com") as imap:
        imap.login(usuario, clave_app)
        imap.select("INBOX", readonly=True)  # solo lectura: no marca nada como leído
        for remitente in REMITENTES:
            _, datos = imap.search(None, f'(FROM "{remitente}" SINCE {desde})')
            for num in datos[0].split():
                _, partes = imap.fetch(num, "(RFC822)")
                msg = email.message_from_bytes(partes[0][1])
                asunto = str(make_header(decode_header(msg.get("Subject", ""))))
                for o in extraer_ofertas_html(_cuerpo_html(msg)):
                    o.fecha = msg.get("Date", "")
                    o.descripcion = f"(Alerta de LinkedIn: «{asunto}». Solo título, empresa y ubicación.)"
                    ofertas.setdefault(o.id, o)
    return list(ofertas.values())
