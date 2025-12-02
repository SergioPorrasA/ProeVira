// src/components/RiesgoBroteForm.js
// Módulo de Predicción de Riesgo de Brote de Dengue
// Utiliza datos históricos de la Secretaría de Salud (2020-2025)

import React, { useState, useEffect } from 'react';
import { datosService, modeloService } from '../services/api';

const RiesgoBroteForm = () => {
    const [regiones, setRegiones] = useState([]);
    const [loadingRegiones, setLoadingRegiones] = useState(true);
    const [formData, setFormData] = useState({
        id_region: '',
        fecha_prediccion: new Date().toISOString().split('T')[0]
    });
    const [predictionResult, setPredictionResult] = useState(null);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState(null);

    // Cargar regiones/estados desde la base de datos
    useEffect(() => {
        const cargarRegiones = async () => {
            try {
                setLoadingRegiones(true);
                const response = await datosService.getRegiones();
                // Ordenar alfabéticamente por nombre
                const regionesOrdenadas = (response.data || []).sort((a, b) => 
                    a.nombre.localeCompare(b.nombre)
                );
                setRegiones(regionesOrdenadas);
            } catch (err) {
                console.error('Error al cargar regiones:', err);
                setError('Error al cargar las regiones. Verifique la conexión con el servidor.');
            } finally {
                setLoadingRegiones(false);
            }
        };
        cargarRegiones();
    }, []);

    const handleChange = (e) => {
        setFormData({ ...formData, [e.target.name]: e.target.value });
        // Limpiar resultados anteriores al cambiar selección
        if (e.target.name === 'id_region') {
            setPredictionResult(null);
            setError(null);
        }
    };

    const handleSubmit = async (e) => {
        e.preventDefault();
        
        if (!formData.id_region) {
            setError('Debe seleccionar un estado');
            return;
        }

        setLoading(true);
        setError(null);
        setPredictionResult(null);

        try {
            const response = await modeloService.predecirRiesgoAutomatico({
                id_region: parseInt(formData.id_region, 10),
                fecha_prediccion: formData.fecha_prediccion
            });
            
            if (response.data.success) {
                setPredictionResult(response.data);
            } else {
                setError(response.data.error || 'Error en la predicción');
            }
        } catch (err) {
            console.error('Error en predicción:', err);
            setError(err.response?.data?.error || 'Error de conexión con el servidor');
        } finally {
            setLoading(false);
        }
    };

    return (
        <div className="p-6 max-w-4xl mx-auto">
            <div className="mb-8">
                <h1 className="text-3xl font-bold text-gray-800 mb-2">
                    🦟 Predicción de Riesgo de Brote de Dengue
                </h1>
                <p className="text-gray-600">
                    Sistema de análisis epidemiológico con datos históricos de la Secretaría de Salud (2020-2025).
                </p>
            </div>

            {/* Información del sistema */}
            <div className="bg-blue-50 border border-blue-200 rounded-xl p-4 mb-6">
                <h3 className="font-semibold text-blue-800 mb-2">ℹ️ ¿Cómo funciona?</h3>
                <ul className="text-sm text-blue-700 space-y-1">
                    <li>• Seleccione un estado y el sistema analizará automáticamente los datos más recientes</li>
                    <li>• Calcula tasas de incidencia, tendencias y factores estacionales</li>
                    <li>• Genera una probabilidad de riesgo basada en datos de 6 años de historia</li>
                    <li>• Los datos se actualizan semanalmente desde fuentes oficiales</li>
                </ul>
            </div>

            {/* Formulario simplificado */}
            <form onSubmit={handleSubmit} className="bg-white p-6 rounded-xl border shadow-lg">
                <h2 className="text-lg font-bold mb-6 flex items-center gap-2">
                    <span className="bg-blue-600 text-white w-8 h-8 rounded-full flex items-center justify-center text-sm">📊</span>
                    Seleccione Estado a Evaluar
                </h2>

                <div className="space-y-4">
                    {/* Selector de Estado */}
                    <div>
                        <label className="block text-sm font-medium text-gray-700 mb-2">
                            Estado / Entidad Federativa *
                        </label>
                        <select 
                            name="id_region" 
                            value={formData.id_region} 
                            onChange={handleChange}
                            required
                            disabled={loadingRegiones}
                            className="w-full p-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 bg-white text-lg"
                        >
                            <option value="">
                                {loadingRegiones ? '⏳ Cargando estados...' : '-- Seleccione un estado --'}
                            </option>
                            {regiones.map((r) => (
                                <option key={r.id} value={r.id}>{r.nombre}</option>
                            ))}
                        </select>
                        {regiones.length > 0 && (
                            <p className="text-xs text-green-600 mt-1">
                                ✓ {regiones.length} estados disponibles con datos epidemiológicos
                            </p>
                        )}
                    </div>

                    {/* Info de fecha - ahora es informativo, no editable */}
                    <div className="p-3 bg-gray-50 rounded-lg border">
                        <p className="text-sm text-gray-600">
                            <strong>📅 Fecha de análisis:</strong> El sistema usará automáticamente los datos más recientes disponibles para el estado seleccionado.
                        </p>
                    </div>
                </div>

                <button 
                    type="submit" 
                    disabled={loading || loadingRegiones || !formData.id_region} 
                    className="mt-6 w-full px-6 py-4 bg-gradient-to-r from-blue-600 to-blue-700 text-white font-bold rounded-xl hover:from-blue-700 hover:to-blue-800 disabled:from-gray-400 disabled:to-gray-500 disabled:cursor-not-allowed transition-all shadow-lg text-lg"
                >
                    {loading ? (
                        <span className="flex items-center justify-center gap-3">
                            <svg className="animate-spin h-6 w-6" viewBox="0 0 24 24">
                                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none"/>
                                <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"/>
                            </svg>
                            Analizando datos epidemiológicos...
                        </span>
                    ) : '🔍 Evaluar Riesgo de Brote'}
                </button>
            </form>

            {/* Error */}
            {error && (
                <div className="mt-6 p-4 bg-red-50 border border-red-300 text-red-700 rounded-xl flex items-start gap-3">
                    <span className="text-xl">⚠️</span>
                    <div>
                        <strong>Error:</strong> {error}
                    </div>
                </div>
            )}

            {/* Resultados */}
            {predictionResult && <ResultDisplay data={predictionResult} />}
        </div>
    );
};

// Componente para mostrar los resultados
const ResultDisplay = ({ data }) => {
    const { 
        estado, 
        fecha_evaluacion,
        riesgo_probabilidad, 
        riesgo_clase,
        nivel_riesgo,
        mensaje,
        datos_utilizados,
        tendencias,
        prediccion
    } = data;

    // Determinar colores según nivel de riesgo
    const getRiskStyle = () => {
        if (riesgo_probabilidad >= 75) {
            return { 
                bg: 'bg-gradient-to-r from-red-500 to-red-600', 
                border: 'border-red-500',
                text: 'text-red-800',
                light: 'bg-red-50',
                icon: '🚨' 
            };
        }
        if (riesgo_probabilidad >= 50) {
            return { 
                bg: 'bg-gradient-to-r from-orange-500 to-orange-600', 
                border: 'border-orange-500',
                text: 'text-orange-800',
                light: 'bg-orange-50',
                icon: '⚠️' 
            };
        }
        if (riesgo_probabilidad >= 25) {
            return { 
                bg: 'bg-gradient-to-r from-yellow-500 to-yellow-600', 
                border: 'border-yellow-500',
                text: 'text-yellow-800',
                light: 'bg-yellow-50',
                icon: '⚡' 
            };
        }
        return { 
            bg: 'bg-gradient-to-r from-green-500 to-green-600', 
            border: 'border-green-500',
            text: 'text-green-800',
            light: 'bg-green-50',
            icon: '✅' 
        };
    };

    const style = getRiskStyle();

    return (
        <div className="mt-8 space-y-6">
            {/* Tarjeta principal de riesgo */}
            <div className={`${style.bg} p-6 rounded-2xl text-white shadow-xl`}>
                <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4">
                    <div className="flex items-center gap-4">
                        <span className="text-5xl">{style.icon}</span>
                        <div>
                            <h2 className="text-3xl font-bold">
                                RIESGO {nivel_riesgo?.toUpperCase() || (riesgo_clase === 1 ? 'ALTO' : 'BAJO')}
                            </h2>
                            <p className="text-white/80 text-lg">
                                {estado} • {fecha_evaluacion}
                            </p>
                        </div>
                    </div>
                    <div className="text-center md:text-right">
                        <p className="text-5xl font-bold">{riesgo_probabilidad}%</p>
                        <p className="text-white/70">Probabilidad de brote</p>
                    </div>
                </div>
                
                <div className={`mt-4 p-4 rounded-xl bg-white/20`}>
                    <p className="text-lg font-medium">{mensaje}</p>
                </div>
            </div>

            {/* Datos epidemiológicos utilizados */}
            {datos_utilizados && (
                <div className="bg-white p-6 rounded-xl border shadow-md">
                    <h3 className="text-lg font-bold mb-4 flex items-center gap-2">
                        📊 Datos Epidemiológicos Analizados
                    </h3>
                    <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                        <div className="p-4 bg-blue-50 rounded-xl text-center">
                            <p className="text-3xl font-bold text-blue-600">
                                {datos_utilizados.casos_ultima_semana}
                            </p>
                            <p className="text-sm text-gray-600">Casos última semana</p>
                        </div>
                        <div className="p-4 bg-blue-50 rounded-xl text-center">
                            <p className="text-3xl font-bold text-blue-600">
                                {datos_utilizados.casos_hace_4_semanas}
                            </p>
                            <p className="text-sm text-gray-600">Casos hace 4 sem.</p>
                        </div>
                        <div className="p-4 bg-purple-50 rounded-xl text-center">
                            <p className="text-3xl font-bold text-purple-600">
                                {datos_utilizados.tasa_incidencia_actual}
                            </p>
                            <p className="text-sm text-gray-600">Tasa incidencia</p>
                        </div>
                        <div className="p-4 bg-gray-50 rounded-xl text-center">
                            <p className="text-3xl font-bold text-gray-600">
                                {datos_utilizados.poblacion_region?.toLocaleString() || 'N/A'}
                            </p>
                            <p className="text-sm text-gray-600">Población</p>
                        </div>
                    </div>
                </div>
            )}

            {/* Tendencias */}
            {tendencias && (
                <div className="bg-white p-6 rounded-xl border shadow-md">
                    <h3 className="text-lg font-bold mb-4">📈 Análisis de Tendencias</h3>
                    <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                        <div className="p-4 rounded-xl bg-gray-50 text-center">
                            <p className="text-sm text-gray-500 mb-2">Tendencia de Casos</p>
                            <p className={`text-xl font-bold ${
                                tendencias.casos === 'Creciente' ? 'text-red-600' : 
                                tendencias.casos === 'Decreciente' ? 'text-green-600' : 'text-gray-600'
                            }`}>
                                {tendencias.casos === 'Creciente' ? '📈 Creciente' : 
                                 tendencias.casos === 'Decreciente' ? '📉 Decreciente' : '➡️ Estable'}
                            </p>
                        </div>
                        <div className="p-4 rounded-xl bg-gray-50 text-center">
                            <p className="text-sm text-gray-500 mb-2">Tendencia de Tasa</p>
                            <p className={`text-xl font-bold ${
                                tendencias.tasa === 'Creciente' ? 'text-red-600' : 
                                tendencias.tasa === 'Decreciente' ? 'text-green-600' : 'text-gray-600'
                            }`}>
                                {tendencias.tasa === 'Creciente' ? '📈 Creciente' : 
                                 tendencias.tasa === 'Decreciente' ? '📉 Decreciente' : '➡️ Estable'}
                            </p>
                        </div>
                        <div className="p-4 rounded-xl bg-gray-50 text-center">
                            <p className="text-sm text-gray-500 mb-2">Temporada de Riesgo</p>
                            <p className={`text-xl font-bold ${
                                tendencias.temporada_riesgo?.includes('Sí') ? 'text-orange-600' : 'text-green-600'
                            }`}>
                                {tendencias.temporada_riesgo?.includes('Sí') ? '🌧️ Sí (lluvias)' : '☀️ No'}
                            </p>
                        </div>
                    </div>
                </div>
            )}

            {/* Predicción de próxima semana */}
            {prediccion && (
                <div className="bg-gradient-to-r from-indigo-500 to-purple-600 p-6 rounded-xl text-white shadow-lg">
                    <h3 className="text-lg font-bold mb-3">🔮 Predicción Próxima Semana</h3>
                    <div className="flex items-center justify-between">
                        <div>
                            <p className="text-4xl font-bold">{prediccion.casos_proxima_semana}</p>
                            <p className="text-indigo-100">casos estimados</p>
                        </div>
                        <div className="text-right text-indigo-100">
                            <p className="text-sm">Basado en análisis de</p>
                            <p className="font-semibold">{prediccion.historial_semanas} semanas de datos</p>
                        </div>
                    </div>
                </div>
            )}

            {/* Recomendaciones */}
            <div className={`${style.light} border ${style.border} p-6 rounded-xl`}>
                <h3 className={`text-lg font-bold mb-3 ${style.text}`}>
                    📋 Recomendaciones
                </h3>
                <ul className={`space-y-2 ${style.text}`}>
                    {riesgo_probabilidad >= 50 ? (
                        <>
                            <li>• Activar protocolo de vigilancia epidemiológica intensiva</li>
                            <li>• Reforzar campañas de control vectorial (fumigación)</li>
                            <li>• Alertar a unidades de salud de la región</li>
                            <li>• Incrementar capacidad de atención hospitalaria</li>
                        </>
                    ) : (
                        <>
                            <li>• Mantener vigilancia epidemiológica estándar</li>
                            <li>• Continuar con medidas preventivas habituales</li>
                            <li>• Monitorear tendencias semanalmente</li>
                        </>
                    )}
                </ul>
            </div>
        </div>
    );
};

export default RiesgoBroteForm;