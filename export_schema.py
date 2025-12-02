import mysql.connector

conn = mysql.connector.connect(
    user='root', 
    password='admin', 
    host='127.0.0.1', 
    database='proyecto_integrador'
)
cursor = conn.cursor()

print("-- =====================================================")
print("-- Script de Base de Datos: proyecto_integrador")
print("-- Sistema de Predicción de Enfermedades Virales (ProeVira)")
print("-- Generado: 2025-12-01")
print("-- =====================================================")
print()
print("DROP DATABASE IF EXISTS proyecto_integrador;")
print("CREATE DATABASE proyecto_integrador CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;")
print("USE proyecto_integrador;")
print()

# Obtener tablas en orden correcto (por dependencias)
tables_order = ['region', 'enfermedad', 'users', 'dato_epidemiologico', 'alerta']

cursor.execute('SHOW TABLES')
all_tables = [t[0] for t in cursor.fetchall()]

# Imprimir estructura de cada tabla
for table in tables_order:
    if table in all_tables:
        cursor.execute(f'SHOW CREATE TABLE {table}')
        result = cursor.fetchone()
        print(f"-- =====================================================")
        print(f"-- Tabla: {table}")
        print(f"-- =====================================================")
        create_stmt = result[1].replace('CREATE TABLE', 'CREATE TABLE IF NOT EXISTS')
        print(create_stmt + ";")
        print()

# Datos de región con población
print("-- =====================================================")
print("-- Datos: Regiones (32 Estados de México)")
print("-- =====================================================")
cursor.execute('SELECT id_region, nombre, poblacion FROM region ORDER BY id_region')
regiones = cursor.fetchall()
print("INSERT INTO region (id_region, nombre, poblacion) VALUES")
values = []
for r in regiones:
    values.append(f"  ({r[0]}, '{r[1]}', {r[2]})")
print(",\n".join(values) + ";")
print()

# Datos de enfermedad
print("-- =====================================================")
print("-- Datos: Enfermedades")
print("-- =====================================================")
cursor.execute('SELECT * FROM enfermedad')
enfermedades = cursor.fetchall()
if enfermedades:
    print("INSERT INTO enfermedad (id_enfermedad, nombre, descripcion) VALUES")
    values = []
    for e in enfermedades:
        desc = e[2] if e[2] else ''
        values.append(f"  ({e[0]}, '{e[1]}', '{desc}')")
    print(",\n".join(values) + ";")
print()

# Datos de usuarios
print("-- =====================================================")
print("-- Datos: Usuarios del sistema")
print("-- =====================================================")
cursor.execute('SELECT * FROM users')
users = cursor.fetchall()
if users:
    cursor.execute('SHOW COLUMNS FROM users')
    cols = [c[0] for c in cursor.fetchall()]
    print(f"INSERT INTO users ({', '.join(cols)}) VALUES")
    values = []
    for u in users:
        vals = []
        for v in u:
            if v is None:
                vals.append("NULL")
            elif isinstance(v, str):
                vals.append(f"'{v}'")
            else:
                vals.append(str(v))
        values.append(f"  ({', '.join(vals)})")
    print(",\n".join(values) + ";")
print()

# Estadísticas de dato_epidemiologico
print("-- =====================================================")
print("-- Datos epidemiológicos")
print("-- NOTA: Los datos se cargan con ETL_LOADER.py desde CSVs")
print("-- =====================================================")
cursor.execute('SELECT COUNT(*), MIN(fecha_fin_semana), MAX(fecha_fin_semana) FROM dato_epidemiologico')
stats = cursor.fetchone()
print(f"-- Total registros: {stats[0]}")
print(f"-- Rango de fechas: {stats[1]} a {stats[2]}")
print("-- Para cargar datos usar: python ETL_LOADER.py")
print()

conn.close()
