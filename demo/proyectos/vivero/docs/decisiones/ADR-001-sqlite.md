# ADR-001: SQLite en vez de un servidor de base de datos

**Estado:** aceptada (marzo de 2025).

## Contexto

El vivero tiene unas trescientas especies, unas cuarenta ventas por día en temporada y una lectura de sensor cada
cinco minutos por zona. Alex mantiene el sistema solo y cobra un abono mensual chico.

## Decisión

Usar SQLite: un archivo en la VPS de la API.

## Consecuencias

- Respaldar es copiar un archivo, y restaurar también.
- Una sola escritura a la vez: alcanza para este volumen, pero las ventas tienen que descontar stock en una
  transacción corta (ver [MODELO-DE-DATOS.md](../MODELO-DE-DATOS.md)).
- Si el vivero abre otra sucursal con otra caja, revisar esta decisión.
