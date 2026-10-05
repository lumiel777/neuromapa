---
name: arreglo-horario-verano
description: Arreglo: el cambio de horario corría los turnos de riego una hora; ahora se calcula todo en hora local
metadata:
  node_type: memory
  type: project
---

**Qué pasaba.** El día del cambio de horario, los turnos de riego se corrieron una hora y el invernadero regó a pleno
sol.

**Por qué.** El programador mezclaba la hora de la Raspberry (UTC) con la hora local del vivero.

**El arreglo.** Todo el cálculo de turnos usa la hora local de Argentina, que hoy no tiene cambio de horario; si
vuelve a tenerlo, alcanza con actualizar la zona horaria del sistema. Ver [[riego-programador]].
