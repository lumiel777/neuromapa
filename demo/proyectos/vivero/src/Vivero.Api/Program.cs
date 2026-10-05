using Vivero.Api.Modulos;

var builder = WebApplication.CreateBuilder(args);
builder.Services.AddVivero(builder.Configuration);
var app = builder.Build();

PlantasModulo.Mapear(app);
StockModulo.Mapear(app);
VentasModulo.Mapear(app);
RiegoModulo.Mapear(app);
WebhooksModulo.Mapear(app);
AvisosModulo.Mapear(app);

app.Run();
