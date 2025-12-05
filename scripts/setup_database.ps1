# Script de inicialización de base de datos para ProeVira (Windows PowerShell)
# Uso: .\setup_database.ps1 -User root -Password admin

param(
    [string]$User = "root",
    [string]$Password = "admin",
    [string]$DbName = "proyecto_integrador",
    [string]$SchemaFile = "..\database_schema_completo.sql"
)

Write-Host "🦟 ProeVira - Configuración de Base de Datos" -ForegroundColor Cyan
Write-Host "==============================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "📌 Usuario: $User"
Write-Host "📌 Base de datos: $DbName"
Write-Host ""

# Verificar si MySQL está instalado
try {
    $mysqlVersion = & mysql --version 2>&1
    Write-Host "✅ MySQL encontrado: $mysqlVersion" -ForegroundColor Green
} catch {
    Write-Host "❌ ERROR: MySQL no está instalado o no está en el PATH" -ForegroundColor Red
    Write-Host "   Por favor instala MySQL 8.0+ y agrega mysql.exe al PATH del sistema"
    exit 1
}

Write-Host ""

# Verificar si el archivo de esquema existe
if (-Not (Test-Path $SchemaFile)) {
    Write-Host "❌ ERROR: No se encuentra el archivo $SchemaFile" -ForegroundColor Red
    exit 1
}

Write-Host "✅ Archivo de esquema encontrado" -ForegroundColor Green
Write-Host ""

# Crear base de datos
Write-Host "📦 Creando base de datos '$DbName'..." -ForegroundColor Yellow

$createDbQuery = "CREATE DATABASE IF NOT EXISTS $DbName CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;"

try {
    $createResult = & mysql -u$User -p$Password -e $createDbQuery 2>&1
    Write-Host "✅ Base de datos creada exitosamente" -ForegroundColor Green
} catch {
    Write-Host "❌ ERROR al crear la base de datos" -ForegroundColor Red
    Write-Host "   Verifica tus credenciales y permisos"
    Write-Host "   Error: $_"
    exit 1
}

Write-Host ""
Write-Host "📊 Cargando esquema de tablas..." -ForegroundColor Yellow

try {
    Get-Content $SchemaFile | & mysql -u$User -p$Password $DbName 2>&1 | Out-Null
    Write-Host "✅ Esquema cargado exitosamente" -ForegroundColor Green
} catch {
    Write-Host "❌ ERROR al cargar el esquema" -ForegroundColor Red
    Write-Host "   Error: $_"
    exit 1
}

Write-Host ""
Write-Host "🔍 Verificando estructura de la base de datos..." -ForegroundColor Yellow

try {
    $tables = & mysql -u$User -p$Password $DbName -e "SHOW TABLES;" 2>&1 | Select-Object -Skip 1
    
    if ($tables) {
        Write-Host "✅ Tablas creadas:" -ForegroundColor Green
        foreach ($table in $tables) {
            Write-Host "   - $table"
        }
    } else {
        Write-Host "⚠️  ADVERTENCIA: No se encontraron tablas en la base de datos" -ForegroundColor Yellow
    }
} catch {
    Write-Host "⚠️  No se pudo verificar las tablas" -ForegroundColor Yellow
}

Write-Host ""
Write-Host "==============================================" -ForegroundColor Cyan
Write-Host "✅ CONFIGURACIÓN COMPLETADA" -ForegroundColor Green
Write-Host "==============================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "📝 Próximos pasos:"
Write-Host "   1. Copia backend\.env.example a backend\.env"
Write-Host "   2. Edita backend\.env con tus credenciales"
Write-Host "   3. Ejecuta: cd backend; pip install -r requirements.txt"
Write-Host "   4. Inicia el servidor: python app.py"
Write-Host ""
