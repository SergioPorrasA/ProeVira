import axios from 'axios';

// API Node.js (configuración, datos, dashboard)
const API_URL = 'http://localhost:5000/api';

// API Flask (modelo Random Forest - predicciones ML)
const FLASK_API_URL = 'http://localhost:5001/api';

const api = axios.create({
  baseURL: API_URL,
  headers: {
    'Content-Type': 'application/json'
  },
  timeout: 30000
});

// Cliente para Flask (modelo ML)
const flaskApi = axios.create({
  baseURL: FLASK_API_URL,
  headers: {
    'Content-Type': 'application/json'
  },
  timeout: 60000
});

// Interceptor para manejar errores - Node.js
api.interceptors.response.use(
  response => response,
  error => {
    console.error('Error en API Node.js:', error);
    if (error.code === 'ERR_NETWORK') {
      console.error('No se puede conectar al backend Node.js en http://localhost:5000');
    }
    return Promise.reject(error);
  }
);

// Interceptor para manejar errores - Flask
flaskApi.interceptors.response.use(
  response => response,
  error => {
    console.error('Error en API Flask:', error);
    if (error.code === 'ERR_NETWORK') {
      console.error('No se puede conectar al backend Flask en http://localhost:5001');
    }
    return Promise.reject(error);
  }
);

// Servicios de autenticación
export const authService = {
  login: (data) => api.post('/auth/login', data)
};

// Servicios de datos generales
export const datosService = {
  getEnfermedades: () => {
    console.log('Llamando a Flask /api/config/enfermedades');
    return flaskApi.get('/config/enfermedades');
  },
  getRegiones: () => {
    console.log('Llamando a Flask /api/config/regiones');
    return flaskApi.get('/config/regiones');
  },
  getModelos: () => {
    console.log('Llamando a /api/config/modelos');
    return api.get('/config/modelos');
  },
  getArchivosRecientes: () => api.get('/datos/archivos-recientes')
};

// Servicios de análisis
export const analisisService = {
  getCasosPorRegion: () => api.get('/analisis/casos-region'),
  getTendenciaMensual: () => api.get('/analisis/tendencia-mensual')
};

// Servicios de dashboard (Flask tiene /dashboard/resumen)
export const dashboardService = {
  getEstadisticasGenerales: () => flaskApi.get('/dashboard/resumen'),
  getCasosPorRegion: () => api.get('/analisis/casos-region'),
  getTendenciaCasos: () => api.get('/analisis/tendencia-mensual'),
  getAlertasRecientes: () => api.get('/dashboard/alertas-recientes')
};

// Servicios de modelos predictivos
export const modeloService = {
  subirDatosCSV: (archivo) => {
    const formData = new FormData();
    formData.append('archivo', archivo);
    return api.post('/modelo/subir-csv', formData, {
      headers: {
        'Content-Type': 'multipart/form-data'
      }
    });
  },
  ejecutarPrediccionDengue: (data) => {
    console.log('Ejecutando predicción con:', data);
    return api.post('/modelo/predecir-dengue', data, {
      timeout: 60000
    });
  },
  evaluarRiesgo: (data) => {
    console.log('Evaluando riesgo con:', data);
    return api.post('/modelo/evaluar-riesgo', data);
  },
  // ⚡ Predicción con Random Forest (Flask - puerto 5001)
  predecirRiesgoAutomatico: (data) => {
    console.log('🔮 Predicción Random Forest (Flask) con:', data);
    return flaskApi.post('/modelo/predecir-riesgo-automatico', data);
  },
  // 🔮 Predicción avanzada con fecha específica
  predecirRiesgoAvanzado: (data) => {
    console.log('🔮 Predicción Avanzada (Flask) con:', data);
    return flaskApi.post('/modelo/predecir-riesgo-avanzado', data);
  },
  obtenerPredicciones: (params) => api.get('/modelo/predicciones', { params })
};

// Servicios de reportes
export const reportesService = {
  getResumen: () => api.get('/reportes/resumen')
};

export default api;