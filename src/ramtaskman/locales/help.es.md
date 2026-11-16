# ramtaskman · cómo interpretar los números

La estructura visual de gputaskman, adaptada a la memoria de Linux, Windows y macOS.

| Campo | Significado |
|---|---|
| PSS | RAM privada más una cuota proporcional de las páginas compartidas |
| USS | Private_Clean + Private_Dirty: páginas residentes privadas |
| RSS | Páginas residentes, incluidas las compartidas; sumarlas puede contarlas varias veces |
| Swap | Swap de smaps_rollup, excluida la swap shmem; puede contar páginas compartidas varias veces |
| SwapPSS | Cuota proporcional de la swap compartida contabilizada por smaps_rollup |
| RAM used | MemTotal − MemAvailable; no coincide con la suma de procesos |
| Cache | Cached + Buffers + SReclaimable − Shmem; se solapa con la memoria disponible |
| PSI some | Porcentaje de tiempo con al menos una tarea esperando memoria, media de 10 s |

**Barra RAM:** ocupa todo el ancho y distribuye contadores Linux en memoria anónima, caché de archivos (Cached − Shmem), compartida/tmpfs, búferes, slab recuperable/no recuperable, otros (residuo calculado) y libre. Son categorías contables: el orden no representa direcciones físicas. La memoria disponible es un indicador separado que incluye caché recuperable, por lo que no es otro segmento. Los detalles clean/dirty y PSS del proceso están en **d**, porque se solapan con los contadores globales. Si faltan campos o la muestra es incoherente, la barra muestra en uso/disponible y explica por qué falta el desglose. La leyenda incluye categorías menores de un carácter.

**Barra USS de apps:** las 10 primeras apps con USS completa y las demás apps completas. La escala es la suma USS de las apps completas de la muestra, no la RAM total. Los números y colores remiten a la leyenda. Se excluyen grupos parciales y se indica la cobertura. La agrupación sigue la tabla; los segmentos no son direcciones físicas.

**Windows/macOS:** USS y RSS provienen de psutil; PSS, Swap y SwapPSS por proceso no se exponen y quedan n/a. En Windows el commit privado/pagefile NO es swap en disco. En macOS RAM used es total − available de psutil, no la presión de memoria de Activity Monitor.

**Aplicación:** en Linux un cgroup systemd explícito identifica la instancia de la app, incluso con auxiliares de distintos ejecutables. Usuarios e instancias diferentes permanecen separados. Sin esa identidad, también en Windows/macOS, se agrupa por usuario + ejecutable o, si no se puede leer la ruta, por usuario + nombre como heurística. El inspector indica el método.

**Búsqueda y filtros:** **/** busca nombre, ejecutable o PID exacto; **f** elige usuario y estado de memoria (**con swap** o **datos parciales**). Los filtros se combinan. Una app coincide si uno de sus procesos cumple la búsqueda o el estado, pero su total conserva todos los miembros. Los filtros permanecen en la vista de procesos. Actúan antes del límite Top 30; gráficos y panel describen todo el sistema. **Intro** desde la búsqueda vuelve a la tabla. **Esc** en los controles o **Reset** limpia filtros; **Esc** en la tabla de procesos vuelve a apps conservándolos. Datos parciales solo considera contadores compatibles; swap desconocida no significa swap usada.

**d** abre el detalle RAM del grupo o proceso: PSS anónima/archivo/shmem, privada y compartida clean/dirty, páginas anónimas, LazyFree y THP. Son campos Linux: en otros sistemas n/a. Las filas son vistas solapadas y no deben sumarse todas. La muestra queda fijada al abrir: cierra y vuelve a abrir para actualizar. **Esc** o **d** cierra el detalle.

**r** o **Intro** sobre un proceso abre el mapa de regiones Linux. En una app, **r** muestra primero sus PID: cada proceso tiene su propio espacio virtual. Las barras de **d** desglosan PSS y RSS por separado; la swap queda fuera de la RAM residente.

En el mapa: **v** alterna RSS/direcciones virtuales, **s** ordena, **/** busca archivo o dirección 0x…, **f** filtra tipo/estado, **z** o **Intro** amplía el entorno de la región seleccionada, **r** actualiza y **Esc** limpia filtros/sale del zoom/vuelve. El mapa sigue direcciones virtuales, no marcos físicos. Los huecos se excluyen de la escala virtual y se marcan con │; las regiones menores de un carácter siguen en la tabla. El tipo indica el origen, no el contenido: un archivo puede incluir páginas CoW privadas; solo se etiquetan heap/pila cuando se reconocen. Las muestras se leen bajo demanda e indican antigüedad, duración y límites. Windows: solo intervalos virtuales experimentales; macOS: mapa de regiones no disponible.

En regiones, **b** fija A, **r** recoge B y **c** abre la comparación. Allí **v** cambia la métrica, **s** el orden, **f** filtra el estado y **Ctrl+B** elimina A. **Ctrl+S** guarda muestras; **Ctrl+O** abre un archivo sin conexión. Los archivos contienen metadatos y pueden incluir rutas personales. Datos ausentes y regiones reorganizadas quedan n/a; un mismo intervalo no demuestra la misma asignación ni una fuga de memoria.

**n/a no es cero.** El total de una app es n/a si falta un solo valor. Lecturas muestra cobertura PSS/USS. Los totales visibles son sumas parciales de lecturas disponibles y no toda la RAM del sistema. Las lecturas no son atómicas: los procesos pueden cambiar durante el muestreo. Otros usuarios, entornos aislados y permisos procfs pueden impedirlas. No hay elevación automática. HugeTLB no está incluido en los contadores RSS/PSS/USS ordinarios mostrados.

El programa lee metadatos, no /proc/PID/mem, cmdline, environment ni contenido de las apps.

**g** apps/procesos · **Intro** procesos de la app seleccionada · **Esc** volver a apps

**s** orden · **c** gráfico · **a** todos/primeros 30 · **m** compacto/completo

**/** búsqueda · **f** filtros · **d** detalles · **r** regiones · **p** pausa · **?** ayuda · **q** salir

Gráficos: últimas 60 muestras, porcentajes en escala 0–100. El espacio vacío indica dato ausente. El intervalo es una pausa después de la lectura; el tiempo real incluye el escaneo.
