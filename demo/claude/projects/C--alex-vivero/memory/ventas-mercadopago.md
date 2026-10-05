---
name: ventas-mercadopago
description: Ventas por la web con Mercado Pago: checkout, webhook, estados del pago y qué pasa con el stock en cada uno
metadata:
  node_type: memory
  type: project
---

La web vende con el checkout de Mercado Pago. El flujo:

1. El cliente arma el carrito; al pagar, la planta queda **reservada** ([[stock-plantas]]).
2. Mercado Pago avisa por webhook a `/webhooks/mercadopago` cuando cambia el estado del pago.
3. Con el pago **aprobado**, la reserva pasa a vendida; con **rechazado** o **vencido** (48 horas sin pagar), la
   planta vuelve a estar a la venta.

Las credenciales van en variables de entorno de la API, nunca en el repo ni en una nota.

Mercado Pago puede mandar el mismo aviso más de una vez: por eso cada pago se procesa una sola vez, por su id. Lo que
pasó cuando no era así: [[arreglo-webhook-duplicado]].
