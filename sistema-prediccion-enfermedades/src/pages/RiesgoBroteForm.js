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

// Componente para mostrar los resultados con slider limpio
const ResultDisplay = ({ data }) => {
    const [currentSlide, setCurrentSlide] = useState(0);

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
            return { bg: 'from-red-500 to-red-600', text: 'text-red-700', light: 'bg-red-50', border: 'border-red-200', icon: '🚨' };
        }
        if (riesgo_probabilidad >= 50) {
            return { bg: 'from-orange-500 to-orange-600', text: 'text-orange-700', light: 'bg-orange-50', border: 'border-orange-200', icon: '⚠️' };
        }
        if (riesgo_probabilidad >= 25) {
            return { bg: 'from-yellow-500 to-yellow-600', text: 'text-yellow-700', light: 'bg-yellow-50', border: 'border-yellow-200', icon: '⚡' };
        }
        return { bg: 'from-green-500 to-green-600', text: 'text-green-700', light: 'bg-green-50', border: 'border-green-200', icon: '✅' };
    };

    const style = getRiskStyle();

    // Definir slides
    const slides = [
        { id: 'riesgo', label: 'Riesgo' },
        { id: 'datos', label: 'Datos' },
        { id: 'tendencias', label: 'Tendencias' },
        { id: 'acciones', label: 'Acciones' }
    ];

    const nextSlide = () => setCurrentSlide((prev) => (prev + 1) % slides.length);
    const prevSlide = () => setCurrentSlide((prev) => (prev - 1 + slides.length) % slides.length);

    // Navegación con teclado
    useEffect(() => {
        const handleKeyDown = (e) => {
            if (e.key === 'ArrowRight') nextSlide();
            if (e.key === 'ArrowLeft') prevSlide();
        };
        window.addEventListener('keydown', handleKeyDown);
        return () => window.removeEventListener('keydown', handleKeyDown);
    }, []);

    return (
        <div className="mt-8">
            {/* Navegación por tabs */}
            <div className="flex items-center justify-between mb-4">
                <div className="flex gap-1 bg-gray-100 p-1 rounded-lg">
                    {slides.map((slide, idx) => (
                        <button
                            key={slide.id}
                            onClick={() => setCurrentSlide(idx)}
                            className={`px-4 py-2 text-sm font-medium rounded-md transition-all ${
                                currentSlide === idx
                                    ? 'bg-white text-gray-900 shadow-sm'
                                    : 'text-gray-500 hover:text-gray-700'
                            }`}
                        >
                            {slide.label}
                        </button>
                    ))}
                </div>
                <div className="flex gap-2">
                    <button onClick={prevSlide} className="p-2 rounded-lg bg-gray-100 hover:bg-gray-200 transition-colors">
                        <svg className="w-5 h-5 text-gray-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
                        </svg>
                    </button>
                    <button onClick={nextSlide} className="p-2 rounded-lg bg-gray-100 hover:bg-gray-200 transition-colors">
                        <svg className="w-5 h-5 text-gray-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
                        </svg>
                    </button>
                </div>
            </div>

            {/* Contenedor del slide */}
            <div className="bg-white rounded-2xl border shadow-lg overflow-hidden min-h-[400px]">
                {/* Slide 0: Nivel de Riesgo */}
                {currentSlide === 0 && (
                    <div className="p-6 h-full animate-fadeIn">
                        <div className={`bg-gradient-to-br ${style.bg} rounded-xl p-8 text-white h-full flex flex-col`}>
                            {/* Header con icono y nivel */}
                            <div className="flex items-center justify-between mb-8">
                                <div className="flex items-center gap-5">
                                    <span className="text-6xl">{style.icon}</span>
                                    <div>
                                        <p className="text-sm text-white/70 uppercase tracking-widest mb-1">Nivel de Riesgo</p>
                                        <h2 className="text-4xl font-bold">
                                            {nivel_riesgo?.toUpperCase() || (riesgo_clase === 1 ? 'ALTO' : 'BAJO')}
                                        </h2>
                                    </div>
                                </div>
                                <div className="text-right">
                                    <p className="text-6xl font-bold">{riesgo_probabilidad}%</p>
                                    <p className="text-white/70">probabilidad de brote</p>
                                </div>
                            </div>

                            {/* Info del estado */}
                            <div className="grid grid-cols-2 gap-4 mb-6">
                                <div className="p-4 bg-white/10 rounded-xl backdrop-blur">
                                    <p className="text-sm text-white/60">Estado</p>
                                    <p className="text-xl font-semibold">{estado}</p>
                                </div>
                                <div className="p-4 bg-white/10 rounded-xl backdrop-blur">
                                    <p className="text-sm text-white/60">Fecha de evaluación</p>
                                    <p className="text-xl font-semibold">{fecha_evaluacion}</p>
                                </div>
                            </div>

                            {/* Mensaje */}
                            <div className="flex-1 flex items-center">
                                <div className="w-full p-5 bg-white/15 rounded-xl backdrop-blur">
                                    <p className="text-lg leading-relaxed">{mensaje}</p>
                                </div>
                            </div>
                        </div>
                    </div>
                )}

                {/* Slide 1: Datos Epidemiológicos */}
                {currentSlide === 1 && datos_utilizados && (
                    <div className="p-6 animate-fadeIn">
                        <h3 className="text-lg font-bold text-gray-800 mb-6">📊 Datos Epidemiológicos</h3>
                        <div className="grid grid-cols-2 gap-4">
                            <div className="p-6 bg-blue-50 rounded-xl text-center">
                                <p className="text-4xl font-bold text-blue-600">{datos_utilizados.casos_ultima_semana}</p>
                                <p className="text-sm text-gray-600 mt-2">Casos última semana</p>
                            </div>
                            <div className="p-6 bg-blue-50 rounded-xl text-center">
                                <p className="text-4xl font-bold text-blue-600">{datos_utilizados.casos_hace_4_semanas}</p>
                                <p className="text-sm text-gray-600 mt-2">Casos hace 4 semanas</p>
                            </div>
                            <div className="p-6 bg-purple-50 rounded-xl text-center">
                                <p className="text-4xl font-bold text-purple-600">{datos_utilizados.tasa_incidencia_actual}</p>
                                <p className="text-sm text-gray-600 mt-2">Tasa de incidencia</p>
                            </div>
                            <div className="p-6 bg-gray-50 rounded-xl text-center">
                                <p className="text-3xl font-bold text-gray-700">{datos_utilizados.poblacion_region?.toLocaleString() || 'N/A'}</p>
                                <p className="text-sm text-gray-600 mt-2">Población total</p>
                            </div>
                        </div>
                    </div>
                )}

                {/* Slide 2: Tendencias y Predicción */}
                {currentSlide === 2 && (
                    <div className="p-6 animate-fadeIn">
                        <h3 className="text-lg font-bold text-gray-800 mb-6">📈 Tendencias y Predicción</h3>
                        {tendencias && (
                            <div className="space-y-3 mb-6">
                                <div className="flex items-center justify-between p-4 bg-gray-50 rounded-xl">
                                    <span className="text-gray-600">Tendencia de casos</span>
                                    <span className={`font-semibold ${
                                        tendencias.casos === 'Creciente' ? 'text-red-600' :
                                        tendencias.casos === 'Decreciente' ? 'text-green-600' : 'text-gray-600'
                                    }`}>
                                        {tendencias.casos === 'Creciente' ? '📈 Creciente' :
                                         tendencias.casos === 'Decreciente' ? '📉 Decreciente' : '➡️ Estable'}
                                    </span>
                                </div>
                                <div className="flex items-center justify-between p-4 bg-gray-50 rounded-xl">
                                    <span className="text-gray-600">Tendencia de tasa</span>
                                    <span className={`font-semibold ${
                                        tendencias.tasa === 'Creciente' ? 'text-red-600' :
                                        tendencias.tasa === 'Decreciente' ? 'text-green-600' : 'text-gray-600'
                                    }`}>
                                        {tendencias.tasa === 'Creciente' ? '📈 Creciente' :
                                         tendencias.tasa === 'Decreciente' ? '📉 Decreciente' : '➡️ Estable'}
                                    </span>
                                </div>
                                <div className="flex items-center justify-between p-4 bg-gray-50 rounded-xl">
                                    <span className="text-gray-600">Temporada de riesgo</span>
                                    <span className={`font-semibold ${
                                        tendencias.temporada_riesgo?.includes('Sí') ? 'text-orange-600' : 'text-green-600'
                                    }`}>
                                        {tendencias.temporada_riesgo?.includes('Sí') ? '🌧️ Sí (lluvias)' : '☀️ No'}
                                    </span>
                                </div>
                            </div>
                        )}
                        {prediccion && (
                            <div className="bg-gradient-to-r from-indigo-500 to-purple-600 rounded-xl p-6 text-white">
                                <p className="text-sm text-indigo-200 mb-1">🔮 Predicción próxima semana</p>
                                <div className="flex items-end justify-between">
                                    <div>
                                        <p className="text-4xl font-bold">{prediccion.casos_proxima_semana}</p>
                                        <p className="text-indigo-200">casos estimados</p>
                                    </div>
                                    <p className="text-indigo-200 text-sm">
                                        Basado en {prediccion.historial_semanas} semanas
                                    </p>
                                </div>
                            </div>
                        )}
                    </div>
                )}

                {/* Slide 3: Recomendaciones */}
                {currentSlide === 3 && (
                    <div className="p-6 animate-fadeIn">
                        <h3 className="text-lg font-bold text-gray-800 mb-6">📋 Recomendaciones</h3>
                        <div className={`${style.light} ${style.border} border rounded-xl p-6`}>
                            <ul className={`space-y-4 ${style.text}`}>
                                {riesgo_probabilidad >= 50 ? (
                                    <>
                                        <li className="flex items-start gap-3">
                                            <span className="w-6 h-6 bg-white rounded-full flex items-center justify-center text-sm shadow-sm">1</span>
                                            <span>Activar protocolo de vigilancia epidemiológica intensiva</span>
                                        </li>
                                        <li className="flex items-start gap-3">
                                            <span className="w-6 h-6 bg-white rounded-full flex items-center justify-center text-sm shadow-sm">2</span>
                                            <span>Reforzar campañas de control vectorial (fumigación)</span>
                                        </li>
                                        <li className="flex items-start gap-3">
                                            <span className="w-6 h-6 bg-white rounded-full flex items-center justify-center text-sm shadow-sm">3</span>
                                            <span>Alertar a unidades de salud de la región</span>
                                        </li>
                                        <li className="flex items-start gap-3">
                                            <span className="w-6 h-6 bg-white rounded-full flex items-center justify-center text-sm shadow-sm">4</span>
                                            <span>Incrementar capacidad de atención hospitalaria</span>
                                        </li>
                                    </>
                                ) : (
                                    <>
                                        <li className="flex items-start gap-3">
                                            <span className="w-6 h-6 bg-white rounded-full flex items-center justify-center text-sm shadow-sm">1</span>
                                            <span>Mantener vigilancia epidemiológica estándar</span>
                                        </li>
                                        <li className="flex items-start gap-3">
                                            <span className="w-6 h-6 bg-white rounded-full flex items-center justify-center text-sm shadow-sm">2</span>
                                            <span>Continuar con medidas preventivas habituales</span>
                                        </li>
                                        <li className="flex items-start gap-3">
                                            <span className="w-6 h-6 bg-white rounded-full flex items-center justify-center text-sm shadow-sm">3</span>
                                            <span>Monitorear tendencias semanalmente</span>
                                        </li>
                                    </>
                                )}
                            </ul>
                        </div>
                    </div>
                )}
            </div>

            {/* Indicadores de slide */}
            <div className="flex justify-center gap-2 mt-4">
                {slides.map((_, idx) => (
                    <button
                        key={idx}
                        onClick={() => setCurrentSlide(idx)}
                        className={`h-2 rounded-full transition-all ${
                            currentSlide === idx ? 'w-6 bg-blue-600' : 'w-2 bg-gray-300 hover:bg-gray-400'
                        }`}
                    />
                ))}
            </div>
            <p className="text-center text-xs text-gray-400 mt-2">
                Usa ← → para navegar
            </p>
        </div>
    );
};

export default RiesgoBroteForm;
