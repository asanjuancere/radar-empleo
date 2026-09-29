"""Fuente 2: API oficial de Adzuna (agregador de ofertas con cobertura en España).

A diferencia de las alertas de LinkedIn, Adzuna devuelve un extracto de la
descripción, así que la IA puede evaluar con más información.
Plan gratuito: 250 llamadas al día (nosotros hacemos ~5).
Alta en https://developer.adzuna.com/ -> app_id y app_key.
"""
from __future__ import annotations

import json
import urllib.parse
import urllib.request

from .modelo import Oferta

API = "https://api.adzuna.com/v1/api/jobs/es/search/1"


def buscar(app_id: str, app_key: str, consultas: list[str], donde: str = "",
           max_dias: int = 2, por_consulta: int = 30) -> list[Oferta]:
    ofertas: dict[str, Oferta] = {}
    for q in consultas:
        params = urllib.parse.urlencode({
            "app_id": app_id, "app_key": app_key, "what": q, **({"where": donde} if donde else {}),
            "max_days_old": max_dias, "results_per_page": por_consulta,
            "sort_by": "date", "content-type": "application/json",
        })
        with urllib.request.urlopen(f"{API}?{params}", timeout=30) as r:
            datos = json.load(r)
        for j in datos.get("results", []):
            salario = ""
            if j.get("salary_min"):
                salario = f"{int(j['salary_min']):,}–{int(j.get('salary_max') or j['salary_min']):,} €".replace(",", ".")
            o = Oferta(
                id=f"adzuna:{j['id']}",
                fuente="adzuna",
                titulo=j.get("title", "").strip(),
                empresa=(j.get("company") or {}).get("display_name", ""),
                ubicacion=(j.get("location") or {}).get("display_name", ""),
                url=j.get("redirect_url", ""),
                descripcion=j.get("description", ""),
                fecha=j.get("created", ""),
                salario=salario,
            )
            ofertas.setdefault(o.id, o)
    return list(ofertas.values())
