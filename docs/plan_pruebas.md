# Plan Integral de Pruebas

Este documento consolida los entregables para los numerales solicitados: 4.1, 4.2, 2.3, 2.4, 4.5, 4.6 y 4.7.

## 4.1 Pruebas unitarias
- **Cobertura**: Componentes críticos (`Dashboard`, `Alertas`, `Login`) y servicios (`api.js`).
- **Archivos**: `src/__tests__/unit/components/*.test.js`, `src/__tests__/unit/services/api.test.js`.
- **Herramienta**: Jest + React Testing Library.
- **Ejecución**: `npm test -- --runTestsByPath src/__tests__/unit/components/Dashboard.test.js` (o `npm test`).
- **Criterios de aceptación**:
  - Hooks y servicios invocados con los datos esperados.
  - Validaciones de negocio para métricas epidemiológicas y formularios.

## 4.2 Pruebas de integración
- **Cobertura**: Flujo completo del módulo `Alertas` (generar → enviar → resolver → exportar).
- **Archivo**: `src/__tests__/integration/AlertasFlow.integration.test.js`.
- **Alcance**:
  - Orquestación de llamadas `fetch` a los endpoints Flask.
  - Navegación entre pestañas y manejo de estados.
  - Exportación de CSV.

## 2.3 Pruebas de usabilidad
- **Documento**: `tests/usability/usability_test_plan.md`.
- **Metodología**:
  - Sesiones moderadas con personal de salud (5 usuarios mínimo).
  - Escenarios: carga de dashboard, generación de alerta, carga de CSV y descarga de reporte.
  - Métricas: tiempo para completar, tasa de errores, SUS (System Usability Scale).
- **Herramientas sugeridas**: Lookback, Hotjar, cuestionarios SUS.

## 2.4 Pruebas de rendimiento
- **Scripts**: `tests/performance/alertas-load-test.js` (k6).
- **Objetivo**: Sustentar 200 req/min al endpoint `/api/alertas/generar-automaticas` y `/api/alertas/enviar-masivo` con latencia < 800 ms P95.
- **Ejecución**: `k6 run tests/performance/alertas-load-test.js`.
- **Monitoreo**: Prometheus + Grafana o New Relic para backend Flask/Node.

## 4.5 Pruebas de seguridad
- **Documento**: `tests/security/security_plan.md`.
- **Cobertura**:
  - Escaneo OWASP ZAP (archivo `zap-baseline.conf`).
  - Dependabot/Snyk para vulnerabilidades de dependencias.
  - Checklist OWASP ASVS nivel 2 (autenticación, gestión de sesiones, cifrado de datos sensibles).

## 4.6 Validación de modelos predictivos
- **Script**: `tests/model_validation/validate_models.py`.
- **Contenido**:
  - Carga de datos de `modelo/datos_dengue.csv`.
  - Reproducción de métricas (Accuracy, Recall, Precision, ROC-AUC para clasificador; RMSE/R² para regresor).
  - Detección de deriva (`Population Stability Index`).
- **Ejecución**: `python tests/model_validation/validate_models.py --dataset modelo/datos_dengue.csv`.

## 4.7 Pruebas de compatibilidad
- **Documento**: `tests/compatibility/compatibility_matrix.md`.
- **Cobertura**:
  - Navegadores: Chrome, Edge, Firefox, Safari (últimas 2 versiones).
  - Dispositivos: Desktop 1440px, Laptop 1280px, Tablet 1024px, Mobile 390px.
  - Sistemas operativos: Windows 11, macOS Sonoma, Ubuntu 24.04.
- **Herramientas**: BrowserStack, Cypress + `cypress.config.cross.json` (pendiente), Lighthouse CI para auditorías móviles.
