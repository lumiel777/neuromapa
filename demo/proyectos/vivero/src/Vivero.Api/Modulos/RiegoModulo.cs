using Vivero.Riego;

namespace Vivero.Api.Modulos
{
    public static class RiegoModulo
    {
        public static void Mapear(WebApplication app)
        {
            app.MapGet("/riego/turnos", (Programador programador) => programador.TurnosDeHoy());
            app.MapPost("/riego/lecturas", (LecturaCruda lectura, Receptor receptor) => receptor.Guardar(lectura));
        }
    }
}
