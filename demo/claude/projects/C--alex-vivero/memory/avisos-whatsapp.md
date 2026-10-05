---
name: avisos-whatsapp
description: Avisos a Marta por WhatsApp: stock bajo y riego fallido, con tope diario y horario para no molestar
metadata:
  node_type: memory
  type: project
---

El sistema le escribe a Marta por WhatsApp en dos casos:

- **Stock bajo:** una especie bajó de su mínimo ([[stock-plantas]]).
- **Riego fallido:** una zona no regó cuando tenía que regar, o un sensor se murió ([[riego-sensores]]).

Reglas para no molestar:
- tope de 5 avisos por día; los que sobran se juntan en un resumen a las 19;
- nada entre las 22 y las 7, salvo el riego fallido del invernadero en verano;
- un aviso por especie por día, aunque siga bajando.

El envío pasa por un servicio de mensajería con plantilla aprobada. La plantilla está en el panel del servicio, no en
el repo.
