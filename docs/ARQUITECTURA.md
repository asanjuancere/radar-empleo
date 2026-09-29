# Cómo está hecho el radar, paso a paso

Este documento explica todo el proyecto: qué hace, cómo está construido, por qué se tomó cada decisión y dónde están sus límites. Está pensado para que cualquier persona, sepa programar o no, pueda entenderlo y reproducirlo.

## 1. Qué problema resuelve

Buscar empleo obliga a revisar cada día decenas de ofertas en varias webs. La mayoría no encajan y las buenas se pierden entre el ruido. El radar hace ese primer filtro de forma automática:

1. Recoge las ofertas nuevas.
2. Las puntúa de 0 a 10 con un criterio definido por la persona.
3. Envía por email solo las que merecen la pena, con el motivo y una idea para el mensaje al reclutador.
4. Mide si su puntuación coincide con la de la persona (evals) y guarda estadísticas anónimas del mercado.

La IA propone y la persona decide. Nada se envía ni se aplica de forma automática.

## 2. Visión general

```
 Alertas de LinkedIn ─┐
   (por email, IMAP)  ├─► Quitar ya vistas ─► Filtro por reglas ─► IA + rúbrica ─► Estudio de empresa ─► Email
 API de Adzuna ───────┘                        (sin coste)          (puntúa)         (solo las buenas)      + métricas
                                                                        │
                                                                        └─► Habilidades pedidas ─► Informe de mercado

 Todo se ejecuta solo, de lunes a viernes, en GitHub Actions.
 Aparte hay un «botón» para evaluar una oferta concreta a demanda.
```

## 3. Estructura de archivos

| Ruta | Función |
|---|---|
| `main.py` | Director de orquesta: ejecuta los pasos en orden |
| `radar/modelo.py` | Define qué es una «oferta» (los mismos campos vengan de donde vengan) |
| `radar/linkedin_email.py` | Fuente 1: lee las alertas de LinkedIn del buzón de correo |
| `radar/adzuna.py` | Fuente 2: consulta la API oficial de Adzuna |
| `radar/puntuar.py` | Filtro por reglas y puntuación con IA |
| `radar/empresa.py` | Estudio breve de la empresa con búsqueda web |
| `radar/mercado.py` | Cuenta qué habilidades piden las ofertas |
| `radar/informe.py` | Diseño del email y guardado de métricas |
| `evaluar_oferta.py` | El «botón»: evalúa una oferta pegada a mano |
| `evals/` | Conjunto de ofertas de ejemplo y script que mide el acierto de la IA |
| `tests/` | Pruebas automáticas |
| `.github/workflows/` | La programación diaria y el botón |
| `perfil.ejemplo.md`, `rubrica.ejemplo.md` | Ejemplos ficticios del formato del criterio |
| `datos/` | Métricas y estadísticas anónimas que genera el radar |

## 4. El modelo de datos

Cada fuente entrega las ofertas con formas distintas. Para que el resto del programa no tenga que saber de dónde vienen, todas se convierten a una misma estructura, `Oferta` (en `radar/modelo.py`): identificador, fuente, título, empresa, ubicación, enlace, descripción, fecha, salario y, una vez puntuada, su evaluación. Añadir una fuente nueva solo exige escribir un traductor a esa estructura.

## 5. Las fuentes

**Alertas de LinkedIn por email.** LinkedIn prohíbe en sus condiciones el acceso automatizado a la web y puede cerrar la cuenta a quien lo hace. Las alertas por email son el canal que la propia plataforma ofrece: LinkedIn manda las ofertas a un buzón y el programa solo lee ese buzón, en modo solo lectura (no marca nada como leído). Para leerlo usa IMAP con una «contraseña de aplicación» de Google, distinta de la contraseña normal y revocable en cualquier momento. El correo se analiza con un lector de HTML que localiza los enlaces a ofertas y toma el texto que los rodea (título, empresa y ubicación). Limitación: las alertas solo traen el título, sin descripción, así que la puntuación de esas ofertas es orientativa y el programa lo indica.

**Adzuna.** Es un buscador de empleo con API oficial y plan gratuito. Devuelve un extracto de la descripción, así que permite puntuar con más información. Se consulta con varias búsquedas configurables y una antigüedad máxima de dos días.

## 6. Quitar las ofertas ya vistas

Cada oferta tiene un identificador. El programa guarda una huella (un hash SHA-256 recortado) de cada identificador ya procesado y descarta las que ya conoce. Se guarda la huella y no el identificador para que el repositorio no revele qué ofertas concretas se han consultado.

## 7. Filtro por reglas

Antes de gastar dinero en IA, unas reglas baratas descartan lo evidente. Por ejemplo, los puestos con títulos de nivel senior o directivo reciben una nota baja sin llamar al modelo. Cada persona puede añadir sus propias reglas con la variable `DESCARTE_EXTRA` (una expresión regular), que se guarda como secreto y no aparece en el código. Es más barato, más rápido y más predecible que preguntárselo a la IA cada vez.

## 8. Puntuación con IA

El archivo `radar/puntuar.py` envía cada oferta a Claude junto con dos textos que configura cada persona: su **rúbrica** (qué es una oferta excelente y una mala) y su **perfil** (su experiencia). Decisiones de diseño:

- **Salida estructurada (tool use).** En lugar de pedir texto libre, se obliga a Claude a responder con una herramienta que tiene un esquema fijo: nota de 0 a 10, veredicto, motivo, qué encaja, qué falta, probabilidad de entrevista, idea para el mensaje, si la información era suficiente, habilidades pedidas y nivel. Así los resultados siempre tienen los mismos campos y se pueden ordenar, contar y comparar.
- **Temperatura 0.** La misma oferta recibe siempre la misma nota. Es imprescindible para poder medir cambios.
- **Prompt caching.** La rúbrica y el perfil son idénticos en todas las llamadas del día; se marcan como reutilizables y desde la segunda llamada esa parte cuesta aproximadamente una décima.
- **Honestidad sobre la información.** Si la oferta solo trae título, el modelo debe marcar `info_suficiente=false` y no inventar habilidades.
- **Aislamiento del criterio.** Rúbrica y perfil se leen de secretos de GitHub (o de un archivo local ignorado por git). El repositorio público solo contiene ejemplos ficticios.

## 9. Estudio de la empresa

Para las ofertas con nota alta, `radar/empresa.py` pide a Claude que busque información pública de la empresa y la resuma en cinco líneas: actividad, tamaño, noticias recientes y opiniones de empleados que aparezcan en fuentes públicas fiables, citando la fuente. No accede a Glassdoor ni a LinkedIn porque sus condiciones lo prohíben; en su lugar, cada tarjeta del email incluye enlaces para consultarlos manualmente. Si la búsqueda falla, se omite y el radar sigue funcionando.

## 10. Inteligencia de mercado

Cada oferta con descripción completa aporta las habilidades que pide. `radar/mercado.py` las normaliza (por ejemplo, «MS Power Automate» y «Power Automate» cuentan igual), cuenta cada habilidad una sola vez por oferta y genera un ranking de los últimos 30 días en `datos/MERCADO.md`. Solo se guardan la fecha, la huella de la oferta, la habilidad y el nivel: ninguna empresa, título ni enlace. Con menos de 20 ofertas el informe avisa de que los porcentajes son orientativos.

## 11. El email

El diseño (`radar/informe.py`) usa la misma paleta y estilo de la web del autor. Los emails no cargan tipografías web, así que se usan Georgia para títulos y Arial para texto. Cada oferta es una tarjeta con nota, veredicto, motivo, qué encaja, qué requiere atención, una idea para el mensaje, el estudio de la empresa y enlaces. Todo el texto variable se escapa (`html.escape`) para que ningún contenido de una oferta pueda alterar el HTML del correo.

## 12. El «botón» para evaluar una oferta

El flujo «Evaluar una oferta» de GitHub Actions muestra un formulario con tres casillas (título, empresa, texto). Al ejecutarlo, `evaluar_oferta.py` puntúa esa oferta con el mismo motor, añade el estudio de empresa y envía la tarjeta por email. **Debe usarse en una copia privada del repositorio**: en un repositorio público, lo escrito en las casillas es visible para cualquiera.

## 13. Evals: medir si la IA acierta

Un programa con IA que no se mide es una opinión. El script `evals/evaluar.py` compara las notas que da la IA con las que da la persona sobre un conjunto de ofertas etiquetadas a mano, y calcula:

- **Error medio absoluto:** cuántos puntos se desvía de media.
- **Acierto a ±2 puntos.**
- **Acierto de decisión:** si coinciden en «aplicar / no aplicar» (umbral de 7).
- **Falsos negativos:** ofertas buenas que la IA descartaría. Es la métrica más importante porque son oportunidades perdidas.
- **Falsos positivos:** ofertas malas que la IA recomendaría.

Cualquier cambio de modelo, de rúbrica o de instrucciones se valida con este examen antes de darlo por bueno.

## 14. Pruebas automáticas

La carpeta `tests/` comprueba, sin llamar a ninguna IA: la lectura de emails de LinkedIn, las reglas de descarte, el cálculo de las métricas, la normalización y el conteo de habilidades, que los archivos públicos no contengan datos de ofertas, que el email escape el HTML y que el estudio de empresa nunca rompa el programa. Se ejecutan antes de cada ejecución diaria: si fallan, el radar no se ejecuta.

## 15. Automatización

Un flujo de GitHub Actions (`.github/workflows/radar-empleo.yml`) ejecuta el radar de lunes a viernes a las 06:15 UTC (08:15 en horario de verano español) en servidores de GitHub, sin ordenador propio. Pasos: descargar el código, instalar dependencias, ejecutar pruebas, ejecutar el radar y guardar las métricas en `datos/`. También se puede lanzar a mano con «Run workflow». Sin clave de Claude configurada funciona en **modo demo**: usa ofertas ficticias y un evaluador simulado, lo que permite comprobar toda la tubería sin coste.

## 16. Privacidad y seguridad

- Las claves y el criterio personal viven en **secretos de GitHub**, que nadie puede leer una vez guardados.
- Los registros de ejecución pueden ser públicos, por eso en ejecuciones reales el programa **no imprime** títulos ni empresas.
- Solo se publican métricas agregadas y anónimas.
- La contraseña de aplicación de Gmail solo da acceso a ese uso y se puede revocar.
- El uso real se recomienda en un repositorio **privado**; el público sirve de escaparate con datos ficticios.

## 17. Configuración

| Variable (secreto) | Para qué sirve |
|---|---|
| `ANTHROPIC_API_KEY` | Clave de la API de Claude |
| `PERFIL`, `RUBRICA` | Criterio de la persona (texto completo) |
| `DESCARTE_EXTRA` | Expresión regular con puestos a descartar sin usar IA (opcional) |
| `GMAIL_USUARIO`, `GMAIL_CLAVE_APP` | Buzón donde llegan las alertas y donde se recibe el resumen |
| `ADZUNA_APP_ID`, `ADZUNA_APP_KEY` | Acceso a la API de Adzuna |
| `CONSULTAS_ADZUNA` | Búsquedas separadas por barra vertical (opcional) |

## 18. Coste

Con el modelo actual y unas decenas de ofertas al día, el gasto de IA es de unos pocos euros al mes. El filtro por reglas, el caché del criterio y el estudio de empresa solo para ofertas buenas mantienen el coste bajo. Cada ejecución registra su coste estimado en `datos/metricas.csv`. GitHub Actions es gratuito para este uso.

## 19. Limitaciones conocidas

- Las alertas de LinkedIn no incluyen descripción: esas puntuaciones son orientativas.
- El estudio de empresa depende de información pública que puede ser escasa o desactualizada.
- La IA puede equivocarse: por eso existen los evals y por eso la decisión final es siempre de la persona.
- El modo demo no evalúa con IA; solo demuestra que el proceso funciona de principio a fin.

## 20. Cómo ampliarlo

Para añadir una fuente (por ejemplo, otra web de empleo con API): crear un archivo en `radar/` que devuelva una lista de `Oferta`, llamarlo desde `recoger()` en `main.py` y añadir una prueba con datos ficticios. El resto del sistema (reglas, puntuación, email, métricas) funciona sin cambios.
