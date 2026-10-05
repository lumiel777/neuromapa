# ADR-002: el riego lo decide una Raspberry en el vivero

**Estado:** aceptada (abril de 2025).

## Contexto

En el vivero, internet se corta varias veces por mes, a veces por horas. Un riego que depende de la VPS no riega
cuando más hace falta: los días de tormenta con viento, que cortan la luz y el cable.

## Decisión

El programador de riego corre en una Raspberry en el galpón, con los sensores conectados directo. La VPS solo recibe
las lecturas y muestra el estado en el panel.

## Consecuencias

- El riego sigue andando sin internet. El algoritmo está en [RIEGO.md](../RIEGO.md).
- Actualizar el programador pide entrar por la VPN.
- La Raspberry necesita guardar en disco lo que ya regó, por si se corta la luz.
