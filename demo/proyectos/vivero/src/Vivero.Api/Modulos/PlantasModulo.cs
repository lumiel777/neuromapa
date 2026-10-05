namespace Vivero.Api.Modulos
{
    public static class PlantasModulo
    {
        public static void Mapear(WebApplication app)
        {
            app.MapGet("/plantas", (Catalogo catalogo) => catalogo.Todas());
            app.MapGet("/plantas/{id:int}", (int id, Catalogo catalogo) => catalogo.Una(id));
        }
    }
}
