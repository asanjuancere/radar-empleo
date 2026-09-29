"""Pruebas automáticas: se ejecutan en cada cambio (GitHub Actions) con `python -m pytest`."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from evals.evaluar import metricas  # noqa: E402
from radar import puntuar  # noqa: E402
from radar.linkedin_email import extraer_ofertas_html  # noqa: E402
from radar.modelo import Oferta  # noqa: E402

# Ejemplo inventado (empresas ficticias).
EMAIL = """
<html><body>
<a href="https://www.linkedin.com/comm/jobs/view/4470880613/?trackingId=abc">Junior AI Operations Specialist</a>
<p>Acme Digital · Ciudad Ejemplo, Provincia Ejemplo, España</p>
<p>Contratando activamente</p>
<a href="https://www.linkedin.com/comm/jobs/view/4470880613/?trackingId=abc">Ver empleo</a>
<table><tr><td><a href="https://www.linkedin.com/comm/jobs/view/4472492940/">Automation &amp; Analytics Specialist</a></td></tr>
<tr><td>Nube Ejemplo S.L.</td></tr><tr><td>Villa Ejemplo</td></tr></table>
<a href="https://www.linkedin.com/comm/jobs/search/?keywords=ia">Ver todos los empleos</a>
</body></html>
"""


def test_extrae_ofertas_del_email():
    ofs = {o.id: o for o in extraer_ofertas_html(EMAIL)}
    assert set(ofs) == {"linkedin:4470880613", "linkedin:4472492940"}
    w = ofs["linkedin:4470880613"]
    assert w.titulo == "Junior AI Operations Specialist"
    assert w.empresa == "Acme Digital" and w.ubicacion.startswith("Ciudad")
    m = ofs["linkedin:4472492940"]
    assert m.titulo == "Automation & Analytics Specialist"
    assert m.empresa == "Nube Ejemplo S.L."
    assert m.ubicacion == "Villa Ejemplo"


def test_reglas_descartan_puestos_senior_sin_llamar_a_la_ia():
    ev = puntuar.filtro_reglas(Oferta(id="x", fuente="manual", titulo="Senior Data Lead"))
    assert ev["puntuacion"] == 2 and ev["por_reglas"]


def test_reglas_no_tocan_ofertas_normales():
    assert puntuar.filtro_reglas(Oferta(id="x", fuente="manual", titulo="Junior AI Operations Specialist")) is None


def test_metricas_eval():
    m = metricas([(9, 8), (8, 4), (2, 3), (1, 7)])
    assert m["mae"] == 3.0  # (1+4+1+6)/4
    assert m["falsos_negativos"] == 1 and m["falsos_positivos"] == 1
    assert m["acierto_decision"] == 0.5


# ---- Inteligencia de mercado ----
from datetime import date  # noqa: E402

from radar import mercado  # noqa: E402


def _oferta(id_, habilidades, suficiente=True, por_reglas=False):
    o = Oferta(id=id_, fuente="adzuna", titulo="secreto", empresa="secreta")
    o.evaluacion = {"habilidades": habilidades, "nivel": "junior",
                    "info_suficiente": suficiente, "por_reglas": por_reglas}
    return o


def test_normaliza_sinonimos():
    assert mercado.normalizar("MS Power Automate") == "Power Automate"
    assert mercado.normalizar(" n8n. ") == "n8n"
    assert mercado.normalizar("Herramienta rara") == "Herramienta rara"


def test_solo_cuentan_ofertas_con_descripcion_completa():
    ofs = [_oferta("a", ["n8n", "Python"]), _oferta("b", ["n8n"], suficiente=False),
           _oferta("c", ["Zapier"], por_reglas=True)]
    filas = mercado.registros(ofs, huella=lambda x: x, hoy=date(2026, 9, 29))
    assert {f[1] for f in filas} == {"a"}


def test_una_oferta_cuenta_cada_habilidad_una_vez():
    filas = mercado.registros([_oferta("a", ["n8n", "N8N", "n8n"])], huella=lambda x: x)
    assert len(filas) == 1


def test_ranking_y_porcentaje():
    ofs = [_oferta("a", ["n8n", "Python"]), _oferta("b", ["n8n"]), _oferta("c", ["SQL"])]
    ranking, n = mercado.top(mercado.registros(ofs, huella=lambda x: x))
    assert n == 3 and ranking[0][0] == "n8n" and ranking[0][1] == 2
    assert round(ranking[0][2], 2) == 0.67


def test_el_csv_publico_no_contiene_datos_de_la_oferta(tmp_path):
    ruta = tmp_path / "h.csv"
    mercado.guardar(ruta, mercado.registros([_oferta("a", ["n8n"])], huella=lambda x: "h123"))
    texto = ruta.read_text(encoding="utf-8")
    assert "secreto" not in texto and "secreta" not in texto and "h123" in texto


def test_informe_md(tmp_path):
    csv_ = tmp_path / "h.csv"
    mercado.guardar(csv_, mercado.registros([_oferta("a", ["n8n"])], huella=lambda x: x))
    md = mercado.escribir_informe(csv_, tmp_path / "M.md")
    assert "n8n" in md and "orientativos" in md


# ---- Email y estudio de empresa ----
from radar import empresa, informe  # noqa: E402


def test_tarjeta_escapa_html_y_enlaza_glassdoor():
    o = Oferta(id="x", fuente="manual", titulo="<b>Puesto</b>", empresa="Acme & Co", url="https://ejemplo.com/o")
    o.evaluacion = {"puntuacion": 8, "veredicto": "aplicar", "motivo": "ok", "probabilidad_entrevista": "media",
                    "argumento_carta": "Idea", "estudio_empresa": "Resumen"}
    h = informe.tarjeta(o)
    assert "<b>Puesto</b>" not in h and "&lt;b&gt;Puesto" in h
    assert "glassdoor.es" in h and "Acme+%26+Co" in h and "Sobre la empresa" in h


def test_estudio_devuelve_vacio_si_falla():
    class Roto:
        class messages:
            @staticmethod
            def create(**kw):
                raise RuntimeError("sin red")

    assert empresa.estudio(Roto(), "Acme", "Puesto") == ""
    assert empresa.estudio(Roto(), "", "Puesto") == ""
