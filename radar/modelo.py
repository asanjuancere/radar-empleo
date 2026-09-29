"""Estructura común para todas las ofertas, vengan de donde vengan.

Cada fuente (LinkedIn, Adzuna...) traduce sus datos a una `Oferta`.
Así el resto del programa no necesita saber de dónde salió cada una.
"""
from dataclasses import dataclass, field, asdict


@dataclass
class Oferta:
    id: str                 # identificador único, p. ej. "linkedin:4472492940"
    fuente: str             # "linkedin" | "adzuna" | "manual"
    titulo: str
    empresa: str = ""
    ubicacion: str = ""
    url: str = ""
    descripcion: str = ""   # vacía en las alertas de LinkedIn (solo traen título)
    fecha: str = ""
    salario: str = ""
    evaluacion: dict = field(default_factory=dict)  # la rellena puntuar.py

    def to_dict(self) -> dict:
        return asdict(self)

    @property
    def nota(self) -> int:
        return int(self.evaluacion.get("puntuacion", -1))
