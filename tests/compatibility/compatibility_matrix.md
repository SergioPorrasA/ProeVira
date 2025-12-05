# 4.7 Pruebas de Compatibilidad

| Plataforma | Navegador | Versión | Resolución | Escenarios prioritarios | Estado |
|------------|-----------|---------|------------|-------------------------|--------|
| Windows 11 | Chrome | Últimas 2 | 1920x1080 | Dashboard, Alertas, Configuración (CSV) | Pendiente |
| Windows 11 | Edge | Últimas 2 | 1366x768 | Login, Reportes | Pendiente |
| macOS Sonoma | Safari | Últimas 2 | 1440x900 | Dashboard, Alertas | Pendiente |
| Ubuntu 24.04 | Firefox | Últimas 2 | 1920x1080 | Dashboard, Modelos | Pendiente |
| iPadOS 17 | Safari | Última | 1024x768 | Alertas, Reportes | Pendiente |
| Android 14 | Chrome | Última | 412x915 | Dashboard, Alertas | Pendiente |
| iOS 18 | Safari | Última | 390x844 | Login, Alertas | Pendiente |

## Procedimiento
1. Ejecutar `npm run build` y desplegar en entorno staging con HTTPS.
2. Utilizar BrowserStack/CrossBrowserTesting para registrar evidencia (capturas, videos).
3. Validar:
   - Responsividad (Tailwind breakpoints `sm/md/lg`).
   - Interacción táctil (botones ≥ 44px).
   - Funcionalidad crítica (envío de alertas, descarga de CSV/PDF, carga de archivos).
4. Registrar hallazgos en issue tracker y repetir hasta obtener estado "Aprobado".
