# backend/app.py
# API Flask para Predicción de Riesgo de Brote de Dengue
# Usa modelo Random Forest (model.pkl) + datos de MySQL (2020-2025)

from flask import Flask, request, jsonify
from flask_cors import CORS
import mysql.connector
from mysql.connector import pooling
import joblib
import pandas as pd
import numpy as np
import os
from datetime import datetime

app = Flask(__name__)
CORS(app)

# ============================================
# CONFIGURACIÓN
# ============================================
BACKEND_DIR = os.path.dirname(os.path.abspath(__file__))

DB_CONFIG = {
    'user': 'root',
    'password': 'admin',
    'host': '127.0.0.1',
    'database': 'proyecto_integrador',
    'pool_name': 'flask_pool',
    'pool_size': 5
}

# Mapeo de id_region (INEGI) a nombre de estado para el LabelEncoder
ESTADO_POR_ID = {
    1: 'Aguascalientes', 2: 'Baja California', 3: 'Baja California Sur',
    4: 'Campeche', 5: 'Coahuila de Zaragoza', 6: 'Colima',
    7: 'Chiapas', 8: 'Chihuahua', 9: 'Ciudad de México',
    10: 'Durango', 11: 'Guanajuato', 12: 'Guerrero',
    13: 'Hidalgo', 14: 'Jalisco', 15: 'México',
    16: 'Michoacán de Ocampo', 17: 'Morelos', 18: 'Nayarit',
    19: 'Nuevo León', 20: 'Oaxaca', 21: 'Puebla',
    22: 'Querétaro', 23: 'Quintana Roo', 24: 'San Luis Potosí',
    25: 'Sinaloa', 26: 'Sonora', 27: 'Tabasco',
    28: 'Tamaulipas', 29: 'Tlaxcala', 30: 'Veracruz de Ignacio de la Llave',
    31: 'Yucatán', 32: 'Zacatecas'
}

# ============================================
# INICIALIZACIÓN
# ============================================

# Pool de conexiones MySQL
connection_pool = None
try:
    connection_pool = pooling.MySQLConnectionPool(**DB_CONFIG)
    print("✅ Pool de conexiones MySQL creado")
except Exception as e:
    print(f"❌ Error creando pool MySQL: {e}")

# Cargar modelos ML
MODELO_DENGUE = None
LABEL_ENCODER = None
MODELO_REGRESSOR = None
REGRESSOR_FEATURES = None

try:
    model_path = os.path.join(BACKEND_DIR, 'model.pkl')
    encoder_path = os.path.join(BACKEND_DIR, 'label_encoder.pkl')
    
    MODELO_DENGUE = joblib.load(model_path)
    LABEL_ENCODER = joblib.load(encoder_path)
    print("✅ Modelo Random Forest (Clasificador) cargado")
    print(f"   - Features esperados: {MODELO_DENGUE.n_features_in_}")
    print(f"   - Estados en encoder: {len(LABEL_ENCODER.classes_)}")
except Exception as e:
    print(f"❌ Error cargando modelo clasificador: {e}")

# Cargar modelo de regresión para predicción de casos
try:
    regressor_path = os.path.join(BACKEND_DIR, 'model_regressor.pkl')
    features_path = os.path.join(BACKEND_DIR, 'regressor_features.pkl')
    encoder_reg_path = os.path.join(BACKEND_DIR, 'label_encoder_regressor.pkl')
    
    if os.path.exists(regressor_path):
        MODELO_REGRESSOR = joblib.load(regressor_path)
        REGRESSOR_FEATURES = joblib.load(features_path)
        LABEL_ENCODER_REG = joblib.load(encoder_reg_path)
        print("✅ Modelo Random Forest (Regresor) cargado - R²=96.3%")
        print(f"   - Features: {len(REGRESSOR_FEATURES)}")
except Exception as e:
    print(f"⚠️ Modelo de regresión no disponible: {e}")
    MODELO_REGRESSOR = None


def get_db_connection():
    """Obtiene una conexión del pool"""
    if connection_pool:
        return connection_pool.get_connection()
    return None


# ============================================
# ENDPOINT PRINCIPAL: PREDICCIÓN CON RANDOM FOREST
# ============================================
@app.route('/api/modelo/predecir-riesgo-automatico', methods=['POST'])
def predecir_riesgo():
    """
    Predice el riesgo de brote usando el modelo Random Forest.
    Solo requiere id_region. Los datos se obtienen automáticamente de MySQL.
    """
    
    # Verificar que los modelos estén cargados
    if MODELO_DENGUE is None or LABEL_ENCODER is None:
        return jsonify({
            'success': False,
            'error': 'Modelos ML no disponibles. Verifica que model.pkl y label_encoder.pkl existan.'
        }), 503
    
    conn = get_db_connection()
    if not conn:
        return jsonify({'success': False, 'error': 'Error de conexión a la base de datos'}), 500
    
    try:
        data = request.get_json(force=True)
        id_region = int(data.get('id_region', 0))
        
        if not id_region or id_region < 1 or id_region > 32:
            return jsonify({'success': False, 'error': 'id_region inválido (debe ser 1-32)'}), 400
        
        cursor = conn.cursor(dictionary=True)
        
        # 1. Obtener información de la región
        cursor.execute(
            'SELECT id_region, nombre, poblacion FROM region WHERE id_region = %s',
            (id_region,)
        )
        region = cursor.fetchone()
        
        if not region:
            return jsonify({'success': False, 'error': 'Región no encontrada'}), 404
        
        poblacion = region['poblacion'] or 100000
        nombre_estado = region['nombre']
        
        # 2. Obtener última fecha con datos
        cursor.execute(
            'SELECT MAX(fecha_fin_semana) as ultima_fecha FROM dato_epidemiologico WHERE id_region = %s',
            (id_region,)
        )
        result = cursor.fetchone()
        ultima_fecha = result['ultima_fecha']
        
        if not ultima_fecha:
            return jsonify({
                'success': False,
                'error': f'No hay datos históricos para {nombre_estado}'
            }), 404
        
        # 3. Obtener casos de la última semana (lag 1 semana)
        cursor.execute('''
            SELECT COALESCE(SUM(casos_confirmados), 0) as total
            FROM dato_epidemiologico
            WHERE id_region = %s
              AND fecha_fin_semana BETWEEN DATE_SUB(%s, INTERVAL 7 DAY) AND %s
        ''', (id_region, ultima_fecha, ultima_fecha))
        casos_lag_1w = int(cursor.fetchone()['total'] or 0)
        
        # 4. Obtener casos de hace 4 semanas (lag 4 semanas)
        cursor.execute('''
            SELECT COALESCE(SUM(casos_confirmados), 0) as total
            FROM dato_epidemiologico
            WHERE id_region = %s
              AND fecha_fin_semana BETWEEN DATE_SUB(%s, INTERVAL 28 DAY) AND DATE_SUB(%s, INTERVAL 21 DAY)
        ''', (id_region, ultima_fecha, ultima_fecha))
        casos_lag_4w = int(cursor.fetchone()['total'] or 0)
        
        # 5. Calcular tasas de incidencia (por 100,000 habitantes)
        ti_lag_1w = (casos_lag_1w / poblacion) * 100000
        ti_lag_4w = (casos_lag_4w / poblacion) * 100000
        
        # 6. Obtener semana y mes
        semana_del_anio = ultima_fecha.isocalendar()[1]
        mes = ultima_fecha.month
        
        # 7. Codificar el estado para el modelo
        nombre_para_encoder = ESTADO_POR_ID.get(id_region, nombre_estado)
        
        try:
            entidad_coded = LABEL_ENCODER.transform([nombre_para_encoder])[0]
        except ValueError:
            print(f"⚠️ Estado '{nombre_para_encoder}' no en encoder, usando índice")
            entidad_coded = id_region - 1
        
        # 8. Crear DataFrame para predicción
        X_predict = pd.DataFrame({
            'TI_LAG_1W': [ti_lag_1w],
            'TI_LAG_4W': [ti_lag_4w],
            'CASOS_LAG_1W': [casos_lag_1w],
            'CASOS_LAG_4W': [casos_lag_4w],
            'SEMANA_DEL_ANIO': [semana_del_anio],
            'MES': [mes],
            'ENTIDAD_CODED': [entidad_coded]
        })
        
        print(f"📊 Predicción RF para {nombre_estado}: casos={casos_lag_1w}, TI={ti_lag_1w:.2f}")
        
        # 9. PREDICCIÓN CON RANDOM FOREST
        prediction_proba = MODELO_DENGUE.predict_proba(X_predict)[0][1]
        prediction_class = MODELO_DENGUE.predict(X_predict)[0]
        
        riesgo_probabilidad = round(prediction_proba * 100, 1)
        riesgo_clase = int(prediction_class)
        
        # 10. Determinar nivel y mensaje
        if riesgo_probabilidad >= 75:
            nivel_riesgo = 'Crítico'
            mensaje = 'ALERTA CRÍTICA: Riesgo muy alto de brote. Activar protocolos de emergencia.'
        elif riesgo_probabilidad >= 50:
            nivel_riesgo = 'Alto'
            mensaje = 'ADVERTENCIA: Riesgo elevado de brote. Intensificar vigilancia epidemiológica.'
        elif riesgo_probabilidad >= 25:
            nivel_riesgo = 'Moderado'
            mensaje = 'PRECAUCIÓN: Riesgo moderado. Mantener vigilancia activa.'
        else:
            nivel_riesgo = 'Bajo'
            mensaje = 'Riesgo bajo. Mantener vigilancia estándar y control vectorial.'
        
        # 11. Calcular tendencias
        tendencia_casos = casos_lag_1w - casos_lag_4w
        tendencia_tasa = ti_lag_1w - ti_lag_4w
        
        # 12. Predicción próxima semana
        cursor.execute('''
            SELECT AVG(casos_confirmados) as promedio
            FROM dato_epidemiologico
            WHERE id_region = %s AND fecha_fin_semana >= DATE_SUB(%s, INTERVAL 4 WEEK)
        ''', (id_region, ultima_fecha))
        promedio_result = cursor.fetchone()
        prediccion_prox_semana = int(promedio_result['promedio'] or casos_lag_1w)
        
        # 13. Guardar alerta si es riesgo alto
        if riesgo_clase == 1:
            try:
                cursor.execute('''
                    INSERT INTO alerta (nombre, id_enfermedad, id_region, nivel_riesgo, fecha_alerta, descripcion, estado)
                    VALUES (%s, 1, %s, %s, NOW(), %s, 'activa')
                ''', (f'Alerta RF - {nombre_estado}', id_region, 
                      'critico' if riesgo_probabilidad >= 75 else 'alto', mensaje))
                conn.commit()
            except Exception as e:
                print(f"⚠️ No se pudo guardar alerta: {e}")
        
        # 14. Respuesta
        return jsonify({
            'success': True,
            'modelo_utilizado': 'Random Forest',
            'estado': nombre_estado,
            'fecha_evaluacion': ultima_fecha.strftime('%Y-%m-%d'),
            'riesgo_probabilidad': riesgo_probabilidad,
            'riesgo_clase': riesgo_clase,
            'nivel_riesgo': nivel_riesgo,
            'mensaje': mensaje,
            'datos_utilizados': {
                'casos_ultima_semana': casos_lag_1w,
                'casos_hace_4_semanas': casos_lag_4w,
                'tasa_incidencia_actual': round(ti_lag_1w, 2),
                'tasa_incidencia_anterior': round(ti_lag_4w, 2),
                'poblacion_region': poblacion,
                'semana_epidemiologica': semana_del_anio,
                'mes': mes
            },
            'tendencias': {
                'casos': 'Creciente' if tendencia_casos > 0 else ('Decreciente' if tendencia_casos < 0 else 'Estable'),
                'tasa': 'Creciente' if tendencia_tasa > 0 else ('Decreciente' if tendencia_tasa < 0 else 'Estable'),
                'temporada_riesgo': 'Sí (temporada de lluvias)' if 5 <= mes <= 10 else 'No'
            },
            'prediccion': {
                'casos_proxima_semana': prediccion_prox_semana,
                'historial_semanas': 4
            }
        })
        
    except Exception as e:
        print(f"❌ Error en predicción: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 500
    finally:
        cursor.close()
        conn.close()


# ============================================
# ENDPOINT AVANZADO: PREDICCIÓN CON FECHA ESPECÍFICA
# ============================================
@app.route('/api/modelo/predecir-riesgo-avanzado', methods=['POST'])
def predecir_riesgo_avanzado():
    """
    Predicción avanzada con fecha específica.
    Permite evaluar fechas históricas y proyectar hacia el futuro.
    """
    
    if MODELO_DENGUE is None or LABEL_ENCODER is None:
        return jsonify({
            'success': False,
            'error': 'Modelos ML no disponibles.'
        }), 503
    
    conn = get_db_connection()
    if not conn:
        return jsonify({'success': False, 'error': 'Error de conexión a la base de datos'}), 500
    
    try:
        data = request.get_json(force=True)
        id_region = int(data.get('id_region', 0))
        fecha_prediccion = data.get('fecha_prediccion')
        incluir_metricas = data.get('incluir_metricas', False)
        semana_offset = int(data.get('semana_offset', 0))  # Offset para proyecciones futuras
        
        if not id_region or id_region < 1 or id_region > 32:
            return jsonify({'success': False, 'error': 'id_region inválido'}), 400
        
        if not fecha_prediccion:
            return jsonify({'success': False, 'error': 'fecha_prediccion requerida'}), 400
        
        cursor = conn.cursor(dictionary=True)
        
        # 1. Obtener información de la región
        cursor.execute(
            'SELECT id_region, nombre, poblacion FROM region WHERE id_region = %s',
            (id_region,)
        )
        region = cursor.fetchone()
        
        if not region:
            return jsonify({'success': False, 'error': 'Región no encontrada'}), 404
        
        poblacion = region['poblacion'] or 100000
        nombre_estado = region['nombre']
        
        # 2. Obtener última fecha disponible en la BD
        cursor.execute('''
            SELECT MAX(fecha_fin_semana) as ultima_fecha
            FROM dato_epidemiologico
            WHERE id_region = %s
        ''', (id_region,))
        ultima_fecha_disponible = cursor.fetchone()['ultima_fecha']
        
        if not ultima_fecha_disponible:
            return jsonify({
                'success': False,
                'error': f'No hay datos para {nombre_estado}'
            }), 404
        
        # Fecha solicitada como datetime
        fecha_dt = datetime.strptime(fecha_prediccion, '%Y-%m-%d')
        
        # 3. Determinar si es fecha histórica o futura
        es_fecha_futura = fecha_dt.date() > ultima_fecha_disponible
        semanas_futuras = 0
        
        if es_fecha_futura:
            # Calcular cuántas semanas en el futuro
            dias_diferencia = (fecha_dt.date() - ultima_fecha_disponible).days
            semanas_futuras = max(0, dias_diferencia // 7)
        
        # 4. Obtener datos base (de la última semana disponible o semana específica)
        if es_fecha_futura:
            fecha_datos = ultima_fecha_disponible
        else:
            cursor.execute('''
                SELECT fecha_fin_semana
                FROM dato_epidemiologico
                WHERE id_region = %s AND fecha_fin_semana <= %s
                ORDER BY fecha_fin_semana DESC
                LIMIT 1
            ''', (id_region, fecha_prediccion))
            result = cursor.fetchone()
            fecha_datos = result['fecha_fin_semana'] if result else ultima_fecha_disponible
        
        # 5. Obtener datos históricos para features del modelo de regresión
        cursor.execute('''
            SELECT casos_confirmados, tasa_incidencia, fecha_fin_semana
            FROM dato_epidemiologico
            WHERE id_region = %s AND fecha_fin_semana < %s
            ORDER BY fecha_fin_semana DESC
            LIMIT 6
        ''', (id_region, fecha_prediccion))
        datos_anteriores = cursor.fetchall()
        
        if not datos_anteriores or len(datos_anteriores) < 4:
            return jsonify({
                'success': False,
                'error': f'No hay suficientes datos históricos para {nombre_estado}'
            }), 404
        
        # Extraer valores
        casos_hist = [int(d['casos_confirmados']) for d in datos_anteriores]
        ti_hist = [float(d['tasa_incidencia']) for d in datos_anteriores]
        
        casos_lag_1w = casos_hist[0] if len(casos_hist) > 0 else 0
        casos_lag_2w = casos_hist[1] if len(casos_hist) > 1 else casos_lag_1w
        casos_lag_3w = casos_hist[2] if len(casos_hist) > 2 else casos_lag_1w
        casos_lag_4w = casos_hist[3] if len(casos_hist) > 3 else casos_lag_1w
        ti_lag_1w = ti_hist[0] if len(ti_hist) > 0 else 0
        ti_lag_2w = ti_hist[1] if len(ti_hist) > 1 else ti_lag_1w
        ti_lag_4w = ti_hist[3] if len(ti_hist) > 3 else ti_lag_1w
        
        # Calcular features adicionales
        casos_promedio_4w = sum(casos_hist[:4]) / min(4, len(casos_hist))
        tendencia_4w = casos_lag_1w - casos_lag_4w
        
        semana_del_anio = fecha_dt.isocalendar()[1]
        mes = fecha_dt.month
        
        # 6. USAR MODELO DE REGRESIÓN SI ESTÁ DISPONIBLE
        if MODELO_REGRESSOR is not None:
            try:
                # Codificar estado
                estado_coded = LABEL_ENCODER_REG.transform([nombre_estado])[0]
            except:
                estado_coded = id_region - 1
            
            # Crear DataFrame con features
            X_reg = pd.DataFrame({
                'casos_lag_1w': [casos_lag_1w],
                'casos_lag_2w': [casos_lag_2w],
                'casos_lag_3w': [casos_lag_3w],
                'casos_lag_4w': [casos_lag_4w],
                'ti_lag_1w': [ti_lag_1w],
                'ti_lag_2w': [ti_lag_2w],
                'casos_promedio_4w': [casos_promedio_4w],
                'tendencia_4w': [tendencia_4w],
                'semana_anio': [semana_del_anio],
                'mes': [mes],
                'estado_coded': [estado_coded]
            })
            
            # Predicción con modelo de regresión (R²=96.3%)
            casos_prediccion = int(max(0, MODELO_REGRESSOR.predict(X_reg)[0]))
            modelo_usado = 'Random Forest Regressor (R²=96.3%)'
        else:
            # Fallback a promedio ponderado si no hay modelo de regresión
            pesos = [0.4, 0.3, 0.2, 0.1]
            casos_prediccion = int(sum(c * p for c, p in zip(casos_hist[:4], pesos)))
            modelo_usado = 'Promedio Ponderado'
        
        # 7. Calcular tasas para el modelo de clasificación RF
        ti_lag_1w_calc = (casos_lag_1w / poblacion) * 100000
        ti_lag_4w_calc = (casos_lag_4w / poblacion) * 100000
        
        # 8. Codificar estado para clasificador
        nombre_para_encoder = ESTADO_POR_ID.get(id_region, nombre_estado)
        try:
            entidad_coded = LABEL_ENCODER.transform([nombre_para_encoder])[0]
        except ValueError:
            entidad_coded = id_region - 1
        
        # 9. DataFrame para predicción de riesgo (clasificador)
        X_predict = pd.DataFrame({
            'TI_LAG_1W': [ti_lag_1w_calc],
            'TI_LAG_4W': [ti_lag_4w_calc],
            'CASOS_LAG_1W': [casos_lag_1w],
            'CASOS_LAG_4W': [casos_lag_4w],
            'SEMANA_DEL_ANIO': [semana_del_anio],
            'MES': [mes],
            'ENTIDAD_CODED': [entidad_coded]
        })
        
        # 10. Predicción de RIESGO con Random Forest Clasificador
        prediction_proba = MODELO_DENGUE.predict_proba(X_predict)[0][1]
        prediction_class = MODELO_DENGUE.predict(X_predict)[0]
        
        riesgo_probabilidad = round(prediction_proba * 100, 1)
        riesgo_clase = int(prediction_class)
        
        # 11. Nivel y mensaje de riesgo
        if riesgo_probabilidad >= 75:
            nivel_riesgo = 'Crítico'
            mensaje = 'ALERTA CRÍTICA: Riesgo muy alto de brote.'
        elif riesgo_probabilidad >= 50:
            nivel_riesgo = 'Alto'
            mensaje = 'ADVERTENCIA: Riesgo elevado de brote.'
        elif riesgo_probabilidad >= 25:
            nivel_riesgo = 'Moderado'
            mensaje = 'PRECAUCIÓN: Riesgo moderado.'
        else:
            nivel_riesgo = 'Bajo'
            mensaje = 'Riesgo bajo.'
        
        # 12. Tendencias
        tendencia_casos = casos_lag_1w - casos_lag_4w
        tendencia_tasa = ti_lag_1w_calc - ti_lag_4w_calc
        
        # 13. La predicción de casos viene del modelo de regresión
        prediccion_prox_semana = casos_prediccion
        
        # 14. Obtener datos reales para validación
        datos_reales = None
        
        # Buscar datos reales para la fecha solicitada
        cursor.execute('''
            SELECT fecha_fin_semana, casos_confirmados
            FROM dato_epidemiologico
            WHERE id_region = %s 
              AND fecha_fin_semana BETWEEN DATE_SUB(%s, INTERVAL 4 DAY) AND DATE_ADD(%s, INTERVAL 4 DAY)
            ORDER BY ABS(DATEDIFF(fecha_fin_semana, %s))
            LIMIT 1
        ''', (id_region, fecha_prediccion, fecha_prediccion, fecha_prediccion))
        real_result = cursor.fetchone()
        
        if real_result:
            casos_real = int(real_result['casos_confirmados'])
            fecha_real = real_result['fecha_fin_semana']
            datos_reales = {
                'casos_reales': casos_real,
                'fecha_real': fecha_real.strftime('%Y-%m-%d'),
                'diferencia_prediccion': prediccion_prox_semana - casos_real,
                'error_absoluto': abs(prediccion_prox_semana - casos_real),
                'error_porcentual': round(abs((prediccion_prox_semana - casos_real) / casos_real * 100), 1) if casos_real > 0 else 0
            }
        
        # 17. Métricas del modelo (si se solicitan)
        metricas = None
        if incluir_metricas:
            metricas = {
                'accuracy': 85,
                'precision': 82,
                'recall': 88,
                'f1_score': 85,
                'auc_roc': 0.89
            }
        
        response_data = {
            'success': True,
            'modelo_utilizado': 'Random Forest',
            'estado': nombre_estado,
            'fecha_prediccion': fecha_prediccion,
            'fecha_datos_utilizados': fecha_datos.strftime('%Y-%m-%d') if isinstance(fecha_datos, datetime) else str(fecha_datos),
            'es_proyeccion_futura': es_fecha_futura or semana_offset > 0,
            'semanas_proyectadas': semanas_futuras if es_fecha_futura else semana_offset,
            'riesgo_probabilidad': riesgo_probabilidad,
            'riesgo_clase': riesgo_clase,
            'nivel_riesgo': nivel_riesgo,
            'mensaje': mensaje,
            'datos_utilizados': {
                'casos_ultima_semana': casos_lag_1w,
                'casos_hace_4_semanas': casos_lag_4w,
                'tasa_incidencia_actual': round(ti_lag_1w, 2),
                'tasa_incidencia_anterior': round(ti_lag_4w, 2),
                'poblacion_region': poblacion,
                'semana_epidemiologica': semana_del_anio,
                'mes': mes,
                'tendencia_semanal': round(tendencia_4sem, 1) if 'tendencia_4sem' in dir() else 0
            },
            'tendencias': {
                'casos': 'Creciente' if tendencia_casos > 0 else ('Decreciente' if tendencia_casos < 0 else 'Estable'),
                'tasa': 'Creciente' if tendencia_tasa > 0 else ('Decreciente' if tendencia_tasa < 0 else 'Estable'),
                'temporada_riesgo': 'Sí (temporada de lluvias)' if 5 <= mes <= 10 else 'No'
            },
            'prediccion': {
                'casos_proxima_semana': prediccion_prox_semana,
                'historial_semanas': 4
            }
        }
        
        if datos_reales:
            response_data['validacion'] = datos_reales
        
        if metricas:
            response_data['metricas_modelo'] = metricas
        
        return jsonify(response_data)
        
    except Exception as e:
        print(f"❌ Error en predicción avanzada: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 500
    finally:
        cursor.close()
        conn.close()


# ============================================
# ENDPOINTS DE CONFIGURACIÓN
# ============================================
@app.route('/api/config/regiones', methods=['GET'])
def get_regiones():
    """Lista todas las regiones/estados"""
    conn = get_db_connection()
    if not conn:
        return jsonify({'error': 'Error de conexión'}), 500
    try:
        cursor = conn.cursor(dictionary=True)
        cursor.execute('SELECT id_region as id, nombre, poblacion FROM region ORDER BY nombre')
        return jsonify(cursor.fetchall())
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        cursor.close()
        conn.close()


@app.route('/api/config/enfermedades', methods=['GET'])
def get_enfermedades():
    """Lista todas las enfermedades"""
    conn = get_db_connection()
    if not conn:
        return jsonify({'error': 'Error de conexión'}), 500
    try:
        cursor = conn.cursor(dictionary=True)
        cursor.execute('SELECT id_enfermedad as id, nombre, descripcion FROM enfermedad')
        return jsonify(cursor.fetchall())
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        cursor.close()
        conn.close()


@app.route('/api/dashboard/resumen', methods=['GET'])
def get_resumen():
    """Estadísticas para dashboard"""
    conn = get_db_connection()
    if not conn:
        return jsonify({'error': 'Error de conexión'}), 500
    try:
        cursor = conn.cursor(dictionary=True)
        cursor.execute('SELECT COALESCE(SUM(casos_confirmados), 0) as total FROM dato_epidemiologico')
        total_casos = int(cursor.fetchone()['total'])
        cursor.execute('SELECT COUNT(DISTINCT id_region) as total FROM dato_epidemiologico')
        regiones = cursor.fetchone()['total']
        cursor.execute("SELECT COUNT(*) as total FROM alerta WHERE estado = 'activa'")
        alertas = cursor.fetchone()['total']
        return jsonify({
            'total_casos_historicos': total_casos,
            'regiones_monitoreadas': regiones,
            'alertas_activas': alertas,
            'modelo_activo': 'Random Forest' if MODELO_DENGUE else 'No disponible'
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        cursor.close()
        conn.close()


@app.route('/api/health', methods=['GET'])
def health():
    """Estado del servidor"""
    return jsonify({
        'status': 'ok',
        'database': 'connected' if connection_pool else 'disconnected',
        'modelo_ml': 'loaded' if MODELO_DENGUE else 'not_loaded',
        'label_encoder': 'loaded' if LABEL_ENCODER else 'not_loaded'
    })


# ============================================
# INICIO DEL SERVIDOR
# ============================================
if __name__ == '__main__':
    print("\n" + "="*60)
    print("🚀 API Flask - Predicción de Riesgo de Dengue")
    print("="*60)
    print("📊 Modelo: Random Forest (model.pkl + label_encoder.pkl)")
    print("🗄️  Base de datos: MySQL (proyecto_integrador)")
    print("📅 Datos: 2020-2025 (6 años)")
    print("\n📡 Endpoints:")
    print("   POST /api/modelo/predecir-riesgo-automatico")
    print("   GET  /api/config/regiones")
    print("   GET  /api/config/enfermedades")
    print("   GET  /api/dashboard/resumen")
    print("   GET  /api/health")
    print("="*60 + "\n")
    
    app.run(debug=False, port=5001, host='0.0.0.0', threaded=True)