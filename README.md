# Radar de empleo con IA

[![Radar de empleo](https://github.com/asanjuancere/radar-empleo/actions/workflows/radar-empleo.yml/badge.svg)](https://github.com/asanjuancere/radar-empleo/actions/workflows/radar-empleo.yml)

Cada mañana revisa las ofertas nuevas, las puntúa con IA según **un criterio propio** y envía por email solo las que merecen la pena, con el porqué y un argumento para la candidatura.

Es una herramienta personal de seguimiento de ofertas. El criterio (perfil y rúbrica) es privado y se carga desde secretos de GitHub; este repositorio incluye **ejemplos inventados** para que cualquiera pueda probarlo. Además de puntuar, **apunta qué herramientas y habilidades piden** las ofertas y con las semanas publica un resumen del mercado: [`datos/MERCADO.md`](datos/MERCADO.md).

## Cómo comprobar que funciona

- **Insignia de arriba:** verde = la última ejecución automática pasó las pruebas y terminó bien.
- **[Pestaña Actions](https://github.com/asanjuancere/radar-empleo/actions):** historial de ejecuciones, una por día laborable, con el registro completo.
- **[`datos/metricas.csv`](datos/):** una fila por ejecución (ofertas analizadas, cuántas buenas, coste). Se actualiza solo.
- **[`datos/MERCADO.md`](datos/):** ranking de habilidades que piden las ofertas, generado a partir de datos reales.
- **Modo demo:** mientras no haya claves conectadas, el flujo se ejecuta con las ofertas inventadas y un evaluador simulado. Sirve para demostrar que la tubería funciona de principio a fin sin coste.

## Estado del proyecto

- [x] Estructura, reglas de descarte y puntuación con IA (tool use, salida estructurada)
- [x] Ejecución automática en GitHub Actions y pruebas automáticas
- [x] Evals: script que compara la nota de la IA con la mía
- [x] Extracción de habilidades e informe de mercado
- [ ] Conectar las fuentes reales (alertas de LinkedIn por email y API de Adzuna)
- [ ] Primer eval con 30 ofertas puntuadas a mano → resultados en `evals/resultados.md`
- [ ] Dos semanas de datos reales y sección de aprendizajes

## Cómo funciona

```
 Alertas de LinkedIn ─┐   (email, vía IMAP)
                      ├──► Quitar ya vistas ──► Filtro por reglas ──► Claude + rúbrica ──► Email diario
 API de Adzuna ───────┘                          (gratis, obvio)      (tool use, JSON)     + métricas
                                  ▲
                    GitHub Actions: lunes a viernes a las 08:15
```

| Archivo | Qué hace |
|---|---|
| `main.py` | Orquesta todo el proceso |
| `radar/linkedin_email.py` | Lee las alertas de LinkedIn del buzón y extrae título, empresa y ubicación |
| `radar/adzuna.py` | Consulta la API oficial de Adzuna (incluye extracto de la descripción) |
| `radar/puntuar.py` | Filtro por reglas + evaluación con Claude y salida estructurada |
| `radar/informe.py` | Email diario y métricas agregadas |
| `radar/mercado.py` | Registro anónimo de habilidades demandadas e informe mensual |
| `rubrica.ejemplo.md` · `perfil.ejemplo.md` | Ejemplos inventados; el criterio real es privado (secretos de GitHub) |
| `evals/` | Conjunto etiquetado y script que mide si la IA acierta |
| `tests/` | Pruebas que se ejecutan antes de cada ejecución |
| `.github/workflows/` | La ejecución diaria automática |

## Cómo usarlo con tu propio criterio

1. Haz un *fork* de este repositorio.
2. Escribe tu perfil y tu rúbrica (parte de `perfil.ejemplo.md` y `rubrica.ejemplo.md`).
3. En *Settings → Secrets and variables → Actions* añade los secretos: `ANTHROPIC_API_KEY`, `PERFIL`, `RUBRICA` y, para las fuentes, `GMAIL_USUARIO`, `GMAIL_CLAVE_APP` (contraseña de aplicación de Google), `ADZUNA_APP_ID` y `ADZUNA_APP_KEY`. Opcionales: `DESCARTE_EXTRA` (una expresión regular de puestos a descartar sin gastar IA).
4. Crea alertas de empleo en LinkedIn con tu correo.
5. En la pestaña *Actions*, lanza el flujo a mano con *Run workflow*. Desde entonces se ejecuta solo cada día laborable.

Sin la clave de Anthropic el flujo funciona en modo demo. Coste con clave: unos pocos euros al mes.

## Decisiones de diseño

- **LinkedIn por email, no scraping.** LinkedIn prohíbe el acceso automatizado y puede bloquear la cuenta. Las alertas por email son el canal oficial; el programa solo lee el propio correo, en modo solo lectura.
- **Reglas antes que IA.** Lo obvio se descarta sin llamar al modelo. Más barato y más predecible.
- **Tool use con esquema JSON.** Claude devuelve siempre los mismos campos (nota, veredicto, encaje, carencias, probabilidad de entrevista), así las notas se pueden ordenar, medir y comparar.
- **Prompt caching.** La rúbrica y el perfil se repiten en cada llamada; se cachean y esa parte cuesta ~10 % a partir de la segunda oferta.
- **Temperatura 0.** La misma oferta debe recibir la misma nota.
- **Honestidad sobre la información.** Si una oferta solo trae título, la IA lo marca (`info_suficiente=false`) y la nota se presenta como orientativa.
- **Privacidad.** El repo es público: no se publican ofertas, empresas ni notas, solo métricas agregadas. Los ids ya vistos se guardan como huella (hash). Las ofertas de ejemplo de los evals son inventadas.

## Inteligencia de mercado

Cada oferta con descripción completa aporta sus habilidades (n8n, Power Automate, agentes de IA...). El programa las cuenta y regenera [`datos/MERCADO.md`](datos/MERCADO.md) con el ranking de los últimos 30 días.

- Las alertas de LinkedIn solo traen el título, así que **no cuentan**: sus habilidades serían suposiciones.
- Solo se guarda fecha, huella de la oferta, habilidad y nivel. Ni empresas, ni títulos, ni enlaces.
- Con pocas ofertas el informe avisa de que los porcentajes son orientativos.

## Evals: ¿puntúa como yo?

Puntúo a mano un conjunto de ofertas y `evals/evaluar.py` compara mis notas con las de la IA:

- error medio en puntos,
- acierto a ±2 puntos,
- acierto en la decisión *aplicar / no aplicar*,
- **falsos negativos**: ofertas buenas que la IA descartaría. Es la métrica que más vigilo, porque son oportunidades perdidas.

Cualquier cambio de prompt o de modelo se valida con el eval antes de darlo por bueno.

## Probarlo en local

```bash
pip install -r requirements.txt
python main.py --demo        # sin claves: datos de ejemplo y evaluador simulado
python -m pytest -q tests
```

## Próximas mejoras

- Juez calibrado: comparar varios modelos (Haiku vs Sonnet) en coste y precisión con el mismo eval.
- Borrador de mensaje al reclutador para las ofertas con nota alta.
- Aprender de mis decisiones: si aplico o descarto, ajustar la rúbrica.
