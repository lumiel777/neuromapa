using System;
using System.Collections.Generic;
using System.Linq;

namespace Vivero.Riego
{
    public sealed class Programador
    {
        private const int HumedadMinima = 35;
        private const int HumedadObjetivo = 60;
        private const int MinutosPorPunto = 2;
        private const int TopeMinutos = 45;

        private readonly IReadOnlyList<Zona> zonas;
        private readonly IRelojDelVivero reloj;
        private readonly IRegistroDeRiego registro;

        public Programador(IReadOnlyList<Zona> zonas, IRelojDelVivero reloj, IRegistroDeRiego registro)
        {
            this.zonas = zonas;
            this.reloj = reloj;
            this.registro = registro;
        }

        public IEnumerable<Turno> TurnosDeHoy()
        {
            return zonas.Select(z => new Turno(z, ProximoHorario(z), CalcularDuracion(z.UltimaLectura)));
        }

        public int CalcularDuracion(Lectura lectura)
        {
            if (lectura == null || lectura.Humedad >= HumedadObjetivo)
            {
                return 0;
            }
            var faltan = HumedadObjetivo - lectura.Humedad;
            return Math.Min(TopeMinutos, faltan * MinutosPorPunto);
        }

        public DateTime ProximoHorario(Zona zona)
        {
            var hoy = reloj.Ahora.Date;
            var temprano = hoy.AddHours(6).AddMinutes(zona.Orden * 20);
            return reloj.Ahora <= temprano ? temprano : temprano.AddDays(1);
        }

        public bool YaRegoHoy(Zona zona)
        {
            var ultimo = registro.UltimoRiego(zona.Id);
            return ultimo.HasValue && ultimo.Value.Date == reloj.Ahora.Date;
        }

        public bool LlovioHace(int horas)
        {
            var lluvia = registro.UltimaLluvia();
            return lluvia.HasValue && reloj.Ahora - lluvia.Value < TimeSpan.FromHours(horas);
        }

        public bool DebeRegar(Zona zona)
        {
            if (zona.SensorMuerto)
            {
                return !YaRegoHoy(zona);
            }
            if (YaRegoHoy(zona) || LlovioHace(12))
            {
                return false;
            }
            return zona.UltimaLectura != null && zona.UltimaLectura.Humedad < HumedadMinima;
        }

        public void Registrar(Zona zona, int minutos)
        {
            registro.Anotar(zona.Id, reloj.Ahora, minutos);
        }
    }
}
