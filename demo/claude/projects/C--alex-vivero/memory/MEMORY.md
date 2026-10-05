# Memoria del vivero

Memoria de los chats que arrancan en `proyectos/vivero`. La de trailbot es otra carpeta.

## Alex y cómo trabajar
- [Perfil de Alex](perfil-alex.md) — freelance en Rosario; explicaciones cortas, con archivo y línea; aprueba antes de tocar la base
- [Commits chicos](commits-chicos.md) — un commit por cambio, mensaje en español con el porqué
- [Probar antes de decir «listo»](probar-antes.md) — `dotnet test` y una prueba a mano; si no se pudo probar, decirlo así

## Cliente y negocio
- [Vivero Las Glicinas](cliente-glicinas.md) — Marta, la dueña: riego, stock y ventas del fin de semana; habla por WhatsApp
- [Temporada alta](temporada-alta.md) — de septiembre a diciembre; nada de cambios grandes un viernes

## El sistema
- [Programador de riego](riego-programador.md) — cuatro zonas, cuándo riega y cuánto; la decisión vive en `Programador.cs`
- [Sensores de humedad](riego-sensores.md) — calibración, lecturas raras y qué hacer si un sensor se muere
- [Stock de plantas](stock-plantas.md) — tabla `stock_plantas`, movimientos y alertas de stock bajo
- [Ventas con Mercado Pago](ventas-mercadopago.md) — checkout, webhook y estados del pago
- [Avisos repetidos de Mercado Pago](mercadopago-avisos-repetidos.md) — el mismo aviso de pago llega varias veces
- [Avisos por WhatsApp](avisos-whatsapp.md) — stock bajo y riego fallido, con tope diario para no molestar a Marta
- [Base de datos](base-de-datos.md) — SQLite, migraciones y respaldo de cada noche
- [La Raspberry del vivero](raspberry-del-vivero.md) — dónde está, cómo entrar y dónde mirar los logs del riego

## Arreglos
- [Arreglo: riego doble](arreglo-riego-doble.md) — la zona del invernadero regaba dos veces después de un corte de luz
- [Arreglo: stock negativo](arreglo-stock-negativo.md) — dos ventas al mismo tiempo dejaban el stock en menos uno
- [Arreglo: webhook duplicado](arreglo-webhook-duplicado.md) — pagos contados dos veces por avisos repetidos
- [Arreglo: horario de verano](arreglo-horario-verano.md) — DST

## Pendientes
- [Pendientes](pendientes.md) — lo que falta, en orden; leer antes de proponer algo nuevo
