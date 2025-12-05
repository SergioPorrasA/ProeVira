// src/pages/MonitoreoTiempoReal.js
// Vista de Monitoreo en Tiempo Real del Sistema y Modelos ML
// Muestra métricas actualizadas automáticamente cada 30 segundos

import React, { useState, useEffect, useCallback } from 'react';
import {
  LineChart, Line, AreaChart, Area, BarChart, Bar, 
  XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer,
  RadarChart, PolarGrid, PolarAngleAxis, PolarRadiusAxis, Radar
} from 'recharts';
import {
  Activity, Server, Database, Cpu, HardDrive, Clock, 
  TrendingUp, AlertTriangle, CheckCircle, XCircle,
  RefreshCw, Zap, Eye, Signal, Wifi, WifiOff
} from 'lucide-react';

const API_URL = 'http://localhost:5001/api';

const MonitoreoTiempoReal = () => {
  const [estadoSistema, setEstadoSistema] = useState({
    api: { estado: 'conectando', tiempoRespuesta: 0, ultimaActualizacion: null },
    baseDatos: { estado: 'conectando', conexionesActivas: 0, consultasPorMinuto: 0 },
    modelos: { estado: 'conectando', prediccionesHoy: 0, tasaExito: 0 }
  });
  
  const [metricsModelo, setMetricsModelo] = useState({
    accuracy: 0,
    precision: 0,
    recall: 0,
    f1Score: 0,
    totalPredicciones: 0,
    distribucionClases: []
  });

  const [historialRendimiento, setHistorialRendimiento] = useState([]);
  const [alertasActivas, setAlertasActivas] = useState([]);
  const [modoAutoRefresh, setModoAutoRefresh] = useState(true);
  const [ultimaActualizacion, setUltimaActualizacion] = useState(new Date());
  const [loading, setLoading] = useState(true);

  // Actualizar datos del sistema
  const actualizarEstadoSistema = useCallback(async () => {
    const tiempoInicio = Date.now();
    
    try {
      // Verificar estado de la API
      const responseAPI = await fetch(`${API_URL}/health`, {
        signal: AbortSignal.timeout(5000)
      });
      const tiempoRespuesta = Date.now() - tiempoInicio;
      
      if (responseAPI.ok) {
        const dataHealth = await responseAPI.json();
        
        setEstadoSistema(prev => ({
          ...prev,
          api: { 
            estado: 'activo', 
            tiempoRespuesta, 
            ultimaActualizacion: new Date() 
          },
          baseDatos: {
            estado: dataHealth.database?.status === 'connected' ? 'activo' : 'error',
            conexionesActivas: dataHealth.database?.active_connections || 0,
            consultasPorMinuto: dataHealth.database?.queries_per_minute || 0
          },
          modelos: {
            estado: dataHealth.models?.loaded ? 'activo' : 'error',
            prediccionesHoy: dataHealth.predictions?.today || 0,
            tasaExito: dataHealth.predictions?.success_rate || 0
          }
        }));

        // Cargar métricas del modelo
        if (dataHealth.models?.metrics) {
          setMetricsModelo({
            accuracy: dataHealth.models.metrics.accuracy || 0,
            precision: dataHealth.models.metrics.precision || 0,
            recall: dataHealth.models.metrics.recall || 0,
            f1Score: dataHealth.models.metrics.f1_score || 0,
            totalPredicciones: dataHealth.predictions?.total || 0,
            distribucionClases: dataHealth.predictions?.distribution || []
          });
        }

        // Actualizar historial de rendimiento
        setHistorialRendimiento(prev => {
          const nuevoRegistro = {
            timestamp: new Date().toLocaleTimeString(),
            tiempoRespuesta,
            predicciones: dataHealth.predictions?.last_minute || 0,
            errorRate: (100 - (dataHealth.predictions?.success_rate || 0))
          };
          return [...prev.slice(-19), nuevoRegistro]; // Mantener últimos 20
        });

        // Cargar alertas activas
        try {
          const responseAlertas = await fetch(`${API_URL}/alertas/activas`);
          if (responseAlertas.ok) {
            const dataAlertas = await responseAlertas.json();
            if (dataAlertas.success && dataAlertas.alertas) {
              setAlertasActivas(dataAlertas.alertas);
            } else {
              setAlertasActivas([]);
            }
          }
        } catch (err) {
          console.error('Error cargando alertas:', err);
          setAlertasActivas([]);
        }
      }
    } catch (error) {
      console.error('Error actualizando estado:', error);
      setEstadoSistema(prev => ({
        ...prev,
        api: { estado: 'error', tiempoRespuesta: 0, ultimaActualizacion: new Date() }
      }));
    } finally {
      setLoading(false);
      setUltimaActualizacion(new Date());
    }
  }, []);

  // Auto-refresh cada 30 segundos
  useEffect(() => {
    actualizarEstadoSistema();
    
    if (modoAutoRefresh) {
      const interval = setInterval(actualizarEstadoSistema, 30000);
      return () => clearInterval(interval);
    }
  }, [modoAutoRefresh, actualizarEstadoSistema]);

  // Componente de estado
  const EstadoComponente = ({ titulo, estado, valor, icono: Icon, detalles }) => {
    const colores = {
      activo: 'bg-green-50 border-green-200 text-green-700',
      error: 'bg-red-50 border-red-200 text-red-700',
      conectando: 'bg-yellow-50 border-yellow-200 text-yellow-700'
    };

    const iconos = {
      activo: CheckCircle,
      error: XCircle,
      conectando: RefreshCw
    };

    const IconoEstado = iconos[estado] || RefreshCw;

    return (
      <div className={`border-2 rounded-xl p-6 ${colores[estado]}`}>
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center gap-3">
            <Icon className="w-6 h-6" />
            <h3 className="text-lg font-bold">{titulo}</h3>
          </div>
          <IconoEstado className={`w-5 h-5 ${estado === 'conectando' ? 'animate-spin' : ''}`} />
        </div>
        
        {valor !== undefined && (
          <div className="text-3xl font-black mb-2">{valor}</div>
        )}
        
        {detalles && (
          <div className="space-y-1 text-sm opacity-80">
            {detalles.map((detalle, idx) => (
              <div key={idx} className="flex justify-between">
                <span>{detalle.label}:</span>
                <span className="font-bold">{detalle.valor}</span>
              </div>
            ))}
          </div>
        )}
      </div>
    );
  };

  // Datos para gráfico de radar (métricas del modelo)
  const dataRadar = [
    { metric: 'Accuracy', value: metricsModelo.accuracy * 100, fullMark: 100 },
    { metric: 'Precision', value: metricsModelo.precision * 100, fullMark: 100 },
    { metric: 'Recall', value: metricsModelo.recall * 100, fullMark: 100 },
    { metric: 'F1-Score', value: metricsModelo.f1Score * 100, fullMark: 100 },
    { metric: 'Éxito', value: estadoSistema.modelos.tasaExito, fullMark: 100 }
  ];

  if (loading && historialRendimiento.length === 0) {
    return (
      <div className="flex-1 p-8 overflow-auto bg-gray-50">
        <div className="flex items-center justify-center h-full">
          <div className="text-center">
            <RefreshCw className="w-16 h-16 mx-auto mb-4 text-primary animate-spin" />
            <p className="text-xl text-gray-600">Cargando monitoreo en tiempo real...</p>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="flex-1 p-8 overflow-auto bg-gradient-to-br from-gray-50 to-blue-50">
      {/* Header */}
      <div className="flex items-center justify-between mb-8">
        <div>
          <h1 className="text-4xl font-black text-gray-800 mb-2">
            <Activity className="inline-block w-10 h-10 mr-3 text-primary" />
            Monitoreo en Tiempo Real
          </h1>
          <p className="text-gray-600">
            Estado del sistema y modelos ML actualizados cada 30 segundos
          </p>
        </div>

        <div className="flex items-center gap-4">
          <div className="text-right text-sm">
            <div className="text-gray-500">Última actualización</div>
            <div className="font-bold text-gray-800">
              {ultimaActualizacion.toLocaleTimeString()}
            </div>
          </div>

          <button
            onClick={() => setModoAutoRefresh(!modoAutoRefresh)}
            className={`flex items-center gap-2 px-4 py-2 rounded-lg font-bold transition ${
              modoAutoRefresh
                ? 'bg-green-500 text-white hover:bg-green-600'
                : 'bg-gray-300 text-gray-700 hover:bg-gray-400'
            }`}
          >
            {modoAutoRefresh ? <Wifi /> : <WifiOff />}
            {modoAutoRefresh ? 'Auto-Refresh ON' : 'Auto-Refresh OFF'}
          </button>

          <button
            onClick={actualizarEstadoSistema}
            className="flex items-center gap-2 px-4 py-2 bg-primary text-white rounded-lg font-bold hover:bg-orange-600 transition"
          >
            <RefreshCw className="w-5 h-5" />
            Actualizar Ahora
          </button>
        </div>
      </div>

      {/* Grid de Estado del Sistema */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
        <EstadoComponente
          titulo="API Flask"
          estado={estadoSistema.api.estado}
          valor={`${estadoSistema.api.tiempoRespuesta}ms`}
          icono={Server}
          detalles={[
            { label: 'Tiempo Respuesta', valor: `${estadoSistema.api.tiempoRespuesta}ms` },
            { label: 'Puerto', valor: '5001' },
            { label: 'Última Check', valor: estadoSistema.api.ultimaActualizacion?.toLocaleTimeString() || 'N/A' }
          ]}
        />

        <EstadoComponente
          titulo="Base de Datos"
          estado={estadoSistema.baseDatos.estado}
          valor={`${estadoSistema.baseDatos.conexionesActivas} conexiones`}
          icono={Database}
          detalles={[
            { label: 'Conexiones Activas', valor: estadoSistema.baseDatos.conexionesActivas },
            { label: 'Consultas/min', valor: estadoSistema.baseDatos.consultasPorMinuto },
            { label: 'Pool Size', valor: '5' }
          ]}
        />

        <EstadoComponente
          titulo="Modelos ML"
          estado={estadoSistema.modelos.estado}
          valor={`${estadoSistema.modelos.prediccionesHoy} predicciones`}
          icono={Zap}
          detalles={[
            { label: 'Predicciones Hoy', valor: estadoSistema.modelos.prediccionesHoy },
            { label: 'Tasa de Éxito', valor: `${estadoSistema.modelos.tasaExito.toFixed(1)}%` },
            { label: 'Total Acumulado', valor: metricsModelo.totalPredicciones }
          ]}
        />
      </div>

      {/* Gráficos de Rendimiento */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-8">
        {/* Tiempo de Respuesta */}
        <div className="bg-white rounded-xl p-6 shadow-lg border border-gray-200">
          <div className="flex items-center gap-3 mb-4">
            <Clock className="w-6 h-6 text-blue-500" />
            <h2 className="text-xl font-bold text-gray-800">Tiempo de Respuesta (ms)</h2>
          </div>
          <ResponsiveContainer width="100%" height={250}>
            <AreaChart data={historialRendimiento}>
              <CartesianGrid strokeDasharray="3 3" stroke="#e0e0e0" />
              <XAxis dataKey="timestamp" stroke="#666" fontSize={12} />
              <YAxis stroke="#666" fontSize={12} />
              <Tooltip 
                contentStyle={{ backgroundColor: '#fff', border: '1px solid #ccc', borderRadius: '8px' }}
              />
              <Area 
                type="monotone" 
                dataKey="tiempoRespuesta" 
                stroke="#3b82f6" 
                fill="#93c5fd" 
                strokeWidth={2}
              />
            </AreaChart>
          </ResponsiveContainer>
        </div>

        {/* Predicciones por Minuto */}
        <div className="bg-white rounded-xl p-6 shadow-lg border border-gray-200">
          <div className="flex items-center gap-3 mb-4">
            <TrendingUp className="w-6 h-6 text-green-500" />
            <h2 className="text-xl font-bold text-gray-800">Actividad de Predicciones</h2>
          </div>
          <ResponsiveContainer width="100%" height={250}>
            <BarChart data={historialRendimiento}>
              <CartesianGrid strokeDasharray="3 3" stroke="#e0e0e0" />
              <XAxis dataKey="timestamp" stroke="#666" fontSize={12} />
              <YAxis stroke="#666" fontSize={12} />
              <Tooltip 
                contentStyle={{ backgroundColor: '#fff', border: '1px solid #ccc', borderRadius: '8px' }}
              />
              <Bar dataKey="predicciones" fill="#22c55e" radius={[8, 8, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* Métricas del Modelo ML */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-8">
        {/* Radar de Métricas */}
        <div className="bg-white rounded-xl p-6 shadow-lg border border-gray-200">
          <div className="flex items-center gap-3 mb-4">
            <Signal className="w-6 h-6 text-purple-500" />
            <h2 className="text-xl font-bold text-gray-800">Métricas del Modelo</h2>
          </div>
          <ResponsiveContainer width="100%" height={300}>
            <RadarChart data={dataRadar}>
              <PolarGrid stroke="#e0e0e0" />
              <PolarAngleAxis dataKey="metric" stroke="#666" fontSize={12} />
              <PolarRadiusAxis angle={90} domain={[0, 100]} stroke="#666" fontSize={10} />
              <Radar 
                name="Performance" 
                dataKey="value" 
                stroke="#8b5cf6" 
                fill="#c4b5fd" 
                fillOpacity={0.6}
                strokeWidth={2}
              />
              <Tooltip />
            </RadarChart>
          </ResponsiveContainer>
        </div>

        {/* Métricas Numéricas */}
        <div className="bg-white rounded-xl p-6 shadow-lg border border-gray-200">
          <div className="flex items-center gap-3 mb-6">
            <Cpu className="w-6 h-6 text-indigo-500" />
            <h2 className="text-xl font-bold text-gray-800">Estadísticas del Modelo</h2>
          </div>
          
          <div className="grid grid-cols-2 gap-4">
            <div className="bg-gradient-to-br from-blue-50 to-blue-100 rounded-lg p-4">
              <div className="text-sm text-blue-700 mb-1">Accuracy</div>
              <div className="text-3xl font-black text-blue-900">
                {(metricsModelo.accuracy * 100).toFixed(1)}%
              </div>
            </div>

            <div className="bg-gradient-to-br from-green-50 to-green-100 rounded-lg p-4">
              <div className="text-sm text-green-700 mb-1">Precision</div>
              <div className="text-3xl font-black text-green-900">
                {(metricsModelo.precision * 100).toFixed(1)}%
              </div>
            </div>

            <div className="bg-gradient-to-br from-purple-50 to-purple-100 rounded-lg p-4">
              <div className="text-sm text-purple-700 mb-1">Recall</div>
              <div className="text-3xl font-black text-purple-900">
                {(metricsModelo.recall * 100).toFixed(1)}%
              </div>
            </div>

            <div className="bg-gradient-to-br from-orange-50 to-orange-100 rounded-lg p-4">
              <div className="text-sm text-orange-700 mb-1">F1-Score</div>
              <div className="text-3xl font-black text-orange-900">
                {(metricsModelo.f1Score * 100).toFixed(1)}%
              </div>
            </div>
          </div>

          <div className="mt-4 p-4 bg-gray-50 rounded-lg">
            <div className="flex justify-between items-center">
              <span className="text-gray-600">Total Predicciones:</span>
              <span className="text-2xl font-black text-gray-800">
                {metricsModelo.totalPredicciones.toLocaleString()}
              </span>
            </div>
          </div>
        </div>
      </div>

      {/* Alertas Activas */}
      {alertasActivas.length > 0 && (
        <div className="bg-white rounded-xl p-6 shadow-lg border border-gray-200">
          <div className="flex items-center gap-3 mb-4">
            <AlertTriangle className="w-6 h-6 text-red-500" />
            <h2 className="text-xl font-bold text-gray-800">
              Alertas Activas ({alertasActivas.length})
            </h2>
          </div>
          
          <div className="space-y-3">
            {alertasActivas.slice(0, 5).map((alerta, idx) => {
              // Determinar el color según el nivel
              const colorClasses = {
                'Crítico': 'bg-red-50 border-red-300 text-red-900',
                'Alto': 'bg-orange-50 border-orange-300 text-orange-900',
                'Moderado': 'bg-yellow-50 border-yellow-300 text-yellow-900',
                'Bajo': 'bg-blue-50 border-blue-300 text-blue-900'
              };
              const colorClass = colorClasses[alerta.nivel] || 'bg-red-50 border-red-200 text-red-900';
              
              return (
                <div 
                  key={alerta.id || idx}
                  className={`flex items-center justify-between p-4 border-2 rounded-lg ${colorClass}`}
                >
                  <div className="flex items-center gap-3 flex-1">
                    <AlertTriangle className="w-5 h-5 flex-shrink-0" />
                    <div className="flex-1">
                      <div className="flex items-center gap-2 mb-1">
                        <span className="font-bold">{alerta.estado || 'Estado Desconocido'}</span>
                        <span className="text-xs px-2 py-1 bg-white rounded-full font-bold">
                          {alerta.nivel || 'N/A'}
                        </span>
                      </div>
                      <div className="text-sm opacity-90">
                        {alerta.mensaje || 'Sin descripción'}
                      </div>
                      {alerta.casos_esperados && (
                        <div className="text-xs mt-1 opacity-75">
                          Casos esperados: {alerta.casos_esperados}
                        </div>
                      )}
                    </div>
                  </div>
                  <div className="text-right text-xs ml-4 flex-shrink-0">
                    {alerta.fecha_generacion && (
                      <div>{new Date(alerta.fecha_generacion).toLocaleString('es-MX')}</div>
                    )}
                    {alerta.probabilidad && (
                      <div className="font-bold mt-1">{(alerta.probabilidad * 100).toFixed(0)}%</div>
                    )}
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* Footer de Información */}
      <div className="mt-8 p-6 bg-white rounded-xl shadow-lg border border-gray-200">
        <div className="grid grid-cols-1 md:grid-cols-4 gap-6 text-center">
          <div>
            <Eye className="w-8 h-8 mx-auto mb-2 text-gray-400" />
            <div className="text-sm text-gray-500">Modo Monitoreo</div>
            <div className="text-lg font-bold text-gray-800">Tiempo Real</div>
          </div>
          <div>
            <RefreshCw className="w-8 h-8 mx-auto mb-2 text-gray-400" />
            <div className="text-sm text-gray-500">Frecuencia</div>
            <div className="text-lg font-bold text-gray-800">30 segundos</div>
          </div>
          <div>
            <HardDrive className="w-8 h-8 mx-auto mb-2 text-gray-400" />
            <div className="text-sm text-gray-500">Historial</div>
            <div className="text-lg font-bold text-gray-800">{historialRendimiento.length} registros</div>
          </div>
          <div>
            <CheckCircle className="w-8 h-8 mx-auto mb-2 text-green-500" />
            <div className="text-sm text-gray-500">Estado General</div>
            <div className="text-lg font-bold text-green-600">Operativo</div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default MonitoreoTiempoReal;
