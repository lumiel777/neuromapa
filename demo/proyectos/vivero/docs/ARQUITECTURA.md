# Arquitectura del sistema del vivero

## Las tres piezas

| Proyecto | Dónde corre | Qué hace |
|---|---|---|
| `src/Vivero.Api` | VPS | API para la web, el panel de Marta y los webhooks |
| `src/Vivero.Riego` | Raspberry en el vivero | Programador de riego y lectura de sensores |
| `src/Vivero.Datos` | Las dos | Acceso a la base SQLite |

El riego corre en el vivero y no en la VPS a propósito: si se corta internet, las plantas tienen que seguir regándose
(ver [ADR-002](decisiones/ADR-002-raspberry.md)).

## El recorrido de una venta por la web

1. El cliente paga: `POST /ventas` llama a `Caja.Cobrar`, que reserva la planta con
   `StockRepositorio.DescontarStock` (descuenta solo si alcanza, en una transacción).
2. La API crea la preferencia de pago y el cliente va al checkout de Mercado Pago.
3. Mercado Pago avisa a `POST /webhooks/mercadopago`. El pago se procesa una sola vez por su id.
4. Con el pago aprobado, la reserva pasa a vendida y queda un movimiento en `stock_movimientos`.

Cada endpoint está en [API.md](API.md) y cada tabla en [MODELO-DE-DATOS.md](MODELO-DE-DATOS.md).

## El riego, en una línea

La Raspberry lee los sensores cada cinco minutos, se las manda a la API (`POST /riego/lecturas`) y decide sola cuándo
regar cada zona. El algoritmo completo: [RIEGO.md](RIEGO.md).
