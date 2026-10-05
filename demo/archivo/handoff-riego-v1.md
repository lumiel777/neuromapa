# Traspaso: riego por horario (v1)

Notas del traspaso de abril de 2025, cuando el riego todavía era por horario fijo. Ya no se usa: el riego decide por
humedad desde agosto de 2025.

- El horario estaba en `config/horarios-riego.json`: dos turnos por día en verano, uno en invierno.
- La bomba se prendía con un relé en el pin 17 de la Raspberry.
- Los detalles por estación estaban en `docs/riego-v1.md`.
- Problema conocido de entonces: regaba igual con lluvia. Se resolvió con los sensores.
