---
name: riego-programador
description: Cómo decide el programador de riego: cuatro zonas, humedad mínima, lluvia reciente y tope de minutos
metadata:
  node_type: memory
  type: project
---

El programador corre en la Raspberry del vivero ([[raspberry-del-vivero]]) y maneja **cuatro zonas**: invernadero,
cantero de afuera, macetas grandes y plantines de estación. Cada zona tiene un sensor de humedad
([[riego-sensores]]).

**Cuándo riega.** La decisión está en `Programador.cs:36` (`DebeRegar`):
- si la zona ya regó hoy, no;
- si llovió en las últimas doce horas, no;
- si la humedad está por debajo de la mínima (35), sí;
- si el sensor está muerto, riega una vez por día a ciegas, para no perder plantas.

**Cuánto riega.** `Programador.cs:30` (`CalcularDuracion`): dos minutos por cada punto que falta para llegar a 60 de
humedad, con tope de 45 minutos por turno.

**A qué hora.** Temprano, desde las seis, una zona cada veinte minutos para que la bomba no pierda presión.

El detalle, con los umbrales y el porqué de cada uno, está en `docs/RIEGO.md`. Los arreglos de este código:
[[arreglo-riego-doble]] y [[arreglo-horario-verano]].
