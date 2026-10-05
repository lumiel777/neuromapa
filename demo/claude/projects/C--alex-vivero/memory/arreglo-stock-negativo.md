---
name: arreglo-stock-negativo
description: Arreglo: dos ventas al mismo tiempo de la última planta dejaban el stock en menos uno
metadata:
  node_type: memory
  type: project
---

**Qué pasaba.** Un sábado se vendió dos veces el último jazmín: una venta en el mostrador y otra por la web, con
segundos de diferencia. El stock quedó en menos uno.

**Por qué.** El código leía el stock, comprobaba que alcanzara y después descontaba, en dos pasos separados. Entre uno y
otro entraba la otra venta.

**El arreglo.** Un solo `UPDATE` que descuenta solo si alcanza, dentro de una transacción (ver [[stock-plantas]]).
Si no alcanza, la venta se rechaza y el cliente de la web ve «sin stock». Arreglado en el commit `4e7a1c9`.

Probado con dos ventas simultáneas desde dos terminales: una pasa y la otra da «sin stock».
