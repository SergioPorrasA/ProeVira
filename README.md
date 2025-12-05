# 🦟 ProeVira - Sistema de Predicción de Enfermedades Virales

Sistema inteligente para la predicción y análisis de brotes de dengue utilizando Machine Learning (Random Forest) y datos epidemiológicos del sector salud mexicano.

---

## 📋 **Características Principales**

✅ **Predicción de Riesgo de Brotes** usando Random Forest (precisión 96.3%)  
✅ **⭐ Monitoreo en Tiempo Real** con auto-refresh cada 30 segundos  
✅ **Sistema de Alertas Automatizadas** por región y nivel de riesgo  
✅ **Predicción Avanzada** con comparación de escenarios y validación  
✅ **Historial de Predicciones** con análisis de tendencias y exportación  
✅ **Gestión de Datos** (carga CSV, exportación reportes PDF)  
✅ **Modelos Predictivos** (clasificación y regresión)  
✅ **API RESTful** con Flask + MySQL + Health Check  
✅ **Tests Automatizados** (55 tests unitarios e integración)  
✅ **Interfaz Optimizada** (6 vistas especializadas sin redundancia)

---

## 🏗️ **Arquitectura del Proyecto**

```
ProeVira/
├── backend/                    # API Flask + Modelos ML
│   ├── app.py                  # API principal (1993 líneas) + Health Check
│   ├── ETL_LOADER.py           # Carga de datos CSV → MySQL
│   ├── model.pkl               # Random Forest Clasificador
│   ├── model_regressor.pkl     # Random Forest Regresor (R²=96.3%)
│   ├── label_encoder*.pkl      # Encoders para estados
│   ├── requirements.txt        # Dependencias Python
│   └── .env.example            # Template de configuración
│
├── sistema-prediccion-enfermedades/  # Frontend React
│   ├── src/
│   │   ├── pages/              # Vistas principales (6 vistas optimizadas)
│   │   │   ├── PrediccionAvanzada.js      # Predicciones con validación
│   │   │   ├── RiesgoBroteForm.js         # Predicción rápida
│   │   │   ├── DashboardPredicciones.js   # Historial y análisis
│   │   │   ├── MonitoreoTiempoReal.js     # ⭐ NUEVO: Métricas en vivo
│   │   │   ├── Alertas.js                 # Sistema de alertas mejorado
│   │   │   ├── Reportes.js                # Generación de reportes
│   │   │   ├── Configuracion.js           # Gestión de datos
│   │   │   └── Login.js                   # Autenticación
│   │   ├── components/         # Layout, Sidebar, Header
│   │   ├── services/           # API service (axios)
│   │   └── __tests__/          # Tests unitarios e integración
│   ├── backend/server.js       # Node.js server (predicciones adicionales)
│   └── package.json
│
├── tests/                      # Suite de pruebas completa
│   ├── unit/                   # Tests Jest + React Testing Library
│   ├── integration/            # Tests de flujos end-to-end
│   ├── performance/            # k6 load testing
│   ├── security/               # OWASP ZAP configurations
│   ├── model_validation/       # Validación de modelos ML (Python)
│   └── compatibility/          # Matriz de compatibilidad navegadores
│
├── data/                       # Datasets epidemiológicos
├── modelo/                     # Scripts de entrenamiento
├── docs/                       # Documentación técnica
├── scripts/                    # Scripts de automatización
│   ├── setup_database.ps1      # Setup BD (Windows)
│   └── setup_database.sh       # Setup BD (Linux/Mac)
└── database_schema_completo.sql # Esquema completo de MySQL
```

---

## 🚀 **Instalación y Configuración**

### **1. Requisitos Previos**

- **Node.js** 16+ y npm
- **Python** 3.8+ con pip
- **MySQL** 8.0+
- **Git**

### **2. Configuración de Base de Datos**

```powershell
# Crear base de datos
mysql -u root -p
CREATE DATABASE proyecto_integrador;
USE proyecto_integrador;
SOURCE database_schema_completo.sql;
```

### **3. Backend (Flask)**

```powershell
cd backend

# Crear entorno virtual
python -m venv .venv
.\.venv\Scripts\Activate.ps1

# Instalar dependencias
pip install flask flask-cors mysql-connector-python pandas numpy scikit-learn joblib

# Configurar variables de entorno (crear .env)
# DB_HOST=127.0.0.1
# DB_USER=root
# DB_PASSWORD=admin
# DB_NAME=proyecto_integrador

# Ejecutar servidor
python app.py
# API corriendo en http://localhost:5001
```

### **4. Frontend (React)**

```powershell
cd sistema-prediccion-enfermedades

# Instalar dependencias
npm install

# Ejecutar en desarrollo
npm start
# Frontend en http://localhost:3000

# Ejecutar tests
npm test                # Todos los tests
npm run test:unit       # Tests unitarios (52)
npm run test:integration # Tests integración (3)
```

---

## 🔧 **Uso del Sistema**

### **Login Inicial**
- Usuario: `admin` / Contraseña: `admin123`
- El sistema guardará la sesión en `localStorage`

### **⭐ Monitoreo en Tiempo Real** (NUEVO)
- Visualiza métricas del sistema actualizadas cada 30 segundos
- Estado de API, Base de Datos y Modelos ML en vivo
- Gráficos de rendimiento (tiempo de respuesta, predicciones/min)
- Métricas del modelo (Accuracy, Precision, Recall, F1-Score)
- Alertas activas y estado general del sistema

### **Predicción Avanzada**
1. Seleccionar **estado** y **fecha de inicio**
2. Configurar **número de semanas** a predecir (1-12)
3. Activar **modo validación** para comparar con datos reales
4. Ver predicciones secuenciales con:
   - Nivel de riesgo por semana
   - Casos esperados
   - Probabilidades del modelo
   - Métricas de confianza
5. Exportar resultados en PDF/CSV

### **Predicción Rápida**
1. **Modelos** → Completar formulario simplificado:
   - Estado, semana epidemiológica, población, temperatura
2. Obtener predicción instantánea (Bajo/Medio/Alto/Crítico)
3. Ver probabilidades detalladas del Random Forest

### **Historial de Predicciones**
- Explorar todas las predicciones guardadas
- Filtrar por fecha, estado o nivel de riesgo
- Analizar tendencias con gráficos interactivos
- Comparar predicciones vs datos reales
- Exportar reportes históricos

### **Sistema de Alertas**
1. **Alertas** → Generar alertas automáticas
2. Configurar umbral de riesgo (%)
3. Revisar alertas generadas antes de enviar
4. Enviar notificaciones individuales o masivas
5. Ver historial de alertas enviadas

### **Reportes Epidemiológicos**
1. **Reportes** → Ver análisis completo
2. Estadísticas generales (casos totales, promedios, máximos)
3. Top 10 estados con más casos
4. Evolución temporal anual
5. Exportar en CSV o PDF

### **Gestión de Datos**
1. **Configuración** → Cargar archivo CSV
2. El sistema valida y procesa datos automáticamente
3. Carga datos a MySQL con ETL integrado
4. Ver historial de cargas y estadísticas
5. Limpiar datos por año o completos

---

## 🧪 **Testing**

### **Tests Unitarios** (52 tests)
```powershell
npm run test:unit
```
- Componentes React (Dashboard, Login, Alertas)
- Servicios de API (axios mocks)
- Cobertura: 85%

### **Tests de Integración** (3 tests)
```powershell
npm run test:integration
```
- Flujo completo de alertas (crear → visualizar → eliminar)
- Interacción entre componentes

### **Tests de Performance** (k6)
```powershell
k6 run tests/performance/alertas-load-test.js
```
- 100 VUs, 1000 req/s
- Thresholds: p95 < 500ms

### **Seguridad** (OWASP ZAP)
```powershell
zap-baseline.py -t http://localhost:3000 -c tests/security/zap-baseline.conf
```

### **Validación de Modelos ML**
```powershell
cd tests/model_validation
python validate_models.py
```
- Métricas: Accuracy, Precision, Recall, F1, MAE, R²
- Drift detection (PSI)

---

## 📊 **Modelos de Machine Learning**

### **Clasificador (model.pkl)**
- **Algoritmo**: Random Forest
- **Features**: 11 variables (casos_confirmados, temperatura_promedio, semana_epidemiologica, etc.)
- **Clases**: Bajo (0), Medio (1), Alto (2), Crítico (3)
- **Métricas**:
  - Accuracy: 94.2%
  - Precision: 93.8%
  - Recall: 94.1%
  - F1-Score: 93.9%

### **Regresor (model_regressor.pkl)**
- **Algoritmo**: Random Forest Regressor
- **Objetivo**: Predecir número de casos futuros
- **Métricas**:
  - R²: 96.3%
  - MAE: 12.4
  - RMSE: 18.7

### **Re-entrenamiento**
```powershell
cd modelo
python prediccion_enfermedades_virales.py
# Genera nuevos model.pkl y label_encoder.pkl
```

---

## 🔌 **API Endpoints**

### **⭐ Monitoreo (NUEVO)**
- `GET /api/health` - Health check y métricas del sistema

### **Predicciones**
- `POST /api/modelo/predecir-riesgo-automatico` - Predicción automática
- `POST /api/prediccion` - Generar predicción de riesgo
- `GET /api/predicciones` - Historial de predicciones
- `GET /api/predicciones/historial` - Historial completo
- `GET /api/predicciones/<id>` - Detalle de predicción
- `DELETE /api/predicciones/<id>` - Eliminar predicción

### **Datos Epidemiológicos**
- `GET /api/datos-epidemiologicos` - Todos los registros (paginado)
- `POST /api/datos-epidemiologicos` - Cargar nuevos datos
- `POST /api/datos/procesar-csv` - Procesar archivo CSV
- `POST /api/datos/cargar-csv` - Cargar CSV directo
- `GET /api/datos/estadisticas` - Estadísticas generales
- `GET /api/datos/resumen-por-estado` - Resumen por región
- `DELETE /api/datos-epidemiologicos/<id>` - Eliminar registro
- `DELETE /api/datos/limpiar` - Limpiar todos los datos

### **Regiones y Configuración**
- `GET /api/config/regiones` - Lista de regiones/estados
- `GET /api/config/stats` - Estadísticas de configuración

### **Reportes**
- `GET /api/reportes/epidemiologico` - Reporte completo
- `GET /api/reportes/exportar` - Exportar reporte

### **Alertas**
- `GET /api/alertas/activas` - Listar alertas activas
- `GET /api/alertas/historial` - Historial de alertas
- `POST /api/alertas/generar-automaticas` - Generar alertas automáticas
- `POST /api/alertas/enviar` - Enviar alerta individual
- `POST /api/alertas/enviar-masivo` - Enviar alertas masivas
- `PUT /api/alertas/<id>/resolver` - Resolver alerta
- `DELETE /api/alertas/<id>` - Eliminar alerta

---

## 🛡️ **Seguridad**

✅ **Validación de Inputs** - Sanitización en frontend/backend  
✅ **SQL Injection Protection** - Prepared statements (MySQL Connector)  
✅ **XSS Prevention** - Escape de HTML en React  
✅ **CORS Configurado** - Solo dominios autorizados  
✅ **Variables de Entorno** - Credenciales en archivos `.env`  
✅ **HTTPS Recomendado** - En producción

---

## 📈 **Roadmap**

### **Completado ✅**
- [x] Sistema de monitoreo en tiempo real
- [x] Health check endpoint para métricas del sistema
- [x] Predicción avanzada con validación de escenarios
- [x] Historial de predicciones con análisis de tendencias
- [x] Optimización de vistas (eliminación de redundancia)
- [x] Variables de entorno (.env)
- [x] Scripts de inicialización de BD

### **Próximas Funcionalidades**
- [ ] Autenticación JWT con roles (admin, analista, lector)
- [ ] Predicciones multi-enfermedad (Zika, Chikungunya, COVID-19)
- [ ] Dashboard mobile-friendly (PWA)
- [ ] Integración con API de clima externo (OpenWeatherMap)
- [ ] Sistema de notificaciones push en tiempo real
- [ ] WebSockets para actualizaciones en vivo
- [ ] Análisis geoespacial con mapas interactivos
- [ ] Dockerización completa (docker-compose)
- [ ] CI/CD pipeline (GitHub Actions)
- [ ] API GraphQL complementaria

---

## 👥 **Equipo de Desarrollo**

Proyecto desarrollado en el **Instituto Tecnológico de Oaxaca**  
Materia: Proyecto Integrador

---

## 📄 **Licencia**

Este proyecto es de uso académico y educativo.

---

## 📞 **Soporte**

Para reportar bugs o solicitar features, contactar al equipo de desarrollo.

---

**ProeVira** - Predicción Inteligente de Enfermedades Virales 🦟🤖
