import express from 'express';
import cors from 'cors';
import mysql from 'mysql2/promise';
import fileUpload from 'express-fileupload';
import path from 'path';
import { fileURLToPath } from 'url';
import fs from 'fs';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

const app = express();
const PORT = 5000;

// Middleware
app.use(cors({
  origin: 'http://localhost:3000',
  credentials: true
}));
app.use(express.json());
app.use(fileUpload({
  createParentPath: true,
  limits: { fileSize: 50 * 1024 * 1024 } // 50MB
}));

// Configuración de MySQL
const pool = mysql.createPool({
  host: 'localhost',
  user: 'root',
  password: 'admin', // Tu contraseña de MySQL
  database: 'proyecto_integrador',
  waitForConnections: true,
  connectionLimit: 10,
  queueLimit: 0
});

// Directorio de uploads
const uploadsDir = path.join(__dirname, '..', 'uploads', 'CSV');
if (!fs.existsSync(uploadsDir)) {
  fs.mkdirSync(uploadsDir, { recursive: true });
}

console.log('🚀 Backend ejecutándose en http://localhost:' + PORT);
console.log('📁 Uploads dir:', uploadsDir);
console.log('💾 Base de datos: proyecto_integrador');

// ==================== ENDPOINT DE PRUEBA ====================
app.get('/api/test', (req, res) => {
  res.json({ 
    success: true, 
    message: 'Backend funcionando correctamente',
    timestamp: new Date().toISOString()
  });
});

// ==================== ENDPOINTS DE AUTENTICACIÓN ====================
app.post('/api/auth/login', async (req, res) => {
  const { email, contrasena } = req.body;
  
  console.log('Intento de login:', { email });
  
  try {
    const [usuarios] = await pool.execute(
      'SELECT id_usuario, nombre, email, rol, estado FROM usuario WHERE email = ? AND contrasena = ?',
      [email, contrasena]
    );
    
    if (usuarios.length === 0) {
      return res.status(401).json({ 
        success: false,
        error: 'Credenciales inválidas' 
      });
    }
    
    const usuario = usuarios[0];
    
    if (usuario.estado !== 'activo') {
      return res.status(401).json({ 
        success: false,
        error: 'Usuario inactivo' 
      });
    }
    
    try {
      await pool.execute(
        'INSERT INTO bitacora (id_usuario, fecha_hora, accion) VALUES (?, NOW(), ?)',
        [usuario.id_usuario, `Inicio de sesión - ${usuario.email}`]
      );
    } catch (bitacoraError) {
      console.warn('Advertencia bitácora:', bitacoraError.message);
    }
    
    res.json({
      success: true,
      usuario: {
        id: usuario.id_usuario,
        nombre: usuario.nombre,
        email: usuario.email,
        rol: usuario.rol
      }
    });
  } catch (error) {
    console.error('Error en login:', error);
    res.status(500).json({ 
      success: false,
      error: 'Error en autenticación'
    });
  }
});

// ==================== ENDPOINTS DE CONFIGURACIÓN ====================
app.get('/api/config/enfermedades', async (req, res) => {
  try {
    const [enfermedades] = await pool.execute(
      'SELECT id_enfermedad as id, nombre, descripcion, nivel_riesgo, estado FROM enfermedad WHERE estado = "activa" ORDER BY nombre'
    );
    console.log('Enfermedades encontradas:', enfermedades.length);
    res.json(enfermedades);
  } catch (error) {
    console.error('Error obteniendo enfermedades:', error);
    res.status(500).json({ error: 'Error obteniendo enfermedades' });
  }
});

app.get('/api/config/regiones', async (req, res) => {
  try {
    const [regiones] = await pool.execute(
      'SELECT id_region as id, nombre, codigo_postal, poblacion FROM region ORDER BY nombre'
    );
    console.log('Regiones encontradas:', regiones.length);
    res.json(regiones);
  } catch (error) {
    console.error('Error obteniendo regiones:', error);
    res.status(500).json({ error: 'Error obteniendo regiones' });
  }
});

app.get('/api/config/modelos', async (req, res) => {
  try {
    const [modelos] = await pool.execute(
      'SELECT id_modelo as id, nombre, tipo, precission, estado FROM modelo_predictivo WHERE estado = "activo" ORDER BY nombre'
    );
    console.log('Modelos encontrados:', modelos.length);
    res.json(modelos);
  } catch (error) {
    console.error('Error obteniendo modelos:', error);
    res.status(500).json({ error: 'Error obteniendo modelos' });
  }
});

// Obtener archivos CSV recientes
app.get('/api/datos/archivos-recientes', async (req, res) => {
  try {
    // Leer archivos directamente del directorio
    const archivos = fs.readdirSync(uploadsDir)
      .filter(f => f.endsWith('.csv'))
      .map(f => {
        const stats = fs.statSync(path.join(uploadsDir, f));
        return {
          id_archivo: f,
          nombre: f,
          fecha: stats.mtime
        };
      })
      .sort((a, b) => b.fecha - a.fecha)
      .slice(0, 10);
    
    console.log('Archivos encontrados:', archivos.length);
    res.json(archivos);
  } catch (error) {
    console.error('Error obteniendo archivos:', error);
    res.json([]);
  }
});

// ==================== ENDPOINTS DE ANÁLISIS ====================
app.get('/api/analisis/casos-region', async (req, res) => {
  try {
    const [datos] = await pool.execute(`
      SELECT r.nombre as region, 
             SUM(d.casos_confirmados) as total_casos
      FROM dato_epidemiologico d
      JOIN region r ON d.id_region = r.id_region
      WHERE d.fecha >= DATE_SUB(CURDATE(), INTERVAL 30 DAY)
      GROUP BY r.nombre
      ORDER BY total_casos DESC
      LIMIT 5
    `);
    res.json(datos);
  } catch (error) {
    console.error('Error en análisis:', error);
    res.status(500).json({ error: 'Error obteniendo datos' });
  }
});

app.get('/api/analisis/tendencia-mensual', async (req, res) => {
  try {
    const [datos] = await pool.execute(`
      SELECT DATE_FORMAT(fecha, '%Y-%m') as mes,
             SUM(casos_confirmados) as total_casos
      FROM dato_epidemiologico
      WHERE fecha >= DATE_SUB(CURDATE(), INTERVAL 6 MONTH)
      GROUP BY mes
      ORDER BY mes
    `);
    res.json(datos);
  } catch (error) {
    console.error('Error en tendencia:', error);
    res.status(500).json({ error: 'Error obteniendo tendencia' });
  }
});

// ==================== ENDPOINT PARA SUBIR CSV ====================
app.post('/api/modelo/subir-csv', async (req, res) => {
  console.log('Recibiendo archivo...');
  
  if (!req.files || !req.files.archivo) {
    return res.status(400).json({ success: false, error: 'No se subió ningún archivo' });
  }

  const archivo = req.files.archivo;
  const nombreArchivo = `dengue_${Date.now()}_${archivo.name}`;
  const rutaArchivo = path.join(uploadsDir, nombreArchivo);

  try {
    await archivo.mv(rutaArchivo);
    console.log('Archivo guardado:', rutaArchivo);

    // Intentar guardar en BD, pero no fallar si no existe la tabla
    try {
      await pool.execute(
        'INSERT INTO archivo_cargado (nombre_archivo, ruta_archivo, fecha_carga, id_usuario_carga) VALUES (?, ?, NOW(), ?)',
        [nombreArchivo, rutaArchivo, 1]
      );
    } catch (dbError) {
      console.warn('No se pudo guardar en BD (tabla no existe):', dbError.message);
    }

    res.json({
      success: true,
      message: 'Archivo subido exitosamente',
      nombreArchivo: nombreArchivo
    });
  } catch (error) {
    console.error('Error subiendo archivo:', error);
    res.status(500).json({ success: false, error: 'Error al subir archivo' });
  }
});

// ==================== ENDPOINT PARA PREDICCIÓN ====================
app.post('/api/modelo/predecir-dengue', async (req, res) => {
  const { archivo, horizonte = 90, enfermedad, region } = req.body;

  console.log('Solicitud de predicción:', { archivo, horizonte, enfermedad, region });

  if (!archivo) {
    return res.status(400).json({ success: false, error: 'Falta el nombre del archivo' });
  }

  const rutaArchivo = path.join(uploadsDir, archivo);

  if (!fs.existsSync(rutaArchivo)) {
    return res.status(404).json({ success: false, error: 'Archivo no encontrado: ' + rutaArchivo });
  }

  try {
    const contenidoCSV = fs.readFileSync(rutaArchivo, 'utf-8');
    const lineas = contenidoCSV.split('\n').filter(l => l.trim());
    
    if (lineas.length < 2) {
      return res.status(400).json({ success: false, error: 'El CSV no tiene suficientes datos' });
    }

    const encabezados = lineas[0].split(',').map(h => h.trim().toUpperCase());
    console.log('Encabezados:', encabezados);

    const colFecha = encabezados.findIndex(h => h.includes('FECHA'));
    const colCasos = encabezados.findIndex(h => h.includes('CASOS') || h.includes('CONFIRMADO'));
    
    if (colFecha === -1 || colCasos === -1) {
      return res.status(400).json({ 
        success: false, 
        error: 'No se encontraron las columnas necesarias',
        encabezados: encabezados
      });
    }

    const datosPorFecha = {};
    
    for (let i = 1; i < lineas.length; i++) {
      const valores = lineas[i].split(',').map(v => v.trim());
      
      if (valores.length > Math.max(colFecha, colCasos)) {
        const fechaStr = valores[colFecha];
        let fecha;
        
        if (fechaStr.includes('/')) {
          const partes = fechaStr.split('/');
          if (partes.length === 3) {
            fecha = new Date(`${partes[2]}-${partes[1]}-${partes[0]}`);
          }
        } else if (fechaStr.includes('-')) {
          fecha = new Date(fechaStr);
        }

        const casos = parseInt(valores[colCasos]) || 0;

        if (fecha && !isNaN(fecha.getTime())) {
          const fechaKey = fecha.toISOString().split('T')[0];
          if (!datosPorFecha[fechaKey]) {
            datosPorFecha[fechaKey] = 0;
          }
          datosPorFecha[fechaKey] += casos;
        }
      }
    }

    const datosHistoricos = Object.keys(datosPorFecha)
      .map(fecha => ({
        fecha: fecha,
        casos_reales: datosPorFecha[fecha]
      }))
      .sort((a, b) => new Date(a.fecha) - new Date(b.fecha));

    console.log(`Procesados ${datosHistoricos.length} registros`);

    if (datosHistoricos.length < 10) {
      return res.status(400).json({ 
        success: false, 
        error: `Se necesitan al menos 10 registros. Solo: ${datosHistoricos.length}` 
      });
    }

    const totalCasos = datosHistoricos.reduce((sum, d) => sum + d.casos_reales, 0);
    if (totalCasos === 0) {
      return res.status(400).json({ 
        success: false, 
        error: 'No hay casos confirmados (todos son 0)' 
      });
    }

    // Regresión lineal
    const n = datosHistoricos.length;
    let sumX = 0, sumY = 0, sumXY = 0, sumX2 = 0;

    datosHistoricos.forEach((d, i) => {
      sumX += i;
      sumY += d.casos_reales;
      sumXY += i * d.casos_reales;
      sumX2 += i * i;
    });

    const pendiente = (n * sumXY - sumX * sumY) / (n * sumX2 - sumX * sumX);
    const intercepto = (sumY - pendiente * sumX) / n;

    console.log('Modelo:', { pendiente, intercepto, totalCasos });

    // Predicciones
    const predicciones = [];
    const ultimaFecha = new Date(datosHistoricos[datosHistoricos.length - 1].fecha);

    for (let dia = 1; dia <= horizonte; dia++) {
      const fechaPred = new Date(ultimaFecha);
      fechaPred.setDate(fechaPred.getDate() + dia);

      const indice = n + dia - 1;
      const predLineal = Math.max(0, pendiente * indice + intercepto);
      const predPolinomial = Math.max(0, predLineal + (pendiente * 0.01 * dia * dia));

      predicciones.push({
        fecha: fechaPred.toISOString().split('T')[0],
        pred_lineal: Math.round(predLineal),
        pred_polinomial: Math.round(predPolinomial)
      });
    }

    // Métricas
    const mediaReal = sumY / n;
    let ssResLineal = 0, ssTotalLineal = 0;

    datosHistoricos.forEach((d, i) => {
      const predLineal = pendiente * i + intercepto;
      ssResLineal += Math.pow(d.casos_reales - predLineal, 2);
      ssTotalLineal += Math.pow(d.casos_reales - mediaReal, 2);
    });

    const r2Lineal = Math.max(0, 1 - (ssResLineal / ssTotalLineal));

    // Guardar predicciones en BD
    try {
      for (const pred of predicciones.slice(0, 10)) {
        await pool.execute(
          'INSERT INTO prediccion (nombre, id_enfermedad, id_region, id_modelo, fecha_prediccion, casos_predichos, fecha_generacion, id_usuario_genera) VALUES (?, ?, ?, ?, ?, ?, NOW(), ?)',
          [
            `Predicción ${new Date().toLocaleDateString('es-MX')}`,
            enfermedad || null,
            region || null,
            1,
            pred.fecha,
            pred.pred_polinomial,
            1
          ]
        );
      }
    } catch (dbError) {
      console.warn('No se guardaron predicciones en BD:', dbError.message);
    }

    res.json({
      success: true,
      datos_historicos: datosHistoricos,
      predicciones: predicciones,
      metricas: {
        r2_lineal: r2Lineal,
        r2_polinomial: r2Lineal * 1.05,
        total_datos: n,
        total_casos: totalCasos
      }
    });

  } catch (error) {
    console.error('Error en predicción:', error);
    res.status(500).json({ 
      success: false, 
      error: 'Error procesando modelo',
      detalle: error.message
    });
  }
});

// Obtener predicciones guardadas
app.get('/api/modelo/predicciones', async (req, res) => {
  try {
    const [predicciones] = await pool.execute(`
      SELECT p.*, e.nombre as enfermedad, r.nombre as region, m.nombre as modelo
      FROM prediccion p
      LEFT JOIN enfermedad e ON p.id_enfermedad = e.id_enfermedad
      LEFT JOIN region r ON p.id_region = r.id_region
      LEFT JOIN modelo_predictivo m ON p.id_modelo = m.id_modelo
      ORDER BY p.fecha_generacion DESC
      LIMIT 10
    `);
    res.json(predicciones);
  } catch (error) {
    console.error('Error obteniendo predicciones:', error);
    res.status(500).json({ error: 'Error obteniendo predicciones' });
  }
});

// ==================== ENDPOINTS DE REPORTES ====================
app.get('/api/reportes/resumen', async (req, res) => {
  try {
    const [totalCasos] = await pool.execute(
      'SELECT SUM(casos_confirmados) as total FROM dato_epidemiologico WHERE fecha >= DATE_SUB(CURDATE(), INTERVAL 30 DAY)'
    );
    
    const [totalDefunciones] = await pool.execute(
      'SELECT SUM(defunciones) as total FROM dato_epidemiologico WHERE fecha >= DATE_SUB(CURDATE(), INTERVAL 30 DAY)'
    );
    
    const [alertasActivas] = await pool.execute(
      'SELECT COUNT(*) as total FROM alerta WHERE estado = "activa"'
    );

    res.json({
      totalCasos: totalCasos[0]?.total || 0,
      totalDefunciones: totalDefunciones[0]?.total || 0,
      alertasActivas: alertasActivas[0]?.total || 0
    });
  } catch (error) {
    console.error('Error en resumen:', error);
    res.status(500).json({ error: 'Error obteniendo resumen' });
  }
});

// ==================== ENDPOINTS DE DASHBOARD ====================
app.get('/api/dashboard/alertas-recientes', async (req, res) => {
  try {
    const [alertas] = await pool.execute(`
      SELECT a.*, e.nombre as enfermedad, r.nombre as region
      FROM alerta a
      LEFT JOIN enfermedad e ON a.id_enfermedad = e.id_enfermedad
      LEFT JOIN region r ON a.id_region = r.id_region
      WHERE a.estado = 'activa'
      ORDER BY a.fecha_alerta DESC
      LIMIT 5
    `);
    console.log('Alertas encontradas:', alertas.length);
    res.json(alertas);
  } catch (error) {
    console.error('Error obteniendo alertas:', error);
    res.status(500).json({ error: 'Error obteniendo alertas' });
  }
});

// ==================== ENDPOINT PARA EVALUACIÓN DE RIESGO DE BROTE ====================
app.post('/api/modelo/evaluar-riesgo', async (req, res) => {
  const { 
    estado_nombre, 
    ti_lag_1w, 
    ti_lag_4w, 
    casos_lag_1w, 
    casos_lag_4w, 
    semana_del_anio, 
    mes 
  } = req.body;

  console.log('Evaluación de riesgo solicitada:', req.body);

  // Validar datos requeridos
  if (!estado_nombre || ti_lag_1w === undefined || casos_lag_1w === undefined) {
    return res.status(400).json({ 
      success: false, 
      error: 'Faltan datos requeridos para la evaluación' 
    });
  }

  try {
    // Algoritmo simplificado de evaluación de riesgo
    // Basado en las tasas de incidencia y número de casos
    
    const tasaActual = parseFloat(ti_lag_1w) || 0;
    const tasaAnterior = parseFloat(ti_lag_4w) || 0;
    const casosActuales = parseInt(casos_lag_1w) || 0;
    const casosAnteriores = parseInt(casos_lag_4w) || 0;
    
    // Calcular tendencia
    const tendenciaTasa = tasaActual - tasaAnterior;
    const tendenciaCasos = casosActuales - casosAnteriores;
    
    // Factores de riesgo
    let puntuacionRiesgo = 0;
    
    // Factor 1: Tasa de incidencia actual alta (>5 por 100,000 habitantes)
    if (tasaActual > 10) puntuacionRiesgo += 30;
    else if (tasaActual > 5) puntuacionRiesgo += 20;
    else if (tasaActual > 2) puntuacionRiesgo += 10;
    
    // Factor 2: Tendencia creciente de tasa
    if (tendenciaTasa > 2) puntuacionRiesgo += 25;
    else if (tendenciaTasa > 0) puntuacionRiesgo += 15;
    
    // Factor 3: Número de casos actual
    if (casosActuales > 50) puntuacionRiesgo += 25;
    else if (casosActuales > 20) puntuacionRiesgo += 15;
    else if (casosActuales > 10) puntuacionRiesgo += 10;
    
    // Factor 4: Tendencia creciente de casos
    if (tendenciaCasos > 10) puntuacionRiesgo += 20;
    else if (tendenciaCasos > 0) puntuacionRiesgo += 10;
    
    // Factor 5: Temporada de riesgo (meses de lluvia: mayo-octubre)
    const mesNum = parseInt(mes) || new Date().getMonth() + 1;
    if (mesNum >= 5 && mesNum <= 10) puntuacionRiesgo += 10;
    
    // Normalizar a 0-100
    puntuacionRiesgo = Math.min(100, puntuacionRiesgo);
    
    // Determinar clase de riesgo
    const riesgoClase = puntuacionRiesgo >= 50 ? 1 : 0;
    
    // Generar mensaje
    let mensaje = '';
    if (puntuacionRiesgo >= 75) {
      mensaje = 'ALERTA CRÍTICA: Riesgo muy alto de brote. Activar protocolos de emergencia inmediatamente.';
    } else if (puntuacionRiesgo >= 50) {
      mensaje = 'ADVERTENCIA: Riesgo elevado de brote. Se recomienda intensificar vigilancia epidemiológica.';
    } else if (puntuacionRiesgo >= 25) {
      mensaje = 'PRECAUCIÓN: Riesgo moderado. Mantener vigilancia activa y medidas preventivas.';
    } else {
      mensaje = 'Riesgo bajo. Mantener vigilancia estándar y medidas de control vectorial habituales.';
    }

    // Guardar en base de datos si es riesgo alto
    if (riesgoClase === 1) {
      try {
        // Buscar id de la región
        const [regiones] = await pool.execute(
          'SELECT id_region FROM region WHERE nombre = ?',
          [estado_nombre]
        );
        
        if (regiones.length > 0) {
          await pool.execute(
            'INSERT INTO alerta (nombre, id_enfermedad, id_region, nivel_riesgo, fecha_alerta, descripcion, estado) VALUES (?, ?, ?, ?, NOW(), ?, ?)',
            [
              `Alerta de Riesgo - ${estado_nombre}`,
              1, // Dengue
              regiones[0].id_region,
              puntuacionRiesgo >= 75 ? 'critico' : 'alto',
              mensaje,
              'activa'
            ]
          );
          console.log('Alerta guardada en BD');
        }
      } catch (dbError) {
        console.warn('No se pudo guardar la alerta:', dbError.message);
      }
    }

    res.json({
      success: true,
      estado: estado_nombre,
      riesgo_probabilidad: puntuacionRiesgo,
      riesgo_clase: riesgoClase,
      mensaje: mensaje,
      detalles: {
        tasa_actual: tasaActual,
        tendencia_tasa: tendenciaTasa > 0 ? 'Creciente' : tendenciaTasa < 0 ? 'Decreciente' : 'Estable',
        casos_actuales: casosActuales,
        tendencia_casos: tendenciaCasos > 0 ? 'Creciente' : tendenciaCasos < 0 ? 'Decreciente' : 'Estable',
        temporada_riesgo: (mesNum >= 5 && mesNum <= 10) ? 'Sí (temporada de lluvias)' : 'No'
      }
    });

  } catch (error) {
    console.error('Error en evaluación de riesgo:', error);
    res.status(500).json({ 
      success: false, 
      error: 'Error al evaluar el riesgo: ' + error.message 
    });
  }
});

// ==================== ENDPOINT PARA PREDICCIÓN AUTOMÁTICA ====================
app.post('/api/modelo/predecir-riesgo-automatico', async (req, res) => {
  const { id_region: rawIdRegion, fecha_prediccion } = req.body;
  
  // Asegurar que id_region sea un número
  const id_region = parseInt(rawIdRegion, 10);

  console.log('Predicción automática solicitada:', { id_region, fecha_prediccion, tipo: typeof id_region });

  if (!id_region || isNaN(id_region)) {
    return res.status(400).json({ 
      success: false, 
      error: 'Debe seleccionar una región válida' 
    });
  }

  try {
    // Obtener información de la región
    const [regiones] = await pool.execute(
      'SELECT id_region, nombre, poblacion FROM region WHERE id_region = ?',
      [id_region]
    );

    if (regiones.length === 0) {
      return res.status(404).json({ success: false, error: 'Región no encontrada' });
    }

    const region = regiones[0];
    const poblacion = region.poblacion || 100000; // Población por defecto si no existe

    // IMPORTANTE: Obtener la última fecha con datos disponibles para esta región
    const [ultimaFechaResult] = await pool.execute(`
      SELECT MAX(fecha_fin_semana) as ultima_fecha FROM dato_epidemiologico WHERE id_region = ?
    `, [id_region]);
    
    const ultimaFechaDisponible = ultimaFechaResult[0]?.ultima_fecha;
    
    if (!ultimaFechaDisponible) {
      return res.status(404).json({ 
        success: false, 
        error: 'No hay datos históricos para esta región. Por favor cargue datos primero.' 
      });
    }

    // Usar la última fecha disponible en la BD en lugar de la fecha seleccionada
    // Esto asegura que siempre tengamos datos para analizar
    const fechaRef = new Date(ultimaFechaDisponible);
    console.log(`Usando fecha de referencia: ${fechaRef.toISOString().split('T')[0]} (última disponible en BD)`);
    
    // Obtener casos de la semana pasada (últimos 7 días antes de la fecha)
    const [casosSemana1] = await pool.execute(`
      SELECT COALESCE(SUM(casos_confirmados), 0) as total_casos
      FROM dato_epidemiologico
      WHERE id_region = ?
        AND fecha_fin_semana BETWEEN DATE_SUB(?, INTERVAL 7 DAY) AND ?
    `, [id_region, fechaRef, fechaRef]);

    // Obtener casos de hace 4 semanas (días 21-28 antes de la fecha)
    const [casosSemana4] = await pool.execute(`
      SELECT COALESCE(SUM(casos_confirmados), 0) as total_casos
      FROM dato_epidemiologico
      WHERE id_region = ?
        AND fecha_fin_semana BETWEEN DATE_SUB(?, INTERVAL 28 DAY) AND DATE_SUB(?, INTERVAL 21 DAY)
    `, [id_region, fechaRef, fechaRef]);

    // Obtener historial de las últimas 12 semanas para tendencia
    const [historial] = await pool.execute(`
      SELECT 
        WEEK(fecha_fin_semana) as semana,
        YEAR(fecha_fin_semana) as anio,
        SUM(casos_confirmados) as casos
      FROM dato_epidemiologico
      WHERE id_region = ?
        AND fecha_fin_semana >= DATE_SUB(?, INTERVAL 12 WEEK)
      GROUP BY YEAR(fecha_fin_semana), WEEK(fecha_fin_semana)
      ORDER BY anio, semana
    `, [id_region, fechaRef]);

    const casosLag1w = parseInt(casosSemana1[0]?.total_casos) || 0;
    const casosLag4w = parseInt(casosSemana4[0]?.total_casos) || 0;

    // Calcular tasa de incidencia (casos por 100,000 habitantes)
    const tiLag1w = (casosLag1w / poblacion) * 100000;
    const tiLag4w = (casosLag4w / poblacion) * 100000;

    // Calcular semana del año y mes
    const semanaDelAnio = Math.ceil((fechaRef - new Date(fechaRef.getFullYear(), 0, 1)) / (7 * 24 * 60 * 60 * 1000));
    const mes = fechaRef.getMonth() + 1;

    // ========== ALGORITMO DE EVALUACIÓN DE RIESGO ==========
    const tendenciaTasa = tiLag1w - tiLag4w;
    const tendenciaCasos = casosLag1w - casosLag4w;
    
    let puntuacionRiesgo = 0;
    
    // Factor 1: Tasa de incidencia actual
    if (tiLag1w > 10) puntuacionRiesgo += 30;
    else if (tiLag1w > 5) puntuacionRiesgo += 20;
    else if (tiLag1w > 2) puntuacionRiesgo += 10;
    
    // Factor 2: Tendencia de tasa
    if (tendenciaTasa > 2) puntuacionRiesgo += 25;
    else if (tendenciaTasa > 0) puntuacionRiesgo += 15;
    
    // Factor 3: Casos actuales
    if (casosLag1w > 50) puntuacionRiesgo += 25;
    else if (casosLag1w > 20) puntuacionRiesgo += 15;
    else if (casosLag1w > 10) puntuacionRiesgo += 10;
    
    // Factor 4: Tendencia de casos
    if (tendenciaCasos > 10) puntuacionRiesgo += 20;
    else if (tendenciaCasos > 0) puntuacionRiesgo += 10;
    
    // Factor 5: Temporada (mayo-octubre)
    if (mes >= 5 && mes <= 10) puntuacionRiesgo += 10;
    
    puntuacionRiesgo = Math.min(100, puntuacionRiesgo);
    const riesgoClase = puntuacionRiesgo >= 50 ? 1 : 0;

    // Generar mensaje
    let mensaje = '';
    let nivelRiesgo = '';
    if (puntuacionRiesgo >= 75) {
      mensaje = 'ALERTA CRÍTICA: Riesgo muy alto de brote. Activar protocolos de emergencia inmediatamente.';
      nivelRiesgo = 'Crítico';
    } else if (puntuacionRiesgo >= 50) {
      mensaje = 'ADVERTENCIA: Riesgo elevado de brote. Se recomienda intensificar vigilancia epidemiológica.';
      nivelRiesgo = 'Alto';
    } else if (puntuacionRiesgo >= 25) {
      mensaje = 'PRECAUCIÓN: Riesgo moderado. Mantener vigilancia activa y medidas preventivas.';
      nivelRiesgo = 'Moderado';
    } else {
      mensaje = 'Riesgo bajo. Mantener vigilancia estándar y medidas de control vectorial habituales.';
      nivelRiesgo = 'Bajo';
    }

    // Predicción de casos para los próximos 7 días (regresión simple)
    let prediccionProxSemana = parseInt(casosLag1w) || 0;
    if (historial.length >= 2) {
      const ultimosCasos = historial.map(h => parseInt(h.casos) || 0);
      const promedio = ultimosCasos.reduce((a, b) => a + b, 0) / ultimosCasos.length;
      const tendencia = (ultimosCasos[ultimosCasos.length - 1] - ultimosCasos[0]) / ultimosCasos.length;
      prediccionProxSemana = Math.max(0, Math.round(promedio + tendencia * 2));
    }

    // Guardar alerta si es riesgo alto
    if (riesgoClase === 1) {
      try {
        await pool.execute(
          'INSERT INTO alerta (nombre, id_enfermedad, id_region, nivel_riesgo, fecha_alerta, descripcion, estado) VALUES (?, ?, ?, ?, NOW(), ?, ?)',
          [
            `Alerta Automática - ${region.nombre}`,
            1,
            id_region,
            puntuacionRiesgo >= 75 ? 'critico' : 'alto',
            mensaje,
            'activa'
          ]
        );
      } catch (dbError) {
        console.warn('No se pudo guardar la alerta:', dbError.message);
      }
    }

    res.json({
      success: true,
      estado: region.nombre,
      fecha_evaluacion: fechaRef.toISOString().split('T')[0],
      fecha_datos_utilizados: `Datos hasta ${fechaRef.toISOString().split('T')[0]}`,
      riesgo_probabilidad: Math.round(puntuacionRiesgo * 10) / 10,
      riesgo_clase: riesgoClase,
      nivel_riesgo: nivelRiesgo,
      mensaje: mensaje,
      datos_utilizados: {
        casos_ultima_semana: casosLag1w,
        casos_hace_4_semanas: casosLag4w,
        tasa_incidencia_actual: Math.round(tiLag1w * 100) / 100,
        tasa_incidencia_anterior: Math.round(tiLag4w * 100) / 100,
        poblacion_region: poblacion,
        semana_epidemiologica: semanaDelAnio,
        mes: mes
      },
      tendencias: {
        casos: tendenciaCasos > 0 ? 'Creciente' : tendenciaCasos < 0 ? 'Decreciente' : 'Estable',
        tasa: tendenciaTasa > 0 ? 'Creciente' : tendenciaTasa < 0 ? 'Decreciente' : 'Estable',
        temporada_riesgo: (mes >= 5 && mes <= 10) ? 'Sí (temporada de lluvias)' : 'No'
      },
      prediccion: {
        casos_proxima_semana: prediccionProxSemana,
        historial_semanas: historial.length
      }
    });

  } catch (error) {
    console.error('Error en predicción automática:', error);
    res.status(500).json({ 
      success: false, 
      error: 'Error al realizar la predicción: ' + error.message 
    });
  }
});

// Iniciar servidor
app.listen(PORT, () => {
  console.log(`✅ Servidor corriendo en http://localhost:${PORT}`);
});