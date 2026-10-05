# vivero — instrucciones para Claude

Sistema del Vivero Las Glicinas: stock de plantas, ventas por la web con Mercado Pago, avisos por WhatsApp y el
programador de riego que corre en una Raspberry en el vivero. El contexto (cliente, reglas, arreglos) está en la
memoria.

## Cómo está armado
- `src/Vivero.Api`: la API (ASP.NET Core, minimal API). La API tiene **5 módulos**, uno por archivo en
  `src/Vivero.Api/Modulos`: plantas, stock, ventas, riego y webhooks.
- `src/Vivero.Riego`: el programador de riego y los sensores. Corre en la Raspberry, no en la VPS.
- `src/Vivero.Datos`: acceso a la base (SQLite).

## Comandos
- Compilar: `dotnet build`. Pruebas: `dotnet test`.
- Levantar la API local: `dotnet run --project src/Vivero.Api`.

## Reglas
- Nada contra la base de producción sin respaldo previo y sin el OK de Alex.
- El riego se prueba primero en la zona del cantero de afuera; el invernadero, al final.
- Credenciales (Mercado Pago, WhatsApp, VPN): en variables de entorno. Nunca en el repo ni en notas.

## Documentos
- [Arquitectura](docs/ARQUITECTURA.md) — capas, carpetas y el recorrido de una venta.
- [Riego](docs/RIEGO.md) — el algoritmo del programador, con los umbrales y su porqué.
- [API](docs/API.md) — cada endpoint, qué recibe y qué devuelve.
- [Modelo de datos](docs/MODELO-DE-DATOS.md) — tablas y relaciones.
- [Despliegue](docs/DESPLIEGUE.md) — la VPS de la API y la Raspberry del riego.
- [Guía de sensores](docs/GUIA-SENSORES.md) — cableado y calibración.
- [Manual para Marta](docs/MANUAL-MARTA.md) — cómo usa el panel la dueña.
- Decisiones: [SQLite](docs/decisiones/ADR-001-sqlite.md), [Raspberry](docs/decisiones/ADR-002-raspberry.md),
  [Mercado Pago](docs/decisiones/ADR-003-mercadopago.md).
- [Plan inicial](docs/viejo/PLAN-INICIAL.md) — el de 2025, para ver de dónde venimos.
