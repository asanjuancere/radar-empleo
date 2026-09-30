# Radar de empleo con IA

[![Radar de empleo](https://github.com/asanjuancere/radar-empleo/actions/workflows/radar-empleo.yml/badge.svg)](https://github.com/asanjuancere/radar-empleo/actions/workflows/radar-empleo.yml)

Cada mañana revisa las ofertas nuevas, las puntúa con IA según **un criterio propio** y envía por email solo las que merecen la pena, con el porqué y un argumento para la candidatura.

Es una herramienta de seguimiento de ofertas. El criterio (perfil y rúbrica) es privado y se carga desde secretos de GitHub; este repositorio incluye **ejemplos inventados** para que cualquiera pueda probarlo. Además de puntuar, **apunta qué herramientas y habilidades piden** las ofertas y con las semanas publica un resumen del mercado: [`datos/MERCADO.md`](datos/MERCADO.md).

**Documentación completa:** [Cómo está hecho, paso a paso](docs/ARQUITECTURA.md) (fuentes, reglas, puntuación con IA, evals, pruebas, automatización, privacidad, costes y límites).

## Cómo comprobar que funciona

- **Insignia de arriba:** verde = la última ejecución automática pasó las pruebas y terminó bien.
- **[Pestaña Actions](https://github.com/asanjuancere/radar-empleo/actions):** historial de ejecuciones, una por día laborable, con el registro completo.
- **[`datos/metricas.csv`](datos/):** una fila por ejecución (ofertas analizadas, cuántas buenas, coste). Se actualiza solo.
- **[`datos/MERCADO.md`](datos/):** ranking de habilidades que piden las ofertas, generado a partir de datos reales.
- **Modo demo:** mientras no haya claves conectadas, el flujo se ejecuta con las ofertas inventadas y un evaluador simulado. Sirve para demostrar que la tubería funciona de principio a fin sin coste.

## Estado del proyecto

- [x] Estructura, reglas de descarte y puntuación con IA (tool use, salida estructurada)
- [x] Ejecución automática en GitHub Actions y pruebas automáticas
- [x] Evals: script que compara la nota de la IA con la nota manual de referencia
- [x] Extracción de habilidades e informe de mercado
- [x] Fuente real conectada: alertas de LinkedIn por email (probado de principio a fin en la copia privada)
- [x] Eval con ofertas puntuadas a mano por el autor (resultados con datos reales, privados)
- [x] Ampliaciones construidas en la copia privada: ver [«Ampliaciones»](#ampliaciones-copia-privada) (unas verificadas, otras pendientes de verificar)
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
| `evaluar_oferta.py` | El «botón»: evalúa una oferta pegada a mano y la envía por email |
| `radar/empresa.py` | Estudio breve de la empresa con búsqueda web |
| `radar/linkedin_email.py` | Lee las alertas de LinkedIn del buzón y extrae título, empresa y ubicación |
| `radar/adzuna.py` | Consulta la API oficial de Adzuna (incluye extracto de la descripción) |
| `radar/puntuar.py` | Filtro por reglas + evaluación con Claude y salida estructurada |
| `radar/informe.py` | Email diario y métricas agregadas |
| `radar/mercado.py` | Registro anónimo de habilidades demandadas e informe mensual |
| `rubrica.ejemplo.md` · `perfil.ejemplo.md` | Ejemplos inventados; el criterio real es privado (secretos de GitHub) |
| `evals/` | Conjunto etiquetado y script que mide si la IA acierta |
| `tests/` | Pruebas que se ejecutan antes de cada ejecución |
| `docs/` | Documentación técnica completa |
| `.github/workflows/` | La ejecución diaria automática y el botón |

## Ampliaciones (copia privada)

El autor usa una copia privada con datos reales. Estas son las ampliaciones que ha construido sobre esta base y su estado, dicho con honestidad:

| Ampliación | Qué hace | Estado |
|---|---|---|
| Núcleo con alertas de LinkedIn | Lee las alertas, puntúa con IA contra el CV y envía el email diario | **Verificado** en ejecución real |
| Calibración con notas del autor | Compara las notas de la IA con las del autor (error medio, acierto ±2, falsos negativos) | **Verificado** |
| Aviso de fallos | Si una ejecución falla, llega un email con el enlace al registro | **Verificado** |
| Webs de empresas | Cada día revisa un lote de las páginas de empleo de una lista de empresas objetivo y añade las vacantes que encajan con el perfil | Descubrimiento **verificado**; evaluación de esas vacantes pendiente de verificar |
| Segunda pasada | Si una oferta prometedora solo trae título, busca su descripción en la web oficial de la empresa y la puntúa de nuevo | Construido, **pendiente de verificar** |
| Aprendizaje con ejemplos | Las notas que pone el autor se incluyen como ejemplos en cada evaluación | Construido, **pendiente de verificar** |
| Candidatura a medida | Borrador de mensaje, logros del CV a destacar y a quién escribir (solo hechos del CV real; el autor revisa y envía) | Construido, **pendiente de verificar** |
| Seguimiento y entrevista | Registro de candidaturas, recordatorio a los 7 días y guion de entrevista a demanda | Construido, **pendiente de verificar** |
| Resumen semanal | Ofertas de la semana y habilidades pedidas que faltan en el CV | Construido, **pendiente de verificar** |

Cómo se cuida el coste y la fiabilidad: una lista larga de empresas se revisa **por lotes rotativos** (unas pocas al día), la ejecución se **detiene y avisa** si la cuenta de la API se queda sin saldo, y las ofertas que no llegaron a evaluarse **no se marcan como vistas**, así que se reintentan.

## Cómo se configura (referencia)

Pasos que sigue el autor en su copia privada, descritos para que se entienda el diseño:

1. Escribir el perfil y tu rúbrica (parte de `perfil.ejemplo.md` y `rubrica.ejemplo.md`).
2. En *Settings → Secrets and variables → Actions* añadir los secretos: `ANTHROPIC_API_KEY`, `PERFIL`, `RUBRICA` y, para las fuentes, `GMAIL_USUARIO`, `GMAIL_CLAVE_APP` (contraseña de aplicación de Google), `ADZUNA_APP_ID` y `ADZUNA_APP_KEY`. Opcionales: `DESCARTE_EXTRA` (una expresión regular de puestos a descartar sin gastar IA).
3. Crear alertas de empleo en LinkedIn con tu correo.
4. En la pestaña *Actions*, lanzar el flujo a mano con *Run workflow*. Desde entonces se ejecuta solo cada día laborable.

Sin la clave de Anthropic el flujo funciona en modo demo. Coste con clave: unos pocos euros al mes.

## Licencia

Código publicado para consulta y evaluación. Todos los derechos reservados: para cualquier otro uso hace falta permiso escrito del autor. Ver [`LICENSE`](LICENSE).

## Decisiones de diseño

- **LinkedIn por email, no scraping.** LinkedIn prohíbe el acceso automatizado y puede bloquear la cuenta. Las alertas por email son el canal oficial; el programa solo lee el propio correo, en modo solo lectura.
- **Reglas antes que IA.** Lo obvio se descarta sin llamar al modelo. Más barato y más predecible.
- **Tool use con esquema JSON.** Claude devuelve siempre los mismos campos (nota, veredicto, encaje, carencias, probabilidad de entrevista), así las notas se pueden ordenar, medir y comparar.
- **Prompt caching.** La rúbrica y el perfil se repiten en cada llamada; se cachean y esa parte cuesta ~10 % a partir de la segunda oferta.
- **Coherencia medida, no supuesta.** Los modelos actuales no permiten fijar la aleatoriedad, así que la coherencia de las notas se apoya en un esquema fijo y una rúbrica estable, y se comprueba con los evals.
- **Honestidad sobre la información.** Si una oferta solo trae título, la IA lo marca (`info_suficiente=false`) y la nota se presenta como orientativa.
- **Privacidad.** El repo es público: no se publican ofertas, empresas ni notas, solo métricas agregadas. Los ids ya vistos se guardan como huella (hash). Las ofertas de ejemplo de los evals son inventadas.

## Inteligencia de mercado

Cada oferta con descripción completa aporta sus habilidades (n8n, Power Automate, agentes de IA...). El programa las cuenta y regenera [`datos/MERCADO.md`](datos/MERCADO.md) con el ranking de los últimos 30 días.

- Las alertas de LinkedIn solo traen el título, así que **no cuentan**: sus habilidades serían suposiciones.
- Solo se guarda fecha, huella de la oferta, habilidad y nivel. Ni empresas, ni títulos, ni enlaces.
- Con pocas ofertas el informe avisa de que los porcentajes son orientativos.

## Evals: ¿puntúa como su dueño?

Se puntúa a mano un conjunto de ofertas y `evals/evaluar.py` compara esas notas con las de la IA:

- error medio en puntos,
- acierto a ±2 puntos,
- acierto en la decisión *aplicar / no aplicar*,
- **falsos negativos**: ofertas buenas que la IA descartaría. Es la métrica más importante, porque son oportunidades perdidas.

Cualquier cambio de prompt o de modelo se valida con el eval antes de darlo por bueno.

## Probarlo en local

```bash
pip install -r requirements.txt
python main.py --demo        # sin claves: datos de ejemplo y evaluador simulado
python -m pytest -q tests
```

## Próximas mejoras

- Juez calibrado: comparar varios modelos (Haiku vs Sonnet) en coste y precisión con el mismo eval.
- Verificar de extremo a extremo las ampliaciones pendientes y publicar su código en este repositorio.
- Publicar un informe de precisión con datos inventados, para que se pueda reproducir sin datos privados.
