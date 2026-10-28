# Cambios

Las versiones siguen el número de `.claude-plugin/plugin.json` (`claude plugin list` lo muestra, y Claude lo ve con `neuromapa --version`). Cada versión que
sale sube ese número; si no, la actualización puede no traer nada (ver [CONTRIBUTING.md](CONTRIBUTING.md)).

## 0.1.7 — en prueba

- El clon ya no queda a medias en Windows. Tres notas de la demo tenían rutas de 70 a 74 letras y, clonadas dentro de
  una carpeta honda, Windows no las creaba («Filename too long») y git dejaba el clon incompleto. Ahora se llaman
  `avisos-repetidos-mp.md`, `arreglo-webhook-doble.md` y `fix-double-reply.md`, con los enlaces y el índice de la demo
  al día, y las pruebas de GitHub revisan que ninguna ruta pase de 68 letras (`herramientas/rutas_cortas.py`). Lo
  encontró y lo arregló Byron (@Bddgc) en el PR #4.
- `--salud` muestra las menciones ambiguas: una nota que nombra `progreso.md` o `LEEME.md` sin carpeta cuando hay
  varias con ese nombre. Antes solo salían en el mapa y en el aviso a los chats, así que la consola daba menos avisos
  que el mapa (en una memoria real, 8 contra 22) y Claude, que lee `--salud`, no las veía. Ahora cada una sale con su
  renglón, las notas candidatas y cómo arreglarla (poner la carpeta, o «un progreso.md» si es uno cualquiera). En el
  mapa y en el aviso a los chats no se cuentan dos veces.
- Las anclas `archivo:línea` que el médico sigue con git ya no proponen números que caen en otro código. En una memoria
  real, de 12 propuestas así solo 5 estaban bien. Pasaba por tres cosas:
  - En las memorias, que no están en git, la fecha de la cita era la del archivo, que cambia con cualquier edición
    posterior. Ahora es la de la primera versión del historial de la memoria que trae esa cita (también si después
    la nota se partió en «parte N» o historias).
  - En un repo, si el renglón se retocó después, la fecha era la del retoque. Ahora, si la cita ya estaba antes de ese
    commit, no da número.
  - Si la nota se escribió con lo leído antes de un commit hecho un rato antes, el número contaba solo lo que se movió
    después. Ahora tiene que dar lo mismo desde cada estado del archivo en las 6 h de alrededor de la cita.

  Cuando esas cuentas no coinciden, o no se sabe de cuándo es la cita, el ancla sale igual si todas dicen que se
  corrió, pero sin número («hoy estaría en la 1498 o la 1530») y sin proponerse como arreglo. También sigue un
  renglón editado en el mismo lugar y las dos puntas de un rango. Con la misma memoria: 7 de esas 12 bien, 2 a 4
  líneas (el renglón ya estaba corrido al escribirse), 1 sin número con la buena entre las opciones y 2 sin marcar;
  ninguna en otro código. Más anclas viejas de los documentos de proyecto salen ahora (antes se callaban cuando dos
  cuentas no coincidían).
- Lo que la pista, `--sobre` y el médico citan de una nota ya no lleva caracteres de control. Un título con un código
  de color de la consola o un pitido le llegaba así a Claude; ahora cada uno queda como «?». El «» que una nota mete
  para cerrar la cita antes de tiempo ya se cambiaba por ‹›; una prueba nueva lo comprueba de punta a punta con una
  nota escrita para meterle órdenes a la pista.
- El índice de búsqueda ya no pierde notas por un mal momento. Si al rearmarlo una carpeta no responde (un junction
  caído, un disco de red) o una nota no se puede leer, el índice nuevo sale con menos notas; antes se guardaba igual y
  la pista se quedaba sin ellas hasta el próximo rearmado. Ahora, si faltan notas cuyo archivo sigue ahí o cuya carpeta
  no se puede leer, contesta con lo que pudo leer pero no lo guarda, y el próximo pedido vuelve a probar. Una nota
  borrada de verdad sale enseguida, y si la carpeta no vuelve en media hora, se acepta el índice más chico.
- Un archivo de datos roto ya no se pisa en silencio. Con `descartados.json` roto, `--descartar-aviso` y
  `--recuperar-aviso` lo dicen y no escriben (antes lo reescribían con lo nuevo y se perdían los avisos descartados).
  Con `aprendido.json` roto, se aparta con la fecha en el nombre antes de armar uno nuevo (antes se pisaba, y volvía lo
  que se había mandado olvidar). En los dos casos `--salud` avisa qué pasó y dónde quedó.
- El conector MCP (`sobre`, `buscar`, `leer_nota`) sigue andando si Neuromapa se actualiza mientras una charla está
  abierta. Antes juntaba módulos viejos, ya cargados, con nuevos, y fallaba con «cannot import name … from archivos»
  hasta reiniciar la charla. Ahora, si el código cambió desde que arrancó, contesta cada pedido en un proceso aparte
  con todo el código nuevo.

## 0.1.6

Para que el índice de la memoria no se llene solo:

- Todo enlace a una nota en un renglón de lista de `MEMORY.md` cuenta como listado, no solo el primero. Un renglón
  que junta varias notas («Nota, historias (archivo): [1](…); [2](…)») ya no las deja en el médico como «sin índice»
  o «se llega por otra». Un enlace de más que apunta a una nota que no existe sale como índice roto.
- Al partir una nota por segunda vez, la historia nueva se junta con la primera en un solo renglón del índice, con el
  gancho de cada una entero, en vez de sumar otro renglón.
- Con `partir_sola` prendido, la pasada de cada día junta en un renglón las historias de una misma nota que estén en
  renglones sueltos del índice, sin cambiar lo que dice cada una: con copia en `respaldos/`, anotado en
  `partidas.log` y con aviso a cada chat. `--por-partir` dice qué juntaría.
- Al editar `MEMORY.md`, si queda un renglón de más de 220 letras que apunta a una sola nota, el hook se lo dice a
  Claude en el momento. Antes se enteraba recién en el próximo `--salud`.
- Ese renglón largo pasa de «para revisar» a aviso del médico (`ganchoLargo`) y nombra la nota de ese renglón: así le
  llega a cada chat como problema nuevo aunque se haya escrito con un script, que el hook de editar no ve. Pasó con
  uno de 557 letras.

Para que una memoria que pasa mucho del tope quede bien partida:

- Con `partir_sola`, la pasada de cada día parte en tantas partes como hagan falta en una sola vez. Antes cortaba
  una vez por día: una nota al 189 % dejó una «parte 2» al 139 %, que tampoco entraba en una lectura. Una historia
  nueva tampoco recibe más del 80 % del tope de una vez: lo que no entra va a otra. `--por-partir` avisa cuando la
  parte nueva seguiría pasada.
- Una memoria que pasa el tope durante el día ya no espera a la pasada del día siguiente (hasta 20 horas): al
  editarla, el hook lo anota, y el primer pedido que llega pasados 10 minutos la parte de fondo, con los mismos
  cuidados. Antes, mientras tanto, cada chat que la leía recibía solo una parte.
- Una memoria que ya va en tres partes o más («parte 2», «parte 3»…) queda «para revisar» en el médico
  (`notaEnPartes`): las partes se cortan por lugar, así que lo vigente y lo que falta quedan repartidos. El médico
  propone reordenarla a mano: arriba lo vigente, lo cerrado a una historia. Hacerlo solo se probó y no conviene:
  reconocer lo cerrado por las palabras («HECHO», «PUBLICADO») mandaba al archivo estados que siguen valiendo.

Para sumar una bóveda de Obsidian como fuente (ver [docs/obsidian.md](docs/obsidian.md)):

- Los `[[enlaces]]` con carpeta llevan a su nota: `[[Carpeta/Sub/Nota|alias]]`, como los escribe Obsidian cuando la
  bóveda tiene carpetas o dos notas con el mismo nombre, y los relativos (`[[../Carpeta/Nota]]`). Antes se buscaban
  solo por el nombre y salían rotos. Si la ruta sirve para dos notas, gana la que está en esa ruta desde la raíz de la
  bóveda; si no se puede decidir, queda en «Menciones ambiguas» y no como roto. Lo reportó iwoyeri en el
  [issue #2](https://github.com/lumiel777/neuromapa/issues/2), con una bóveda de 1.068 notas, las cifras y un arreglo
  probado.
- Los enlaces Markdown que escribe Obsidian con «Usar [[Wikilinks]]» apagado llevan a su nota: con el nombre solo
  (`[x](Tareas.md)`), desde la raíz de la bóveda (`[x](Proyectos/Tareas.md)`, con o sin `/` adelante), sin `.md` y con
  espacios codificados. Antes se buscaban desde la carpeta de la nota y salían rotos; pasaba en el médico, en la
  página y en `--renombrar`, que ahora también los cambia. Fuera de una bóveda, todo igual.
- Si un `[[enlace]]` por el nombre sirve para dos notas y una está en la raíz de la bóveda, gana esa, como en
  Obsidian. Antes ganaba la de la misma carpeta que la nota que enlaza, o quedaba como ambiguo.
- Un enlace a un adjunto (`![[foto.png]]`, un PDF, un `.canvas`) ya no cuenta como enlace a una nota que no existe.
- En el resumen de una nota (el título, la descripción y el gancho del índice que se ven en el mapa, en los
  pendientes y al partir), `[[destino|alias]]` muestra el alias, como en Obsidian y en el panel de la nota, y
  `![[incrustado]]` ya no deja el «!». Antes mostraba el destino.
- Un enlace dentro de código (entre comillas invertidas o en un bloque) ya no cuenta como enlace, igual que en
  Obsidian: una nota que explica la sintaxis con ejemplos ya no da avisos. Si el ejemplo nombra una memoria, cuenta
  como mención.
- El médico marca cada enlace roto en su renglón, aunque el mismo texto aparezca antes en la nota.
- `--renombrar` cambia solo el nombre dentro de un enlace con carpeta, y la carpeta queda.
- No se leen las carpetas `.obsidian` (las opciones de Obsidian) ni `.trash` (su papelera): una nota borrada volvía al
  mapa como viva.
- Los alias y las etiquetas de Obsidian: antes se perdían, porque el encabezado solo se leía como «clave: valor» y
  Obsidian guarda las listas un valor por renglón. Ahora los `aliases:` sirven para encontrar la nota con `--sobre` y
  la pista, y las etiquetas (`tags:` y, dentro de una bóveda que no sea la memoria, los `#tema` del texto) también
  ayudan a encontrarla, se ven en su panel y arman un filtro «Etiquetas» en la columna del mapa. Medido con el examen
  de la pista: con notas sin alias ni etiquetas da exactamente lo mismo que antes.
- En el mapa, el panel de una nota que está en una bóveda de Obsidian (una carpeta con `.obsidian`, también la
  memoria si la abriste como bóveda) tiene un botón **Abrir en Obsidian**, para pasar a editarla a mano.
- Lo que una bóveda excluye en Obsidian («Excluded files», en `.obsidian/app.json`: plantillas, adjuntos, archivo) y los dibujos de Excalidraw (`.excalidraw.md`) no entran como notas. Antes no había forma de sacar una
  subcarpeta de una sola fuente. Un enlace a algo excluido no sale como roto, porque en Obsidian sigue andando.
- La carpeta de plantillas de Obsidian (la que se elige en las opciones de Plantillas) y la de Templater cuentan como
  excluidas aunque no estén en esa lista: antes sus notas entraban con títulos como `{{title}}` y daban enlaces rotos.
  Una carpeta vacía o «/» no deja nada afuera, y si se cambia, el mapa se rearma.
- Una fuente con `"huerfanas": false` queda afuera del aviso de nota huérfana, de la cuenta «no se alcanzan» y de las
  huérfanas de Salud. Ese aviso está pensado para la memoria, y en una bóveda con diarios y notas sueltas salía por
  cientos de notas que están bien así. De fábrica sigue igual. Lo pidió iwoyeri en el
  [issue #3](https://github.com/lumiel777/neuromapa/issues/3).
- Una propiedad con espacios en el nombre (`notas relacionadas:`, `related notes:`) ya no mete sus valores en las
  etiquetas o los alias de arriba: salían etiquetas falsas como `#[[Carpeta/B]]`.
- En una bóveda no entra nada de una carpeta con punto, como en Obsidian: ni la papelera `.trash` aunque tengas tu
  propia lista `podar`, ni las versiones viejas que guarda Syncthing en `.stversions`. Se cuenta desde la raíz de la
  bóveda, así que la memoria de Claude bajo `~/.claude`, abierta como bóveda, sigue entrando.
- Una copia de conflicto de Obsidian Sync, Dropbox o Syncthing ya no le gana el nombre a la nota buena: en la
  memoria manda el nombre del archivo, como en Obsidian. El médico avisa cada copia que tiene su original al lado.
- Un `[[{{date}}]]` o `[[<% tp.date.now() %>]]` de una plantilla no cuenta como enlace ni sale como roto.
- «Abrir en Obsidian» le pasa a Obsidian la ruta de la nota, y Obsidian elige la bóveda: antes iba por el nombre de
  la carpeta, y las memorias de todos los proyectos se llaman «memory».
- Un nombre con acento guardado de otra forma Unicode (como lo dejan las Mac) encuentra su nota, como en Obsidian.
- Una fuente `historico`, un changelog o una nota de archivo ya no dan avisos de enlaces rotos, como decía
  [Cómo funciona](docs/como-funciona.md): son viejos a propósito y nombran cosas que ya cambiaron. Antes solo el aviso
  al editar los salteaba; el médico, Salud y los problemas que llegan a los chats sí los marcaban.

Para usar Neuromapa desde Codex (ver [cómo funciona](docs/como-funciona.md#codex-opcional)):

- El conector reconoce a Codex, le da sus propias instrucciones y anota sus usos como «Chat de Codex». Antes los
  habría anotado como charlas de la app de escritorio de Claude.
- `hook_servir.py --codex`, para el hook de cada pedido de Codex: da solo la pista, sin anotarla en el registro ni
  sumar los avisos de problemas de la memoria. En la misma charla no repite lo que ya le dio, como en Claude Code
  (lo recuerda 3 horas en `en-vivo/codex-servidas.json`: la nota y sus renglones, nunca el pedido).
- El conector y la pista para Codex tapan lo que tiene forma de clave (`sk-…`, `ghp_…`, una clave privada, un texto
  largo de letras y números mezclados) antes de devolver una nota. Antes la devolvían entera, y con Codex eso va a
  OpenAI. «La clave es verde» y otras frases comunes quedan como están.
- Una consulta de Codex por el conector ya no cuenta como pista para lo aprendido ni para el acierto de `--salud`:
  Neuromapa no ve qué lee Codex con sus propias herramientas, así que la habría dado por fallida.

Para cambiarle el nombre a una nota sin romper nada (`--renombrar`):

- Ya no cambia una carpeta, un archivo ni un comando que se llaman como la nota (`D:\launcher-nuevo\src`,
  `git checkout launcher-nuevo`): el nombre pegado a una barra o a una extensión, o dentro de un bloque de código, lo
  muestra en el plan con su renglón para cambiarlo a mano. Entre comillas invertidas y solo, sí lo cambia.
- Si dos notas comparten el `name:`, ya no puede cambiarle el `name:` a la otra, y el plan sale igual en cada
  corrida: antes dependía de un orden al azar, y el código de `--confirmar` a veces no servía en la corrida siguiente.
  El mapa tampoco dibuja una mención a una de las dos elegida al azar.
- En una bóveda (o cualquier fuente que no es memoria), no acepta un nombre que ya usa otra nota en otra carpeta: los
  `[[enlaces]]` a ese nombre quedaban ambiguos, sin aviso.

Para el mapa:

- El dibujo simple de las conexiones arranca a las 800 notas en pantalla, no a las 500: un mapa de 500 notas ya no
  cambia de aspecto solo porque se sumaron unas pocas. Si la compu no da abasto, igual pasa al simple sola, como antes.
- La primera vez, el archivo de la clave existe desde que arranca el mapa. Antes se creaba recién con el primer
  pedido, y quien no tenía navegador (WSL, SSH) no lo encontraba donde la consola decía.
- Cada zona del cerebro tiene un solo nombre: arriba, chico y de color, el del lóbulo («FRONTAL»), y debajo, el de
  sus grupos. Antes salían dos nombres distintos uno encima del otro («FRONTAL · IDEAS Y PLANES» sobre «IDEAS Y
  DECISIONES»), que se pisaban con las notas y, en el celular, entre ellos. Lo que dice `lobulos` del `config.json`
  sigue en la ayuda (`?`, «Lóbulos»), aunque no empiece con el nombre del lóbulo.
- Bloque nuevo, «Lo que hizo por vos», a la izquierda, debajo del buscador: en los últimos 7 días, cuántas pistas le pasó a Claude,
  cuántas sirvieron (después leyó una de esas notas o abrió un archivo que nombraban), cuántas notas recomendadas leyó
  y cuántos problemas del médico (graves y avisos) se arreglaron, con la lista de cuáles. Un problema cuenta como
  arreglado si dejó de estar en una nota que sigue en el mapa, y deja de contar si vuelve; de cada uno se guarda solo
  la ruta, el tipo y la hora, por 30 días, en `problemas.json`. Las cuentas de las pistas son las que ya daba
  `--aprendido`: dicen lo que pasó después de cada pista, no que sin ella no hubiera pasado igual.

Para que la pista traiga lo justo:

- En un pedido largo busca también las últimas frases, no solo las primeras: cuando se pega un error o un log y la
  pregunta va al final, antes la pista buscaba el error y la pregunta nunca se buscaba.
- «Para comprobar» busca el archivo primero en el proyecto del que habla la nota y después en el del chat: con dos
  `servidor.py` en dos proyectos, ofrecía el del chat aunque la nota hablara del otro.
- Una «decisión» es la del mismo ítem de la lista y tiene que nombrar lo pedido: antes le pegaba al tema el renglón
  con «eligió» o «a propósito» de otro ítem (una de cada cuatro).
- Si todo lo de la pista ya se le dio a esa charla con el mismo tramo, no se repite entera (después de compactar, sí
  vuelve a salir).
- El proyecto de cada nota, para la pista, sale de la misma regla que la vista «Proyectos» del mapa (antes solo de su
  sección del índice): una nota de otro proyecto ya no le llega con peso entero a un chat por estar en una sección
  mezclada. Las reglas de cómo trabajar les siguen llegando a todos.

Para medir bien si lo aprendido sirve (`--aprendido` y `--salud`):

- Una comparación justa: «con lo aprendido contra sin» ya no cuenta lo que sumó lo aprendido, que agrega cosas a cada
  pista y así siempre «ganaba», y dice el margen («+1 puntos, ± 10: todavía no se puede decir que ayude»). Cuenta
  aparte cuánto se abrió de lo que sumó lo aprendido y la charla todavía no había tocado. La cuenta vieja sigue
  saliendo hasta que haya días medidos así, con un aviso de que favorece a lo aprendido.
- Una nota leída cuenta como acierto de una sola pista, la más nueva que la recomendó (antes, de hasta tres).
- El código que nombran las notas cuenta como abierto solo si se abre ese archivo, no otro con el mismo nombre en
  otra carpeta.

Para que lo aprendido haga lo que dice:

- Con el mapa abierto, lo aprendido se olvida a la mitad cada 14 días de verdad. Se guarda cada minuto, y con 4
  decimales la baja de un minuto de una unión floja se redondeaba a cero: no bajaba nunca, y las de entre 1,45 y 2,9
  bajaban hasta el doble de rápido. Ahora se guarda con 7.
- Una unión nueva de un archivo muy usado ya no se corta al minuto siguiente: se guardan hasta 90 por archivo y, para
  sugerir, se siguen usando las 30 más pesadas. Antes las notas más usadas quedaban congeladas con lo primero que
  aprendieron, y eran la semilla de un tercio de las pistas.

Para que ande más rápido (medido con una memoria de 500 notas):

- La regla «puede que ya esté resuelto» del médico pasó de ~18 s a ~2 s con el mismo resultado: repetía 236.000 veces
  el mismo trabajo con cada mensaje de commit. Era la mayor parte de lo que tardaban `--salud`, el armado del mapa y el
  índice de búsqueda, y de lo que gastaba el servidor cada vez que cambiaba una nota. `--salud` bajó de ~24 s a ~11 s.
- La línea de gasto de `--salud` y el freno de agentes leen las charlas desde el final: con una charla de 3,4 GB,
  5 s → 0,07 s, con la misma cuenta.
- El aviso de dato viejo, al editar una nota, mira una vez por nota si es la editada o una de historia, y no una vez
  por sección.

Para que el médico no avise de más:

- Con `partir_sola`, una memoria que ya no entra en un Read ya no se manda a partir a mano ni les llega a los chats
  como un problema para arreglar: el médico dice que la pasada de cada día la parte sola. Si la última pasada no la
  pudo partir, vuelve a ser un aviso con el motivo y el comando para hacerlo a mano.
- «Puede que ya esté resuelto» ya no toma como problema un renglón que solo describe cómo es algo («cada falla
  muestra un aviso», «si falla, reintenta», «a propósito», «el formato no guarda…», «venía roto»). Medido con una
  memoria de 500 notas: de 15 avisos quedaron 7, y se fueron justo los 8 falsos. Lo rotulado como hallazgo de una
  auditoría («Problema:», «Verificador:», «| E6 |») sigue contando.
- Un aviso descartado a mano sigue callado cuando la nota se parte y el renglón pasa a su «parte N» o a una historia;
  `--descartados` dice a qué nota pasó.
- Una ruta que ya no existe dentro de una carpeta temporal (la de una sesión de Claude o la del sistema) queda «para
  revisar»: se puede descartar y no llega a los chats, porque esa carpeta se borra sola. Si el renglón ya dice que era
  temporal, no avisa. A una que todavía existe ya no le propone sumarla a las fuentes.
- «Memorias parecidas» reconoce las partes que arma el propio Neuromapa (`…-parte-N`, `…-historia-N`) y dice de qué
  nota son, en vez de mandar a fusionarlas. Dos notas numeradas de series distintas ya no salen como «partes de» una
  tercera que enlaza a las dos.
- En `--pendientes`, un «sin commit» cuyo repositorio ya no tiene nada sin commit, y tuvo un commit desde la fecha de
  la frase, sale como «quizás ya está commiteado». El que nombra otra carpeta se mira con el repositorio de esa carpeta.
- `indice_meta_kb` en `config.json`: tu meta de tamaño para `MEMORY.md`, en KB. El médico avisa cuando la pasa, en
  vez de recién cerca de los 19 KB.
- `--salud` junta en un renglón los hallazgos del mismo tipo en una misma nota («6 anclas corridas (renglones 164,
  170, 177, 178 y 2 más)») y pone primero las notas que la pista más usa. Si la pasada de cada noche ya tiene el
  arreglo listo, el renglón lo dice con los números para `--aplicar`. Antes era un renglón por hallazgo: en una
  memoria con 102 «para revisar», 89 eran `archivo:línea` corridos, y el arreglo listo quedaba en otro renglón, al
  final. Con el mismo largo ahora se ven 59 hallazgos en vez de 28. `--salud --todo` los sigue mostrando uno por uno.

Para quien abre el mapa por primera vez:

- La primera vez, al terminar la intro, una tarjeta «Para empezar» dice en tres renglones qué son las figuras, qué
  muestra «Ahora» y qué es la barra de problemas. Sale una sola vez, y nunca en modo cine ni anónimo.
- La ayuda (`?`) dice que cada figura es una nota (la forma, el tipo; el tamaño, cuántas conexiones tiene) y que los
  puntitos son tejido de adorno; antes decía «cada punto es una nota». Muestra la forma de cada tipo, arranca por lo
  que más hace falta y pliega los colores de «Ahora» y las conexiones: de tres pantallas y media a menos de dos.
- La barra de arriba dice «1 grave · 6 avisos · 9 para revisar», como la consola, en vez de «7 problemas». Salud
  tiene una leyenda de colores, el primer grupo de tarjetas se titula y va de lo más grave a lo menos, y tocar la barra
  abre la tarjeta más grave. Los enlaces rotos son aviso, como en el médico.
- Cada tarjeta de Salud dice qué es al pasar el ratón y, al abrirla, qué hacer. Los nombres, con su singular («1
  Enlace roto»), y sin jerga: «Cómo trabajar» en vez de «Feedback», «Nombre para enlazar» en vez de «Slug», «Enlace
  [[…]]» en vez de «Wiki [[…]]». La consola usa los mismos nombres.
- «Lo que aprendió» ya no parece contradecirse: aclara que las listas son de todo lo aprendido y no de la semana, y
  dice «fuerte», «media» o «floja» en vez de un número suelto.
- En el tema claro, los verbos de «Ahora», sus cifras y el medidor de abajo se leen (antes, 1,6 a 1 de contraste);
  las filas viejas van en gris en vez de transparentes.
- Con el teclado, abrir una nota lleva el foco a su título y cerrarla lo devuelve; la barra de problemas lo lleva a
  la tarjeta que abrió.
- «Mi día» sin nada registrado lo dice sin preguntar antes si va con nombres. En modo anónimo, la barra de problemas
  se apaga y las notas se llaman «Nota 1», «Nota 2» (antes, «Proyecto 10», como los proyectos).
- En la demo ya no aparece un proyecto «Neuromapa» con el plan y los precios del negocio inventado.
- El README arranca con «Empezar en un minuto» y dice que hay que cerrar y volver a abrir Claude Code después de
  instalar.

Para que un error de tipeo o un archivo raro no rompa nada en silencio:

- En Mac y Linux, lo que dice el ítem siguiente de una lista («se borró», «temporal») ya no calla el aviso de una ruta
  que no existe. Para ver si el renglón ya lo aclaraba, el médico miraba 80 letras después de la ruta, y con las
  rutas cortas de esos sistemas llegaba al ítem de abajo. Ahora mira solo hasta el final del ítem o del párrafo.
- `neuromapa chequeo` (y `--chequeo`) revisa la instalación y dice qué falta en palabras simples: Python, la
  configuración, si encuentra notas, si los hooks están puestos (y no dos veces, ni apuntando a una carpeta que se
  movió), si el registro anota y Claude recibe la pista, el mapa, git, los permisos y Codex. No cambia nada ni muestra
  el contenido de `settings.json` ni de la configuración de Codex.

- El historial de la memoria guarda aunque cambien cientos de notas de una vez (un `--renombrar` grande, una
  reorganización). Antes, con unas 800, el mensaje de la versión pasaba el tope de la línea de comandos de Windows y
  no guardaba nunca más. `--salud` avisa si una carpeta lleva más de un día sin poder guardar.
- El médico encuentra cuándo cambió cada archivo que citan las notas aunque sean cientos, y también los que tienen
  tildes o eñes en el nombre.
- En `config.json`, un sí o no entre comillas (`"memoria": "false"`) o una lista escrita como texto ya no se toman
  mal: el error dice cuál es y cómo va. Antes `"false"` contaba como sí, y una carpeta de documentos podía pasar por
  memoria. Una clave mal escrita se avisa con la más parecida («¿quisiste decir `partir_sola`?»), y un archivo que no
  está en UTF-8 lo dice así.
- Una nota en UTF-16, o en UTF-8 con un byte roto, se lee bien y `--salud` lo avisa. Antes entraba como basura, y el
  médico decía, en falso, que no tenía encabezado.
- Si dos carpetas de una fuente no tienen alias, las notas que se llaman igual (dos `MEMORY.md`) ya no se pisan: antes
  la segunda desaparecía del mapa.
- Una carpeta sin permiso de lectura, o una nota con una fecha de archivo rara, ya no tumba el mapa: `--salud` las
  nombra y sigue con lo demás.
- Al escribir una nota (`--partir`, `--renombrar`, la pasada de cada día, `--aplicar`), lo escrito se fuerza al disco,
  un enlace duro o simbólico sigue siéndolo, y un Ctrl+C a mitad de camino deshace todo. `--renombrar` crea primero la
  nota con el nombre nuevo, así ningún enlace apunta a una que todavía no existe.
- Al juntar las historias de una nota en un renglón del índice, lo que decía el título de cada una queda en su pedazo.
- El tope de tiempo de cada llamada a git (en el médico y el historial, también desde los hooks), a Claude (en la
  pasada de cada día) y al armado del mapa corta de verdad en Windows. El `git.exe` de `Git\cmd` es un lanzador que
  arranca otro git: al pasarse el tiempo se cerraba solo el lanzador, y el programa se quedaba esperando al otro, sin
  tope. Ahora se cierra todo lo que arrancó (con 2 s de tope cortaba a los 20 s; ahora, a los 2).

## 0.1.5 — en prueba

Para que la pista encuentre la nota aunque se pregunte con otras palabras:

- Preguntas que responde cada nota: una nota puede decirlas en su encabezado, en una línea `preguntas:` (o
  `questions:`), y también cuentan las de las fichas de `--fichas`. En `--sobre` y en la pista, entre las notas que ya
  tienen que ver con el pedido sube la que dice responderlo. No agregan notas ni hacen aparecer una pista donde antes
  no había: eso se decide igual que antes. Con las notas del autor, todas con sus preguntas, la nota justa pasó a aparecer
  en 124 de 177 preguntas de prueba (antes 118, sin perder ninguna) y a salir primera en 88 (antes 83), con las
  mismas pistas en los pedidos ajenos. Si solo una parte de las notas tiene preguntas, esas les ganan a las demás.
  Se apaga con `"ordenar_con_preguntas": false` en el `config.json`. `--buscar` no cambia.

Para cuidar el índice de la memoria:

- El médico deja «para revisar» cada renglón de `MEMORY.md` de más de 220 letras que apunta a una sola nota (regla
  `ganchoLargo`), y cuando el índice se acerca a su tope de 25 KB nombra los tres renglones más largos. Ese archivo
  se carga entero al empezar cada charla: con renglones largos entran menos notas.

## 0.1.4 — en prueba

Para ordenar la memoria cuando crece:

- `--partir NOTA` y `--renombrar NOTA NUEVO`: para la nota que ya no entra en una lectura y para cambiarle el nombre a
  una sin dejar enlaces rotos. Muestran primero el plan y lo hacen recién con el código de ese plan (`--confirmar`);
  antes copian las notas como estaban a `respaldos/` y comprueban que no se pierda un renglón.
- `partir_sola` en el `config.json` (viene apagado): la pasada de cada día parte sola las memorias que están por
  llenarse, con ese mismo cuidado, lo anota en `respaldos/partidas.log` y se lo avisa a Claude. `--por-partir` dice qué
  haría y `--partir-llenas` lo hace en el momento. El médico avisa antes con la regla nueva «casi llena».
- Las notas de archivo se reconocen también por su descripción («(archivo) …»), no solo por el título del índice, y
  pesan apenas menos que las vigentes (0,95 en vez de 0,85), porque muchas guardan datos que siguen valiendo. El médico
  deja «para revisar» la que parece de archivo y no lo dice.
- Una memoria que el índice nombra en un renglón junto con otras («Historias: [1](…); [2](…)») toma el proyecto de su
  sección. Antes quedaba sin proyecto y la pista la ofrecía en chats de otro.
- [docs/obsidian.md](docs/obsidian.md): cómo abrir la memoria en Obsidian sin que los dos se pisen.

Para ver qué hay y qué falta:

- El mapa se puede pintar por proyecto: el botón «Grupos / Proyectos», la lista «Proyectos» y la ficha de cada nota.
  Cada proyecto puede llevar `nombre` y `color` en el `config.json`.
- `--pendientes`: junta lo que las memorias dicen que falta (probar, decidir, commit, hacer), con su nota, su renglón y
  su fecha. Solo lee.
- `--reglas` y `--regla NOTA`: proponen qué memorias convienen como regla por carpeta de Claude Code (`.claude/rules/`
  con `paths:`), que se carga sola al tocar un archivo de esa carpeta. `--recetas` y `--receta NOTA:N` hacen lo mismo
  con los tramos «Cómo se hace…», que pueden ser skills. Escriben recién con `--confirmar` y no pisan lo que no
  escribieron. El registro anota cuándo Claude Code carga una de esas reglas (su ruta, nunca su texto), y `--reglas`
  dice cuántas veces cargó cada una.

Para saber qué cambió:

- `--sobre "tema" --al 6/10` (y `--buscar`): responde con la memoria como estaba ese día, sacada del historial.
- `--cambios NOTA`: qué dato de una nota cambió y cuándo: qué decía antes y qué pasó a decir, sin contar lo que solo se
  mudó tal cual a otra nota. Sin nota, qué notas cambiaron en los últimos días.
- `--sobre`, por la consola, avisa debajo de lo que manda a leer si el renglón citado cambió y qué decía antes.

Arreglos:

- El médico ya no toma por commits las huellas de archivos de una lista («SHA OK (motor `…`, lanzador `…`)»).
- Lo aprendido del uso no guarda ni sugiere archivos temporales (`.tmp` o `.temp` en el nombre, `~$`, `.swp`).

## 0.1.3 — en prueba

- En Mac y Linux, el médico no encontraba el archivo de una cita con carpeta (`app/models/cosa.py:564`) cuando ese
  nombre de archivo existe en más de una carpeta: la daba «sin un archivo de código con ese nombre», y dar la carpeta
  dejaba peor que no darla. Ahora la carpeta elige el archivo justo, como en Windows. Lo reportó jroberto1386 en el
  [issue #1](https://github.com/lumiel777/neuromapa/issues/1), con la causa y cómo reproducirlo.

## 0.1.2 — en prueba

- En Windows con Python 3.10 a 3.12, lo aprendido a veces se volvía a repasar enseguida y el índice de búsqueda se
  podía rearmar dos veces seguidas: el reloj de esas versiones va a saltos y una marca recién puesta parecía estar
  unos milisegundos en el futuro. Ahora se acepta esa diferencia, y un reloj atrasado de verdad sigue sin trabar nada.
- Las pruebas de GitHub también corren solas cada lunes y con el botón «Run workflow».

## 0.1.1 — en prueba

- El mapa arranca sin preguntarle a la red el nombre de la computadora, que no usaba. En algunas Mac esa pregunta
  hacía esperar unos 35 segundos cada vez que se abría el mapa.
- Las pruebas automáticas de GitHub: Chrome tiene de nuevo 3 minutos para abrir la página. Si en una máquina de
  GitHub se cuelga igual, esa prueba se saltea con el motivo; en una computadora común sigue siendo una prueba. Además,
  el arranque doble tiene más tiempo en máquinas lentas, cada prueba se ve con su hora y todo se corta a los 30 minutos.

## 0.1.0 — en prueba

Primera versión, para los primeros probadores.

- El mapa en vivo: la memoria de Claude Code y tus `CLAUDE.md` como un cerebro 3D, con lo que hacen los chats y los
  agentes en este momento, la lista, el panel de salud y la copia «Sin notas» para mostrarlo sin enseñar nada. Con
  500 notas o más, la lista dibuja solo las filas que se ven, así abre y reordena al instante. Abajo, el río del tiempo:
  los últimos 10 minutos, una línea por chat, con lo que hizo, tus mensajes, sus agentes y la espera de tu OK.
- El médico (`/neuromapa:salud`): rutas y enlaces que ya no existen, anclas `archivo:línea` corridas, commits que no
  existen, problemas anotados que un commit posterior parece haber resuelto, cifras viejas cargadas en `hechos.json`,
  memorias sin índice, repetidas o que copian el `CLAUDE.md`, y un `MEMORY.md` que pasa lo que Claude lee al arrancar
  (200 líneas o 25 KB, lo que llegue antes). Un «para revisar» ya comprobado se calla con `--descartar-aviso` y vuelve
  solo si ese renglón cambia.
- Historial de la memoria (`--historial`): cada vez que la memoria cambia, al terminar una respuesta, guarda una
  versión con git en la carpeta de datos, sin tocar la carpeta de la memoria. Si un chat (o el ordenado automático de
  Claude Code) borra algo, `--historial "texto"` dice cuándo se borró y qué decía.
- Buscar en las charlas viejas (`--charlas "palabras"`): lo que se habló con Claude y nunca se anotó. Busca en el
  momento en lo que escribiste vos y lo que respondió Claude (nunca en lo que devolvieron las herramientas), sin
  guardar copia, y tapa lo que parece una clave. Si un pedido nombra algo dicho antes («lo que te dije», «como
  quedamos») y la memoria no tiene nada seguro, la pista sugiere buscar ahí y en el historial.
- El buscador (`/neuromapa:sobre`): qué se sabe de un tema, qué leer primero, las decisiones anotadas que lo tocan y
  el código que esas notas citan para comprobarlo (con la línea y la función, aunque la nota no ponga la línea, si
  escribe al lado con qué buscarla), en español y en inglés, con los datos viejos marcados. En las notas largas sin
  títulos busca por pasajes, así un dato del medio no se pierde entre el resto. Una nota con un dato viejo comprobado
  (una ruta que ya no existe, una cifra o un commit) pasa detrás de las limpias, con su ⚠.
- Revisar al guardar: si Claude corrige un dato en una nota («92 de 111» → «93 de 111») y otra nota todavía dice el de
  antes, se lo avisa en el momento, con la nota y la línea.
- Dormir: una vez por día, con el primer pedido, repasa las notas de fondo y propone arreglos (líneas de código
  corridas, cifras viejas), sin tocarlas; Claude te avisa una vez y se aplican solo los que apruebes
  (`--propuestas`, `--aplicar`, `--descartar`). Con `dormir_con_claude` (apagado de fábrica, con tope de gasto por
  día) también le pregunta a Claude si lo que parece resuelto lo está de verdad, con una línea del código de hoy como
  prueba, y qué notas se contradicen.
- Fichas (`--fichas USD`, con tope de gasto): Claude arma una ficha por nota con otras formas de nombrar lo que dice y
  las preguntas que responde, así el buscador la encuentra aunque la busques con otras palabras. Solo se rehacen las
  de las notas que cambian; nunca toca las notas.
- Por qué eligió cada nota: los rayos de la pista salen de un color según el motivo (las palabras del pedido, un índice
  que la nombra o lo aprendido), la fila de «Ahora» lo resume y el panel de la nota dice por qué y en qué renglones.
  El registro guarda solo el motivo, los números de renglón y las rutas, nunca el texto del pedido.
- Modo de comparación (`comparar_aprendido`, apagado de fábrica): una parte de los pedidos va sin lo aprendido y
  `--aprendido` compara cuántas pistas sirvieron con y sin, para saber si aprender del uso ayuda de verdad.
- La primera vez que se abre Claude Code después de instalarlo, avisa que quedó instalado y cómo abrir el mapa.
- Aprende del uso, en tu computadora: qué archivos se abren juntos (se refuerza con la repetición y se olvida a la mitad
  cada 14 días) y si las notas que recomendó se leyeron. Con eso la pista suma código y notas, y el mapa engrosa las
  conexiones que más se usan (los pulsos corren más rápido por ellas, saltando de cuenta en cuenta), muestra las
  conexiones «Aprendida» y el bloque «Lo que aprendió», que se ve aprender en vivo: el camino que recorre un chat se
  ilumina y los caminos nacen, se engrosan y se apagan sin recargar la página. Lee una vez las charlas guardadas
  de antes (solo rutas) y las usa de respaldo. No sugiere código de un proyecto donde ese chat casi nunca trabaja, ni a
  partir de un `CLAUDE.md` o un `MEMORY.md`, y lo que la pista misma sugirió cuenta la mitad, para que no se refuerce
  solo. De los agentes no une notas con notas, y no aprende acciones que fallaron ni archivos de librerías o
  generados. `--aprendido` lo cuenta (con un archivo, con qué se usa ese), `--olvidar` borra una unión o todo lo de
  un archivo sin que vuelva al rearmar, y `"aprender": false` lo apaga.
- Avisos automáticos a Claude: memoria parecida a otra, dos chats editando el mismo archivo, rutas y enlaces rotos al
  escribirlos y problemas nuevos en tus notas. Con el contexto automático prendido, al editar un archivo de código le
  recuerda la nota que se suele leer con él (de lo aprendido), una vez por archivo y por chat, si todavía no la leyó.
  Y le recuerda guardar: al volver de compactar, que pase a la memoria lo decidido que todavía no esté escrito (si no,
  se pierde en la próxima compactación); al terminar una respuesta, si cambió 5 archivos o hizo un commit sin escribir
  nada en sus notas, una vez cada 15 minutos como mucho. El mapa lo muestra como «guardar».
- `--choques`, `--gasto` y el freno de agentes, `--lecciones`, `--aprendido`, `--proponer-hechos`, `--entidad`, `--mapa`.
- Un conector opcional para el modo Chat de la app de escritorio de Claude (`conector_mcp.py`, se registra a mano en
  `claude_desktop_config.json`): esas charlas pueden consultar y leer tus notas, en solo lectura, y se ven en el mapa
  como «Chat de la app»; nunca guarda lo que se preguntó.
- Anda con Git Bash y con PowerShell, en Windows y en Linux; sin internet (d3 y marked vienen adentro). Con 10.000
  notas, el mapa se arma en ~20 s; sin el mapa abierto, la pista no se traba armando el índice (lo arma de fondo).
- Seguridad: lo que guarda en la carpeta de datos son solo datos (el índice de búsqueda va en JSON, no en un formato
  que pueda correr código al cargarse); las carpetas que crea nacen cerradas para tu cuenta y `--salud` avisa si otra
  cuenta de la PC puede escribir en la carpeta de datos o en la del programa. El hook no le manda la clave al mapa: el
  mapa primero demuestra que la sabe y el pedido va firmado. El navegador entra con un número de un solo uso y queda
  con una galleta propia: la clave no queda en el historial ni en la galleta.
