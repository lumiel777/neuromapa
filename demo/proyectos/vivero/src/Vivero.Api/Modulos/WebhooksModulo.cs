namespace Vivero.Api.Modulos
{
    public static class WebhooksModulo
    {
        public static void Mapear(WebApplication app)
        {
            app.MapPost("/webhooks/mercadopago", (AvisoDePago aviso, Pagos pagos) => pagos.Procesar(aviso));
        }
    }
}
