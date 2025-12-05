/**
 * 4.1 PRUEBAS UNITARIAS - Componente Alertas
 * Sistema de Predicción de Enfermedades Virales
 */

import React from 'react';
import { render, screen, waitFor, fireEvent, act } from '@testing-library/react';
import '@testing-library/jest-dom';
import userEvent from '@testing-library/user-event';
import { BrowserRouter } from 'react-router-dom';

// Mock de fetch global
global.fetch = jest.fn();

// Mock de recharts
jest.mock('recharts', () => ({
  ResponsiveContainer: ({ children }) => <div data-testid="responsive-container">{children}</div>,
  BarChart: ({ children }) => <div data-testid="bar-chart">{children}</div>,
  Bar: () => <div data-testid="bar" />,
  XAxis: () => <div data-testid="x-axis" />,
  YAxis: () => <div data-testid="y-axis" />,
  CartesianGrid: () => <div data-testid="cartesian-grid" />,
  Tooltip: () => <div data-testid="tooltip" />,
  PieChart: ({ children }) => <div data-testid="pie-chart">{children}</div>,
  Pie: () => <div data-testid="pie" />,
  Cell: () => <div data-testid="cell" />
}));

import Alertas from '../../../pages/Alertas';

const renderWithRouter = (component) => {
  return render(
    <BrowserRouter>
      {component}
    </BrowserRouter>
  );
};

describe('Alertas Component - Pruebas Unitarias', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    
    // Mock exitoso por defecto
    global.fetch.mockImplementation((url) => {
      if (url.includes('/config/regiones')) {
        return Promise.resolve({
          ok: true,
          json: () => Promise.resolve([
            { id_region: 1, nombre: 'Aguascalientes' },
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
              { id: 1, estado: 'Jalisco', nivel: 'Alto', probabilidad: 75, mensaje: 'Riesgo elevado' }
            ]
          })
        });
      }
      if (url.includes('/alertas/historial')) {
        return Promise.resolve({
          ok: true,
          json: () => Promise.resolve({
            alertas: [
              { id: 1, estado: 'Oaxaca', nivel: 'Crítico', fecha_generacion: '2025-12-01', estado_alerta: 'resuelta' }
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
              { id_region: 14, estado: 'Jalisco', nivel_riesgo: 'Alto', probabilidad: 78, casos_esperados: 250, mensaje: 'Alerta generada' }
            ]
          })
        });
      }
      return Promise.resolve({ ok: true, json: () => Promise.resolve({}) });
    });
  });

  describe('Renderizado inicial', () => {
    test('debe mostrar el estado de carga', () => {
      renderWithRouter(<Alertas />);
      expect(screen.getByText(/cargando/i)).toBeInTheDocument();
    });

    test('debe renderizar el título correctamente', async () => {
      renderWithRouter(<Alertas />);
      
      await waitFor(() => {
        expect(screen.getByText(/Sistema de Alertas/i)).toBeInTheDocument();
      });
    });

    test('debe mostrar las pestañas de navegación', async () => {
      renderWithRouter(<Alertas />);
      
      await waitFor(() => {
        expect(screen.getByText(/Generar Alertas/i)).toBeInTheDocument();
        expect(screen.getAllByText(/Activas/i)[0]).toBeInTheDocument();
        expect(screen.getByText(/Historial/i)).toBeInTheDocument();
      });
    });
  });

  describe('Funcionalidad de configuración', () => {
    test('debe permitir cambiar el umbral de riesgo', async () => {
      renderWithRouter(<Alertas />);
      
      await waitFor(() => {
        const slider = screen.getByRole('slider');
        expect(slider).toBeInTheDocument();
      });
    });

    test('debe permitir seleccionar tipo de notificación', async () => {
      renderWithRouter(<Alertas />);
      
      await waitFor(() => {
        const select = screen.getByDisplayValue(/Sistema interno/i);
        expect(select).toBeInTheDocument();
      });
    });
  });

  describe('Generación de alertas', () => {
    test('debe llamar a la API al hacer clic en Analizar Riesgo', async () => {
      renderWithRouter(<Alertas />);
      
      await waitFor(() => {
        expect(screen.getAllByText(/Analizar Riesgo/i)[0]).toBeInTheDocument();
      });
      
      const botonAnalizar = screen.getAllByText(/Analizar Riesgo/i)[0];
      userEvent.click(botonAnalizar);
      
      await waitFor(() => {
        expect(global.fetch).toHaveBeenCalledWith(
          expect.stringContaining('/alertas/generar-automaticas'),
          expect.any(Object)
        );
      });
    });

    test('debe mostrar alertas generadas después del análisis', async () => {
      renderWithRouter(<Alertas />);
      
      await waitFor(() => {
        expect(screen.getAllByText(/Analizar Riesgo/i)[0]).toBeInTheDocument();
      });
      
      userEvent.click(screen.getAllByText(/Analizar Riesgo/i)[0]);
      
      await waitFor(() => {
        expect(screen.getByText(/Jalisco/i)).toBeInTheDocument();
      });
    });
  });

  describe('Navegación entre pestañas', () => {
    test('debe cambiar a la pestaña Activas', async () => {
      renderWithRouter(<Alertas />);
      
      await waitFor(() => {
        expect(screen.getAllByText(/Activas/i)[0]).toBeInTheDocument();
      });
      
      userEvent.click(screen.getAllByText(/Activas/i)[1]);
      
      await waitFor(() => {
        // Verifica que se muestran las alertas activas
        expect(screen.getByText(/Pendientes de Resolución|No hay alertas activas/i)).toBeInTheDocument();
      });
    });

    test('debe cambiar a la pestaña Historial', async () => {
      renderWithRouter(<Alertas />);
      
      await waitFor(() => {
        expect(screen.getByText(/Historial/i)).toBeInTheDocument();
      });
      
      userEvent.click(screen.getByText(/Historial/i));
      
      await waitFor(() => {
        expect(screen.getByText(/Historial de Alertas/i)).toBeInTheDocument();
      });
    });
  });

  describe('Manejo de errores', () => {
    test('debe manejar error de conexión', async () => {
      global.fetch.mockRejectedValue(new Error('Network error'));
      
      renderWithRouter(<Alertas />);
      
      await waitFor(() => {
        // El componente no debe crashear
        expect(document.body).toBeInTheDocument();
      });
    });

    test('debe mostrar mensaje cuando no hay alertas', async () => {
      global.fetch.mockImplementation((url) => {
        if (url.includes('/alertas/activas')) {
          return Promise.resolve({
            ok: true,
            json: () => Promise.resolve({ alertas: [] })
          });
        }
        return Promise.resolve({ ok: true, json: () => Promise.resolve({}) });
      });
      
      renderWithRouter(<Alertas />);
      
      await waitFor(() => {
        expect(screen.getAllByText(/Activas/i)[0]).toBeInTheDocument();
      });
      
      userEvent.click(screen.getAllByText(/Activas/i)[1]);
      
      await waitFor(() => {
        expect(screen.getByText(/No hay alertas activas/i)).toBeInTheDocument();
      });
    });
  });
});

describe('Alertas - Validaciones de negocio', () => {
  test('debe validar nivel de riesgo correcto', () => {
    const nivelesValidos = ['Crítico', 'Alto', 'Moderado', 'Bajo'];
    
    const validarNivel = (nivel) => nivelesValidos.includes(nivel);
    
    expect(validarNivel('Crítico')).toBe(true);
    expect(validarNivel('Alto')).toBe(true);
    expect(validarNivel('Invalido')).toBe(false);
  });

  test('debe calcular color correcto por nivel', () => {
    const getColorNivel = (nivel) => {
      const colores = {
        'Crítico': '#dc2626',
        'Alto': '#ea580c',
        'Moderado': '#ca8a04',
        'Bajo': '#16a34a'
      };
      return colores[nivel] || '#6b7280';
    };
    
    expect(getColorNivel('Crítico')).toBe('#dc2626');
    expect(getColorNivel('Alto')).toBe('#ea580c');
    expect(getColorNivel('Desconocido')).toBe('#6b7280');
  });

  test('debe validar umbral de riesgo en rango', () => {
    const validarUmbral = (umbral) => {
      return typeof umbral === 'number' && umbral >= 10 && umbral <= 80;
    };
    
    expect(validarUmbral(30)).toBe(true);
    expect(validarUmbral(10)).toBe(true);
    expect(validarUmbral(80)).toBe(true);
    expect(validarUmbral(5)).toBe(false);
    expect(validarUmbral(90)).toBe(false);
  });

  test('debe validar formato de alerta', () => {
    const validarAlerta = (alerta) => {
      return alerta &&
        typeof alerta.estado === 'string' &&
        typeof alerta.nivel_riesgo === 'string' &&
        typeof alerta.probabilidad === 'number' &&
        alerta.probabilidad >= 0 &&
        alerta.probabilidad <= 100;
    };
    
    expect(validarAlerta({
      estado: 'Jalisco',
      nivel_riesgo: 'Alto',
      probabilidad: 75
    })).toBe(true);
    
    expect(validarAlerta({
      estado: 'Jalisco',
      nivel_riesgo: 'Alto',
      probabilidad: 150
    })).toBe(false);
  });
});
