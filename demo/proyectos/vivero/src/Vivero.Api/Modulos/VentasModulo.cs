namespace Vivero.Api.Modulos
{
    public static class VentasModulo
    {
        public static void Mapear(WebApplication app)
        {
            app.MapPost("/ventas", (NuevaVenta venta, Caja caja) => caja.Cobrar(venta));
            app.MapGet("/ventas/hoy", (Caja caja) => caja.DeHoy());
        }
    }
}
