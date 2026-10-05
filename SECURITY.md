# Seguridad · Security

**Si encontrás una falla de seguridad, no abras un issue público.** Reportala en privado desde la pestaña
**Security → Report a vulnerability** de este repositorio. Contestamos lo antes posible y avisamos cuando esté arreglada.

**If you find a security problem, please don't open a public issue.** Report it privately from this repository's
**Security → Report a vulnerability** tab. We answer as soon as we can and let you know when it is fixed.

## Qué importa especialmente · What matters most

- Los hooks corren en cada acción de Claude Code: cualquier forma de que ejecuten algo que no deben, o de que guarden
  el texto de mensajes, comandos, búsquedas o direcciones web completas.
- El servidor local del mapa (`servidor.py`): acceso sin la clave, desde otro sitio web o desde otra máquina.
- La página: que una nota pueda ejecutar código al mostrarse.

- The hooks run on every Claude Code action: any way to make them run something they shouldn't, or store the text of
  messages, commands, searches or full web addresses.
- The local map server (`servidor.py`): access without the key, from another website or from another machine.
- The page: a note being able to run code when displayed.

## Versiones · Versions

Solo la última versión recibe arreglos. · Only the latest version gets fixes.
