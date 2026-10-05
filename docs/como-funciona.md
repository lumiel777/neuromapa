# Cómo funciona Neuromapa por dentro

Todo es Python estándar (3.10 o más nuevo) y una sola página HTML. No hay base de datos ni dependencias que instalar:
el mapa usa d3 y marked, que vienen en `vendor/` (con sus licencias en `vendor/LICENCIAS.md`) y entran adentro de la
página al armarla, con la huella verificada. Si faltara `vendor/`, la página las pide al CDN con la misma huella;
`python3 herramientas/bajar_librerias.py` (en Windows, `py -3 herramientas/bajar_librerias.py`) las vuelve a bajar.

## Las piezas

| Pieza | Qué hace |
|---|---|
| `cerebro.py` | Junta las notas de las fuentes, las conecta y arma la página (`cerebro.html`) metiendo los datos en `plantilla.html`. También es la consola: `--sobre`, `--buscar`, `--salud`, `--parecidas`, `--entidad`, `--mapa`, `--choques`, `--gasto`, `--lecciones`, `--aprendido` (con un archivo, con qué se usa ese), `--olvidar`, `--proponer-hechos`, `--dormir`, `--propuestas`, `--aplicar`, `--descartar`, `--descartar-aviso`, `--descartados`, `--recuperar-aviso`, `--fichas`, `--historial`, `--charlas`. |
| `plantilla.html` | La página: el cerebro 3D (WebGL, con dibujo 2D si no hay), la lista, el panel de salud, el panel «Ahora», el río del tiempo (los últimos 10 minutos, un carril por chat con hasta 5, armado con los mismos eventos que ya llegan en vivo; se esconde si no pasó nada, en pantallas chicas y en el modo cine) y la ayuda. |
| `servidor.py` | El servidor local (solo `127.0.0.1`, con clave): sirve la página, rearma los datos cuando cambia una nota y manda en vivo lo que anota el registro. Mientras está prendido, rearma lo aprendido cada minuto y se lo manda a la página (evento `aprendido`). Anota su puerto en `en-vivo/servidor.json` y lo borra al apagarse. El hook y un segundo arranque no le mandan la clave: primero le piden que demuestre que la sabe (`/hola`, con `firmas.py`) y después el hook manda el pedido firmado, así otro programa que ocupe ese puerto no recibe ni el pedido ni la clave. Si al arrancar ya hay uno prendido sobre los mismos datos, el nuevo le pide que se apague (`/apagar`, solo con firma) y ocupa su lugar: abrirlo de nuevo reinicia (desde el plugin, en cambio, se reusa el que está). Un candado (`en-vivo/servidor.lock`) evita que dos arranques casi a la vez dejen dos prendidos. El navegador entra con un número de un solo uso que vence en un minuto (`?entrada=`; el que abre desde otra ventana se lo pide al mapa con un pedido firmado, `/entrada`), y el servidor lo cambia por una galleta propia que no es la clave: la clave no queda en el historial del navegador. A mano se puede entrar con `?clave=`. Si se actualiza el programa, lo avisa en su ventana. La página corre solo sus propios scripts: cada vez que la sirve les pone un nonce nuevo y la política de seguridad no deja correr ningún otro (ni uno metido en el texto de una nota). |
| `configuracion.py`, `donde.py` | Leen `config.json` y deciden dónde viven los datos (ver abajo). |
| `buscador.py` | El buscador de `--sobre` y `--buscar`: BM25 sobre renglones y secciones, con raíces de palabras en español y en inglés. Una sección de más de 2.000 letras se parte en pasajes (por párrafos o ítems de lista, nunca adentro de un bloque de código), así un dato escondido en una nota larga sin títulos puntúa por su pasaje y no se ahoga en el resto; los pasajes de una misma sección no se suman entre sí como si fueran secciones distintas, para que una nota larga no le gane siempre a una corta y específica. Las notas de archivo (con «(archivo)» en su título del índice, como las crónicas viejas) pesan un poco menos (×0,85: ahí terminan los arreglos viejos cuando un registro se parte, y tienen que poder salir), los changelog vivos pesan como cualquier nota, y a «leer primero» entra como mucho una nota de archivo, solo si está entre las dos mejores o si sobra lugar; nunca entran como enlazadas ni como la que se suele leer junto. Una nota cuyo tramo a leer tiene un dato viejo comprobado por el médico (una ruta que ya no existe, una cifra de `hechos.json` que cambió o un commit que no existe) pasa detrás de las limpias en «leer primero», sin desaparecer y con su ⚠: actuar sobre un dato viejo es peor que no tenerlo. «Puede que ya esté resuelto» (sin comprobar) y una línea de código corrida (el dato sigue valiendo) no la bajan. |
| `medico.py` | El médico de `--salud`: rutas que no existen, anclas `archivo:línea` corridas (compara contra el código; las que no tienen un nombre cerca para buscar, con `git diff` desde la fecha del renglón, y solo si la cuenta da lo mismo mirando también el último commit de ese archivo en las 24 h siguientes, por si la nota se escribió con cambios sin commitear), commits que no existen, renglones que dicen que algo no anda cuando un commit posterior del mismo proyecto nombra lo mismo (fecha el renglón con `git blame`, o por la fecha del archivo en las memorias), cifras de `hechos.json`, memorias sin índice, repetidas o que copian el `CLAUDE.md`, y si `MEMORY.md` pasa lo que Claude lee al arrancar (las primeras 200 líneas o 25 KB, lo que llegue antes; dice desde qué línea no lo ve). Un «para revisar» que ya se comprobó se calla con `--descartar-aviso RUTA:LÍNEA` (`--motivo` opcional): `descartados.json` guarda la regla, la ruta y una huella del renglón (nunca su texto), así deja de salir en `--salud`, la página y los ⚠ de la pista, y vuelve solo si ese renglón cambia; `--descartados` los lista y `--recuperar-aviso` deshace. Los avisos y los graves no se descartan: son problemas concretos. |
| `parecidas.py`, `entidades.py` | Notas parecidas (para no crear duplicados) y qué notas nombran un archivo, un commit o una tabla. |
| `mapa.py` | `--mapa`: las funciones de un archivo de código con su línea de inicio y fin. |
| `choques.py` | `--choques`: archivos que editaron dos chats o agentes con menos de 15 minutos entre uno y otro. |
| `gasto.py` | `--gasto` y el freno: los tokens de las charlas que guarda Claude Code, por chat y por agente. |
| `lecciones.py` | `--lecciones`: errores de las herramientas de archivos que se repiten, con la regla que los evitaría. |
| `pruebas.py` | La memoria con pruebas: `--proponer-hechos` y `--aprobar-hecho` (`hechos.json`). |
| `problemas.py` | La lista de problemas nuevos (`problemas.json`) y el aviso que manda `hook_servir.py`. |
| `dormir.py` | Una vez por día, con el primer pedido, `hook_servir.py` larga de fondo una pasada (`--dormir`) que repasa las notas con el médico y propone arreglos, sin tocarlas: anclas `archivo:línea` corridas cuando el médico sabe la línea nueva, y cifras de `hechos.json` que cambiaron (cambian solo ese pedazo del renglón); los problemas que quizás ya se resolvieron y las anclas sin un número seguro quedan «para mirar». Las guarda en `en-vivo/dormir.json` y avisa una sola vez por pasada. `--propuestas` las lista con el antes y el después; `--aplicar 1,3` (o `todas`) cambia esas notas solo si el renglón sigue igual que en la pasada, respetando la codificación y los fines de renglón del archivo; `--descartar` hace que no se vuelvan a proponer. `--salud` cuenta las pendientes. |
| `dormir_claude.py` | Con `dormir_con_claude` en la configuración (apagado de fábrica), la misma pasada le pregunta a Claude, con el Claude Code de la computadora (`claude -p`, sin tus ajustes ni hooks, en una carpeta vacía y con tope de gasto por pregunta y por día): (1) cada problema que quizás ya se resolvió, con el commit y sus cambios (sin los archivos sensibles); Claude puede leer el código de hoy de ese repositorio con Read, Grep y Glob (no comandos, y las reglas le niegan los archivos sensibles en cualquier carpeta) y tiene que citar el renglón de código que lo prueba. Si la cita no está en ese archivo, o es una nota o un `.md`, no se cree. «Resuelto» se vuelve un arreglo para aplicar (una marca «✅ Resuelto el día (`commit`)» al final del párrafo); «sigue» o «no se sabe» quedan para mirar, con lo que vio. (2) Pares de renglones de notas vigentes distintas que nombran dos o más cosas raras iguales (archivos, números, nombres), de a 10 por pregunta, primero los que tocan una memoria; no entran las notas históricas ni las de una fuente con `anclas_resumidas` (informes que anotan cómo estaba todo el día que se escribieron). Los que se contradicen quedan para mirar en la que parece vieja, con la otra al lado, si los renglones que cita están en lo que se le mostró y si su explicación no dice que no chocan. Lo revisado queda en `en-vivo/dormir-claude.json` y no se vuelve a preguntar mientras esos renglones no cambien; lo que no entra en el tope del día sigue en la pasada siguiente. El aviso espera a que termine (hasta 40 minutos). |
| `fichas.py` | `--fichas USD` le pide a Claude (Sonnet, con el mismo `claude -p` de Dormir, sin herramientas) una ficha por nota del foco: de qué trata, palabras y frases con las que alguien la buscaría aunque la nota no las use (sinónimos, palabras de todos los días, el término en inglés y en castellano) y preguntas que responde. Junta hasta 25 notas o 80.000 letras por pregunta, calcula cuánto puede costar cada una antes de hacerla y no la hace si no queda margen, así el gasto nunca pasa el tope. Las guarda en `fichas.json` (fuera de git: tiene parte del texto de las notas) con la huella del texto de cada nota: otra pasada rehace solo las de las notas que cambiaron. El buscador usa la ficha (BM25 aparte) solo para sumar notas que no coinciden por su texto: las que sí coinciden se ordenan igual que sin fichas (sumarle la ficha a todas desordenaba los pedidos reales), y si el pedido tiene que ver con tus notas se decide sin las fichas (con ellas, pedidos ajenos recibían pista). El corrector de errores no cambia una palabra que está en una ficha. Nunca toca las notas. |
| `historial.py` | Que nada de lo que se borre de la memoria se pierda. Al terminar cada respuesta y al volver de compactar (`hook_guardar.py`), y con `--salud`, mira si cambió algún `.md` de las carpetas de memoria (tamaño y fecha, en milisegundos) y, si cambió, guarda una versión con git en `historial/` dentro de la carpeta de datos (nace cerrada para tu cuenta, como `en-vivo/`): un repositorio por carpeta de memoria, con la carpeta de la memoria como lugar de trabajo, así no escribe nada adentro de ella ni toca las notas. El mensaje de cada versión dice qué notas cambiaron, nacieron o se borraron (solo los nombres). Deja afuera, como el mapa, los archivos delicados por el nombre (`archivos.es_sensible`: `.env`, `id_rsa`, `.ssh/`…) y las carpetas ocultas; si uno ya estaba, sale en la versión siguiente (en las viejas queda hasta que se borre la carpeta). Si otro chat está guardando a la vez, no espera: lo guarda la próxima vez; un candado de git de más de 10 minutos (de un hook cortado a mitad de camino) se saca. Guardar tiene 6 s en total, así nunca llega al tope del hook. En ese repositorio interno (nadie más lo ve ni se sube) la firma de commits y los hooks de git están apagados: si tu git obliga a firmar o tiene un hook global, el historial igual guarda, sin pedirte la clave. Buscar pide 3 letras o más y mira las últimas 100 versiones que cambiaron ese texto. `--historial` muestra los últimos cambios; `--historial "texto"` dice cuándo apareció o se borró ese texto (sin importar mayúsculas), qué renglón era y con qué comando de git leer la versión entera de antes. Sin git, queda apagado y `--salud` lo dice. Guarda copia del texto de las notas: como `cerebro.html`, no se comparte. |
| `charlas.py` | `--charlas "palabras"`: lo que se habló y nunca se anotó. Recorre en el momento las charlas que guarda Claude Code (`~/.claude/projects/*/*.jsonl`, sin las de los agentes) y lee solo los textos de los mensajes del usuario y de Claude: nunca lo que devolvieron las herramientas, los comandos, el pensamiento interno, los mensajes internos de Claude Code, el resumen de compactar ni los avisos del sistema (`<system-reminder>` y parecidos). Busca todas las palabras en el mismo mensaje, sin importar mayúsculas ni acentos; antes de buscar tapa lo que parece una clave (formatos conocidos como `sk-…`, `re_…`, `ghp_…`, claves privadas, `ALGO_KEY=valor`, `clave: …` cuando el valor tiene números o símbolos, textos largos al azar y la clave del propio servidor), así buscar una clave no la encuentra y no se muestra. Muestra las charlas más nuevas primero, con su carpeta, las fechas y los últimos 3 mensajes de cada una (`--cuantos` dice cuántas charlas). No guarda copia ni índice: unas 2,5 GB de charlas se recorren en unos 3 s. |
| `consultas.py` | Cuánto se usa el buscador y cuántas notas recomendadas por las pistas se leyeron después (las líneas de `--salud`), y la clave de cada ruta en el registro. |
| `permisos.py` | Que otra cuenta de la PC no pueda escribir en los datos: las carpetas que crea Neuromapa (la de datos si no existía, `en-vivo/`, `historial/`) nacen cerradas para tu cuenta, y `--salud` avisa, con el comando para cerrarla, si otra cuenta puede escribir en la carpeta de datos, en `en-vivo/` o en la del programa. |
| `aprender.py` | Aprende del registro (`--aprendido`, `--olvidar`). Está partido por trabajo: `aprender.py` junta todo, rearma (`consolidar`, con su candado) y tiene los comandos; `aprender_comun.py` los números que se ajustan, las rutas y la lectura del registro; `aprender_memoria.py` cómo aprende de cada evento; `aprender_charlas.py` la lectura de las charlas guardadas; `aprender_pista.py` lo que usa la pista (qué va con qué, lo reciente, lo ya leído); `aprender_informe.py` lo que cuenta en la consola, la página y `--salud`. Los demás programas importan solo `aprender`. cada archivo leído o editado se une con los últimos 8 del mismo pedido, todo pierde la mitad cada 14 días y, por cada pista, cuenta si la nota recomendada se leyó. Lo resume en `en-vivo/aprendido.json` leyendo solo lo nuevo; el buscador lo usa para sumar código y notas a la pista, y la página para las conexiones «Aprendida» (si las dos notas ya estaban conectadas, no dibuja otra línea: engrosa la que había, en tres niveles de fuerza, con cuentitas de luz desde el segundo, y los pulsos tardan hasta un 45 % menos en recorrerla, saltando de cuenta en cuenta; también corren por las «Aprendida»). Con el mapa abierto todo eso va en vivo: cuando un chat lee una nota y enseguida otra que ya está conectada, esa conexión se ilumina; y cada vez que cambia `aprendido.json`, el evento `aprendido` trae los caminos (`caminos`: ids de las dos notas y la fuerza) y la página los pone al día sin recargar: nacen los nuevos, destellan los que suben de nivel y se apagan los olvidados (la primera vez que llega, al conectarse, solo se pone al día, sin animar). No aprende de las corridas de prueba (`NEUROMAPA_PRUEBA=1`), de archivos sensibles ni de lo temporal de Claude. Además lee una sola vez las charlas guardadas de Claude Code de antes del primer evento del registro (solo hora, sesión y rutas de lecturas y ediciones, de a pedazos en el hook) y eso queda aparte, de respaldo para las notas de las que todavía no aprendió nada firme. También cuenta, por la carpeta de cada chat, en qué proyecto cae el código que toca, para no sugerir código de un proyecto donde ese chat casi nunca trabaja (menos del 5 %). Lo que la pista sugirió por lo aprendido y Claude abrió suma la mitad con las notas de esa pista, para que una sugerencia no se refuerce sola. De los agentes, que al buscar leen muchas notas seguidas, no une notas con notas ni cuenta esas lecturas; de las charlas no aprende las acciones que fallaron, y nunca aprende archivos de librerías ni generados (`node_modules`, `.git`, `__pycache__`, `.next`, entornos de Python). Si cambia lo que guarda, sube la versión de `aprendido.json` y se rearma solo, con las últimas 8 semanas del registro (lo de antes pesa menos de 1/16). `--olvidar` borra un archivo entero o una unión y anota desde cuándo (en `olvidos`, que sobrevive a ese rearmado): lo usado antes ya no la vuelve a formar, ni del registro ni de las charlas; lo que se use después, sí. Si no hay nada nuevo, no lo reescribe (anota la vuelta en `aprendido.visto`), así la página no recibe `aprendido` de balde. |
| `hook_*.py` | Los hooks de Claude Code (ver abajo). |
| `neuromapa.py`, `bin/` | El comando `neuromapa`, que el plugin pone en la consola de Claude. |
| `scripts/` | Los lanzadores de Python de los hooks: `python.sh` (Git Bash, Linux y Mac) y `python.cmd` (Windows sin Git Bash). |
| `vendor/` | d3 y marked, que entran adentro de la página (licencias en `vendor/LICENCIAS.md`). |
| `herramientas/prueba_humo.py` | Arma notas inventadas en una carpeta temporal y revisa todo sin tocar lo tuyo. |
| `herramientas/verificar.py` | Revisa la sintaxis del JavaScript de la página y que se arme, en una carpeta temporal. |
| `herramientas/bajar_librerias.py` | Vuelve a bajar d3 y marked a `vendor/`, verificando su huella. |

## Los hooks

Claude Code los corre en cada momento de la sesión. Todos pasan por un lanzador (`scripts/python.sh` o
`scripts/python.cmd`) que busca Python 3.10 o más nuevo y, si no hay, no hace nada (el de arranque avisa una vez).
Comparten `hooks_comun.py`: leer la entrada, correr cada paso sin que un error corte los demás ni a Claude Code, y
responder. Con la variable `NEUROMAPA_DEPURAR=1`, los errores que se tragan aparecen en la salida de errores.

| Hook | Cuándo | Qué hace |
|---|---|---|
| `hook_cerebro.py` → `hook_evento.py` | Casi todos los eventos, de fondo | Anota en `en-vivo/eventos.jsonl` qué pasó: tipo de herramienta, ruta, cantidades. Nunca el texto de mensajes, comandos, búsquedas ni direcciones web completas. Al terminar cada respuesta, rearma lo aprendido (cada 10 minutos como mucho). |
| `hook_inicio.py` | Al arrancar | Deja anotado dónde están los datos, para el comando `neuromapa`. |
| `hook_servir.py` | Cada pedido | Avisa una vez por chat los problemas nuevos de tus notas (los de una memoria, solo a los chats de su proyecto; sin el mapa abierto, rearma la lista de fondo cada 6 horas); con el primer pedido del día larga de fondo la pasada de `dormir.py` y, cuando hay propuestas, lo avisa una sola vez; con el contexto automático prendido, le pasa a Claude qué leer primero, las decisiones anotadas que tocan el pedido y hasta 3 archivos de código o scripts que esas notas citan, para que los compruebe antes de responder, sin repetir el `CLAUDE.md` ni el `MEMORY.md` que ya tiene cargados, ni lo que ese chat ya leyó desde su última compactación (la nota entera o el tramo justo). Con lo aprendido suma 1 archivo que se suele abrir con esas notas (nunca a partir de un `CLAUDE.md` o un `MEMORY.md`, y con su carpeta si el nombre se repite), la nota que se suele leer junto con la primera (si también tiene que ver con el pedido; si la pista se pasa del tope, primero se recortan las citas de las otras) y sube lo leído en las últimas 3 horas en el mismo proyecto; y anota en el registro qué notas recomendó y por qué eligió cada una: por las palabras del pedido, porque la nombra un índice o porque se suele leer junto con la primera, con el tramo de renglones y la ruta de la otra nota (solo códigos, números y rutas, nunca el texto del pedido). En el mapa, cada rayo de la pista sale del color de su motivo, la fila de «Ahora» lo resume y el panel de la nota dice por qué la eligió. Si el pedido no tiene que ver con tus notas (la mejor no llega a 0,9 de lo que suma una palabra rara encontrada de lleno, una vara que no depende de cuántas notas tengas) o ningún renglón de una nota junta al menos 3 de sus palabras, no suma nada. Alcanzan 3 palabras de tema, con o sin «?», y los errores de tipeo se corrigen solos. Si el pedido nombra algo dicho antes («lo que te dije», «como quedamos», «el otro día», «acordate», y sus parecidas en inglés), suma una línea al final (o sola, si no hay pista) que sugiere `--charlas` para lo que se habló sin anotar y `--historial` para lo que estaba anotado y se borró; con las frases de hoy salta en menos de 1 de cada 100 pedidos. |
| `hook_parecidas.py` | Al crear un archivo | Si es una memoria parecida a otra, se lo dice a Claude. |
| `hook_choques.py` | Al editar | Si otro chat editó el mismo archivo hace poco, o si lo nuevo nombra una ruta que no existe, se lo dice a Claude. Con el contexto automático prendido, al editar un archivo de código le dice cuál es la nota más unida a él en lo aprendido (con fuerza de 0,25 o más, sin contar un `CLAUDE.md` o `MEMORY.md` que ya tiene cargado), una vez por archivo y por chat (de nuevo después de compactar), si ese chat todavía no la leyó; si ya la leyó, no baja a una más floja. A los agentes no. Lo anota en el registro como `recuerda` (solo las dos rutas) y `--salud` cuenta cuántas de esas notas se leyeron después. También revisa al guardar: si un `Edit` en una nota reemplaza un dato por otro en el mismo lugar (las dos palabras de antes siguen y el dato cambia: «sale en 92 de» → «sale en 93 de»; un número de una o dos cifras se lleva también la palabra de después; fechas y horas no cuentan), busca esa frase vieja en las demás notas con el índice guardado, la confirma en el archivo de verdad (así no avisa por una nota que ya se corrigió) y le dice a Claude cuáles la siguen diciendo, con la línea (hasta 3; nunca las notas de historia ni la editada). Con las 1.537 ediciones de notas que hicieron los chats hasta el 4/10, avisa en 2. No guarda nada. |
| `hook_guardar.py` | Al volver de compactar y al terminar cada respuesta | Con el contexto automático prendido. Al volver de compactar le dice a Claude que el resumen es lo único que queda de lo anterior y que lo decidido que no esté escrito se pierde en la próxima compactación. Al terminar una respuesta, si desde la última vez que el chat escribió en una nota (o desde el último recordatorio) cambió 5 archivos o más, o hizo un commit con al menos un archivo cambiado, le recuerda anotar lo que valga la pena, una vez cada 15 minutos como mucho; los `.md` y `.txt` no cuentan como cambios. Lo anota en el registro como `guarda` (el motivo y cuántos archivos, nunca texto). Espera a que termine (no corre de fondo): si no, el aviso no le llega a Claude. En los dos momentos, aunque el contexto automático esté apagado, guarda una versión de la memoria si cambió (ver `historial.py`). |
| `hook_freno.py` | Antes de lanzar agentes | Con un `freno` en la configuración, pregunta si ya se gastaron muchos tokens. |

### Por qué cada comando de `hooks/hooks.json` tiene dos mitades

Claude Code corre los hooks con Git Bash si está instalado y, si no, con PowerShell. Cada comando sirve para los dos:

```
/bin/sh "${CLAUDE_PLUGIN_ROOT}/scripts/python.sh" -I -S "${CLAUDE_PLUGIN_ROOT}/hook_x.py" \; . "${CLAUDE_PLUGIN_ROOT}/scripts/python.cmd" hook_x.py
```

- En `sh`, `\;` es un argumento más: `python.sh` le pasa a Python el hook con eso y lo que sigue, que el hook ignora.
- En PowerShell, `/bin/sh` no existe y falla sin hacer nada; el `;` separa comandos y el `.` corre `python.cmd`, que
  busca Python en Windows y arma la ruta del hook desde su propia carpeta (`%~dp0`), por eso recibe solo el nombre.

JSON no admite comentarios, así que la explicación vive acá; `herramientas/prueba_humo.py` comprueba que cada
comando tenga esta forma y lo corre con los dos.

## El registro en vivo (`en-vivo/eventos.jsonl`)

Un renglón JSON por evento, con claves cortas porque se escribe en cada paso de Claude. Es lo que hablan entre sí el
hook (que escribe), el servidor (que lo lee, lo resume y lo filtra con una lista blanca antes de mandarlo) y la página.

| Clave | Qué guarda |
|---|---|
| `t` | La hora (segundos desde 1970, con milésimas). |
| `s` | Los primeros 8 caracteres del id del chat. |
| `e` | La fase: `pre`, `post`, `falla`, `usuario`, `fin`, `sub-fin`, `espera`, `compacta`, `inicio`, `cierre`, `aviso` (la pista del contexto automático) o `recuerda` (la nota que se le recordó al editar un archivo de código: `f` es el archivo y `fs` la nota). |
| `h` | El nombre de la herramienta (hasta 120 caracteres). |
| `k` | El tipo: `leer`, `buscar`, `editar`, `crear`, `ejecutar`, `agente`, `web`, `consulta`, `otro`, o la fase. |
| `c` | La carpeta del chat. |
| `a`, `at` | El agente que hizo el paso y su tipo, si fue un agente. |
| `id` | El final del id de la llamada, para juntar el antes y el después. |
| `f` | La ruta del archivo (o la carpeta de una búsqueda); nunca una dirección web. |
| `fs` | Hasta 5 notas `.md` que tocó un comando o que recomendó una consulta o una pista. De un comando, solo rutas de archivos: nada de un comando de red (`curl`, `wget`, `ssh`, `Invoke-WebRequest`…), nada que empiece con una IP o `localhost`, y un nombre suelto sin carpeta solo si el archivo existe (o si el comando lo crea). |
| `fc` | En una pista, el código para comprobar que nombran sus notas (el nombre del archivo). |
| `na`, `ca` | En una pista, lo que sumó lo aprendido: la nota que se suele leer junto y la ruta del código que se suele abrir. Sirven para medir aparte si Claude lo usó (`--salud`, `--aprendido`). |
| `z` | `1` si el evento es de una corrida de prueba (`NEUROMAPA_PRUEBA=1`): lo aprendido no lo usa. |
| `b` | La familia del comando, de una lista fija: `commit`, `compila`, `prueba`, `git`, `base` y `cerebro` por lo que hace en cualquier parte; si no, por el primer programa (sin contar `cd`): `lee`, `busca`, `lista`, `python`, `node`, `red`, `archivos`, `sistema`, `script` u `otro`. |
| `d` | Cuánto tardó la herramienta, en milisegundos (si Claude Code lo manda). |
| `xc` | En la falla de un comando, el código con que salió (solo el número del principio del error, «Exit code N»). |
| `bg` | `1` si el comando corrió en segundo plano. |
| `nr` | `1` si el comando no encontró nada («No matches found»). |
| `p` | Un dato corto según el tipo: la opción de una consulta, el tipo de agente, el dominio de una web, el nombre de una skill, o el motivo de compactar, arrancar o cerrar (de una lista fija). |
| `n` | El largo del mensaje del usuario (solo el número). |
| `m` | Líneas nuevas y viejas de una edición. |
| `r` | Línea de inicio, líneas leídas y total de una lectura. |
| `x` | Si una falla fue por interrupción y si fue por tiempo. |
| `o` | `app` si el evento lo escribió el conector de la app de escritorio (ver abajo), no un hook de Claude Code. |

A los 5 MB, o cuando su primer evento tiene más de una semana, rota a `eventos-AAAAMMDD-HHMMSS.jsonl`. El servidor
resume cada rotado por día (`resumen-dias.json`), lo comprime a los 30 días y, como el hook al rotar, borra lo que pasa
de `borrar_registros_dias` (a más tardar una semana después, porque borra rotados enteros).

## Conector para la app de escritorio de Claude (opcional)

En el modo Chat de la app de escritorio los hooks no corren: Neuromapa no ve esas charlas ni les pasa la pista.
`conector_mcp.py` es un servidor MCP local y de solo lectura que les da cuatro herramientas: `sobre` (la misma pista que
`--sobre`), `buscar`, `leer_nota` (solo notas del índice, nunca otro archivo ni uno delicado) y `avisar_charla`, que no
lleva ni devuelve texto: solo marca que hay una charla nueva, con su propia marca, para que se vea en el mapa aunque no
haga falta leer notas. Claude usa las herramientas cuando le parece; para que avise siempre, sumá a tus preferencias de
la cuenta algo como «Si tenés las herramientas de Neuromapa, al empezar cada charla llamá una vez a avisar_charla, y
usá sobre cuando el pedido pueda tener que ver con mis notas». Cada uso queda en el
registro como un chat más, «Chat de la app» (`"o": "app"`), con la opción y las rutas que devolvió, así se ve en el mapa
y lo aprendido lo cuenta; nunca guarda lo que se preguntó. El texto de las notas que lea va a esa charla, como cualquier
archivo que Claude abre. Contesta enseguida y anota después, en segundo plano.

La app también les pasa el conector a sus charlas de Claude Code. Ahí no hace falta: las instrucciones le dicen a Claude
que no llame a `avisar_charla`, y si una charla de Code usa una herramienta del conector, el conector no la anota como
«Chat de la app» (se da cuenta porque el hook de Claude Code anotó un instante antes `mcp__…neuromapa…__<herramienta>`,
y esa charla ya figura con su nombre).

El plugin no lo registra solo. Para sumarlo, agregá esto en `claude_desktop_config.json` (en Windows, en
`%APPDATA%\Claude\`; en Mac, en `~/Library/Application Support/Claude/`) con la ruta a una copia de Neuromapa que no se
mueva (por ejemplo un clon del repo: la carpeta del plugin cambia con cada versión), y reiniciá la app:

```json
{"mcpServers": {"neuromapa": {"command": "python3", "args": ["/ruta/a/neuromapa/conector_mcp.py"]}}}
```

En Windows, `"command": "py"` con `"args": ["-3", "C:\\ruta\\a\\neuromapa\\conector_mcp.py"]`. Usa la misma
configuración que la consola: si tus datos están en otra carpeta, sumá `"env": {"CEREBRO_CONFIG": "<ruta al config.json>"}`.

## Dónde viven los datos

En este orden: la variable `CEREBRO_CONFIG` (la ruta a un `config.json`; si es relativa, desde la carpeta del
programa); la carpeta de datos elegida en las opciones del plugin; la carpeta propia del plugin
(`~/.claude/plugins/data/neuromapa-…`, que sobrevive a las actualizaciones); un `config.json` al lado del código; o lo
que anotó el arranque. Ahí van `cerebro.html`, `en-vivo/` (registro, clave del servidor, cachés), `historial/` (las
versiones de la memoria) y `problemas.json`, y
también los dos archivos que podés escribir vos: `hechos.json` (ver abajo) y `sugerencias.json`, una lista de
`{"de": nota, "a": nota}` (ruta o id, y opcional `"clase": "duplicado"`) con conexiones que el mapa dibuja como
«sugerida» o «posible duplicado».
Aparte, el lanzador anota qué Python usar (`python.txt`) y el arranque dónde está esa carpeta (`donde.txt`) en la
carpeta propia del plugin, y `--demo` escribe su página y su registro dentro de `demo/`.

Si no hay `config.json`, se arma solo: la memoria de cada proyecto de `~/.claude/projects` y tus `CLAUDE.md` de
`~/.claude`.

## `config.json`

Las rutas pueden ser absolutas o relativas a la carpeta del `config.json`. [demo/config.json](../demo/config.json) es un
ejemplo completo. Si lo cambiás con el mapa prendido, abrilo con `/neuromapa:abrir --reiniciar`: el servidor lee la
configuración al arrancar (la consola y los hooks la leen cada vez), y cerrar la pestaña no alcanza porque sigue
prendido 10 minutos y un `/neuromapa:abrir` común lo reusa. Sin el plugin es igual con `sh bin/neuromapa abrir
--reiniciar`; `abrir-cerebro.bat` y `abrir-cerebro.sh`, abiertos de nuevo, ya reinician.

| Campo | Qué es |
|---|---|
| `usuario` | Tu nombre, para los textos («lo decide…»). |
| `fuentes` | Las carpetas de notas, cada una un grupo del mapa (ver abajo). Si no lo ponés, usa las de fábrica: la memoria de Claude Code y tus `CLAUDE.md`. |
| `proyectos` | Tus proyectos: `raiz`, `alias`, `codigo` (carpetas de código contra las que el médico compara las anclas), `extensiones` (las que se toman como archivos al buscar entidades), y opcionales `marca` (expresión regular que dice que un renglón habla de ese proyecto), `pistas`, `remite_a`, `prefijo_carpeta`, `marca_seccion` y `aparte` (`true` si no comparte temas con los demás: en sus chats, las notas de los otros proyectos pesan la mitad en la pista, y al revés; la carpeta del propio Neuromapa ya va aparte). |
| `lobulos` | El rótulo de cada lóbulo: `prefrontal`, `frontal`, `parietal`, `occipital`, `temporal`, `cerebelo`, `tronco`. |
| `alias_rutas` | Pares `[ruta que se ve, ruta real]`, para carpetas que se ven por dos caminos (enlaces). |
| `podar`, `podar_si_contiene`, `excluir_fragmentos`, `excluir_claude_bajo` | Carpetas que no se recorren (hay valores de fábrica razonables). |
| `carpetas_pesadas` | `{contiene, bajar_solo}`: en carpetas enormes, bajar solo a las subcarpetas nombradas. |
| `prefijos_tabla` | Prefijos de nombres de tablas de base de datos, para reconocerlas como entidades. |
| `handoffs` | `{prefijo, nombre, lados}`: notas de traspaso entre dos equipos o chats, para marcar las que nadie contestó. |
| `freno` | `{tokens_de_agentes_por_hora, workflow_siempre}`: el freno de agentes. |
| `dormir_con_claude` | `{tope_usd_por_dia, modelo}`: prende la revisión con Claude de la pasada de cada día (ver `dormir_claude.py`). El tope es en dólares, hasta 20 (con una suscripción no es plata aparte: sale de tu cupo de uso); el modelo, `sonnet` si no se dice. Sin este campo no le pregunta nada a Claude. |
| `borrar_registros_dias` | A cuántos días se borran los registros viejos del mapa, ya resumidos por día (90; 0 es nunca). |
| `aprender` | Si aprende del uso (`true` de fábrica). Con `false` no anota las pistas, no rearma `aprendido.json` y el buscador no lo usa. |
| `comparar_aprendido` | El modo de comparación, para saber si lo aprendido ayuda: la parte de los pedidos (de 0 a 0,5; 0,2 es uno de cada cinco) cuya pista se arma sin lo aprendido (sin la nota que se suele leer junto, sin el código que se suele abrir con esas notas y sin el empujón a las notas que se leyeron cuando se recomendaron). El aviso del registro lo marca (`sa`) y `--aprendido` compara cuántas pistas sirvieron en cada grupo (Claude leyó una nota o abrió un archivo de ella) desde que empezó; con menos de 30 pistas sin lo aprendido avisa que todavía no alcanza. Apagado de fábrica (0). |
| `sensibles` | Nombres de carpetas o archivos con claves de tus proyectos que se suman a la lista de fábrica (claves SSH y de PuTTY, `.env`, `.pem`, `.key`, `.npmrc`, `.netrc`, `.git-credentials`, `.kube`, terraform, KeePass, tokens, contraseñas de Chrome, la clave del mapa…): lo aprendido y la pista nunca los nombran. Por ejemplo `["_firmas", "servidor.ini"]`. |

Cada **fuente** lleva `id`, `nombre`, `color` y `raices` (cada una `ruta`, o `[ruta, recursivo, alias]`), y puede
llevar:

| Campo | Qué hace |
|---|---|
| `patron` | Qué archivos toma (de fábrica, `*.md`; por ejemplo `CLAUDE.md`). |
| `excluir` | Patrones de archivos que no toma. |
| `memoria` y `proyecto` | Es una memoria de Claude Code, y de qué proyecto. |
| `foco` | Entra en la búsqueda de fábrica de `--sobre`. |
| `peso_busqueda` | Cuánto pesa en la búsqueda (1 de fábrica). `planes_vigentes` exime de ese peso a los archivos que empiezan con «plan». |
| `prioridad` | Orden en el informe del médico (más bajo, antes; 2 de fábrica). |
| `historico` | Notas viejas a propósito (changelogs, archivo): el médico no les revisa rutas, enlaces ni anclas, y no se proponen como cifras de control. Los archivos que empiezan con «changelog» cuentan como históricos siempre. |
| `registro` | Registro de decisiones: sus enlaces rotos no se marcan (nombran cosas que ya cambiaron). |
| `anclas_resumidas` | El médico resume sus anclas corridas en vez de listarlas una por una. |
| `lobulo` y `ancla` | En qué lóbulo va el grupo, y opcionalmente dónde exactamente (`[x, y, radio]` o `[x, y, radio, achatado]`). |

## `hechos.json`

Cifras de control: un dato de una nota («la API tiene 6 módulos») y cómo contarlo en el disco (líneas de un archivo,
archivos o carpetas de una ruta). El médico avisa el día que dejen de coincidir. `neuromapa --proponer-hechos` sugiere
algunos solo y `neuromapa --aprobar-hecho 1,3` los suma.

## Probar un cambio

```
python3 herramientas/prueba_humo.py
python3 cerebro.py --demo --salud
python3 servidor.py --demo --sin-navegador --puerto 8799
claude plugin validate .
```

En Windows, `py -3` en lugar de `python3`.
