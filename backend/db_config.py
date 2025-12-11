import mysql.connector
import os
from dotenv import load_dotenv

# Cargar variables de entorno
load_dotenv()

def get_db_connection():
    """Crea y retorna una conexión a la base de datos MySQL usando variables de entorno."""
    try:
        connection = mysql.connector.connect(
            host=os.getenv('DB_HOST', '127.0.0.1'),
            user=os.getenv('DB_USER', 'root'),
            password=os.getenv('DB_PASSWORD', ''),
            database=os.getenv('DB_NAME', 'proyecto_integrador')
        )
        return connection
    except mysql.connector.Error as err:
        print(f"❌ Error conectando a la base de datos: {err}")
        raise err

# Exportar configuración por si se necesita en otros lugares (opcional)
DB_CONFIG = {
    'host': os.getenv('DB_HOST', '127.0.0.1'),
    'user': os.getenv('DB_USER', 'root'),
    'password': os.getenv('DB_PASSWORD', ''),
    'database': os.getenv('DB_NAME', 'proyecto_integrador')
}
