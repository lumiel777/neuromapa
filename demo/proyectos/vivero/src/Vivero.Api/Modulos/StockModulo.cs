using Vivero.Datos;

namespace Vivero.Api.Modulos
{
    public static class StockModulo
    {
        public static void Mapear(WebApplication app)
        {
            app.MapGet("/stock/{id:int}", (int id, StockRepositorio stock) => stock.StockDe(id));
            app.MapGet("/stock/bajo", (AlertasDeStock alertas) => alertas.Pendientes());
        }
    }
}
