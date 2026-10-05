---
name: stock-plantas
description: Stock de plantas: tabla stock_plantas, los 3 estados de una planta y las alertas de stock bajo
metadata:
  node_type: memory
  type: project
---

El stock vive en la tabla `stock_plantas` (una fila por especie y tamaño de maceta) y cada cambio queda en
`stock_movimientos`, con el motivo: venta, pérdida, compra o ajuste de inventario.

Una planta pasa por 4 estados: **en producción** (plantín, todavía no se vende), **a la venta**, **reservada** (pagada
por la web, sin retirar) y **vendida**. Las reservadas no cuentan como disponibles.

**Descontar.** Toda venta pasa por `StockRepositorio.cs:15` (`DescontarStock`), que descuenta dentro de una
transacción y solo si alcanza. Antes no era así: ver [[arreglo-stock-negativo]].

**Alertas.** Cada especie tiene su mínimo; cuando el disponible baja de ahí, se manda un aviso ([[avisos-whatsapp]]).
Marta ajusta los mínimos desde el panel.
