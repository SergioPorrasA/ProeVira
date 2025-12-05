// src/pages/EntrenamientoModelos.js
// Vista para Entrenar y Re-entrenar Modelos de Machine Learning

import React, { useState, useEffect } from 'react';
import {
  Brain, Upload, TrendingUp, Activity, CheckCircle, 
  XCircle, AlertTriangle, RefreshCw, FileText, Zap,
  BarChart3, Target, Database, Settings
} from 'lucide-react';

const API_URL = 'http://localhost:5001/api';

const EntrenamientoModelos = () => {
  const [modelosInfo, setModelosInfo] = useState(null);
  const [archivosCSV, setArchivosCSV] = useState([]);
  const [loading, setLoading] = useState(true);
  const [entrenando, setEntrenando] = useState(false);
  const [resultado, setResultado] = useState(null);
  const [error, setError] = useState(null);
  
  const [formData, setFormData] = useState({
    tipo_modelo: 'clasificador',
    archivo_csv: ''
  });

  // Cargar información de modelos y archivos CSV
  useEffect(() => {
    cargarInformacion();
  }, []);

  const cargarInformacion = async () => {
    setLoading(true);
    setError(null);
    
    try {
      const response = await fetch(`${API_URL}/modelos/info`, {
        method: 'GET',
        headers: { 'Content-Type': 'application/json' }
      });
      
      if (!response.ok) {
        throw new Error(`Error HTTP: ${response.status}`);
      }
      
      const data = await response.json();
      
      if (data.success) {
        setModelosInfo(data.modelos);
        setArchivosCSV(data.archivos_csv || []);
      } else {
        setError(data.error || 'Error al cargar información de modelos');
      }
    } catch (err) {
      console.error('Error cargando información:', err);
      if (err.message.includes('Failed to fetch') || err.message.includes('NetworkError')) {
        setError('No se puede conectar al servidor Flask (http://localhost:5001). Verifica que el backend esté ejecutándose.');
      } else {
        setError(`Error de conexión: ${err.message}`);
      }
    } finally {
      setLoading(false);
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    
    if (!formData.archivo_csv) {
      setError('Debe seleccionar un archivo CSV');
      return;
    }
    
    setEntrenando(true);
    setResultado(null);
    setError(null);
    
    try {
      const response = await fetch(`${API_URL}/modelos/entrenar`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(formData)
      });
      
      if (!response.ok) {
        throw new Error(`Error HTTP: ${response.status}`);
      }
      
      const data = await response.json();
      
      if (data.success) {
        setResultado(data);
        setError(null);
        // Recargar información de modelos
        setTimeout(() => cargarInformacion(), 1000);
      } else {
        setError(data.error || 'Error al entrenar el modelo');
      }
    } catch (err) {
      console.error('Error entrenando modelo:', err);
      if (err.message.includes('Failed to fetch') || err.message.includes('NetworkError')) {
        setError('No se puede conectar al servidor Flask (http://localhost:5001). Verifica que el backend esté ejecutándose.');
      } else {
        setError(`Error: ${err.message}`);
      }
    } finally {
      setEntrenando(false);
    }
  };

  const handleChange = (e) => {
    const { name, value } = e.target;
    setFormData(prev => ({ ...prev, [name]: value }));
  };

  // Componente de estado del modelo
  const EstadoModelo = ({ tipo, info }) => {
    const estaActivo = info.cargado && info.existe;
    
    return (
      <div className={`border-2 rounded-xl p-6 ${
        estaActivo 
          ? 'bg-green-50 border-green-200' 
          : 'bg-gray-50 border-gray-200'
      }`}>
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center gap-3">
            <Brain className={`w-8 h-8 ${estaActivo ? 'text-green-600' : 'text-gray-400'}`} />
            <div>
              <h3 className="text-lg font-bold text-gray-800">
                Modelo {tipo === 'clasificador' ? 'Clasificador' : 'Regresor'}
              </h3>
              <p className="text-sm text-gray-600">{info.archivo}</p>
            </div>
          </div>
          {estaActivo ? (
            <CheckCircle className="w-6 h-6 text-green-600" />
          ) : (
            <XCircle className="w-6 h-6 text-gray-400" />
          )}
        </div>
        
        <div className="grid grid-cols-2 gap-4 text-sm">
          <div>
            <span className="text-gray-600">Estado:</span>
            <span className={`ml-2 font-bold ${estaActivo ? 'text-green-700' : 'text-gray-500'}`}>
              {estaActivo ? 'Activo' : 'No cargado'}
            </span>
          </div>
          <div>
            <span className="text-gray-600">Archivo existe:</span>
            <span className={`ml-2 font-bold ${info.existe ? 'text-green-700' : 'text-red-600'}`}>
              {info.existe ? 'Sí' : 'No'}
            </span>
          </div>
          {tipo === 'clasificador' && (
            <>
              <div>
                <span className="text-gray-600">Features:</span>
                <span className="ml-2 font-bold text-gray-800">{info.n_features || 0}</span>
              </div>
              <div>
                <span className="text-gray-600">Clases:</span>
                <span className="ml-2 font-bold text-gray-800">{info.n_classes || 0}</span>
              </div>
            </>
          )}
          {tipo === 'regresor' && info.features && info.features.length > 0 && (
            <div className="col-span-2">
              <span className="text-gray-600">Features:</span>
              <div className="flex flex-wrap gap-1 mt-1">
                {info.features.map((feat, idx) => (
                  <span key={idx} className="px-2 py-1 bg-blue-100 text-blue-700 rounded text-xs">
                    {feat}
                  </span>
                ))}
              </div>
            </div>
          )}
        </div>
      </div>
    );
  };

  if (loading) {
    return (
      <div className="flex-1 p-8 overflow-auto bg-gray-50">
        <div className="flex items-center justify-center h-full">
          <div className="text-center">
            <RefreshCw className="w-16 h-16 mx-auto mb-4 text-primary animate-spin" />
            <p className="text-xl text-gray-600">Cargando información de modelos...</p>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="flex-1 p-8 overflow-auto bg-gradient-to-br from-gray-50 to-purple-50">
      {/* Header */}
      <div className="mb-8">
        <h1 className="text-4xl font-black text-gray-800 mb-2">
          <Brain className="inline-block w-10 h-10 mr-3 text-primary" />
          Entrenamiento de Modelos ML
        </h1>
        <p className="text-gray-600">
          Entrena o re-entrena modelos de Machine Learning con tus propios datos
        </p>
      </div>

      {/* Estado Actual de los Modelos */}
      <div className="mb-8">
        <h2 className="text-2xl font-bold text-gray-800 mb-4 flex items-center gap-2">
          <Activity className="w-6 h-6 text-blue-500" />
          Estado Actual de los Modelos
        </h2>
        
        {modelosInfo && (
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            <EstadoModelo tipo="clasificador" info={modelosInfo.clasificador} />
            <EstadoModelo tipo="regresor" info={modelosInfo.regresor} />
          </div>
        )}
      </div>

      {/* Formulario de Entrenamiento */}
      <div className="bg-white rounded-xl p-8 shadow-lg border border-gray-200 mb-8">
        <h2 className="text-2xl font-bold text-gray-800 mb-6 flex items-center gap-2">
          <Zap className="w-6 h-6 text-orange-500" />
          Entrenar Nuevo Modelo
        </h2>

        <form onSubmit={handleSubmit} className="space-y-6">
          {/* Tipo de Modelo */}
          <div>
            <label className="block text-sm font-bold text-gray-700 mb-2">
              <Settings className="inline-block w-4 h-4 mr-2" />
              Tipo de Modelo
            </label>
            <select
              name="tipo_modelo"
              value={formData.tipo_modelo}
              onChange={handleChange}
              className="w-full px-4 py-3 border-2 border-gray-300 rounded-lg focus:border-primary focus:outline-none text-gray-800 font-medium"
            >
              <option value="clasificador">🎯 Clasificador (Nivel de Riesgo)</option>
              <option value="regresor">📈 Regresor (Número de Casos)</option>
            </select>
            
            <div className="mt-2 p-4 bg-blue-50 border border-blue-200 rounded-lg">
              <p className="text-sm text-blue-800">
                {formData.tipo_modelo === 'clasificador' ? (
                  <>
                    <strong>Clasificador:</strong> Predice el nivel de riesgo (Bajo, Medio, Alto, Crítico) 
                    basado en las tasas de incidencia y características temporales.
                  </>
                ) : (
                  <>
                    <strong>Regresor:</strong> Predice el número exacto de casos esperados basado en 
                    datos históricos y patrones estacionales.
                  </>
                )}
              </p>
            </div>
          </div>

          {/* Archivo CSV */}
          <div>
            <label className="block text-sm font-bold text-gray-700 mb-2">
              <Database className="inline-block w-4 h-4 mr-2" />
              Archivo CSV de Entrenamiento
            </label>
            <select
              name="archivo_csv"
              value={formData.archivo_csv}
              onChange={handleChange}
              className="w-full px-4 py-3 border-2 border-gray-300 rounded-lg focus:border-primary focus:outline-none text-gray-800 font-medium"
              required
            >
              <option value="">-- Seleccionar archivo CSV --</option>
              {archivosCSV.map((archivo, idx) => (
                <option key={idx} value={archivo.ruta}>
                  {archivo.nombre} ({archivo.tamano_mb} MB - {archivo.n_columnas} columnas)
                </option>
              ))}
            </select>

            {/* Mostrar columnas del archivo seleccionado */}
            {formData.archivo_csv && archivosCSV.find(a => a.ruta === formData.archivo_csv)?.columnas.length > 0 && (
              <div className="mt-3 p-4 bg-gray-50 border border-gray-200 rounded-lg">
                <p className="text-sm font-bold text-gray-700 mb-2">
                  Columnas detectadas en el archivo:
                </p>
                <div className="flex flex-wrap gap-2">
                  {archivosCSV.find(a => a.ruta === formData.archivo_csv).columnas.map((col, idx) => (
                    <span key={idx} className="px-3 py-1 bg-white border border-gray-300 rounded text-xs font-mono text-gray-700">
                      {col}
                    </span>
                  ))}
                </div>
              </div>
            )}
          </div>

          {/* Mensajes */}
          {error && (
            <div className="flex items-center gap-3 p-4 bg-red-50 border-2 border-red-200 rounded-lg">
              <AlertTriangle className="w-6 h-6 text-red-600 flex-shrink-0" />
              <div>
                <p className="font-bold text-red-900">Error</p>
                <p className="text-sm text-red-700">{error}</p>
              </div>
            </div>
          )}

          {/* Botón de Entrenamiento */}
          <button
            type="submit"
            disabled={entrenando || !formData.archivo_csv}
            className={`w-full py-4 rounded-lg font-bold text-white text-lg flex items-center justify-center gap-3 transition ${
              entrenando || !formData.archivo_csv
                ? 'bg-gray-400 cursor-not-allowed'
                : 'bg-gradient-to-r from-orange-500 to-red-500 hover:from-orange-600 hover:to-red-600'
            }`}
          >
            {entrenando ? (
              <>
                <RefreshCw className="w-6 h-6 animate-spin" />
                Entrenando modelo...
              </>
            ) : (
              <>
                <Zap className="w-6 h-6" />
                Iniciar Entrenamiento
              </>
            )}
          </button>
        </form>
      </div>

      {/* Resultado del Entrenamiento */}
      {resultado && (
        <div className="bg-gradient-to-br from-green-50 to-emerald-50 rounded-xl p-8 shadow-lg border-2 border-green-200">
          <div className="flex items-center gap-3 mb-6">
            <CheckCircle className="w-10 h-10 text-green-600" />
            <div>
              <h2 className="text-2xl font-black text-green-900">
                ¡Entrenamiento Exitoso!
              </h2>
              <p className="text-green-700">{resultado.mensaje}</p>
            </div>
          </div>

          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            {/* Métricas */}
            <div className="bg-white rounded-lg p-6 border border-green-200">
              <h3 className="text-lg font-bold text-gray-800 mb-4 flex items-center gap-2">
                <BarChart3 className="w-5 h-5 text-blue-500" />
                Métricas del Modelo
              </h3>
              
              {resultado.tipo_modelo === 'clasificador' && resultado.metricas && (
                <div className="space-y-3">
                  <div className="flex justify-between items-center p-3 bg-blue-50 rounded">
                    <span className="text-gray-700 font-medium">Accuracy</span>
                    <span className="text-2xl font-black text-blue-600">
                      {(resultado.metricas.accuracy * 100).toFixed(1)}%
                    </span>
                  </div>
                  <div className="flex justify-between items-center p-3 bg-green-50 rounded">
                    <span className="text-gray-700 font-medium">Precision</span>
                    <span className="text-2xl font-black text-green-600">
                      {(resultado.metricas.precision * 100).toFixed(1)}%
                    </span>
                  </div>
                  <div className="flex justify-between items-center p-3 bg-purple-50 rounded">
                    <span className="text-gray-700 font-medium">Recall</span>
                    <span className="text-2xl font-black text-purple-600">
                      {(resultado.metricas.recall * 100).toFixed(1)}%
                    </span>
                  </div>
                  <div className="flex justify-between items-center p-3 bg-orange-50 rounded">
                    <span className="text-gray-700 font-medium">F1-Score</span>
                    <span className="text-2xl font-black text-orange-600">
                      {(resultado.metricas.f1_score * 100).toFixed(1)}%
                    </span>
                  </div>
                </div>
              )}

              {resultado.tipo_modelo === 'regresor' && resultado.metricas && (
                <div className="space-y-3">
                  <div className="flex justify-between items-center p-3 bg-blue-50 rounded">
                    <span className="text-gray-700 font-medium">R² Score</span>
                    <span className="text-2xl font-black text-blue-600">
                      {(resultado.metricas.r2_score * 100).toFixed(1)}%
                    </span>
                  </div>
                  <div className="flex justify-between items-center p-3 bg-orange-50 rounded">
                    <span className="text-gray-700 font-medium">MAE</span>
                    <span className="text-2xl font-black text-orange-600">
                      {resultado.metricas.mae.toFixed(2)}
                    </span>
                  </div>
                </div>
              )}
            </div>

            {/* Datos */}
            <div className="bg-white rounded-lg p-6 border border-green-200">
              <h3 className="text-lg font-bold text-gray-800 mb-4 flex items-center gap-2">
                <FileText className="w-5 h-5 text-purple-500" />
                Información de Datos
              </h3>
              
              <div className="space-y-3">
                <div className="flex justify-between items-center">
                  <span className="text-gray-600">Total de Registros:</span>
                  <span className="font-bold text-gray-800">
                    {resultado.datos.total_registros.toLocaleString()}
                  </span>
                </div>
                <div className="flex justify-between items-center">
                  <span className="text-gray-600">Entrenamiento:</span>
                  <span className="font-bold text-gray-800">
                    {resultado.datos.registros_entrenamiento.toLocaleString()} (80%)
                  </span>
                </div>
                <div className="flex justify-between items-center">
                  <span className="text-gray-600">Prueba:</span>
                  <span className="font-bold text-gray-800">
                    {resultado.datos.registros_prueba.toLocaleString()} (20%)
                  </span>
                </div>
                <div className="pt-3 border-t border-gray-200">
                  <span className="text-gray-600 block mb-2">Features:</span>
                  <div className="flex flex-wrap gap-2">
                    {resultado.datos.features.map((feat, idx) => (
                      <span key={idx} className="px-2 py-1 bg-purple-100 text-purple-700 rounded text-xs font-mono">
                        {feat}
                      </span>
                    ))}
                  </div>
                </div>
                <div className="pt-3 border-t border-gray-200">
                  <div className="flex items-center gap-2 text-green-700">
                    <CheckCircle className="w-5 h-5" />
                    <span className="font-bold">
                      Guardado como: {resultado.archivo_guardado}
                    </span>
                  </div>
                </div>
              </div>
            </div>
          </div>

          <div className="mt-6 p-4 bg-yellow-50 border border-yellow-200 rounded-lg">
            <p className="text-sm text-yellow-800">
              <strong>📌 Nota:</strong> El modelo ha sido entrenado y guardado exitosamente. 
              El sistema ahora utilizará este modelo para realizar las predicciones. 
              Refresca la página de monitoreo para ver el modelo activo.
            </p>
          </div>
        </div>
      )}

      {/* Información Adicional */}
      <div className="mt-8 p-6 bg-white rounded-xl shadow-lg border border-gray-200">
        <h3 className="text-xl font-bold text-gray-800 mb-4 flex items-center gap-2">
          <Target className="w-6 h-6 text-indigo-500" />
          Requisitos de los Datos
        </h3>
        
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          <div>
            <h4 className="font-bold text-gray-700 mb-2">Para Modelo Clasificador:</h4>
            <ul className="space-y-2 text-sm text-gray-600">
              <li>• <code className="bg-gray-100 px-2 py-1 rounded">TI_LAG_1W</code> - Tasa de incidencia semana anterior</li>
              <li>• <code className="bg-gray-100 px-2 py-1 rounded">TI_LAG_4W</code> - Tasa de incidencia 4 semanas atrás</li>
              <li>• <code className="bg-gray-100 px-2 py-1 rounded">SEMANA_DEL_ANIO</code> - Número de semana (1-52)</li>
              <li>• <code className="bg-gray-100 px-2 py-1 rounded">MES</code> - Mes del año (1-12)</li>
              <li>• <code className="bg-gray-100 px-2 py-1 rounded">ENTIDAD_FED</code> - Nombre del estado</li>
              <li>• <code className="bg-gray-100 px-2 py-1 rounded">NIVEL_RIESGO</code> - Target (bajo/medio/alto/crítico)</li>
            </ul>
          </div>
          
          <div>
            <h4 className="font-bold text-gray-700 mb-2">Para Modelo Regresor:</h4>
            <ul className="space-y-2 text-sm text-gray-600">
              <li>• <code className="bg-gray-100 px-2 py-1 rounded">TI_LAG_1W</code> - Tasa de incidencia semana anterior</li>
              <li>• <code className="bg-gray-100 px-2 py-1 rounded">TI_LAG_4W</code> - Tasa de incidencia 4 semanas atrás</li>
              <li>• <code className="bg-gray-100 px-2 py-1 rounded">SEMANA_DEL_ANIO</code> - Número de semana (1-52)</li>
              <li>• <code className="bg-gray-100 px-2 py-1 rounded">MES</code> - Mes del año (1-12)</li>
              <li>• <code className="bg-gray-100 px-2 py-1 rounded">ENTIDAD_FED</code> - Nombre del estado</li>
              <li>• <code className="bg-gray-100 px-2 py-1 rounded">casos_confirmados</code> - Target (número de casos)</li>
            </ul>
          </div>
        </div>
      </div>
    </div>
  );
};

export default EntrenamientoModelos;
