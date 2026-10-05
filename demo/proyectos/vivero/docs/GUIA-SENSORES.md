# Guía de sensores de humedad

## Cableado

Cada sensor capacitivo tiene tres cables: alimentación (3,3 V), tierra y señal. La señal va a un conversor analógico
de cuatro canales conectado a la Raspberry; un canal por zona, en el orden de [RIEGO.md](RIEGO.md).

Usar cable mallado si el sensor queda a más de cinco metros: con cable común, la lectura salta cuando arranca la
bomba.

## Calibración

1. Con el sensor seco, al aire, anotar la lectura cruda (ronda 820).
2. Con el sensor en un vaso de agua, hasta la línea, anotar la lectura (ronda 390).
3. Poner esos dos valores en la configuración de la zona. El programador convierte la lectura a humedad de 0 a 100.

Cada sensor viene un poco distinto: si se cambia uno, se calibra de nuevo.

## Síntomas

- Saltos grandes en un minuto: cable flojo o sin mallar.
- Siempre 0 o siempre 100: sensor quemado o desconectado.
- Sin datos hace más de 90 minutos: el programador lo da por muerto y riega esa zona a ciegas una vez por día.
