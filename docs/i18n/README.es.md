# ramtaskman

[Italiano](README.it.md) · [English](../../README.md) · [中文（简体）](README.zh.md) · [한국어](README.ko.md) · [Français](README.fr.md) · [Tiếng Việt](README.vi.md) · [Español](README.es.md) · [Português](README.pt.md) · [Deutsch](README.de.md) · [日本語](README.ja.md)

### Descubre adónde va la RAM, directamente desde la terminal.

ramtaskman es un monitor experimental de memoria desarrollado y probado en Linux y Windows. Nació de la curiosidad y la investigación para entender la memoria en distintos sistemas sin recurrir a herramientas complicadas. Es un proyecto [VibeWare](https://umbertogiacobbi.biz/vibeware/manifesto).

También hay un backend experimental para macOS. No tenemos un Mac, así que no lo hemos probado ni validado. Nuestras pruebas y la CI se centran en Linux y Windows.

[Documentación](../README.md) · [Contribuir](../../CONTRIBUTING.md) · [MIT](../../LICENSE)

![ramtaskman](../images/cover.png)

*Interfaz Textual real capturada en Linux con datos sintéticos. La portada muestra un recorte del panel y la tabla; la interfaz presentada está en inglés.*

## Cómo empezar

Se necesitan Python 3.11+ y uv. Linux requiere /proc y smaps_rollup. El primer inicio necesita red para instalar las dependencias fijadas. El entorno y la caché permanecen en el proyecto.

```bash
git clone https://github.com/umbertotechnopreneur/ramtaskman.git
cd ramtaskman
./run.sh
```

En Windows, desde la carpeta del proyecto en Windows Terminal:

```powershell
.\run.cmd
```

Usa --once o --json para una muestra única o salida JSON. No compartas .venv entre sistemas: vuelve a crearlo localmente. El proyecto no está publicado en PyPI.

Teclas útiles: m cambia de modo, g alterna aplicaciones/procesos, / busca, f filtra, d muestra detalles, r abre regiones, ? explica las métricas y q sale. La guía técnica completa está actualmente en inglés.

Inicia la pantalla principal con `./run.sh --language es` (Windows: `.\run.cmd --language es`). Los textos de la aplicación están disponibles en diez idiomas: `--language` selecciona el idioma de la interfaz, el pie de página, la ayuda, la CLI y el informe de texto `--once`. También se traducen los mensajes técnicos generados por la aplicación. Los identificadores y el esquema JSON permanecen estables; los detalles del sistema operativo y los textos de las capturas guardadas conservan su idioma original. La verificación local abarca Linux con Python 3.14.4: interfaz sintética a 160×48 y 80×24, CLI, construcción de paquetes, instalación aislada y replay. Las verificaciones de Windows se ejecutan en CI; macOS queda excluido de las verificaciones del proyecto. Las traducciones todavía necesitan revisión de hablantes nativos.

## Funciones principales

1. Consulta RAM, memoria disponible, caché e historial de un vistazo; elige el modo Slim o diagnóstico completo.
2. Explora aplicaciones y procesos, ordena las métricas disponibles y comprueba la cobertura.
3. Consulta RSS y USS; en Linux también PSS, swap y SwapPSS, con detalles y datos ausentes indicados.
4. Busca por nombre, ejecutable o PID exacto y filtra por usuario, swap o datos parciales.
5. Explora regiones de memoria en Linux; la vista virtual de Windows es experimental.
6. Compara dos muestras y guarda o abre capturas locales, incluso sin conexión.

## Un vistazo al interior

![Full diagnostics](../images/full-diagnostics.png)

[Galería](../images/README.md) · [A/B](../images/regions-comparison.png) · [10 languages](../images/multilingual.png)

## Valor de la RAM y reparto mensual

```bash
./run.sh --ram-price 320 --ram-currency EUR --ram-months 36
```

Introduce el precio de toda la RAM: no se consultan precios ni se hacen solicitudes de red. La capacidad predeterminada es la visible para el sistema; usa `--ram-capacity-gib 32` para un kit nominal de 32 GiB. Valor = precio × bytes atribuibles / capacidad. `--ram-months` divide este valor del hardware entre los meses elegidos: no es una factura, consumo energético, promedio mensual ni ahorro garantizado. Linux usa PSS; Windows usa USS, solo memoria privada residente. No se sustituye por RSS. Los grupos incompletos quedan en n/a (`null` en JSON). No sumes las aplicaciones con sus procesos ni con la memoria del sistema. Las muestras son secuenciales, no atómicas. JSON añade `ram_valuation` solo cuando se solicita. F1 abre la información y los créditos; Esc vuelve al monitor.

## Experimental: interpreta los datos con cuidado

Las lecturas son secuenciales, los permisos pueden limitar la visibilidad y la agrupación de aplicaciones es heurística. Los datos ausentes son n/a, no cero. RSS puede contar páginas compartidas varias veces; la PSS de procesos no es toda la RAM. La caché se solapa con la memoria disponible. La swap por proceso no se deduce del commit.

Linux ofrece PSS y swap por proceso cuando son legibles. Aquí no se exponen en Windows ni en el backend experimental de macOS. Las regiones Linux usan smaps; Windows muestra intervalos virtuales experimentales y macOS aún no tiene mapa. Las verificaciones del proyecto abarcan Linux local y Windows en CI nativa; macOS permanece fuera de ese alcance.

La comprobación manual en un PC Windows personal sigue pendiente.

## Usa, modifica y comparte

Puedes usar, copiar, modificar y redistribuir ramtaskman, incluso comercialmente, según la [licencia MIT](../../LICENSE). Conserva los avisos de copyright y permiso en las copias o partes sustanciales. El software se proporciona sin garantías. Se agradecen contribuciones y correcciones de traducción; las dependencias conservan sus propias licencias.

[Contribuir](../../CONTRIBUTING.md) · [Atribuciones de terceros](../../THIRD_PARTY_NOTICES.md)

## Inspiración y agradecimientos

Gracias a Scott Hanselman y a GPU Taskman por la inspiración. ramtaskman reutiliza partes del proyecto y adapta su interfaz de terminal a la RAM; es independiente y no es una versión oficial. [Scott Hanselman](https://github.com/shanselman) · [GPU Taskman](https://github.com/shanselman/gputaskman) · [Provenance](../upstream.md)

Traducciones realizadas con ayuda de IA. Se agradecen las correcciones de traductores y hablantes nativos.

[Guía técnica completa (inglés)](../guida.md) · [Licencia MIT; se conserva el copyright original.](../../LICENSE)
