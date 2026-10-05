---
description: Revisa la salud de la memoria y de las notas (rutas que ya no existen, anclas corridas, cifras viejas, notas que nadie nombra, memorias repetidas). Usalo después de guardar o cambiar notas, y cuando el usuario pida revisar la memoria.
allowed-tools:
  - Bash(neuromapa --salud*)
  - Bash(sh "${CLAUDE_PLUGIN_ROOT}/bin/neuromapa" --salud*)
  - PowerShell(neuromapa --salud*)
  - PowerShell(& "${CLAUDE_PLUGIN_ROOT}/bin/neuromapa.cmd" --salud*)
---

Revisá la memoria con el médico de Neuromapa:

```
neuromapa --salud
```

Si la consola no encuentra `neuromapa`, corré `sh "${CLAUDE_PLUGIN_ROOT}/bin/neuromapa" --salud`, o en PowerShell
`& "${CLAUDE_PLUGIN_ROOT}/bin/neuromapa.cmd" --salud`.

Qué hacer con lo que marca:

- **En la memoria** (las notas de `~/.claude/projects/*/memory/`): arreglalo vos, verificando antes contra el disco o
  git que el dato nuevo es el correcto.
- **En archivos de un proyecto** (CLAUDE.md, documentación): arreglalo si lo rompiste en esta charla; si no, contale al
  usuario qué marca y preguntale antes de tocarlo.
- Los «para revisar» son datos que pueden haber quedado viejos: no son urgentes. Si comprobás uno contra el código o
  git y la nota está bien como está, proponele al usuario callarlo con `neuromapa --descartar-aviso RUTA:LÍNEA
  --motivo "por qué"`; con su OK, corrélo (vuelve solo si ese renglón cambia, y `--descartados` los lista).

Al terminar, resumí en pocas líneas qué arreglaste y qué quedó para el usuario.
