# API del vivero

Todas las rutas devuelven JSON. Las del panel piden sesión; los webhooks se validan con la firma del proveedor.

| Método | Ruta | Módulo | Qué hace |
|---|---|---|---|
| GET | `/plantas` | Plantas | Catálogo con precio y disponible |
| GET | `/plantas/{id}` | Plantas | Una planta, con fotos |
| GET | `/stock/{id}` | Stock | Cantidad disponible de una planta |
| GET | `/stock/bajo` | Stock | Especies por debajo de su mínimo |
| POST | `/ventas` | Ventas | Cobra una venta y reserva el stock |
| GET | `/ventas/hoy` | Ventas | Ventas del día, para la caja |
| GET | `/riego/turnos` | Riego | Turnos de hoy, con minutos por zona |
| POST | `/riego/lecturas` | Riego | Lecturas de la Raspberry |
| POST | `/webhooks/mercadopago` | Webhooks | Avisos de pago de Mercado Pago |
| GET | `/avisos/hoy` | Avisos | Mensajes de WhatsApp enviados hoy |

Cada módulo es un archivo en `src/Vivero.Api/Modulos`. El recorrido de una venta, paso a paso, está en
[ARQUITECTURA.md](ARQUITECTURA.md).
