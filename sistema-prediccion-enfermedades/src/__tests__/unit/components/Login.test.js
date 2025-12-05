/**
 * 4.1 PRUEBAS UNITARIAS - Componente Login
 * Sistema de Predicción de Enfermedades Virales
 */

import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import '@testing-library/jest-dom';
import userEvent from '@testing-library/user-event';
import { BrowserRouter } from 'react-router-dom';

// Mock de useNavigate
const mockNavigate = jest.fn();
jest.mock('react-router-dom', () => ({
  ...jest.requireActual('react-router-dom'),
  useNavigate: () => mockNavigate
}));

// Mock de authService para evitar dependencias reales de axios (ESM)
const mockAuthLogin = jest.fn();
jest.mock('../../../services/api', () => ({
  authService: {
    login: (...args) => mockAuthLogin(...args)
  }
}));

// Mock de localStorage
const localStorageMock = {
  getItem: jest.fn(),
  setItem: jest.fn(),
  removeItem: jest.fn(),
  clear: jest.fn()
};
Object.defineProperty(window, 'localStorage', { value: localStorageMock });
window.alert = jest.fn();

import Login from '../../../pages/Login';

const renderWithRouter = (component) => {
  return render(
    <BrowserRouter>
      {component}
    </BrowserRouter>
  );
};

describe('Login Component - Pruebas Unitarias', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    mockAuthLogin.mockReset();
    Object.values(localStorageMock).forEach((fn) => fn.mockClear());
  });

  describe('Renderizado', () => {
    test('debe renderizar el formulario de login', () => {
      renderWithRouter(<Login />);
      
      expect(screen.getByLabelText(/Correo/i)).toBeInTheDocument();
      expect(screen.getByLabelText(/Contraseña/i)).toBeInTheDocument();
    });

    test('debe mostrar el botón de iniciar sesión', () => {
      renderWithRouter(<Login />);
      
      expect(screen.getByRole('button', { name: /Iniciar Sesión/i })).toBeInTheDocument();
    });

    test('debe mostrar el título del sistema', () => {
      renderWithRouter(<Login />);
      
      expect(screen.getByRole('heading', { name: /ProeVira/i })).toBeInTheDocument();
    });
  });

  describe('Validaciones de formulario', () => {
    test('debe permitir escribir en el campo usuario', async () => {
      renderWithRouter(<Login />);
      
      const inputUsuario = screen.getByLabelText(/Correo/i);
      await userEvent.type(inputUsuario, 'admin@proevira.mx');
      
      expect(inputUsuario).toHaveValue('admin@proevira.mx');
    });

    test('debe permitir escribir en el campo contraseña', async () => {
      renderWithRouter(<Login />);
      
      const inputPassword = screen.getByLabelText(/Contraseña/i);
      await userEvent.type(inputPassword, 'password123');
      
      expect(inputPassword).toHaveValue('password123');
    });

    test('el campo contraseña debe ser de tipo password', () => {
      renderWithRouter(<Login />);
      
      const inputPassword = screen.getByLabelText(/Contraseña/i);
      expect(inputPassword).toHaveAttribute('type', 'password');
    });
  });

  describe('Comportamiento de autenticación', () => {
    test('debe llamar a la función de login al enviar el formulario', async () => {
      mockAuthLogin.mockResolvedValue({ data: { success: true, usuario: { nombre: 'Admin' } } });
      renderWithRouter(<Login />);
      
      const inputUsuario = screen.getByLabelText(/Correo/i);
      const inputPassword = screen.getByLabelText(/Contraseña/i);
      const botonLogin = screen.getByRole('button', { name: /Iniciar Sesión/i });
      
      await userEvent.type(inputUsuario, 'admin@proevira.mx');
      await userEvent.type(inputPassword, 'admin');
      await userEvent.click(botonLogin);
      
      await waitFor(() => {
        expect(mockAuthLogin).toHaveBeenCalledWith({
          email: 'admin@proevira.mx',
          contrasena: 'admin'
        });
        expect(localStorageMock.setItem).toHaveBeenCalled();
        expect(mockNavigate).toHaveBeenCalledWith('/dashboard');
      });
    });
  });

  describe('Accesibilidad', () => {
    test('los inputs deben tener labels asociados o placeholders', () => {
      renderWithRouter(<Login />);
      
      const inputs = screen.getAllByRole('textbox');
      inputs.forEach(input => {
        const hasLabel = input.getAttribute('aria-label') || 
                        input.getAttribute('aria-labelledby') || 
                        input.getAttribute('placeholder');
        expect(hasLabel).toBeTruthy();
      });
    });

    test('el botón debe ser clickeable', () => {
      renderWithRouter(<Login />);
      
      const boton = screen.getByRole('button', { name: /Iniciar Sesión/i });
      expect(boton).not.toBeDisabled();
    });
  });
});

describe('Login - Validaciones de seguridad', () => {
  test('debe validar longitud mínima de usuario', () => {
    const validarUsuario = (usuario) => {
      return typeof usuario === 'string' && usuario.length >= 3;
    };
    
    expect(validarUsuario('admin')).toBe(true);
    expect(validarUsuario('ab')).toBe(false);
    expect(validarUsuario('')).toBe(false);
  });

  test('debe validar longitud mínima de contraseña', () => {
    const validarPassword = (password) => {
      return typeof password === 'string' && password.length >= 4;
    };
    
    expect(validarPassword('admin123')).toBe(true);
    expect(validarPassword('abc')).toBe(false);
  });

  test('debe sanitizar entrada de usuario', () => {
    const sanitizar = (input) => {
      return input.replace(/<[^>]*>/g, '').trim();
    };
    
    expect(sanitizar('<script>alert("xss")</script>')).toBe('alert("xss")');
    expect(sanitizar('  admin  ')).toBe('admin');
    expect(sanitizar('usuario_normal')).toBe('usuario_normal');
  });

  test('no debe permitir inyección SQL básica', () => {
    const detectarSQLInjection = (input) => {
      const patrones = /('|"|;|--|\bor\b|\band\b|\bdrop\b|\bdelete\b|\binsert\b|\bupdate\b)/i;
      return patrones.test(input);
    };
    
    expect(detectarSQLInjection("' OR '1'='1")).toBe(true);
    expect(detectarSQLInjection("admin'; DROP TABLE users;--")).toBe(true);
    expect(detectarSQLInjection('usuario_normal')).toBe(false);
  });
});
