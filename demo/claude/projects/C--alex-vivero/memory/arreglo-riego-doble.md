---
name: arreglo-riego-doble
description: Arreglo: después de un corte de luz, la zona del invernadero regaba dos veces el mismo día
metadata:
  node_type: memory
  type: project
---

**Qué pasaba.** Después de un corte de luz, la Raspberry arrancaba sin saber que esa mañana ya había regado, y la zona
del invernadero regaba de nuevo. Dos veces en un día de calor está bien; en un día nublado, los plantines se pudren.

**Por qué.** El registro de riegos vivía en memoria y se perdía con el corte.

**El arreglo.** Cada riego se anota en disco al terminar, y el programador pregunta `YaRegoHoy` antes de decidir
(ver [[riego-programador]]).

Probado el 12/9 con un corte de luz de verdad: se bajó la térmica a las 7:30, después del turno del invernadero, y al
volver no regó de nuevo.
