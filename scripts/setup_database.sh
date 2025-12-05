#!/bin/bash
# Script de inicialización de base de datos para ProeVira
# Uso: ./setup_database.sh [usuario] [contraseña]

USER=${1:-root}
PASSWORD=${2:-admin}
DB_NAME="proyecto_integrador"
SCHEMA_FILE="../database_schema_completo.sql"

echo "🦟 ProeVira - Configuración de Base de Datos"
echo "=============================================="
echo ""
echo "📌 Usuario: $USER"
echo "📌 Base de datos: $DB_NAME"
echo ""

# Verificar si MySQL está instalado
if ! command -v mysql &> /dev/null; then
    echo "❌ ERROR: MySQL no está instalado o no está en el PATH"
    echo "   Por favor instala MySQL 8.0+ y vuelve a intentar"
    exit 1
fi

echo "✅ MySQL encontrado"
echo ""

# Verificar si el archivo de esquema existe
if [ ! -f "$SCHEMA_FILE" ]; then
    echo "❌ ERROR: No se encuentra el archivo $SCHEMA_FILE"
    exit 1
fi

echo "✅ Archivo de esquema encontrado"
echo ""

# Crear base de datos
echo "📦 Creando base de datos '$DB_NAME'..."
mysql -u"$USER" -p"$PASSWORD" -e "CREATE DATABASE IF NOT EXISTS $DB_NAME CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;" 2>/dev/null

if [ $? -eq 0 ]; then
    echo "✅ Base de datos creada exitosamente"
else
    echo "❌ ERROR al crear la base de datos"
    echo "   Verifica tus credenciales y permisos"
    exit 1
fi

echo ""
echo "📊 Cargando esquema de tablas..."
mysql -u"$USER" -p"$PASSWORD" "$DB_NAME" < "$SCHEMA_FILE" 2>/dev/null

if [ $? -eq 0 ]; then
    echo "✅ Esquema cargado exitosamente"
else
    echo "❌ ERROR al cargar el esquema"
    exit 1
fi

echo ""
echo "🔍 Verificando estructura de la base de datos..."
TABLES=$(mysql -u"$USER" -p"$PASSWORD" "$DB_NAME" -e "SHOW TABLES;" 2>/dev/null | tail -n +2)

if [ -z "$TABLES" ]; then
    echo "⚠️  ADVERTENCIA: No se encontraron tablas en la base de datos"
else
    echo "✅ Tablas creadas:"
    echo "$TABLES" | sed 's/^/   - /'
fi

echo ""
echo "=============================================="
echo "✅ CONFIGURACIÓN COMPLETADA"
echo "=============================================="
echo ""
echo "📝 Próximos pasos:"
echo "   1. Copia backend/.env.example a backend/.env"
echo "   2. Edita backend/.env con tus credenciales"
echo "   3. Ejecuta: cd backend && pip install -r requirements.txt"
echo "   4. Inicia el servidor: python app.py"
echo ""
