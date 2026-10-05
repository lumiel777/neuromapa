# Migrar el vivero a PostgreSQL (descartado)

En septiembre de 2025, después de que trailbot pasó a PostgreSQL, se evaluó hacer lo mismo con el vivero.

Se descartó:
- El vivero tiene una sola caja y una sola escritura a la vez alcanza.
- Con SQLite, respaldar y restaurar es copiar un archivo; Marta no paga un servicio más.
- Los problemas de concurrencia que hubo (el stock negativo) se resolvieron con una transacción corta, no con otra
  base.

Volver a pensarlo si abre una segunda sucursal con su propia caja.
