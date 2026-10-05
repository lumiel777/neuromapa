using System;

namespace Vivero.Riego
{
    public sealed class Sensor
    {
        private const int LecturaSeca = 820;
        private const int LecturaMojada = 390;
        private const int MinutosSinDatos = 90;

        public int Pin { get; }
        public DateTime? UltimoDato { get; private set; }

        public Sensor(int pin)
        {
            Pin = pin;
        }

        public Lectura Convertir(int crudo, DateTime cuando)
        {
            UltimoDato = cuando;
            var rango = LecturaSeca - LecturaMojada;
            var humedad = (LecturaSeca - crudo) * 100 / rango;
            return new Lectura(Math.Clamp(humedad, 0, 100), cuando);
        }

        public bool EstaMuerto(DateTime ahora)
        {
            return !UltimoDato.HasValue || ahora - UltimoDato.Value > TimeSpan.FromMinutes(MinutosSinDatos);
        }
    }
}
