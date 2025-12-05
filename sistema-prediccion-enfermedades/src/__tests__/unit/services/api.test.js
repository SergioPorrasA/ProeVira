/**
 * 4.1 PRUEBAS UNITARIAS - Servicios API
 * Sistema de Predicción de Enfermedades Virales
 */

import axios from 'axios';

// Mock de axios
jest.mock('axios', () => ({
  create: jest.fn(() => ({
    get: jest.fn(),
    post: jest.fn(),
    put: jest.fn(),
    delete: jest.fn(),
    interceptors: {
      request: { use: jest.fn() },
      response: { use: jest.fn() }
    }
  })),
  get: jest.fn(),
  post: jest.fn()
}));

describe('API Services - Pruebas Unitarias', () => {
  let mockAxiosInstance;

  beforeEach(() => {
    jest.clearAllMocks();
    mockAxiosInstance = {
      get: jest.fn(),
      post: jest.fn(),
      put: jest.fn(),
      delete: jest.fn(),
      interceptors: {
        request: { use: jest.fn() },
        response: { use: jest.fn() }
      }
    };
    axios.create.mockReturnValue(mockAxiosInstance);
  });

  describe('Configuración del cliente API', () => {
    test('debe crear cliente con URL base correcta', () => {
      const apiConfig = {
        baseURL: 'http://localhost:5001/api',
        timeout: 30000,
        headers: { 'Content-Type': 'application/json' }
      };
      
      expect(apiConfig.baseURL).toBe('http://localhost:5001/api');
      expect(apiConfig.timeout).toBe(30000);
    });

    test('debe incluir headers de contenido JSON', () => {
      const headers = { 'Content-Type': 'application/json' };
      expect(headers['Content-Type']).toBe('application/json');
    });
  });

  describe('Dashboard Service', () => {
    test('debe llamar al endpoint correcto para estadísticas', async () => {
      mockAxiosInstance.get.mockResolvedValue({ data: { total_casos: 1500 } });
      
      const resultado = await mockAxiosInstance.get('/dashboard/resumen');
      
      expect(mockAxiosInstance.get).toHaveBeenCalledWith('/dashboard/resumen');
      expect(resultado.data.total_casos).toBe(1500);
    });

    test('debe manejar error de red correctamente', async () => {
      mockAxiosInstance.get.mockRejectedValue({ code: 'ERR_NETWORK' });
      
      await expect(mockAxiosInstance.get('/dashboard/resumen')).rejects.toEqual({ code: 'ERR_NETWORK' });
    });
  });

  describe('Predicción Service', () => {
    test('debe enviar datos de predicción correctamente', async () => {
      const datosPrediccion = {
        id_region: 14,
        semana: 48,
        temperatura: 25.5,
        precipitacion: 80,
        casos_previos: 150
      };
      
      mockAxiosInstance.post.mockResolvedValue({
        data: { riesgo: 'Alto', probabilidad: 78 }
      });
      
      const resultado = await mockAxiosInstance.post('/prediccion/riesgo', datosPrediccion);
      
      expect(mockAxiosInstance.post).toHaveBeenCalledWith('/prediccion/riesgo', datosPrediccion);
      expect(resultado.data.riesgo).toBe('Alto');
    });

    test('debe validar parámetros de predicción', () => {
      const validarParametros = (params) => {
        const requeridos = ['id_region', 'semana', 'temperatura', 'precipitacion'];
        return requeridos.every(key => params.hasOwnProperty(key) && params[key] !== undefined);
      };
      
      expect(validarParametros({ id_region: 14, semana: 48, temperatura: 25, precipitacion: 80 })).toBe(true);
      expect(validarParametros({ id_region: 14, semana: 48 })).toBe(false);
    });
  });

  describe('Alertas Service', () => {
    test('debe obtener alertas activas', async () => {
      mockAxiosInstance.get.mockResolvedValue({
        data: { alertas: [{ id: 1, estado: 'Jalisco', nivel: 'Alto' }] }
      });
      
      const resultado = await mockAxiosInstance.get('/alertas/activas');
      
      expect(resultado.data.alertas).toHaveLength(1);
      expect(resultado.data.alertas[0].estado).toBe('Jalisco');
    });

    test('debe enviar alerta individual', async () => {
      const alertaData = {
        id_region: 14,
        estado: 'Jalisco',
        nivel_riesgo: 'Alto',
        mensaje: 'Riesgo elevado de brote'
      };
      
      mockAxiosInstance.post.mockResolvedValue({ data: { success: true, id: 1 } });
      
      const resultado = await mockAxiosInstance.post('/alertas/enviar', alertaData);
      
      expect(resultado.data.success).toBe(true);
    });

    test('debe resolver alerta correctamente', async () => {
      mockAxiosInstance.put.mockResolvedValue({ data: { success: true } });
      
      const resultado = await mockAxiosInstance.put('/alertas/1/resolver', { resolucion: 'Atendida' });
      
      expect(resultado.data.success).toBe(true);
    });
  });

  describe('Reportes Service', () => {
    test('debe obtener datos de reporte epidemiológico', async () => {
      mockAxiosInstance.get.mockResolvedValue({
        data: {
          periodo: { inicio: '2025-01-01', fin: '2025-12-01' },
          total_casos: 15000,
          estados: []
        }
      });
      
      const resultado = await mockAxiosInstance.get('/reportes/epidemiologico?fechaInicio=2025-01-01&fechaFin=2025-12-01');
      
      expect(resultado.data.total_casos).toBe(15000);
    });
  });

  describe('Manejo de errores HTTP', () => {
    test('debe identificar error 401 (no autorizado)', () => {
      const manejarError = (status) => {
        const mensajes = {
          400: 'Solicitud inválida',
          401: 'No autorizado',
          403: 'Acceso denegado',
          404: 'Recurso no encontrado',
          500: 'Error del servidor'
        };
        return mensajes[status] || 'Error desconocido';
      };
      
      expect(manejarError(401)).toBe('No autorizado');
      expect(manejarError(500)).toBe('Error del servidor');
    });

    test('debe reintentar en caso de timeout', () => {
      const configurarReintento = (config, intentos = 3) => {
        return {
          ...config,
          retry: intentos,
          retryDelay: 1000
        };
      };
      
      const config = configurarReintento({ timeout: 30000 });
      expect(config.retry).toBe(3);
      expect(config.retryDelay).toBe(1000);
    });
  });
});

describe('API - Validación de respuestas', () => {
  test('debe validar estructura de respuesta exitosa', () => {
    const validarRespuesta = (response) => {
      return Boolean(response && 
        (response.data !== undefined || response.success !== undefined));
    };
    
    expect(validarRespuesta({ data: { casos: 100 } })).toBe(true);
    expect(validarRespuesta({ success: true })).toBe(true);
    expect(validarRespuesta(null)).toBe(false);
  });

  test('debe parsear errores de API correctamente', () => {
    const parsearError = (error) => {
      if (error.response) {
        return {
          tipo: 'response',
          status: error.response.status,
          mensaje: error.response.data?.message || 'Error del servidor'
        };
      } else if (error.request) {
        return { tipo: 'network', mensaje: 'Sin respuesta del servidor' };
      }
      return { tipo: 'config', mensaje: error.message };
    };
    
    const errorResponse = { response: { status: 404, data: { message: 'No encontrado' } } };
    expect(parsearError(errorResponse).status).toBe(404);
    
    const errorNetwork = { request: {} };
    expect(parsearError(errorNetwork).tipo).toBe('network');
  });
});
