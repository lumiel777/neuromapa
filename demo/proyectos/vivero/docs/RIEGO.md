# Programador de riego

El programador decide, para cada una de las cuatro zonas, si hoy riega, cuánto y a qué hora. Vive en
`src/Vivero.Riego/Programador.cs` y corre en la Raspberry del vivero.

## Zonas

| Orden | Zona | Plantas | Sensor |
|---|---|---|---|
| 0 | Invernadero | Plantines | Capacitivo, pin 0 |
| 1 | Cantero de afuera | Arbustos y rosales | Capacitivo, pin 1 |
| 2 | Macetas grandes | Frutales y palmeras | Capacitivo, pin 2 |
| 3 | Estación | Flores de la temporada | Capacitivo, pin 3 |

## Cuándo riega (`Programador.cs:59`, `DebeRegar`)

1. Si el sensor está muerto (más de 90 minutos sin datos), riega una sola vez por día, a ciegas.
2. Si la zona ya regó hoy, no riega. El registro está en disco: sobrevive a un corte de luz.
3. Si llovió en las últimas doce horas, no riega.
4. Si la humedad está por debajo de **35**, riega.

¿Por qué 35? Por debajo de ese valor los plantines del invernadero empiezan a marchitarse en verano; lo midió Marta
con el sensor y una maceta de prueba durante una semana de enero.

## Cuánto riega (`Programador.cs:30`, `CalcularDuracion`)

Dos minutos por cada punto que falta para llegar a **60**, con tope de **45 minutos**. El tope existe porque la bomba
recalienta con más de tres cuartos de hora seguidos.

## A qué hora

Desde las 6, una zona cada 20 minutos, en el orden de la tabla. Temprano, para que el agua no se evapore; de a una,
para que la bomba no pierda presión.

## Lecturas

Las lecturas llegan a `riego_lecturas` y cada riego queda en `riego_turnos`, con la zona, la hora y los minutos. La
calibración de los sensores está en [GUIA-SENSORES.md](GUIA-SENSORES.md).
