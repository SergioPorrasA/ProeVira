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
    'password': '1234567',
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
                'tendencia_semanal': round(tendencia_tasa, 1)
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
# ENDPOINTS PARA REPORTES EPIDEMIOLÓGICOS
# ============================================

@app.route('/api/reportes/epidemiologico', methods=['GET'])
def get_reporte_epidemiologico():
    """Reporte epidemiológico completo con estadísticas históricas"""
    conn = get_db_connection()
    if not conn:
        return jsonify({'error': 'Error de conexión'}), 500
    
    try:
        cursor = conn.cursor(dictionary=True)
        
        # 1. Estadísticas generales
        cursor.execute("""
            SELECT 
                COUNT(*) as total_registros,
                COALESCE(SUM(casos_confirmados), 0) as total_casos,
                COALESCE(AVG(casos_confirmados), 0) as promedio_casos,
                COALESCE(MAX(casos_confirmados), 0) as max_casos,
                MIN(fecha_fin_semana) as fecha_inicio_datos,
                MAX(fecha_fin_semana) as fecha_fin_datos,
                COUNT(DISTINCT id_region) as total_estados,
                COUNT(DISTINCT YEAR(fecha_fin_semana)) as total_anios
            FROM dato_epidemiologico
        """)
        estadisticas = cursor.fetchone()
        
        # Convertir Decimal a float/int
        for key in estadisticas:
            if hasattr(estadisticas[key], 'real'):
                estadisticas[key] = float(estadisticas[key])
            elif isinstance(estadisticas[key], (int, float)):
                estadisticas[key] = int(estadisticas[key]) if isinstance(estadisticas[key], int) else float(estadisticas[key])
        
        # 2. Top 10 estados con más casos
        cursor.execute("""
            SELECT 
                r.nombre as estado,
                d.id_region,
                SUM(d.casos_confirmados) as total_casos,
                AVG(d.casos_confirmados) as promedio_semanal,
                MAX(d.casos_confirmados) as max_semanal,
                COUNT(*) as semanas_con_datos
            FROM dato_epidemiologico d
            JOIN region r ON d.id_region = r.id_region
            GROUP BY d.id_region, r.nombre
            ORDER BY total_casos DESC
            LIMIT 10
        """)
        top_estados = cursor.fetchall()
        for estado in top_estados:
            for key in estado:
                if hasattr(estado[key], 'real'):
                    estado[key] = float(estado[key])
        
        # 3. Evolución anual
        cursor.execute("""
            SELECT 
                YEAR(fecha_fin_semana) as anio,
                SUM(casos_confirmados) as total_casos,
                AVG(casos_confirmados) as promedio_semanal,
                COUNT(DISTINCT id_region) as estados_afectados
            FROM dato_epidemiologico
            GROUP BY YEAR(fecha_fin_semana)
            ORDER BY anio
        """)
        evolucion_anual = cursor.fetchall()
        for item in evolucion_anual:
            for key in item:
                if hasattr(item[key], 'real'):
                    item[key] = float(item[key])
        
        # 4. Tendencia mensual (últimos 24 meses)
        cursor.execute("""
            SELECT 
                DATE_FORMAT(fecha_fin_semana, '%Y-%m') as mes,
                SUM(casos_confirmados) as total_casos,
                AVG(casos_confirmados) as promedio
            FROM dato_epidemiologico
            WHERE fecha_fin_semana >= DATE_SUB(CURDATE(), INTERVAL 24 MONTH)
            GROUP BY DATE_FORMAT(fecha_fin_semana, '%Y-%m')
            ORDER BY mes
        """)
        tendencia_mensual = cursor.fetchall()
        for item in tendencia_mensual:
            for key in item:
                if hasattr(item[key], 'real'):
                    item[key] = float(item[key])
        
        # 5. Distribución por semana epidemiológica (promedio histórico)
        cursor.execute("""
            SELECT 
                WEEK(fecha_fin_semana) as semana_epidemiologica,
                AVG(casos_confirmados) as promedio_casos,
                SUM(casos_confirmados) as total_casos
            FROM dato_epidemiologico
            GROUP BY WEEK(fecha_fin_semana)
            ORDER BY WEEK(fecha_fin_semana)
        """)
        por_semana_epi = cursor.fetchall()
        for item in por_semana_epi:
            for key in item:
                if hasattr(item[key], 'real'):
                    item[key] = float(item[key])
        
        # 6. Comparativa de años
        cursor.execute("""
            SELECT 
                YEAR(fecha_fin_semana) as anio,
                MONTH(fecha_fin_semana) as mes,
                SUM(casos_confirmados) as casos
            FROM dato_epidemiologico
            WHERE YEAR(fecha_fin_semana) >= YEAR(CURDATE()) - 3
            GROUP BY YEAR(fecha_fin_semana), MONTH(fecha_fin_semana)
            ORDER BY anio, mes
        """)
        comparativa_anual = cursor.fetchall()
        for item in comparativa_anual:
            for key in item:
                if hasattr(item[key], 'real'):
                    item[key] = float(item[key])
        
        # 7. Alertas de alto riesgo (semanas con casos > promedio * 2)
        cursor.execute("""
            SELECT 
                r.nombre as estado,
                d.fecha_fin_semana as fecha_inicio,
                WEEK(d.fecha_fin_semana) as semana_epidemiologica,
                d.casos_confirmados,
                d.tasa_incidencia
            FROM dato_epidemiologico d
            JOIN region r ON d.id_region = r.id_region
            WHERE d.casos_confirmados > (
                SELECT AVG(casos_confirmados) * 2 FROM dato_epidemiologico
            )
            ORDER BY d.casos_confirmados DESC
            LIMIT 20
        """)
        alertas_alto_riesgo = cursor.fetchall()
        for item in alertas_alto_riesgo:
            item['fecha_inicio'] = item['fecha_inicio'].isoformat() if item['fecha_inicio'] else None
            for key in item:
                if hasattr(item[key], 'real'):
                    item[key] = float(item[key])
        
        # Convertir fechas en estadísticas
        if estadisticas.get('fecha_inicio_datos'):
            estadisticas['fecha_inicio_datos'] = estadisticas['fecha_inicio_datos'].isoformat()
        if estadisticas.get('fecha_fin_datos'):
            estadisticas['fecha_fin_datos'] = estadisticas['fecha_fin_datos'].isoformat()
        
        return jsonify({
            'success': True,
            'estadisticas': estadisticas,
            'top_estados': top_estados,
            'evolucion_anual': evolucion_anual,
            'tendencia_mensual': tendencia_mensual,
            'por_semana_epidemiologica': por_semana_epi,
            'comparativa_anual': comparativa_anual,
            'alertas_alto_riesgo': alertas_alto_riesgo,
            'generado_en': datetime.now().isoformat()
        })
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500
    finally:
        cursor.close()
        conn.close()


@app.route('/api/reportes/estado/<int:id_region>', methods=['GET'])
def get_reporte_estado(id_region):
    """Reporte detallado por estado específico"""
    conn = get_db_connection()
    if not conn:
        return jsonify({'error': 'Error de conexión'}), 500
    
    try:
        cursor = conn.cursor(dictionary=True)
        
        # Info del estado
        cursor.execute("SELECT nombre FROM region WHERE id = %s", (id_region,))
        estado_info = cursor.fetchone()
        if not estado_info:
            return jsonify({'error': 'Estado no encontrado'}), 404
        
        # Estadísticas del estado
        cursor.execute("""
            SELECT 
                SUM(casos_confirmados) as total_casos,
                AVG(casos_confirmados) as promedio_semanal,
                MAX(casos_confirmados) as max_casos,
                AVG(tasa_incidencia) as tasa_promedio
            FROM dato_epidemiologico
            WHERE id_region = %s
        """, (id_region,))
        stats = cursor.fetchone()
        for key in stats:
            if hasattr(stats[key], 'real'):
                stats[key] = float(stats[key])
        
        # Evolución mensual del estado
        cursor.execute("""
            SELECT 
                DATE_FORMAT(fecha_inicio, '%Y-%m') as mes,
                SUM(casos_confirmados) as casos
            FROM dato_epidemiologico
            WHERE id_region = %s
            GROUP BY DATE_FORMAT(fecha_inicio, '%Y-%m')
            ORDER BY mes
        """, (id_region,))
        evolucion = cursor.fetchall()
        for item in evolucion:
            for key in item:
                if hasattr(item[key], 'real'):
                    item[key] = float(item[key])
        
        return jsonify({
            'success': True,
            'estado': estado_info['nombre'],
            'id_region': id_region,
            'estadisticas': stats,
            'evolucion_mensual': evolucion
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        cursor.close()
        conn.close()


# ============================================
# ENDPOINTS PARA GUARDAR/LISTAR PREDICCIONES
# ============================================

def crear_tabla_predicciones():
    """Crea la tabla predicciones_guardadas si no existe"""
    conn = get_db_connection()
    if not conn:
        return False
    try:
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS predicciones_guardadas (
                id INT AUTO_INCREMENT PRIMARY KEY,
                fecha_generacion DATETIME NOT NULL,
                nombre_lote VARCHAR(100),
                estado VARCHAR(100) NOT NULL,
                id_region INT,
                fecha_inicio DATE NOT NULL,
                numero_semanas INT NOT NULL,
                datos_prediccion JSON NOT NULL,
                datos_validacion JSON,
                metricas JSON,
                usuario VARCHAR(100) DEFAULT 'sistema',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                INDEX idx_fecha_gen (fecha_generacion),
                INDEX idx_estado (estado)
            )
        """)
        conn.commit()
        return True
    except Exception as e:
        print(f"Error creando tabla: {e}")
        return False
    finally:
        cursor.close()
        conn.close()


@app.route('/api/predicciones/guardar', methods=['POST'])
def guardar_prediccion():
    """Guarda una predicción en la base de datos"""
    import json
    
    data = request.json
    
    required = ['estado', 'fecha_inicio', 'numero_semanas', 'predicciones']
    if not all(k in data for k in required):
        return jsonify({'error': 'Faltan campos requeridos'}), 400
    
    conn = get_db_connection()
    if not conn:
        return jsonify({'error': 'Error de conexión a BD'}), 500
    
    try:
        cursor = conn.cursor()
        
        # Preparar datos
        fecha_gen = datetime.now()
        nombre_lote = data.get('nombre_lote', f"Predicción {fecha_gen.strftime('%Y-%m-%d %H:%M')}")
        
        cursor.execute("""
            INSERT INTO predicciones_guardadas 
            (fecha_generacion, nombre_lote, estado, id_region, fecha_inicio, 
             numero_semanas, datos_prediccion, datos_validacion, metricas, usuario)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """, (
            fecha_gen,
            nombre_lote,
            data['estado'],
            data.get('id_region'),
            data['fecha_inicio'],
            data['numero_semanas'],
            json.dumps(data['predicciones']),
            json.dumps(data.get('validacion', [])),
            json.dumps(data.get('metricas', {})),
            data.get('usuario', 'sistema')
        ))
        
        conn.commit()
        prediccion_id = cursor.lastrowid
        
        return jsonify({
            'success': True,
            'mensaje': 'Predicción guardada exitosamente',
            'id': prediccion_id,
            'nombre_lote': nombre_lote,
            'fecha_generacion': fecha_gen.isoformat()
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        cursor.close()
        conn.close()


@app.route('/api/predicciones/historial', methods=['GET'])
def listar_predicciones():
    """Lista todas las predicciones guardadas (para el ComboBox)"""
    conn = get_db_connection()
    if not conn:
        return jsonify({'error': 'Error de conexión'}), 500
    
    try:
        cursor = conn.cursor(dictionary=True)
        cursor.execute("""
            SELECT 
                id,
                fecha_generacion,
                nombre_lote,
                estado,
                fecha_inicio,
                numero_semanas,
                created_at
            FROM predicciones_guardadas
            ORDER BY fecha_generacion DESC
            LIMIT 100
        """)
        
        predicciones = cursor.fetchall()
        
        # Convertir fechas a string
        for p in predicciones:
            p['fecha_generacion'] = p['fecha_generacion'].isoformat() if p['fecha_generacion'] else None
            p['fecha_inicio'] = p['fecha_inicio'].isoformat() if p['fecha_inicio'] else None
            p['created_at'] = p['created_at'].isoformat() if p['created_at'] else None
        
        return jsonify({
            'success': True,
            'predicciones': predicciones,
            'total': len(predicciones)
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        cursor.close()
        conn.close()


@app.route('/api/predicciones/<int:id>', methods=['GET'])
def obtener_prediccion(id):
    """Obtiene una predicción específica con todos sus datos"""
    import json
    
    conn = get_db_connection()
    if not conn:
        return jsonify({'error': 'Error de conexión'}), 500
    
    try:
        cursor = conn.cursor(dictionary=True)
        cursor.execute("""
            SELECT * FROM predicciones_guardadas WHERE id = %s
        """, (id,))
        
        prediccion = cursor.fetchone()
        
        if not prediccion:
            return jsonify({'error': 'Predicción no encontrada'}), 404
        
        # Parsear JSON y convertir fechas
        prediccion['datos_prediccion'] = json.loads(prediccion['datos_prediccion']) if prediccion['datos_prediccion'] else []
        prediccion['datos_validacion'] = json.loads(prediccion['datos_validacion']) if prediccion['datos_validacion'] else []
        prediccion['metricas'] = json.loads(prediccion['metricas']) if prediccion['metricas'] else {}
        prediccion['fecha_generacion'] = prediccion['fecha_generacion'].isoformat() if prediccion['fecha_generacion'] else None
        prediccion['fecha_inicio'] = prediccion['fecha_inicio'].isoformat() if prediccion['fecha_inicio'] else None
        prediccion['created_at'] = prediccion['created_at'].isoformat() if prediccion['created_at'] else None
        
        return jsonify({
            'success': True,
            'prediccion': prediccion
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        cursor.close()
        conn.close()


@app.route('/api/predicciones/<int:id>', methods=['DELETE'])
def eliminar_prediccion(id):
    """Elimina una predicción"""
    conn = get_db_connection()
    if not conn:
        return jsonify({'error': 'Error de conexión'}), 500
    
    try:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM predicciones_guardadas WHERE id = %s", (id,))
        conn.commit()
        
        if cursor.rowcount == 0:
            return jsonify({'error': 'Predicción no encontrada'}), 404
        
        return jsonify({
            'success': True,
            'mensaje': 'Predicción eliminada'
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        cursor.close()
        conn.close()


# ============================================
# ENDPOINTS PARA GESTIÓN DE DATOS (CONFIGURACIÓN)
# ============================================

# Población 2025 por estado
POBLACION_2025 = {
    1: 1512400, 2: 3968300, 3: 850700, 4: 1011800, 5: 3328500, 6: 775100,
    7: 6000100, 8: 3998500, 9: 9386700, 10: 1913400, 11: 6555200, 12: 3724300,
    13: 3327600, 14: 8847600, 15: 18016500, 16: 4975800, 17: 2056000, 18: 1294800,
    19: 6231200, 20: 4432900, 21: 6886400, 22: 2603300, 23: 1989500, 24: 2931400,
    25: 3274600, 26: 3154100, 27: 2601900, 28: 3682900, 29: 1421000, 30: 8871300,
    31: 2561900, 32: 1698200
}

@app.route('/api/datos/estadisticas', methods=['GET'])
def get_estadisticas_datos():
    """Obtiene estadísticas generales de los datos cargados"""
    conn = get_db_connection()
    if not conn:
        return jsonify({'error': 'Error de conexión'}), 500
    
    try:
        cursor = conn.cursor(dictionary=True)
        
        # Total registros
        cursor.execute("SELECT COUNT(*) as total FROM dato_epidemiologico")
        total_registros = cursor.fetchone()['total']
        
        # Rango de fechas
        cursor.execute("SELECT MIN(fecha_fin_semana) as fecha_min, MAX(fecha_fin_semana) as fecha_max FROM dato_epidemiologico")
        rango = cursor.fetchone()
        
        # Total casos
        cursor.execute("SELECT COALESCE(SUM(casos_confirmados), 0) as total FROM dato_epidemiologico")
        total_casos = cursor.fetchone()['total']
        
        # Por año
        cursor.execute("""
            SELECT YEAR(fecha_fin_semana) as anio, 
                   COUNT(*) as registros,
                   SUM(casos_confirmados) as casos
            FROM dato_epidemiologico 
            GROUP BY YEAR(fecha_fin_semana) 
            ORDER BY anio
        """)
        por_anio = cursor.fetchall()
        
        # Regiones con datos
        cursor.execute("SELECT COUNT(DISTINCT id_region) as total FROM dato_epidemiologico")
        regiones_con_datos = cursor.fetchone()['total']
        
        # Última carga
        cursor.execute("SELECT MAX(fecha_carga) as ultima FROM dato_epidemiologico")
        ultima_carga = cursor.fetchone()['ultima']
        
        return jsonify({
            'success': True,
            'total_registros': total_registros,
            'total_casos': int(total_casos) if total_casos else 0,
            'fecha_inicio': rango['fecha_min'].isoformat() if rango['fecha_min'] else None,
            'fecha_fin': rango['fecha_max'].isoformat() if rango['fecha_max'] else None,
            'regiones_con_datos': regiones_con_datos,
            'ultima_carga': ultima_carga.isoformat() if ultima_carga else None,
            'por_anio': por_anio
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        cursor.close()
        conn.close()


@app.route('/api/datos/procesar-csv', methods=['POST'])
def procesar_csv_preview():
    """Procesa un archivo CSV y devuelve preview sin guardar en BD"""
    if 'archivo' not in request.files:
        return jsonify({'error': 'No se envió ningún archivo'}), 400
    
    archivo = request.files['archivo']
    if archivo.filename == '':
        return jsonify({'error': 'Nombre de archivo vacío'}), 400
    
    if not archivo.filename.endswith('.csv'):
        return jsonify({'error': 'Solo se permiten archivos CSV'}), 400
    
    try:
        # Leer CSV
        df = pd.read_csv(archivo)
        registros_originales = len(df)
        
        # Validar columnas requeridas
        columnas_requeridas = ['FECHA_SIGN_SINTOMAS', 'ENTIDAD_RES', 'ESTATUS_CASO']
        columnas_faltantes = [c for c in columnas_requeridas if c not in df.columns]
        if columnas_faltantes:
            return jsonify({
                'success': False,
                'error': f'Columnas faltantes: {", ".join(columnas_faltantes)}',
                'columnas_encontradas': list(df.columns)
            }), 400
        
        # Procesar datos
        df['FECHA_SIGN_SINTOMAS'] = pd.to_datetime(df['FECHA_SIGN_SINTOMAS'], errors='coerce')
        df.dropna(subset=['FECHA_SIGN_SINTOMAS'], inplace=True)
        df_confirmados = df[df['ESTATUS_CASO'] == 1].copy()
        
        if len(df_confirmados) == 0:
            return jsonify({
                'success': False,
                'error': 'No hay casos confirmados (ESTATUS_CASO=1) en el archivo',
                'registros_totales': registros_originales
            }), 400
        
        # Agregar población y nombre de estado
        df_confirmados['POBLACION'] = df_confirmados['ENTIDAD_RES'].map(POBLACION_2025)
        df_confirmados.dropna(subset=['POBLACION'], inplace=True)
        df_confirmados['NOMBRE_ESTADO'] = df_confirmados['ENTIDAD_RES'].map(ESTADO_POR_ID)
        
        # Agregar a series de tiempo (semanal)
        df_ts = (
            df_confirmados.groupby(['ENTIDAD_RES', 'NOMBRE_ESTADO', 'POBLACION'])
            .resample('W', on='FECHA_SIGN_SINTOMAS')
            .size()
            .reset_index(name='casos_confirmados')
        )
        df_ts.rename(columns={'FECHA_SIGN_SINTOMAS': 'fecha_fin_semana'}, inplace=True)
        
        # Calcular tasa de incidencia
        df_ts['tasa_incidencia'] = (df_ts['casos_confirmados'] / df_ts['POBLACION']) * 100000
        
        # Calcular target de riesgo (percentil 75)
        umbral_riesgo = df_ts['tasa_incidencia'].quantile(0.75)
        df_ts['riesgo_brote_target'] = np.where(df_ts['tasa_incidencia'] > umbral_riesgo, 1, 0).astype(int)
        
        # Preparar preview (primeros 10 registros)
        preview_data = []
        for _, row in df_ts.head(10).iterrows():
            preview_data.append({
                'estado': row['NOMBRE_ESTADO'],
                'id_region': int(row['ENTIDAD_RES']),
                'fecha_fin_semana': row['fecha_fin_semana'].strftime('%Y-%m-%d'),
                'casos_confirmados': int(row['casos_confirmados']),
                'tasa_incidencia': round(float(row['tasa_incidencia']), 4),
                'riesgo_brote': bool(row['riesgo_brote_target'] == 1)
            })
        
        # Estadísticas del procesamiento
        años_procesados = sorted(df_ts['fecha_fin_semana'].dt.year.unique().tolist())
        estados_procesados = df_ts['NOMBRE_ESTADO'].unique().tolist()
        fecha_inicio = df_ts['fecha_fin_semana'].min().strftime('%Y-%m-%d')
        fecha_fin = df_ts['fecha_fin_semana'].max().strftime('%Y-%m-%d')
        
        return jsonify({
            'success': True,
            'resumen': {
                'registros_originales': registros_originales,
                'casos_confirmados': len(df_confirmados),
                'registros_procesados': len(df_ts),
                'estados_procesados': len(estados_procesados),
                'años': años_procesados,
                'fecha_inicio': fecha_inicio,
                'fecha_fin': fecha_fin,
                'umbral_riesgo_ti': round(float(umbral_riesgo), 4)
            },
            'preview': preview_data
        })
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/datos/cargar-csv', methods=['POST'])
def cargar_csv():
    """Carga un archivo CSV con datos de dengue y los procesa"""
    if 'archivo' not in request.files:
        return jsonify({'error': 'No se envió ningún archivo'}), 400
    
    archivo = request.files['archivo']
    if archivo.filename == '':
        return jsonify({'error': 'Nombre de archivo vacío'}), 400
    
    if not archivo.filename.endswith('.csv'):
        return jsonify({'error': 'Solo se permiten archivos CSV'}), 400
    
    conn = get_db_connection()
    if not conn:
        return jsonify({'error': 'Error de conexión a base de datos'}), 500
    
    try:
        # Leer CSV
        df = pd.read_csv(archivo)
        registros_originales = len(df)
        
        # Validar columnas requeridas
        columnas_requeridas = ['FECHA_SIGN_SINTOMAS', 'ENTIDAD_RES', 'ESTATUS_CASO']
        columnas_faltantes = [c for c in columnas_requeridas if c not in df.columns]
        if columnas_faltantes:
            return jsonify({
                'error': f'Columnas faltantes: {", ".join(columnas_faltantes)}',
                'columnas_encontradas': list(df.columns)
            }), 400
        
        # Procesar datos
        df['FECHA_SIGN_SINTOMAS'] = pd.to_datetime(df['FECHA_SIGN_SINTOMAS'], errors='coerce')
        df.dropna(subset=['FECHA_SIGN_SINTOMAS'], inplace=True)
        df_confirmados = df[df['ESTATUS_CASO'] == 1].copy()
        
        if len(df_confirmados) == 0:
            return jsonify({
                'error': 'No hay casos confirmados (ESTATUS_CASO=1) en el archivo',
                'registros_totales': registros_originales
            }), 400
        
        # Agregar población
        df_confirmados['POBLACION'] = df_confirmados['ENTIDAD_RES'].map(POBLACION_2025)
        df_confirmados.dropna(subset=['POBLACION'], inplace=True)
        
        # Agregar nombre de estado
        df_confirmados['NOMBRE_ESTADO'] = df_confirmados['ENTIDAD_RES'].map(ESTADO_POR_ID)
        
        # Agregar a series de tiempo (semanal)
        df_ts = (
            df_confirmados.groupby(['ENTIDAD_RES', 'NOMBRE_ESTADO', 'POBLACION'])
            .resample('W', on='FECHA_SIGN_SINTOMAS')
            .size()
            .reset_index(name='casos_confirmados')
        )
        df_ts.rename(columns={'FECHA_SIGN_SINTOMAS': 'fecha_fin_semana'}, inplace=True)
        
        # Calcular tasa de incidencia
        df_ts['tasa_incidencia'] = (df_ts['casos_confirmados'] / df_ts['POBLACION']) * 100000
        
        # Calcular target de riesgo (percentil 75)
        umbral_riesgo = df_ts['tasa_incidencia'].quantile(0.75)
        df_ts['riesgo_brote_target'] = np.where(df_ts['tasa_incidencia'] > umbral_riesgo, 1, 0).astype(int)
        
        # Preparar para inserción
        cursor = conn.cursor()
        fecha_carga = datetime.now().date()
        
        insert_sql = """
        INSERT INTO dato_epidemiologico 
            (id_enfermedad, id_region, fecha_fin_semana, casos_confirmados, 
             defunciones, tasa_incidencia, riesgo_brote_target, fecha_carga)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        ON DUPLICATE KEY UPDATE 
            casos_confirmados = VALUES(casos_confirmados), 
            tasa_incidencia = VALUES(tasa_incidencia),
            riesgo_brote_target = VALUES(riesgo_brote_target),
            fecha_carga = VALUES(fecha_carga)
        """
        
        registros_insertados = 0
        for _, row in df_ts.iterrows():
            cursor.execute(insert_sql, (
                1,  # id_enfermedad (Dengue)
                int(row['ENTIDAD_RES']),
                row['fecha_fin_semana'].date(),
                int(row['casos_confirmados']),
                0,  # defunciones
                round(float(row['tasa_incidencia']), 4),
                int(row['riesgo_brote_target']),
                fecha_carga
            ))
            registros_insertados += 1
        
        conn.commit()
        
        # Estadísticas del archivo procesado
        años_procesados = df_ts['fecha_fin_semana'].dt.year.unique().tolist()
        estados_procesados = df_ts['NOMBRE_ESTADO'].unique().tolist()
        
        return jsonify({
            'success': True,
            'mensaje': f'Datos cargados exitosamente',
            'estadisticas': {
                'registros_originales': registros_originales,
                'casos_confirmados': len(df_confirmados),
                'registros_insertados': registros_insertados,
                'años_procesados': sorted(años_procesados),
                'estados_procesados': len(estados_procesados),
                'fecha_carga': fecha_carga.isoformat()
            }
        })
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500
    finally:
        cursor.close()
        conn.close()


@app.route('/api/datos/limpiar', methods=['DELETE'])
def limpiar_datos():
    """Elimina todos los datos epidemiológicos (usar con precaución)"""
    conn = get_db_connection()
    if not conn:
        return jsonify({'error': 'Error de conexión'}), 500
    
    try:
        cursor = conn.cursor()
        
        # Contar antes de eliminar
        cursor.execute("SELECT COUNT(*) FROM dato_epidemiologico")
        registros_antes = cursor.fetchone()[0]
        
        # Eliminar datos
        cursor.execute("DELETE FROM dato_epidemiologico")
        conn.commit()
        
        return jsonify({
            'success': True,
            'mensaje': 'Datos eliminados',
            'registros_eliminados': registros_antes
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        cursor.close()
        conn.close()


@app.route('/api/datos/limpiar-anio/<int:anio>', methods=['DELETE'])
def limpiar_datos_anio(anio):
    """Elimina datos de un año específico"""
    conn = get_db_connection()
    if not conn:
        return jsonify({'error': 'Error de conexión'}), 500
    
    try:
        cursor = conn.cursor()
        
        # Contar antes de eliminar
        cursor.execute("SELECT COUNT(*) FROM dato_epidemiologico WHERE YEAR(fecha_fin_semana) = %s", (anio,))
        registros_antes = cursor.fetchone()[0]
        
        # Eliminar datos del año
        cursor.execute("DELETE FROM dato_epidemiologico WHERE YEAR(fecha_fin_semana) = %s", (anio,))
        conn.commit()
        
        return jsonify({
            'success': True,
            'mensaje': f'Datos del año {anio} eliminados',
            'registros_eliminados': registros_antes
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        cursor.close()
        conn.close()


@app.route('/api/datos/resumen-por-estado', methods=['GET'])
def resumen_por_estado():
    """Obtiene resumen de datos por estado"""
    conn = get_db_connection()
    if not conn:
        return jsonify({'error': 'Error de conexión'}), 500
    
    try:
        cursor = conn.cursor(dictionary=True)
        cursor.execute("""
            SELECT 
                r.id_region,
                r.nombre as estado,
                r.poblacion,
                COUNT(d.id_dato) as total_registros,
                COALESCE(SUM(d.casos_confirmados), 0) as total_casos,
                COALESCE(AVG(d.tasa_incidencia), 0) as promedio_ti,
                MIN(d.fecha_fin_semana) as fecha_inicio,
                MAX(d.fecha_fin_semana) as fecha_fin
            FROM region r
            LEFT JOIN dato_epidemiologico d ON r.id_region = d.id_region
            GROUP BY r.id_region, r.nombre, r.poblacion
            ORDER BY total_casos DESC
        """)
        estados = cursor.fetchall()
        
        for estado in estados:
            if estado['fecha_inicio']:
                estado['fecha_inicio'] = estado['fecha_inicio'].isoformat()
            if estado['fecha_fin']:
                estado['fecha_fin'] = estado['fecha_fin'].isoformat()
            if estado['promedio_ti']:
                estado['promedio_ti'] = float(estado['promedio_ti'])
        
        return jsonify({'success': True, 'estados': estados})
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        cursor.close()
        conn.close()


@app.route('/api/sistema/info', methods=['GET'])
def info_sistema():
    """Información del sistema y modelos"""
    return jsonify({
        'success': True,
        'sistema': {
            'nombre': 'ProeVira - Sistema de Predicción de Enfermedades',
            'version': '1.0.0',
            'base_datos': 'MySQL (proyecto_integrador)'
        },
        'modelos': {
            'clasificador': {
                'nombre': 'Random Forest Classifier',
                'archivo': 'model.pkl',
                'cargado': MODELO_DENGUE is not None,
                'features': MODELO_DENGUE.n_features_in_ if MODELO_DENGUE else None
            },
            'regresor': {
                'nombre': 'Random Forest Regressor',
                'archivo': 'model_regressor.pkl',
                'cargado': MODELO_REGRESSOR is not None,
                'r2_score': '96.3%' if MODELO_REGRESSOR else None
            }
        },
        'conexion_db': connection_pool is not None
    })


# ============================================
# ENDPOINTS PARA SISTEMA DE ALERTAS
# ============================================

def crear_tabla_alertas():
    """Crea la tabla de alertas si no existe"""
    conn = get_db_connection()
    if not conn:
        return False
    try:
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS alertas_epidemiologicas (
                id INT AUTO_INCREMENT PRIMARY KEY,
                id_region INT NOT NULL,
                estado VARCHAR(100) NOT NULL,
                nivel VARCHAR(20) NOT NULL,
                probabilidad FLOAT,
                casos_esperados INT,
                mensaje TEXT,
                recomendaciones TEXT,
                tipo_notificacion VARCHAR(50),
                prioridad VARCHAR(20),
                estado_alerta VARCHAR(20) DEFAULT 'activa',
                fecha_generacion DATETIME DEFAULT CURRENT_TIMESTAMP,
                fecha_envio DATETIME,
                fecha_resolucion DATETIME,
                resolucion TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                INDEX idx_region (id_region),
                INDEX idx_estado_alerta (estado_alerta),
                INDEX idx_nivel (nivel)
            )
        """)
        conn.commit()
        return True
    except Exception as e:
        print(f"Error creando tabla alertas: {e}")
        return False
    finally:
        cursor.close()
        conn.close()


@app.route('/api/alertas/generar-automaticas', methods=['POST'])
def generar_alertas_automaticas():
    """Genera alertas automáticas basadas en predicciones de riesgo"""
    conn = get_db_connection()
    if not conn:
        return jsonify({'error': 'Error de conexión'}), 500
    
    try:
        data = request.get_json() or {}
        umbral_riesgo = data.get('umbral_riesgo', 50)
        
        cursor = conn.cursor(dictionary=True)
        
        # Obtener todas las regiones
        cursor.execute("SELECT id_region, nombre, poblacion FROM region ORDER BY id_region")
        regiones = cursor.fetchall()
        
        alertas = []
        fecha_actual = datetime.now().strftime('%Y-%m-%d')
        
        for region in regiones:
            id_region = region['id_region']
            nombre = region['nombre']
            poblacion = region['poblacion'] or 100000
            
            # Obtener datos históricos recientes
            cursor.execute('''
                SELECT casos_confirmados, tasa_incidencia, fecha_fin_semana
                FROM dato_epidemiologico
                WHERE id_region = %s
                ORDER BY fecha_fin_semana DESC
                LIMIT 4
            ''', (id_region,))
            datos = cursor.fetchall()
            
            if len(datos) < 2:
                continue
            
            # Calcular tendencia y riesgo
            casos_reciente = datos[0]['casos_confirmados'] if datos else 0
            casos_anterior = datos[1]['casos_confirmados'] if len(datos) > 1 else casos_reciente
            ti_actual = float(datos[0]['tasa_incidencia']) if datos else 0
            
            # Tendencia
            if casos_reciente > casos_anterior * 1.2:
                tendencia = 'Creciente'
            elif casos_reciente < casos_anterior * 0.8:
                tendencia = 'Decreciente'
            else:
                tendencia = 'Estable'
            
            # Usar modelo de clasificación si está disponible
            if MODELO_DENGUE is not None:
                try:
                    casos_hist = [int(d['casos_confirmados']) for d in datos]
                    ti_hist = [float(d['tasa_incidencia']) for d in datos]
                    
                    casos_lag_1w = casos_hist[0]
                    casos_lag_4w = casos_hist[3] if len(casos_hist) > 3 else casos_lag_1w
                    ti_lag_1w = ti_hist[0]
                    ti_lag_4w = ti_hist[3] if len(ti_hist) > 3 else ti_lag_1w
                    
                    semana = datetime.now().isocalendar()[1]
                    mes = datetime.now().month
                    
                    try:
                        entidad_coded = LABEL_ENCODER.transform([nombre])[0]
                    except:
                        entidad_coded = id_region - 1
                    
                    X_predict = pd.DataFrame({
                        'TI_LAG_1W': [ti_lag_1w],
                        'TI_LAG_4W': [ti_lag_4w],
                        'CASOS_LAG_1W': [casos_lag_1w],
                        'CASOS_LAG_4W': [casos_lag_4w],
                        'SEMANA_DEL_ANIO': [semana],
                        'MES': [mes],
                        'ENTIDAD_CODED': [entidad_coded]
                    })
                    
                    probabilidad = round(MODELO_DENGUE.predict_proba(X_predict)[0][1] * 100, 1)
                except Exception as e:
                    probabilidad = min(100, max(0, ti_actual * 2))
            else:
                probabilidad = min(100, max(0, ti_actual * 2))
            
            # Solo incluir si supera el umbral
            if probabilidad < umbral_riesgo:
                continue
            
            # Determinar nivel de riesgo
            if probabilidad >= 75:
                nivel = 'Crítico'
                mensaje = f'ALERTA CRÍTICA: {nombre} presenta un riesgo muy alto de brote de dengue.'
                recomendaciones = 'Activar protocolos de emergencia. Intensificar fumigación. Desplegar brigadas de salud. Comunicar a la población.'
            elif probabilidad >= 50:
                nivel = 'Alto'
                mensaje = f'ADVERTENCIA: {nombre} presenta riesgo elevado de brote de dengue.'
                recomendaciones = 'Aumentar vigilancia epidemiológica. Iniciar campañas de descacharrización. Preparar recursos médicos.'
            elif probabilidad >= 25:
                nivel = 'Moderado'
                mensaje = f'PRECAUCIÓN: {nombre} muestra indicadores de riesgo moderado.'
                recomendaciones = 'Mantener vigilancia activa. Reforzar educación comunitaria sobre prevención.'
            else:
                nivel = 'Bajo'
                mensaje = f'{nombre}: Riesgo bajo de brote.'
                recomendaciones = 'Continuar con medidas preventivas habituales.'
            
            # Predicción de casos (si hay modelo de regresión)
            casos_esperados = casos_reciente
            if MODELO_REGRESSOR is not None:
                try:
                    X_reg = pd.DataFrame({
                        'casos_lag_1w': [casos_lag_1w],
                        'casos_lag_2w': [casos_hist[1] if len(casos_hist) > 1 else casos_lag_1w],
                        'casos_lag_3w': [casos_hist[2] if len(casos_hist) > 2 else casos_lag_1w],
                        'casos_lag_4w': [casos_lag_4w],
                        'ti_lag_1w': [ti_lag_1w],
                        'ti_lag_2w': [ti_hist[1] if len(ti_hist) > 1 else ti_lag_1w],
                        'casos_promedio_4w': [sum(casos_hist[:4]) / min(4, len(casos_hist))],
                        'tendencia_4w': [casos_lag_1w - casos_lag_4w],
                        'semana_anio': [semana],
                        'mes': [mes],
                        'estado_coded': [entidad_coded]
                    })
                    casos_esperados = int(max(0, MODELO_REGRESSOR.predict(X_reg)[0]))
                except:
                    pass
            
            alertas.append({
                'id_region': id_region,
                'estado': nombre,
                'nivel_riesgo': nivel,
                'probabilidad': probabilidad,
                'casos_esperados': casos_esperados,
                'casos_semana_actual': casos_reciente,
                'tendencia': tendencia,
                'mensaje': mensaje,
                'recomendaciones': recomendaciones,
                'fecha': fecha_actual,
                'enviada': False
            })
        
        # Ordenar por probabilidad descendente
        alertas.sort(key=lambda x: x['probabilidad'], reverse=True)
        
        return jsonify({
            'success': True,
            'alertas': alertas,
            'total': len(alertas),
            'umbral_usado': umbral_riesgo,
            'fecha_analisis': fecha_actual
        })
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500
    finally:
        cursor.close()
        conn.close()


@app.route('/api/alertas/enviar', methods=['POST'])
def enviar_alerta():
    """Envía una alerta a una entidad federativa y la guarda en BD"""
    conn = get_db_connection()
    if not conn:
        return jsonify({'error': 'Error de conexión'}), 500
    
    try:
        data = request.get_json()
        
        cursor = conn.cursor()
        
        # Insertar alerta en la base de datos
        cursor.execute("""
            INSERT INTO alertas_epidemiologicas 
            (id_region, estado, nivel, probabilidad, casos_esperados, 
             mensaje, recomendaciones, tipo_notificacion, prioridad, 
             estado_alerta, fecha_envio)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, 'enviada', NOW())
        """, (
            data.get('id_region'),
            data.get('estado'),
            data.get('nivel_riesgo'),
            data.get('probabilidad'),
            data.get('casos_esperados'),
            data.get('mensaje'),
            data.get('recomendaciones'),
            data.get('tipo_notificacion', 'sistema'),
            data.get('prioridad', 'alta')
        ))
        
        conn.commit()
        alerta_id = cursor.lastrowid
        
        # Aquí se integraría con servicio de email/SMS real
        # Por ahora solo simulamos el envío
        
        return jsonify({
            'success': True,
            'mensaje': f'Alerta enviada exitosamente a {data.get("estado")}',
            'alerta_id': alerta_id,
            'tipo_envio': data.get('tipo_notificacion', 'sistema')
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        cursor.close()
        conn.close()


@app.route('/api/alertas/enviar-masivo', methods=['POST'])
def enviar_alertas_masivo():
    """Envía múltiples alertas"""
    conn = get_db_connection()
    if not conn:
        return jsonify({'error': 'Error de conexión'}), 500
    
    try:
        data = request.get_json()
        alertas = data.get('alertas', [])
        
        cursor = conn.cursor()
        enviadas = 0
        
        for alerta in alertas:
            cursor.execute("""
                INSERT INTO alertas_epidemiologicas 
                (id_region, estado, nivel, probabilidad, casos_esperados, 
                 mensaje, recomendaciones, tipo_notificacion, prioridad, 
                 estado_alerta, fecha_envio)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, 'enviada', NOW())
            """, (
                alerta.get('id_region'),
                alerta.get('estado'),
                alerta.get('nivel_riesgo'),
                alerta.get('probabilidad'),
                alerta.get('casos_esperados'),
                alerta.get('mensaje'),
                alerta.get('recomendaciones'),
                data.get('tipo_notificacion', 'sistema'),
                data.get('prioridad', 'alta')
            ))
            enviadas += 1
        
        conn.commit()
        
        return jsonify({
            'success': True,
            'enviadas': enviadas,
            'mensaje': f'{enviadas} alertas enviadas exitosamente'
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        cursor.close()
        conn.close()


@app.route('/api/alertas/activas', methods=['GET'])
def get_alertas_activas():
    """Obtiene las alertas activas (no resueltas)"""
    conn = get_db_connection()
    if not conn:
        return jsonify({'error': 'Error de conexión'}), 500
    
    try:
        cursor = conn.cursor(dictionary=True)
        cursor.execute("""
            SELECT id, id_region, estado, nivel, probabilidad, 
                   casos_esperados, mensaje, recomendaciones,
                   fecha_generacion, fecha_envio, estado_alerta
            FROM alertas_epidemiologicas
            WHERE estado_alerta IN ('activa', 'enviada')
            ORDER BY 
                CASE nivel 
                    WHEN 'Crítico' THEN 1 
                    WHEN 'Alto' THEN 2 
                    WHEN 'Moderado' THEN 3 
                    ELSE 4 
                END,
                fecha_generacion DESC
        """)
        alertas = cursor.fetchall()
        
        for a in alertas:
            if a.get('fecha_generacion'):
                a['fecha_generacion'] = a['fecha_generacion'].isoformat()
            if a.get('fecha_envio'):
                a['fecha_envio'] = a['fecha_envio'].isoformat()
        
        return jsonify({
            'success': True,
            'alertas': alertas,
            'total': len(alertas)
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        cursor.close()
        conn.close()


@app.route('/api/alertas/historial', methods=['GET'])
def get_historial_alertas():
    """Obtiene el historial de alertas"""
    conn = get_db_connection()
    if not conn:
        return jsonify({'error': 'Error de conexión'}), 500
    
    try:
        cursor = conn.cursor(dictionary=True)
        cursor.execute("""
            SELECT id, id_region, estado, nivel, probabilidad, 
                   mensaje, estado_alerta, fecha_generacion, 
                   fecha_resolucion, resolucion
            FROM alertas_epidemiologicas
            ORDER BY fecha_generacion DESC
            LIMIT 100
        """)
        alertas = cursor.fetchall()
        
        for a in alertas:
            if a.get('fecha_generacion'):
                a['fecha_generacion'] = a['fecha_generacion'].isoformat()
            if a.get('fecha_resolucion'):
                a['fecha_resolucion'] = a['fecha_resolucion'].isoformat()
        
        return jsonify({
            'success': True,
            'alertas': alertas,
            'total': len(alertas)
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        cursor.close()
        conn.close()


@app.route('/api/alertas/<int:alerta_id>/resolver', methods=['PUT'])
def resolver_alerta(alerta_id):
    """Marca una alerta como resuelta"""
    conn = get_db_connection()
    if not conn:
        return jsonify({'error': 'Error de conexión'}), 500
    
    try:
        data = request.get_json() or {}
        resolucion = data.get('resolucion', 'Alerta atendida')
        
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE alertas_epidemiologicas
            SET estado_alerta = 'resuelta',
                fecha_resolucion = NOW(),
                resolucion = %s
            WHERE id = %s
        """, (resolucion, alerta_id))
        
        conn.commit()
        
        return jsonify({
            'success': True,
            'mensaje': 'Alerta marcada como resuelta'
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        cursor.close()
        conn.close()


# ============================================
# INICIO DEL SERVIDOR
# ============================================
if __name__ == '__main__':
    # Crear tablas si no existen
    crear_tabla_predicciones()
    crear_tabla_alertas()
    print("\n" + "="*60)
    print("🚀 API Flask - Predicción de Riesgo de Dengue")
    print("="*60)
    print("📊 Modelo: Random Forest (model.pkl + label_encoder.pkl)")
    print("🗄️  Base de datos: MySQL (proyecto_integrador)")
    print("📅 Datos: 2020-2025 (6 años)")
    print("\n📡 Endpoints:")
    print("   POST /api/modelo/predecir-riesgo-automatico")
    print("   POST /api/modelo/predecir-riesgo-avanzado")
    print("   POST /api/predicciones/guardar")
    print("   GET  /api/predicciones/historial")
    print("   GET  /api/predicciones/<id>")
    print("   DELETE /api/predicciones/<id>")
    print("   GET  /api/config/regiones")
    print("   GET  /api/config/enfermedades")
    print("   GET  /api/dashboard/resumen")
    print("   GET  /api/health")
    print("   POST /api/datos/procesar-csv")
    print("   POST /api/datos/cargar-csv")
    print("   GET  /api/datos/estadisticas")
    print("   GET  /api/datos/resumen-por-estado")
    print("   DELETE /api/datos/limpiar")
    print("   POST /api/alertas/generar-automaticas")
    print("   POST /api/alertas/enviar")
    print("   POST /api/alertas/enviar-masivo")
    print("   GET  /api/alertas/activas")
    print("   GET  /api/alertas/historial")
    print("   PUT  /api/alertas/<id>/resolver")
    print("="*60 + "\n")
    
    app.run(debug=False, port=5001, host='0.0.0.0', threaded=True)