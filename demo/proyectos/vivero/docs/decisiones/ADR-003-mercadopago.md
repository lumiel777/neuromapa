# ADR-003: cobrar con Mercado Pago

**Estado:** aceptada (junio de 2025).

## Contexto

Los clientes del vivero son de la zona y pagan con tarjeta en cuotas o con dinero en la cuenta. Marta ya usa Mercado
Pago en el mostrador.

## Decisión

La web cobra con el checkout de Mercado Pago y recibe el resultado por webhook.

## Consecuencias

- El webhook tiene que ser idempotente: el mismo aviso puede llegar varias veces. Cada pago se procesa una sola vez
  por su id (tabla `pagos` en [MODELO-DE-DATOS.md](../MODELO-DE-DATOS.md)).
- El webhook contesta en menos de cinco segundos; lo pesado va después.
- Las ventas de la web y del mostrador quedan en el mismo lugar para Marta.
