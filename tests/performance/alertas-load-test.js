import http from 'k6/http';
import { check, sleep } from 'k6';

/**
 * 2.4 Pruebas de rendimiento
 * Escenario de carga para endpoints críticos del sistema de alertas.
 */

export const options = {
  vus: 50,
  duration: '2m',
  thresholds: {
    http_req_duration: ['p(95)<800', 'avg<500'],
    http_req_failed: ['rate<0.01']
  },
  stages: [
    { duration: '30s', target: 20 },
    { duration: '1m', target: 50 },
    { duration: '30s', target: 0 }
  ]
};

const BASE_URL = 'http://localhost:5001/api/alertas';

export default function () {
  // 1. Generación automática de alertas
  const generar = http.post(`${BASE_URL}/generar-automaticas`, JSON.stringify({ umbral_riesgo: 30 }), {
    headers: { 'Content-Type': 'application/json' }
  });

  check(generar, {
    'genera alertas 200': (r) => r.status === 200,
    'respuesta < 800ms': (r) => r.timings.duration < 800
  });

  // 2. Envío masivo con las alertas recibidas
  if (generar.status === 200) {
    const payload = generar.json()?.alertas?.map((alerta) => ({
      ...alerta,
      tipo_notificacion: 'sistema',
      prioridad: 'alta'
    })) || [];

    const enviar = http.post(`${BASE_URL}/enviar-masivo`, JSON.stringify({ alertas: payload }), {
      headers: { 'Content-Type': 'application/json' }
    });

    check(enviar, {
      'envía alertas 200': (r) => r.status === 200,
      'envío < 900ms': (r) => r.timings.duration < 900
    });
  }

  sleep(1);
}
