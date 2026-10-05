---
name: mercadopago-avisos-repetidos
description: Mercado Pago manda el mismo aviso de pago varias veces: se procesa una sola vez por id de pago
metadata:
  node_type: memory
  type: project
---

Mercado Pago reintenta el webhook cuando la respuesta tarda o falla, y a veces manda el mismo aviso de pago dos o tres
veces aunque haya salido bien. Si cada aviso se procesa, el mismo pago aprobado descuenta el stock dos veces y la
venta aparece duplicada en la caja.

La regla: cada pago se procesa **una sola vez por su id**. El id del pago se guarda antes de tocar el stock, con una
restricción única en la tabla de pagos; si el id ya estaba, el aviso se contesta con 200 y no se hace nada más.

Contestar siempre rápido (menos de cinco segundos) y dejar el trabajo pesado para después: si Mercado Pago no recibe
el 200 a tiempo, vuelve a mandar el aviso. El flujo completo del pago está en [[ventas-mercadopago]].
