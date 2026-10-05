---
name: riego-sensores
description: Sensores de humedad del riego: calibración (seco 820, mojado 390), lecturas raras y qué hacer cuando uno se muere
metadata:
  node_type: memory
  type: project
---

Cada zona tiene un sensor capacitivo conectado a la Raspberry. `Sensor.cs:27` (`EstaMuerto`) da por muerto un sensor
que no manda datos hace más de 90 minutos; el programador ([[riego-programador]]) pasa esa zona a riego a ciegas.

**Calibración.** La lectura cruda va de 820 (seco al aire) a 390 (en un vaso de agua). Si se cambia un sensor, hay
que medir esos dos puntos de nuevo: cada sensor viene un poco distinto. Cómo cablearlos y calibrarlos, paso a paso:
`docs/GUIA-SENSORES.md`.

**Lecturas raras.** Un salto de 30 puntos en un minuto casi siempre es el cable flojo, no la tierra. El sensor del
invernadero se moja con el rocío de la mañana: sus lecturas antes de las siete no se usan.

Los sensores se compran a un proveedor de Córdoba: [[sensores-proveedor]].
