# Demo de Neuromapa

Notas inventadas para ver Neuromapa andando sin usar las tuyas. Son de «Alex», que tiene dos proyectos de mentira:

- **vivero** (en español): el sistema de un vivero, con riego automático, stock y ventas por la web.
- **trailbot** (en inglés): un bot de Telegram que recomienda una caminata para hoy.

## Cómo abrirla

Con el plugin, en Claude Code: `/neuromapa:abrir --demo`. Sin el plugin, desde la carpeta raíz del repositorio:

```
sh bin/neuromapa abrir --demo
```

(En Windows: `bin\neuromapa.cmd abrir --demo`.) Todo acepta `--demo`, por ejemplo `sh bin/neuromapa --demo --salud` o
`sh bin/neuromapa --demo --sobre "riego"` (con el plugin, Claude lo corre como `neuromapa --demo …`). La página y el registro de la demo quedan acá adentro
(`demo/cerebro.html` y `demo/en-vivo/`): nunca tocan los tuyos. El botón «Probar» de la página muestra cómo se ve un
chat trabajando.

## Qué trae

73 notas en 7 grupos: la memoria del vivero y la de trailbot (como las que guarda Claude Code), los `CLAUDE.md`, los
documentos de cada proyecto, ideas y decisiones, y un archivo de notas viejas. Más un poco de código de mentira en
`proyectos/`, para que el médico tenga contra qué comparar. Todo va con rutas relativas a esta carpeta.

Los `CLAUDE.md` de acá son de los proyectos inventados: no son instrucciones para quien trabaja en Neuromapa.

## Los problemas puestos a propósito

| Problema | Dónde |
|---|---|
| El índice apunta a una nota que no existe (grave) | `MEMORY.md` de trailbot → `old-roadmap.md` |
| Al frontmatter le falta el tipo | `telegram-commands.md` |
| Repite lo que ya dice el `CLAUDE.md` | `small-prs.md` |
| Memoria que el índice no lista | `idea-app-movil.md` |
| Nota que nadie nombra | `docs/notas-sueltas.md` del vivero |
| Nombra un archivo que ya no existe | `docs/viejo/PLAN-INICIAL.md` → `docs/riego-v1.md` |
| Ancla `archivo.cs:línea` corrida | `riego-programador.md` → `Programador.cs:36` (`DebeRegar` está en la 59) |
| Ancla `archivo.py:línea` corrida, y más allá del final | `weather-provider.md` → `weather.py:40` (`get_forecast` está en la 16; el archivo tiene 37 líneas) |
| La descripción y el cuerpo dicen cifras distintas | `stock-plantas.md` (3 y 4 estados) |
| Descripción que no dice nada | `base-de-datos.md` |
| El `name` no coincide con el archivo | `weather-provider.md` |
| Línea del índice sin gancho | `MEMORY.md` del vivero → `arreglo-horario-verano.md` |
| Dos memorias que cuentan lo mismo | `arreglo-webhook-duplicado.md` y `mercadopago-avisos-repetidos.md` |
| «Sin probar» contra «probado» | `pendientes.md` contra `arreglo-riego-doble.md` |
| Cifra vieja, controlada por `hechos.json` | `CLAUDE.md` del vivero (dice 5 módulos y hay 6) |
| Enlace roto (en `--salud` y en el panel de salud de la página) | `temporada-alta.md` → `[[calendario-de-ventas]]` |

`arreglo-stock-negativo.md` cita un commit, pero los proyectos de la demo no tienen repositorio git propio: el médico
avisa que no pudo verificarlo, en vez de darlo por inexistente. Si bajaste Neuromapa con `git clone`, la demo queda
adentro de ese repositorio, y el médico usa su historia solo para decir de cuándo es cada renglón de las notas. Con
tus notas, los commits se verifican contra los proyectos con git de tu `config.json`.

Si cambiás algo de la demo, corré `python3 herramientas/prueba_humo.py` (en Windows,
`py -3 herramientas/prueba_humo.py`): revisa que el médico siga encontrando estos
problemas y ninguno más.
