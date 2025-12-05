# 4.5 Pruebas de Seguridad

## Objetivos
- Identificar vulnerabilidades OWASP Top 10 en los frontends React y APIs Node/Flask.
- Validar controles de autenticación/autorización.
- Asegurar cifrado y protección de datos sensibles (predicciones, CSV cargados).

## Alcance
1. **Aplicación web React** (localhost:3000)
2. **API Node.js** (localhost:5000)
3. **API Flask** (localhost:5001)
4. **Base de datos MySQL** (solo pruebas de credenciales/puertos expuestos)

## Herramientas
- `OWASP ZAP` (scan activo + baseline) – configuración en `tests/security/zap-baseline.conf`.
- `npm audit`, `pip-audit`, `safety`, `snyk test` para dependencias.
- `bandit` para scripts Python (`modelo/` y `tests/model_validation`).

## Plan
1. **Escaneo automático (CI/CD)**
   - Ejecutar `zap-baseline.py -t http://localhost:3000 -c tests/security/zap-baseline.conf`.
   - Reportar alertas ≥ Medium como fallas.
2. **Pruebas manuales**
   - Fuzzing de parámetros en `/api/alertas/*` y `/api/datos/procesar-csv`.
   - Verificar controles de origen (`CORS`, `CSRF`).
   - Revisión de almacenamiento seguro de tokens (`localStorage`).
3. **Validaciones de autenticación**
   - Intentos de fuerza bruta limitados.
   - Expiración de sesión y limpieza de `localStorage` en logout.
4. **Hardening**
   - TLS en despliegue (Let’s Encrypt) + headers (`Content-Security-Policy`, `X-Content-Type-Options`, etc.).

## Entregables
- Reportes OWASP ZAP almacenados en `reports/security/`.
- Registro de hallazgos y remediación en tablero (Jira/DevOps).