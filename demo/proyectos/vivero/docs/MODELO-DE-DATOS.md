# Modelo de datos

Base SQLite, un solo archivo. Por qué SQLite: [ADR-001](decisiones/ADR-001-sqlite.md).

## Stock

- `stock_plantas`: una fila por especie y tamaño de maceta. Columnas: `id`, `especie`, `tamano`, `cantidad`,
  `minimo`, `precio`.
- `stock_movimientos`: cada cambio de stock, con `planta_id`, `cantidad` (negativa si sale), `motivo` y fecha. Nunca
  se borra: es la historia para el inventario.

## Ventas

- `ventas`: una fila por venta, con canal (mostrador o web) y estado (reservada, vendida, anulada).
- `pagos`: un pago de Mercado Pago por fila; `id_pago` tiene restricción única, y así un aviso repetido no se
  procesa dos veces.

## Riego

- `riego_lecturas`: zona, humedad (0 a 100) y hora de cada lectura.
- `riego_turnos`: cada riego, con zona, hora de inicio y minutos. El programador lo consulta para saber si ya regó
  hoy.
