namespace Vivero.Api.Modulos
{
    public static class AvisosModulo
    {
        public static void Mapear(WebApplication app)
        {
            app.MapGet("/avisos/hoy", (Avisador avisador) => avisador.EnviadosHoy());
        }
    }
}
