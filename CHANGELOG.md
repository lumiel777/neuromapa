# Cambios

Las versiones siguen el número de `.claude-plugin/plugin.json` (`claude plugin list` lo muestra, y Claude lo ve con `neuromapa --version`). Cada versión que
sale sube ese número; si no, la actualización puede no traer nada (ver [CONTRIBUTING.md](CONTRIBUTING.md)).

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
