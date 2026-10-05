---
name: arreglo-webhook-duplicado
description: Compras de la web registradas por duplicado porque Mercado Pago reenvía avisos ya entregados; ahora cada pago cuenta una vez
metadata:
  node_type: memory
  type: project
---

**Síntoma.** Algunas compras de la web figuraban duplicadas en la caja y restaban stock de más.

**Causa.** Mercado Pago reintenta el webhook cuando la respuesta demora y, a veces, reenvía un aviso de pago que ya
había entregado. El código trataba cada aviso como un pago nuevo.

**Solución.** El id del pago se guarda con una restricción única antes de tocar el stock; si ya estaba, el webhook
responde 200 y listo. Además responde enseguida y deja lo pesado para más tarde, así Mercado Pago no reintenta.

Comprobado reenviando diez veces un aviso desde el panel de pruebas de Mercado Pago: quedó una sola compra.
