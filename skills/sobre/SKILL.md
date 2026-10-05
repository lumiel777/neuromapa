---
description: Busca en la memoria y en las notas del proyecto qué se sabe de un tema, dice qué leer primero y avisa los datos viejos. Usalo antes de empezar una tarea sobre algo que puede estar anotado, y cuando el usuario pregunte qué se sabía de un tema.
argument-hint: "[tema]"
allowed-tools:
  - Bash(neuromapa --sobre*)
  - Bash(sh "${CLAUDE_PLUGIN_ROOT}/bin/neuromapa" --sobre*)
  - PowerShell(neuromapa --sobre*)
  - PowerShell(& "${CLAUDE_PLUGIN_ROOT}/bin/neuromapa.cmd" --sobre*)
---

Buscá el tema en las notas con Neuromapa:

```
neuromapa --sobre "$ARGUMENTS"
```

Si la consola no encuentra `neuromapa`, corré `sh "${CLAUDE_PLUGIN_ROOT}/bin/neuromapa" --sobre "$ARGUMENTS"`, o en PowerShell
`& "${CLAUDE_PLUGIN_ROOT}/bin/neuromapa.cmd" --sobre "$ARGUMENTS"`.

Cómo usar lo que devuelve:

- **Para leer primero:** abrí esas notas con Read desde la línea que indica, antes de tocar nada.
- **⚠ dato viejo:** el médico comprobó que ese dato ya no vale y dice el actual. Usá el actual y, si importa, confirmalo
  en el código.
- **⚠ puede que ya esté resuelto:** un commit posterior toca lo mismo que ese renglón, pero nadie lo comprobó. Mirá el
  código antes de dar el dato por bueno o por viejo.
- **Para comprobar en el código:** son los archivos que nombran esas notas, con la ruta entera. Abrí el que venga al
  caso; si ninguno es, seguí buscando.
- Si no encontró nada, decilo en una línea y seguí con la tarea.
- Si el usuario se acuerda de algo anotado que ya no aparece, puede haberse borrado: `neuromapa --historial "texto"`
  dice cuándo se borró, de qué nota y qué decía.
- Si se acuerda de algo que se habló en una charla pero nunca se anotó, `neuromapa --charlas "palabras"` lo busca en
  las charlas viejas (lo que escribió el usuario y lo que respondió Claude).

No copies en tu respuesta el texto entero de la salida: usalo para trabajar.
