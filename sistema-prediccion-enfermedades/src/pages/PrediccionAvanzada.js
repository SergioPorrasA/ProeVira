// src/pages/PrediccionAvanzada.js
// Módulo Avanzado de Predicción de Riesgo de Brote de Dengue
// Permite seleccionar fecha, período y comparar predicciones con datos reales

import React, { useState, useEffect, useRef } from 'react';
import { datosService, modeloService } from '../services/api';

const API_URL = 'http://localhost:5001/api';

const PrediccionAvanzada = () => {
    const [regiones, setRegiones] = useState([]);
    const [loadingRegiones, setLoadingRegiones] = useState(true);
    const [formData, setFormData] = useState({
        id_region: '',
        fecha_inicio: '',
        semanas_prediccion: 4,
        modo_validacion: false // Nuevo: modo para comparar con datos reales
    });
    const [predicciones, setPredicciones] = useState([]);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState(null);
    const [resumenModelo, setResumenModelo] = useState(null);
    const [metricsValidacion, setMetricsValidacion] = useState(null);
    const [guardando, setGuardando] = useState(false);
    const [mensajeGuardado, setMensajeGuardado] = useState(null);

    // Cargar regiones
    useEffect(() => {
        const cargarRegiones = async () => {
            try {
                setLoadingRegiones(true);
                const response = await datosService.getRegiones();
                const regionesOrdenadas = (response.data || []).sort((a, b) =>
                    a.nombre.localeCompare(b.nombre)
                );
                setRegiones(regionesOrdenadas);
            } catch (err) {
                console.error('Error al cargar regiones:', err);
                setError('Error al cargar las regiones.');
            } finally {
                setLoadingRegiones(false);
            }
        };
        cargarRegiones();
    }, []);

    const handleChange = (e) => {
        const { name, value, type, checked } = e.target;
        setFormData(prev => ({
            ...prev,
            [name]: type === 'checkbox' ? checked : value
        }));
    };

    const handleSubmit = async (e) => {
        e.preventDefault();

        if (!formData.id_region || !formData.fecha_inicio) {
            setError('Debe seleccionar un estado y una fecha de inicio');
            return;
        }

        setLoading(true);
        setError(null);
        setPredicciones([]);
        setResumenModelo(null);
        setMetricsValidacion(null);

        try {
            const resultados = [];
            const fechaBase = new Date(formData.fecha_inicio);
            const semanasAPredecir = parseInt(formData.semanas_prediccion, 10);

            // Generar predicciones para cada semana
            for (let i = 0; i < semanasAPredecir; i++) {
                const fechaPrediccion = new Date(fechaBase);
                fechaPrediccion.setDate(fechaBase.getDate() + (i * 7));

                const response = await modeloService.predecirRiesgoAvanzado({
                    id_region: parseInt(formData.id_region, 10),
                    fecha_prediccion: fechaPrediccion.toISOString().split('T')[0],
                    incluir_metricas: true,
                    incluir_validacion: formData.modo_validacion,
                    semana_offset: i  // Enviar offset para proyecciones secuenciales
                });

                if (response.data.success) {
                    resultados.push({
                        semana: i + 1,
                        fecha: fechaPrediccion.toISOString().split('T')[0],
                        ...response.data
                    });
                }
            }

            setPredicciones(resultados);

            // Calcular resumen del modelo
            if (resultados.length > 0) {
                const promedioRiesgo = resultados.reduce((sum, r) => sum + r.riesgo_probabilidad, 0) / resultados.length;
                const maxRiesgo = Math.max(...resultados.map(r => r.riesgo_probabilidad));
                const minRiesgo = Math.min(...resultados.map(r => r.riesgo_probabilidad));

                setResumenModelo({
                    total_predicciones: resultados.length,
                    promedio_riesgo: promedioRiesgo.toFixed(1),
                    max_riesgo: maxRiesgo,
                    min_riesgo: minRiesgo,
                    estado: resultados[0].estado,
                    modelo: resultados[0].modelo_utilizado || 'Random Forest',
                    confiabilidad: resultados[0].metricas_modelo?.accuracy || 85
                });

                // Calcular métricas de validación si hay datos reales
                const conValidacion = resultados.filter(r => r.validacion);
                if (conValidacion.length > 0) {
                    const errores = conValidacion.map(r => {
                        const predicho = r.prediccion?.casos_proxima_semana || r.datos_utilizados?.casos_ultima_semana;
                        const real = r.validacion.casos_reales;
                        return {
                            error_absoluto: Math.abs(predicho - real),
                            error_porcentual: real > 0 ? Math.abs((predicho - real) / real) * 100 : 0,
                            predicho,
                            real
                        };
                    });

                    const mae = errores.reduce((sum, e) => sum + e.error_absoluto, 0) / errores.length;
                    const mape = errores.reduce((sum, e) => sum + e.error_porcentual, 0) / errores.length;
                    const rmse = Math.sqrt(errores.reduce((sum, e) => sum + Math.pow(e.error_absoluto, 2), 0) / errores.length);

                    // Calcular R² (coeficiente de determinación)
                    const mediaReal = errores.reduce((sum, e) => sum + e.real, 0) / errores.length;
                    const ssRes = errores.reduce((sum, e) => sum + Math.pow(e.real - e.predicho, 2), 0);
                    const ssTot = errores.reduce((sum, e) => sum + Math.pow(e.real - mediaReal, 2), 0);
                    const r2 = ssTot > 0 ? 1 - (ssRes / ssTot) : 0;

                    setMetricsValidacion({
                        registros_validados: conValidacion.length,
                        mae: mae.toFixed(1),
                        mape: mape.toFixed(1),
                        rmse: rmse.toFixed(1),
                        r2: (r2 * 100).toFixed(1),
                        precision_general: (100 - mape).toFixed(1)
                    });
                }
            }

        } catch (err) {
            console.error('Error en predicción:', err);
            setError(err.response?.data?.error || 'Error al generar predicciones');
        } finally {
            setLoading(false);
        }
    };

    const getNivelRiesgo = (prob) => {
        if (prob >= 75) return { nivel: 'Crítico', color: 'bg-red-500', textColor: 'text-red-600' };
        if (prob >= 50) return { nivel: 'Alto', color: 'bg-orange-500', textColor: 'text-orange-600' };
        if (prob >= 25) return { nivel: 'Moderado', color: 'bg-yellow-500', textColor: 'text-yellow-600' };
        return { nivel: 'Bajo', color: 'bg-green-500', textColor: 'text-green-600' };
    };

    const getErrorColor = (errorPct) => {
        if (errorPct <= 10) return 'text-green-600 bg-green-50';
        if (errorPct <= 25) return 'text-yellow-600 bg-yellow-50';
        if (errorPct <= 50) return 'text-orange-600 bg-orange-50';
        return 'text-red-600 bg-red-50';
    };

    // Ref y funciones para slider horizontal en la Escala de Error
    const escalaRef = useRef(null);
    const scrollEscala = (dir = 1) => {
        if (!escalaRef.current) return;
        const ancho = escalaRef.current.clientWidth || 300;
        escalaRef.current.scrollBy({ left: dir * Math.round(ancho * 0.8), behavior: 'smooth' });
    };
    // Ref y funciones para slider horizontal en la sección de resultados
    const resultadosRef = useRef(null);
    const scrollResultados = (dir = 1) => {
        if (!resultadosRef.current) return;
        const ancho = resultadosRef.current.clientWidth || 600;
        resultadosRef.current.scrollBy({ left: dir * Math.round(ancho * 0.9), behavior: 'smooth' });
    };

    // Función para guardar predicción en la base de datos
    const guardarPrediccion = async () => {
        if (predicciones.length === 0) {
            setError('No hay predicciones para guardar');
            return;
        }

        setGuardando(true);
        setMensajeGuardado(null);

        try {
            const estadoNombre = regiones.find(r => r.id === parseInt(formData.id_region))?.nombre || 'Desconocido';

            // Preparar datos para guardar
            const datosGuardar = {
                estado: estadoNombre,
                id_region: parseInt(formData.id_region),
                fecha_inicio: formData.fecha_inicio,
                numero_semanas: parseInt(formData.semanas_prediccion),
                predicciones: predicciones.map(p => ({
                    semana: p.semana,
                    fecha: p.fecha,
                    casos_estimados: p.prediccion?.casos_proxima_semana || p.datos_utilizados?.casos_ultima_semana || 0,
                    nivel_riesgo: getNivelRiesgo(p.riesgo_probabilidad).nivel,
                    probabilidad: p.riesgo_probabilidad
                })),
                validacion: formData.modo_validacion ? predicciones.filter(p => p.validacion).map(p => ({
                    semana: p.semana,
                    casos_reales: p.validacion?.casos_reales,
                    error_porcentaje: p.validacion?.casos_reales > 0
                        ? Math.abs(((p.prediccion?.casos_proxima_semana || 0) - p.validacion.casos_reales) / p.validacion.casos_reales) * 100
                        : 0
                })) : [],
                metricas: metricsValidacion || {}
            };

            const response = await fetch(`${API_URL}/predicciones/guardar`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(datosGuardar)
            });

            const data = await response.json();

            if (data.success) {
                setMensajeGuardado({
                    tipo: 'success',
                    texto: 'Predicción guardada exitosamente'
                });
            } else {
                throw new Error(data.error || 'Error al guardar');
            }
        } catch (err) {
            console.error('Error guardando:', err);
            setMensajeGuardado({
                tipo: 'error',
                texto: `Error: ${err.message}`
            });
        } finally {
            setGuardando(false);
        }
    };

    return (
        <div className="p-6 max-w-7xl mx-auto">
            {/* ═══════════════════════════════════════════════════════════════
                HEADER PRINCIPAL - Con mejor simbología y negritas
            ═══════════════════════════════════════════════════════════════ */}
            <div className="mb-8 bg-gradient-to-r from-blue-600 via-blue-700 to-indigo-700 p-8 rounded-2xl text-white shadow-2xl">
                <div className="flex items-center gap-6">
                    <div className="w-20 h-20 bg-white/20 rounded-2xl flex items-center justify-center backdrop-blur-sm">
                        <span className="text-5xl">🔮</span>
                    </div>
                    <div>
                        <h1 className="text-3xl font-black mb-2">
                            Predicción Avanzada de Dengue
                        </h1>
                        <p className="text-blue-100 text-lg">
                            <strong>Genera predicciones</strong> para un período específico y <strong>compara con datos reales</strong> para evaluar la precisión del modelo.
                        </p>
                    </div>
                </div>
                {/* Badges informativos */}
                <div className="mt-6 flex flex-wrap gap-3">
                    <span className="px-4 py-2 bg-white/20 rounded-xl text-sm font-bold flex items-center gap-2">
                        <span>🤖</span> <strong>Random Forest</strong> - 85% precisión
                    </span>
                    <span className="px-4 py-2 bg-white/20 rounded-xl text-sm font-bold flex items-center gap-2">
                        <span>📊</span> <strong>9,760+</strong> registros históricos
                    </span>
                    <span className="px-4 py-2 bg-white/20 rounded-xl text-sm font-bold flex items-center gap-2">
                        <span>📅</span> Datos <strong>2020-2025</strong>
                    </span>
                </div>
            </div>

            {/* ═══════════════════════════════════════════════════════════════
                FORMULARIO DE CONFIGURACIÓN
            ═══════════════════════════════════════════════════════════════ */}
            <div className="bg-white p-6 rounded-2xl border-2 border-blue-100 shadow-xl mb-8">
                <h2 className="text-xl font-black mb-6 flex items-center gap-3 text-gray-800">
                    <span className="w-10 h-10 bg-blue-100 rounded-xl flex items-center justify-center">
                        <span className="text-xl">⚙️</span>
                    </span>
                    <span>Configuración de <strong>Predicción</strong></span>
                </h2>

                <form onSubmit={handleSubmit}>
                    <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
                        {/* Estado */}
                        <div>
                            <label className="block text-sm font-black text-gray-700 mb-2 flex items-center gap-2">
                                <span>📍</span> Estado / Entidad <span className="text-red-500">*</span>
                            </label>
                            <select
                                name="id_region"
                                value={formData.id_region}
                                onChange={handleChange}
                                required
                                disabled={loadingRegiones}
                                className="w-full p-3 border-2 border-gray-200 rounded-xl focus:ring-2 focus:ring-blue-500 focus:border-blue-500 font-medium transition-all"
                            >
                                <option value="">
                                    {loadingRegiones ? '⏳ Cargando...' : '-- Seleccione --'}
                                </option>
                                {regiones.map((r) => (
                                    <option key={r.id} value={r.id}>{r.nombre}</option>
                                ))}
                            </select>
                        </div>

                        {/* Fecha de inicio */}
                        <div>
                            <label className="block text-sm font-black text-gray-700 mb-2 flex items-center gap-2">
                                <span>📅</span> Fecha de Inicio <span className="text-red-500">*</span>
                            </label>
                            <input
                                type="date"
                                name="fecha_inicio"
                                value={formData.fecha_inicio}
                                onChange={handleChange}
                                required
                                className="w-full p-3 border-2 border-gray-200 rounded-xl focus:ring-2 focus:ring-blue-500 focus:border-blue-500 font-medium transition-all"
                            />
                            <p className="text-xs text-blue-600 mt-1 font-medium">
                                💡 Usa fechas <strong>pasadas</strong> para validar
                            </p>
                        </div>

                        {/* Semanas a predecir */}
                        <div>
                            <label className="block text-sm font-black text-gray-700 mb-2 flex items-center gap-2">
                                <span>📆</span> Semanas a Predecir
                            </label>
                            <select
                                name="semanas_prediccion"
                                value={formData.semanas_prediccion}
                                onChange={handleChange}
                                className="w-full p-3 border-2 border-gray-200 rounded-xl focus:ring-2 focus:ring-blue-500 focus:border-blue-500 font-medium transition-all"
                            >
                                <option value="1">1 semana</option>
                                <option value="2">2 semanas</option>
                                <option value="4">4 semanas (1 mes)</option>
                                <option value="8">8 semanas (2 meses)</option>
                                <option value="12">12 semanas (3 meses)</option>
                            </select>
                        </div>

                        {/* Modo validación */}
                        <div className="flex items-center">
                            <label className="flex items-center gap-3 cursor-pointer p-3 border rounded-lg hover:bg-gray-50 w-full">
                                <input
                                    type="checkbox"
                                    name="modo_validacion"
                                    checked={formData.modo_validacion}
                                    onChange={handleChange}
                                    className="w-5 h-5 text-blue-600 rounded focus:ring-blue-500"
                                />
                                <div>
                                    <span className="font-medium text-gray-700">Comparar con datos reales</span>
                                    <p className="text-xs text-gray-500">Valida precisión del modelo</p>
                                </div>
                            </label>
                        </div>
                    </div>

                    {/* Botón de envío mejorado */}
                    <button
                        type="submit"
                        disabled={loading || loadingRegiones}
                        className="mt-6 px-10 py-4 bg-gradient-to-r from-blue-600 to-indigo-600 text-white font-black text-lg rounded-xl hover:from-blue-700 hover:to-indigo-700 disabled:from-gray-400 disabled:to-gray-500 disabled:cursor-not-allowed transition-all shadow-lg hover:shadow-xl hover:scale-105 active:scale-95 flex items-center gap-3"
                    >
                        {loading ? (
                            <>
                                <svg className="animate-spin h-6 w-6" viewBox="0 0 24 24">
                                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none"/>
                                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"/>
                                </svg>
                                <span>Generando predicciones...</span>
                            </>
                        ) : (
                            <>
                                <span>🚀</span>
                                <span>Generar Predicciones</span>
                            </>
                        )}
                    </button>
                </form>
            </div>

            {/* Error */}
            {error && (
                <div className="mb-6 p-4 bg-red-50 border border-red-300 text-red-700 rounded-xl">
                    <strong>⚠️ Error:</strong> {error}
                </div>
            )}

            {/* Métricas de Validación */}
            {metricsValidacion && (
                <div className="mb-8 bg-gradient-to-r from-blue-500 to-indigo-600 p-6 rounded-xl text-white shadow-xl">
                    <h3 className="text-xl font-bold mb-4 flex items-center gap-2">
                        ✅ Validación del Modelo vs Datos Reales
                    </h3>
                    <div className="grid grid-cols-2 md:grid-cols-6 gap-4">
                        <div className="bg-white/20 p-4 rounded-xl text-center">
                            <p className="text-3xl font-bold">{metricsValidacion.registros_validados}</p>
                            <p className="text-blue-100 text-sm">Semanas Validadas</p>
                        </div>
                        <div className="bg-white/20 p-4 rounded-xl text-center">
                            <p className="text-3xl font-bold">{metricsValidacion.precision_general}%</p>
                            <p className="text-blue-100 text-sm">Precisión Casos</p>
                        </div>
                        <div className="bg-white/20 p-4 rounded-xl text-center">
                            <p className="text-3xl font-bold">{metricsValidacion.mae}</p>
                            <p className="text-blue-100 text-sm">MAE (Error Abs.)</p>
                        </div>
                        <div className="bg-white/20 p-4 rounded-xl text-center">
                            <p className="text-3xl font-bold">{metricsValidacion.mape}%</p>
                            <p className="text-blue-100 text-sm">MAPE (Error %)</p>
                        </div>
                        <div className="bg-white/20 p-4 rounded-xl text-center">
                            <p className="text-3xl font-bold">{metricsValidacion.rmse}</p>
                            <p className="text-blue-100 text-sm">RMSE</p>
                        </div>
                        <div className="bg-white/20 p-4 rounded-xl text-center">
                            <p className="text-3xl font-bold">{metricsValidacion.r2}%</p>
                            <p className="text-blue-100 text-sm">R² (Ajuste)</p>
                        </div>
                    </div>
                    <div className="mt-4 p-3 bg-white/10 rounded-lg">
                        <p className="text-sm">
                            <strong>📊 Nota importante:</strong> La <strong>Probabilidad de Riesgo</strong> (calculada por Random Forest con 85% de precisión)
                            es el indicador más confiable. Los <strong>Casos Estimados</strong> son aproximaciones basadas en promedios históricos
                            y pueden variar significativamente en épocas de cambios bruscos.
                            {parseFloat(metricsValidacion.mape) <= 30 ?
                                ' ✅ El error de estimación está en rango aceptable.' :
                                ' ⚠️ Se recomienda enfocarse en el nivel de riesgo más que en el número exacto de casos.'}
                        </p>
                    </div>
                </div>
            )}

            {/* Dashboard de Resultados */}
            {resumenModelo && (
                <div className="mb-8">
                    {/* Tarjetas de resumen */}
                    <div className="grid grid-cols-2 md:grid-cols-5 gap-4 mb-6">
                        <div className="bg-white p-4 rounded-xl border shadow text-center">
                            <p className="text-3xl font-bold text-indigo-600">{resumenModelo.total_predicciones}</p>
                            <p className="text-sm font-bold text-gray-700">Predicciones</p>
                        </div>
                        <div className="bg-white p-4 rounded-xl border shadow text-center">
                            <p className="text-3xl font-bold text-purple-600">{resumenModelo.promedio_riesgo}%</p>
                            <p className="text-sm font-bold text-gray-700">Riesgo Promedio</p>
                        </div>
                        <div className="bg-white p-4 rounded-xl border shadow text-center">
                            <p className="text-3xl font-bold text-red-600">{resumenModelo.max_riesgo}%</p>
                            <p className="text-sm font-bold text-gray-700">Riesgo Máximo</p>
                        </div>
                        <div className="bg-white p-4 rounded-xl border shadow text-center">
                            <p className="text-3xl font-bold text-green-600">{resumenModelo.min_riesgo}%</p>
                            <p className="text-sm font-bold text-gray-700">Riesgo Mínimo</p>
                        </div>
                        <div className="bg-white p-4 rounded-xl border-2 border-blue-500 shadow text-center">
                            <p className="text-3xl font-bold text-blue-600">{resumenModelo.confiabilidad}%</p>
                            <p className="text-sm font-bold text-gray-700">Precisión Riesgo</p>
                            <p className="text-xs text-blue-500">Random Forest</p>
                        </div>
                    </div>

                    {/* Nota sobre el modelo */}
                    <div className="mt-4 p-3 bg-blue-50 border border-blue-200 rounded-lg">
                        <p className="text-sm text-blue-800">
                            <strong>Guía de uso:</strong> El modelo Random Forest tiene <strong>85% de precisión</strong> para detectar
                            <strong> riesgo de brote</strong> (Crítico/Alto/Moderado/Bajo). Use el nivel de riesgo para tomar decisiones
                            de prevención. Los casos estimados son orientativos.
                        </p>
                    </div>

                    {/* SIMBOLOGÍA DE NIVELES DE RIESGO */}
                    <div className="mt-6 bg-white p-5 rounded-xl border shadow-lg">
                        <h3 className="text-lg font-bold text-gray-800 mb-4">Simbología de Niveles de Riesgo</h3>
                        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                            <div className="flex items-center gap-3 p-3 bg-red-50 rounded-lg border border-red-200">
                                <div className="w-5 h-5 bg-red-500 rounded-full flex-shrink-0"></div>
                                <div>
                                    <p className="font-bold text-red-700">Crítico</p>
                                    <p className="text-xs text-red-600">≥ 75% probabilidad</p>
                                </div>
                            </div>
                            <div className="flex items-center gap-3 p-3 bg-orange-50 rounded-lg border border-orange-200">
                                <div className="w-5 h-5 bg-orange-500 rounded-full flex-shrink-0"></div>
                                <div>
                                    <p className="font-bold text-orange-700">Alto</p>
                                    <p className="text-xs text-orange-600">50% - 74% probabilidad</p>
                                </div>
                            </div>
                            <div className="flex items-center gap-3 p-3 bg-yellow-50 rounded-lg border border-yellow-200">
                                <div className="w-5 h-5 bg-yellow-500 rounded-full flex-shrink-0"></div>
                                <div>
                                    <p className="font-bold text-yellow-700">Moderado</p>
                                    <p className="text-xs text-yellow-600">25% - 49% probabilidad</p>
                                </div>
                            </div>
                            <div className="flex items-center gap-3 p-3 bg-green-50 rounded-lg border border-green-200">
                                <div className="w-5 h-5 bg-green-500 rounded-full flex-shrink-0"></div>
                                <div>
                                    <p className="font-bold text-green-700">Bajo</p>
                                    <p className="text-xs text-green-600">&lt; 25% probabilidad</p>
                                </div>
                            </div>
                        </div>
                    </div>

                    {/* Slider de Resultados de Predicción */}
                    <div className="bg-white p-6 rounded-xl border shadow-lg mb-6 mt-6">
                        <h3 className="text-lg font-bold mb-4">Resultados de Predicción - {resumenModelo.estado}</h3>
                        <div className="relative">
                            {/* Flecha izquierda */}
                            <button
                                type="button"
                                onClick={() => scrollResultados(-1)}
                                className="absolute left-0 top-1/2 -translate-y-1/2 z-10 p-2 bg-white rounded-full shadow-lg border border-gray-200 hover:bg-gray-50 hover:scale-110 transition-all"
                            >
                                <svg className="w-6 h-6 text-gray-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
                                </svg>
                            </button>

                            {/* Contenedor deslizable */}
                            <div
                                ref={resultadosRef}
                                className="flex gap-4 overflow-x-auto scroll-smooth px-12 py-4 snap-x snap-mandatory"
                                style={{ scrollbarWidth: 'none', msOverflowStyle: 'none' }}
                            >
                                {predicciones.map((pred, idx) => {
                                    const riesgo = getNivelRiesgo(pred.riesgo_probabilidad);
                                    const casosEstimados = pred.prediccion?.casos_proxima_semana || pred.datos_utilizados?.casos_ultima_semana;
                                    return (
                                        <div
                                            key={idx}
                                            className={`flex-none w-64 p-5 rounded-xl border-2 shadow-lg snap-center transition-all hover:scale-105 ${
                                                riesgo.nivel === 'Crítico' ? 'bg-gradient-to-br from-red-50 to-red-100 border-red-300' :
                                                riesgo.nivel === 'Alto' ? 'bg-gradient-to-br from-orange-50 to-orange-100 border-orange-300' :
                                                riesgo.nivel === 'Moderado' ? 'bg-gradient-to-br from-yellow-50 to-yellow-100 border-yellow-300' :
                                                'bg-gradient-to-br from-green-50 to-green-100 border-green-300'
                                            }`}
                                        >
                                            {/* Header de la tarjeta */}
                                            <div className="flex justify-between items-center mb-3">
                                                <span className="text-sm font-bold text-gray-600">Semana {pred.semana}</span>
                                                <span className={`px-3 py-1 rounded-full text-xs font-bold text-white ${riesgo.color}`}>
                                                    {riesgo.nivel}
                                                </span>
                                            </div>

                                            {/* Fecha */}
                                            <p className="text-xs text-gray-500 mb-3">{pred.fecha}</p>

                                            {/* Probabilidad de riesgo */}
                                            <div className="text-center mb-3">
                                                <p className={`text-4xl font-black ${riesgo.textColor}`}>
                                                    {pred.riesgo_probabilidad}%
                                                </p>
                                                <p className="text-xs text-gray-500">Probabilidad de Riesgo</p>
                                            </div>

                                            {/* Barra de progreso */}
                                            <div className="h-3 bg-gray-200 rounded-full overflow-hidden mb-3">
                                                <div
                                                    className={`h-full ${riesgo.color} transition-all duration-700`}
                                                    style={{ width: `${pred.riesgo_probabilidad}%` }}
                                                />
                                            </div>

                                            {/* Casos estimados */}
                                            <div className="text-center p-2 bg-white/60 rounded-lg">
                                                <p className="text-2xl font-bold text-blue-600">{casosEstimados}</p>
                                                <p className="text-xs text-gray-500">Casos Estimados</p>
                                            </div>
                                        </div>
                                    );
                                })}
                            </div>

                            {/* Flecha derecha */}
                            <button
                                type="button"
                                onClick={() => scrollResultados(1)}
                                className="absolute right-0 top-1/2 -translate-y-1/2 z-10 p-2 bg-white rounded-full shadow-lg border border-gray-200 hover:bg-gray-50 hover:scale-110 transition-all"
                            >
                                <svg className="w-6 h-6 text-gray-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
                                </svg>
                            </button>
                        </div>

                        {/* Indicadores de posición */}
                        <div className="flex justify-center gap-2 mt-4">
                            {predicciones.map((_, idx) => (
                                <div key={idx} className="w-2 h-2 rounded-full bg-gray-300"></div>
                            ))}
                        </div>
                    </div>

                    {/* Información del modelo */}
                    <div className="bg-gradient-to-r from-blue-500 to-indigo-500 p-6 rounded-xl text-white shadow-lg mb-6">
                        <h3 className="text-lg font-bold mb-4">Información del Modelo</h3>
                        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                            <div>
                                <p className="text-blue-100 text-sm">Algoritmo</p>
                                <p className="font-bold text-lg">{resumenModelo.modelo}</p>
                            </div>
                            <div>
                                <p className="text-blue-100 text-sm">Datos de Entrenamiento</p>
                                <p className="font-bold text-lg">2020-2025</p>
                            </div>
                            <div>
                                <p className="text-blue-100 text-sm">Registros Históricos</p>
                                <p className="font-bold text-lg">9,760+</p>
                            </div>
                            <div>
                                <p className="text-blue-100 text-sm">Precisión Estimada</p>
                                <p className="font-bold text-lg">{resumenModelo.confiabilidad}%</p>
                            </div>
                        </div>
                    </div>
                </div>
            )}

            {/* Tabla detallada con comparación */}
            {predicciones.length > 0 && (
                <div className="bg-white rounded-xl border shadow-lg overflow-hidden">
                    <div className="p-4 bg-gray-50 border-b flex justify-between items-center flex-wrap gap-3">
                        <h3 className="text-lg font-bold">Detalle de Predicciones vs Datos Reales</h3>
                        <div className="flex items-center gap-3">
                            {formData.modo_validacion && (
                                <span className="px-3 py-1 bg-green-100 text-green-700 rounded-full text-sm font-medium">
                                    ✓ Modo Validación Activo
                                </span>
                            )}
                            {/* Botón Guardar Predicción */}
                            <button
                                onClick={guardarPrediccion}
                                disabled={guardando}
                                className="px-4 py-2 bg-gradient-to-r from-blue-600 to-indigo-600 text-white font-medium rounded-lg hover:from-blue-700 hover:to-indigo-700 disabled:from-gray-400 disabled:to-gray-500 disabled:cursor-not-allowed flex items-center gap-2 shadow-md transition-all"
                            >
                                {guardando ? (
                                    <>
                                        <svg className="animate-spin h-4 w-4" viewBox="0 0 24 24">
                                            <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none"/>
                                            <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"/>
                                        </svg>
                                        Guardando...
                                    </>
                                ) : (
                                    <>💾 Guardar Predicción</>
                                )}
                            </button>
                        </div>
                    </div>

                    {/* Mensaje de guardado */}
                    {mensajeGuardado && (
                        <div className={`mx-4 mt-4 p-3 rounded-lg ${
                            mensajeGuardado.tipo === 'success'
                                ? 'bg-green-50 text-green-700 border border-green-200'
                                : 'bg-red-50 text-red-700 border border-red-200'
                        }`}>
                            {mensajeGuardado.texto}
                            {mensajeGuardado.tipo === 'success' && (
                                <span className="ml-2 text-sm">
                                    - Ve al <a href="/dashboard-predicciones" className="underline font-medium hover:text-green-800">Dashboard de Predicciones</a> para visualizar
                                </span>
                            )}
                        </div>
                    )}
                    <div className="overflow-x-auto">
                        <table className="w-full">
                            <thead className="bg-gray-100">
                                <tr>
                                    <th className="px-4 py-3 text-left text-sm font-semibold text-gray-600">Semana</th>
                                    <th className="px-4 py-3 text-left text-sm font-semibold text-gray-600">Fecha</th>
                                    <th className="px-4 py-3 text-center text-sm font-semibold text-gray-600">Prob. Riesgo</th>
                                    <th className="px-4 py-3 text-center text-sm font-semibold text-gray-600">Nivel</th>
                                    <th className="px-4 py-3 text-center text-sm font-semibold text-gray-600 bg-blue-50">
                                        Casos Estimados
                                    </th>
                                    <th className="px-4 py-3 text-center text-sm font-semibold text-gray-600 bg-green-50">
                                        Casos Reales
                                    </th>
                                    <th className="px-4 py-3 text-center text-sm font-semibold text-gray-600 bg-amber-50">
                                        Δ Diferencia
                                    </th>
                                    <th className="px-4 py-3 text-center text-sm font-semibold text-gray-600">Error %</th>
                                    <th className="px-4 py-3 text-center text-sm font-semibold text-gray-600">Tendencia</th>
                                </tr>
                            </thead>
                            <tbody className="divide-y divide-gray-200">
                                {predicciones.map((pred, idx) => {
                                    const riesgo = getNivelRiesgo(pred.riesgo_probabilidad);
                                    const casosEstimados = pred.prediccion?.casos_proxima_semana || pred.datos_utilizados?.casos_ultima_semana;
                                    const casosReales = pred.validacion?.casos_reales;
                                    const diferencia = casosReales !== undefined ? casosEstimados - casosReales : null;
                                    const errorPct = casosReales > 0 ? Math.abs((diferencia / casosReales) * 100) : null;

                                    return (
                                        <tr key={idx} className="hover:bg-gray-50">
                                            <td className="px-4 py-3 font-medium">{pred.semana}</td>
                                            <td className="px-4 py-3 text-gray-600">{pred.fecha}</td>
                                            <td className="px-4 py-3 text-center">
                                                <span className={`inline-flex items-center px-3 py-1 rounded-full text-sm font-bold text-white ${riesgo.color}`}>
                                                    {pred.riesgo_probabilidad}%
                                                </span>
                                            </td>
                                            <td className={`px-4 py-3 text-center font-semibold ${riesgo.textColor}`}>
                                                {riesgo.nivel}
                                            </td>
                                            <td className="px-4 py-3 text-center bg-blue-50">
                                                <span className="font-bold text-blue-700 text-lg">{casosEstimados}</span>
                                            </td>
                                            <td className="px-4 py-3 text-center bg-green-50">
                                                {casosReales !== undefined ? (
                                                    <span className="font-bold text-green-700 text-lg">{casosReales}</span>
                                                ) : (
                                                    <span className="text-gray-400 text-sm">Sin datos</span>
                                                )}
                                            </td>
                                            <td className="px-4 py-3 text-center bg-purple-50">
                                                {diferencia !== null ? (
                                                    <span className={`font-bold ${diferencia > 0 ? 'text-orange-600' : diferencia < 0 ? 'text-blue-600' : 'text-green-600'}`}>
                                                        {diferencia > 0 ? '+' : ''}{diferencia}
                                                    </span>
                                                ) : (
                                                    <span className="text-gray-400">-</span>
                                                )}
                                            </td>
                                            <td className="px-4 py-3 text-center">
                                                {errorPct !== null ? (
                                                    <span className={`px-2 py-1 rounded font-medium ${getErrorColor(errorPct)}`}>
                                                        {errorPct.toFixed(1)}%
                                                    </span>
                                                ) : (
                                                    <span className="text-gray-400">-</span>
                                                )}
                                            </td>
                                            <td className="px-4 py-3 text-center">
                                                {pred.tendencias?.casos === 'Creciente' ? (
                                                    <span className="inline-flex items-center gap-1 text-red-600 font-medium text-xs">
                                                        <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 17l9.2-9.2M17 17V7H7" />
                                                        </svg>
                                                        Sube
                                                    </span>
                                                ) : pred.tendencias?.casos === 'Decreciente' ? (
                                                    <span className="inline-flex items-center gap-1 text-green-600 font-medium text-xs">
                                                        <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17 7l-9.2 9.2M7 7v10h10" />
                                                        </svg>
                                                        Baja
                                                    </span>
                                                ) : (
                                                    <span className="inline-flex items-center gap-1 text-gray-500 font-medium text-xs">
                                                        <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 12h14" />
                                                        </svg>
                                                        Estable
                                                    </span>
                                                )}
                                            </td>
                                        </tr>
                                    );
                                })}
                            </tbody>
                        </table>
                    </div>

                    {/* Leyenda de la tabla */}
                    <div className="p-4 bg-gray-50 border-t">
                        <h4 className="font-bold text-gray-700 mb-3">Leyenda de Colores</h4>
                        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                            {/* Columnas de datos */}
                            <div className="flex items-center gap-2 text-sm">
                                <span className="w-4 h-4 bg-blue-200 rounded border border-blue-300"></span>
                                <span className="text-gray-700"><strong>Azul</strong> - Casos Estimados</span>
                            </div>
                            <div className="flex items-center gap-2 text-sm">
                                <span className="w-4 h-4 bg-green-200 rounded border border-green-300"></span>
                                <span className="text-gray-700"><strong>Verde</strong> - Casos Reales</span>
                            </div>
                            <div className="flex items-center gap-2 text-sm">
                                <span className="w-4 h-4 bg-purple-200 rounded border border-purple-300"></span>
                                <span className="text-gray-700"><strong>Morado</strong> - Diferencia</span>
                            </div>
                        </div>
                        {/* Tendencias */}
                        <div className="mt-4 pt-3 border-t border-gray-200">
                            <p className="text-xs font-semibold text-gray-600 uppercase mb-2">Indicadores de Tendencia</p>
                            <div className="flex flex-wrap gap-4 text-sm">
                                <div className="flex items-center gap-2">
                                    <span className="text-red-600 font-bold">↗ Sube</span>
                                    <span className="text-gray-500">- Creciente</span>
                                </div>
                                <div className="flex items-center gap-2">
                                    <span className="text-green-600 font-bold">↘ Baja</span>
                                    <span className="text-gray-500">- Decreciente</span>
                                </div>
                                <div className="flex items-center gap-2">
                                    <span className="text-gray-500 font-bold">→ Estable</span>
                                    <span className="text-gray-500">- Sin cambios</span>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
            )}

            {/* Métricas de confiabilidad */}
            {predicciones.length > 0 && (
                <div className="mt-8 bg-white p-6 rounded-xl border shadow-lg">
                    <h3 className="text-lg font-bold mb-4">Guía de Interpretación de Métricas</h3>
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                        <div className="space-y-4">
                            <h4 className="font-semibold text-gray-700">Métricas de Error:</h4>
                            <ul className="space-y-2 text-sm text-gray-600">
                                <li className="flex items-start gap-2">
                                    <span className="text-blue-500 font-bold">MAE</span>
                                    <span>Error Absoluto Medio - Promedio de diferencias en casos</span>
                                </li>
                                <li className="flex items-start gap-2">
                                    <span className="text-blue-500 font-bold">MAPE</span>
                                    <span>Error Porcentual Absoluto Medio - % de error promedio</span>
                                </li>
                                <li className="flex items-start gap-2">
                                    <span className="text-blue-500 font-bold">RMSE</span>
                                    <span>Raíz del Error Cuadrático Medio - Penaliza errores grandes</span>
                                </li>
                                <li className="flex items-start gap-2">
                                    <span className="text-blue-500 font-bold">R²</span>
                                    <span>Coeficiente de Determinación - Qué tan bien el modelo explica la variabilidad</span>
                                </li>
                            </ul>
                        </div>
                        <div className="space-y-4">
                            <h4 className="font-semibold text-gray-700">Cómo usar esta información:</h4>
                            <ul className="space-y-2 text-sm text-gray-600">
                                <li className="flex items-center gap-2">
                                    <span className="text-green-500">✓</span>
                                    Usa fechas históricas (ej. 2024) para validar el modelo
                                </li>
                                <li className="flex items-center gap-2">
                                    <span className="text-green-500">✓</span>
                                    Compara predicciones con datos reales de la BD
                                </li>
                                <li className="flex items-center gap-2">
                                    <span className="text-green-500">✓</span>
                                    Un MAPE menor a 20% indica buena precisión
                                </li>
                                <li className="flex items-center gap-2">
                                    <span className="text-green-500">✓</span>
                                    R² mayor a 70% indica buen ajuste del modelo
                                </li>
                                <li className="flex items-center gap-2">
                                    <span className="text-yellow-500">⚠</span>
                                    Predicciones a futuro no tienen datos reales para comparar
                                </li>
                            </ul>
                        </div>
                    </div>

                    {/* Escala de Error */}
                    <div className="mt-6 p-4 bg-transparent rounded-lg border border-gray-200">
                        <h4 className="font-semibold text-gray-700 mb-3">Escala de Error Porcentual:</h4>
                        <div className="relative">
                            <button type="button" onClick={() => scrollEscala(-1)} className="absolute left-2 top-1/2 -translate-y-1/2 z-10 p-1 bg-white/90 rounded-full shadow-sm border hover:bg-white">
                                <svg className="w-5 h-5 text-gray-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
                                </svg>
                            </button>

                            <div ref={escalaRef} className="flex gap-3 overflow-x-auto px-10 py-2 scroll-smooth">
                                <div className="flex-none min-w-[220px] flex items-center gap-2 p-2 bg-green-100 rounded-lg border border-green-300">
                                    <span className="w-3 h-3 bg-green-500 rounded-full"></span>
                                    <span className="text-sm text-green-800 font-medium">Menor o igual a 10% - Excelente</span>
                                </div>
                                <div className="flex-none min-w-[220px] flex items-center gap-2 p-2 bg-yellow-100 rounded-lg border border-yellow-300">
                                    <span className="w-3 h-3 bg-yellow-500 rounded-full"></span>
                                    <span className="text-sm text-yellow-800 font-medium">Menor o igual a 25% - Bueno</span>
                                </div>
                                <div className="flex-none min-w-[220px] flex items-center gap-2 p-2 bg-orange-100 rounded-lg border border-orange-300">
                                    <span className="w-3 h-3 bg-orange-500 rounded-full"></span>
                                    <span className="text-sm text-orange-800 font-medium">Menor o igual a 50% - Aceptable</span>
                                </div>
                                <div className="flex-none min-w-[220px] flex items-center gap-2 p-2 bg-red-100 rounded-lg border border-red-300">
                                    <span className="w-3 h-3 bg-red-500 rounded-full"></span>
                                    <span className="text-sm text-red-800 font-medium">Mayor a 50% - Revisar</span>
                                </div>
                            </div>

                            <button type="button" onClick={() => scrollEscala(1)} className="absolute right-2 top-1/2 -translate-y-1/2 z-10 p-1 bg-white/90 rounded-full shadow-sm border hover:bg-white">
                                <svg className="w-5 h-5 text-gray-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
                                </svg>
                            </button>
                        </div>
                    </div>

                    {/* Escala de confiabilidad */}
                    <div className="mt-6 p-4 bg-gray-50 rounded-lg">
                        <h4 className="font-semibold text-gray-700 mb-3">Escala de Confiabilidad por Horizonte de Predicción:</h4>
                        <div className="flex items-center gap-2">
                            <div className="flex-1 h-4 bg-gradient-to-r from-green-500 via-yellow-500 to-red-500 rounded-full"></div>
                        </div>
                        <div className="flex justify-between text-xs text-gray-500 mt-1">
                            <span>1 semana (Alta: ~90%)</span>
                            <span>4 semanas (~75%)</span>
                            <span>8 semanas (~60%)</span>
                            <span>12 semanas (Menor: ~50%)</span>
                        </div>
                    </div>
                </div>
            )}
        </div>
    );
};

export default PrediccionAvanzada;
