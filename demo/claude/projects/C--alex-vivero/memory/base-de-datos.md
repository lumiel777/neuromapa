---
name: base-de-datos
description: Base de datos
metadata:
  node_type: memory
  type: reference
---

La base es **SQLite**, un solo archivo en la VPS de la API. Alcanza de sobra para el volumen del vivero y se respalda
copiando un archivo (por qué SQLite y no otra: ADR-001-sqlite.md, en las decisiones del proyecto).

- Migraciones con el comando de migraciones de la API; nunca a mano en producción.
- Respaldo cada noche a las 3, con siete días de historia, más una copia semanal fuera de la VPS.
- Antes de migrar en producción: respaldo manual y avisar a Alex.

Cada tabla, con sus columnas, está en MODELO-DE-DATOS.md.
