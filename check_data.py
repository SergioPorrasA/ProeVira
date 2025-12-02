import mysql.connector

conn = mysql.connector.connect(
    user='root', 
    password='admin', 
    host='127.0.0.1', 
    database='proyecto_integrador'
)
cursor = conn.cursor()

# Estados con más casos en 2025
cursor.execute('''
    SELECT r.nombre, r.id_region, SUM(d.casos_confirmados) as total
    FROM dato_epidemiologico d
    JOIN region r ON d.id_region = r.id_region
    WHERE YEAR(d.fecha_fin_semana) = 2025
    GROUP BY r.id_region
    ORDER BY total DESC
    LIMIT 10
''')
print('Top 10 estados con más casos en 2025:')
for r in cursor.fetchall():
    print(f'  {r[1]:2d}. {r[0]}: {r[2]} casos')

# Verificar Aguascalientes (id=1) en Oct-Nov 2025
cursor.execute('''
    SELECT fecha_fin_semana, casos_confirmados 
    FROM dato_epidemiologico 
    WHERE id_region = 1 AND fecha_fin_semana >= '2025-10-01'
    ORDER BY fecha_fin_semana
''')
print('\nAguascalientes Oct-Nov 2025:')
for r in cursor.fetchall():
    print(f'  {r[0]}: {r[1]} casos')

# Verificar Guerrero (alto dengue)
cursor.execute('''
    SELECT fecha_fin_semana, casos_confirmados 
    FROM dato_epidemiologico 
    WHERE id_region = 12 AND fecha_fin_semana >= '2025-10-01'
    ORDER BY fecha_fin_semana
''')
print('\nGuerrero Oct-Nov 2025:')
for r in cursor.fetchall():
    print(f'  {r[0]}: {r[1]} casos')

conn.close()
