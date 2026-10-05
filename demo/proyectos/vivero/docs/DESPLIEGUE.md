# Despliegue

## La API (VPS)

1. `dotnet publish src/Vivero.Api -c Release -o publicar`
2. Copiar `publicar/` a la VPS, en una carpeta nueva con la fecha.
3. Apuntar el enlace `actual` a esa carpeta y reiniciar el servicio `vivero-api`.

Las credenciales van en el archivo de entorno del servicio, en la VPS. La base se respalda cada noche; antes de una
migración, respaldo manual.

## El riego (Raspberry)

La Raspberry corre el servicio `riego`. Para instalarla desde cero:

1. Grabar el sistema en la tarjeta y activar la VPN del vivero.
2. Copiar `src/Vivero.Riego` publicado para ARM y crear el servicio con reinicio automático.
3. Conectar los sensores según [GUIA-SENSORES.md](GUIA-SENSORES.md) y calibrarlos.
4. Probar primero con la zona del cantero de afuera.

Si se corta internet, la Raspberry sigue regando con lo último que sabe y sube las lecturas cuando vuelve.
