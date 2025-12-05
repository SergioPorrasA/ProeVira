/**
 * 4.2 PRUEBAS DE INTEGRACIÓN - Flujo completo de Alertas
 */

import React from 'react';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import '@testing-library/jest-dom';
import { BrowserRouter } from 'react-router-dom';

import Alertas from '../../pages/Alertas';

const renderWithRouter = (component) => (
  render(
    <BrowserRouter>
      {component}
    </BrowserRouter>
  )
);

const createMockFetch = () => {
  return jest.fn((url, options = {}) => {
    if (url.includes('/config/regiones')) {
      return Promise.resolve({
        ok: true,
        json: () => Promise.resolve([
          { id_region: 14, nombre: 'Jalisco' },
          { id_region: 30, nombre: 'Veracruz' }
        ])
      });
    }
    if (url.includes('/alertas/activas')) {
      return Promise.resolve({
        ok: true,
        json: () => Promise.resolve({
          alertas: [
            {
              id: 1,
              estado: 'Veracruz',
              nivel: 'Alto',
              probabilidad: 72,
              mensaje: 'Riesgo elevado'
            }
          ]
        })
      });
    }
    if (url.includes('/alertas/historial')) {
      return Promise.resolve({
        ok: true,
        json: () => Promise.resolve({
          alertas: [
            {
              id: 9,
              estado: 'Oaxaca',
              nivel: 'Moderado',
              probabilidad: 45,
              fecha_generacion: '2025-11-01T12:00:00',
              estado_alerta: 'resuelta'
            }
          ]
        })
      });
    }
    if (url.includes('/alertas/generar-automaticas')) {
      return Promise.resolve({
        ok: true,
        json: () => Promise.resolve({
          success: true,
          alertas: [
            {
              id_region: 14,
              estado: 'Jalisco',
              nivel_riesgo: 'Crítico',
              probabilidad: 88,
              casos_esperados: 320,
              casos_semana_actual: 280,
              mensaje: 'Incremento acelerado',
              recomendaciones: 'Activar brigadas'
            }
          ]
        })
      });
    }
    if (url.includes('/alertas/enviar')) {
      return Promise.resolve({
        ok: true,
        json: () => Promise.resolve({ success: true, id: 101 })
      });
    }
    if (url.includes('/alertas/1/resolver')) {
      return Promise.resolve({
        ok: true,
        json: () => Promise.resolve({ success: true })
      });
    }
    return Promise.resolve({ ok: true, json: () => Promise.resolve({}) });
  });
};

beforeAll(() => {
  global.URL.createObjectURL = jest.fn(() => 'blob:mock');
});

describe('Flujo de Alertas - Pruebas de Integración', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    global.fetch = createMockFetch();
  });

  test('debe completar el flujo de generación y envío de una alerta', async () => {
    renderWithRouter(<Alertas />);

    await waitFor(() => {
      expect(screen.getByText(/Sistema de Alertas Epidemiológicas/i)).toBeInTheDocument();
    });

    userEvent.click(screen.getAllByText(/Analizar Riesgo/i)[0]);

    await waitFor(() => {
      expect(screen.getByText(/Jalisco/i)).toBeInTheDocument();
      expect(screen.getByText(/Crítico/i)).toBeInTheDocument();
    });

    const botonEnviar = screen.getAllByRole('button', { name: /enviar/i })[0];
    userEvent.click(botonEnviar);

    await waitFor(() => {
      expect(global.fetch).toHaveBeenCalledWith(
        expect.stringContaining('/alertas/enviar'),
        expect.objectContaining({ method: 'POST' })
      );
    });
  });

  test('debe resolver una alerta activa desde la pestaña Activas', async () => {
    renderWithRouter(<Alertas />);

    await waitFor(() => {
      expect(screen.getAllByText(/Activas/i)[0]).toBeInTheDocument();
    });

    userEvent.click(screen.getAllByText(/Activas/i)[1]);

    await waitFor(() => {
      expect(screen.getByText(/Veracruz/i)).toBeInTheDocument();
    });

    userEvent.click(screen.getByRole('button', { name: /resolver/i }));

    await waitFor(() => {
      expect(global.fetch).toHaveBeenCalledWith(
        expect.stringContaining('/alertas/1/resolver'),
        expect.objectContaining({ method: 'PUT' })
      );
    });
  });

  test('debe exportar CSV desde la pestaña Historial', async () => {
    const clickSpy = jest.spyOn(HTMLAnchorElement.prototype, 'click').mockImplementation(() => {});

    renderWithRouter(<Alertas />);

    await waitFor(() => {
      expect(screen.getByText(/Historial/i)).toBeInTheDocument();
    });

    userEvent.click(screen.getByText(/Historial/i));

    await waitFor(() => {
      expect(screen.getByText(/Historial de Alertas/)).toBeInTheDocument();
    });

    const botonExportar = screen.getAllByRole('button', { name: /Exportar CSV/i })[0];
    userEvent.click(botonExportar);

    expect(global.URL.createObjectURL).toHaveBeenCalled();
    expect(clickSpy).toHaveBeenCalled();

    clickSpy.mockRestore();
  });
});
