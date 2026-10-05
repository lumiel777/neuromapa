---
description: Abre el mapa en vivo de Neuromapa en el navegador (el cerebro 3D de las notas, con lo que hacen los chats y los agentes en este momento).
argument-hint: "[--demo] [--reiniciar]"
disable-model-invocation: true
allowed-tools:
  - Bash(neuromapa abrir*)
  - Bash(sh "${CLAUDE_PLUGIN_ROOT}/bin/neuromapa" abrir*)
  - PowerShell(neuromapa abrir*)
  - PowerShell(& "${CLAUDE_PLUGIN_ROOT}/bin/neuromapa.cmd" abrir*)
---

Levantá el mapa en vivo **en segundo plano** (con `run_in_background`, porque el servidor queda prendido):

```
neuromapa abrir $ARGUMENTS
```

Con `--demo` muestra las notas inventadas que trae el plugin, en vez de las del usuario. Con `--reiniciar` apaga el
mapa que estaba prendido y arranca uno nuevo: hace falta después de actualizar el plugin o de cambiar el `config.json`,
porque el servidor que sigue prendido tiene la versión y la configuración de cuando arrancó.

Si la consola no encuentra `neuromapa`, corré `sh "${CLAUDE_PLUGIN_ROOT}/bin/neuromapa" abrir $ARGUMENTS`, o en
PowerShell `& "${CLAUDE_PLUGIN_ROOT}/bin/neuromapa.cmd" abrir $ARGUMENTS`.

El servidor arma la página y la manda a abrir en el navegador con la clave puesta; en la consola imprime la dirección
sin la clave y dice en qué archivo está. **No leas ni copies la clave en tu respuesta.** Contale al usuario lo que dijo
la consola: que el mapa se abrió en su navegador o, si dice «No pude abrir el navegador», la dirección y el archivo de
la clave para que lo abra él. Se apaga solo 10 minutos después de cerrar la última pestaña. Si dice «ya estaba
prendido», se abrió el mismo de antes y el comando termina enseguida (con `--reiniciar` no lo reusa).

Si falla porque no hay Python, decile que instale Python 3.10 o más nuevo desde https://www.python.org/downloads/.
