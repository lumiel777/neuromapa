using System.Data;
using Microsoft.Data.Sqlite;

namespace Vivero.Datos
{
    public sealed class StockRepositorio
    {
        private readonly string cadena;

        public StockRepositorio(string cadena)
        {
            this.cadena = cadena;
        }

        public bool DescontarStock(int plantaId, int cantidad, string motivo)
        {
            using var conexion = new SqliteConnection(cadena);
            conexion.Open();
            using var transaccion = conexion.BeginTransaction(IsolationLevel.Serializable);
            var descontar = conexion.CreateCommand();
            descontar.Transaction = transaccion;
            descontar.CommandText = "UPDATE stock_plantas SET cantidad = cantidad - $c WHERE id = $id AND cantidad >= $c";
            descontar.Parameters.AddWithValue("$c", cantidad);
            descontar.Parameters.AddWithValue("$id", plantaId);
            if (descontar.ExecuteNonQuery() == 0)
            {
                transaccion.Rollback();
                return false;
            }
            var movimiento = conexion.CreateCommand();
            movimiento.Transaction = transaccion;
            movimiento.CommandText = "INSERT INTO stock_movimientos (planta_id, cantidad, motivo) VALUES ($id, -$c, $m)";
            movimiento.Parameters.AddWithValue("$id", plantaId);
            movimiento.Parameters.AddWithValue("$c", cantidad);
            movimiento.Parameters.AddWithValue("$m", motivo);
            movimiento.ExecuteNonQuery();
            transaccion.Commit();
            return true;
        }

        public int StockDe(int plantaId)
        {
            using var conexion = new SqliteConnection(cadena);
            conexion.Open();
            var consulta = conexion.CreateCommand();
            consulta.CommandText = "SELECT cantidad FROM stock_plantas WHERE id = $id";
            consulta.Parameters.AddWithValue("$id", plantaId);
            return System.Convert.ToInt32(consulta.ExecuteScalar() ?? 0);
        }
    }
}
