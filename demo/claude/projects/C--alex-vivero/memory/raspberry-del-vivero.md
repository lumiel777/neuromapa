---
name: raspberry-del-vivero
description: La Raspberry que maneja el riego: dónde está, cómo entrar por la VPN y dónde mirar los logs
metadata:
  node_type: memory
  type: reference
---

La Raspberry está en el galpón, en la caja estanca al lado del tablero de la bomba. Corre el programador de riego
([[riego-programador]]) y manda las lecturas de los sensores a la API cada cinco minutos.

- Se entra por la VPN del vivero; el usuario y la clave los tiene Alex, no van en notas.
- El servicio se llama `riego` y sus logs se miran con journalctl.
- Si se corta internet, sigue regando sola con lo último que sabe y sube las lecturas cuando vuelve.

Cómo se instala desde cero: `docs/DESPLIEGUE.md`.
