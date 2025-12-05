import React, { useState } from 'react';
import { authService } from '../services/api';
import { useNavigate, Link } from 'react-router-dom';

const Login = () => {
  const navigate = useNavigate();
  const [formData, setFormData] = useState({
    email: '',
    contrasena: ''
  });
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const handleChange = (e) => {
    setFormData({
      ...formData,
      [e.target.name]: e.target.value
    });
    setError('');
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    
    if (!formData.email || !formData.contrasena) {
      setError('Por favor completa todos los campos');
      return;
    }

    try {
      setLoading(true);
      setError('');

      console.log('Enviando login:', formData); // Debug

      const response = await authService.login(formData);

      console.log('Respuesta del servidor:', response.data); // Debug

      if (response.data.success) {
        // Guardar datos del usuario en localStorage
        localStorage.setItem('usuario', JSON.stringify(response.data.usuario));
        
        alert('¡Login exitoso!'); // Confirmación visual
        
        // Redirigir al dashboard
        navigate('/dashboard');
      } else {
        setError(response.data.error || 'Credenciales inválidas');
      }

      setLoading(false);
    } catch (err) {
      console.error('Error completo en login:', err);
      console.error('Respuesta del servidor:', err.response);
      
      setError(
        err.response?.data?.error || 
        err.response?.data?.detalle || 
        err.message || 
        'Error al iniciar sesión'
      );
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 to-purple-50 flex items-center justify-center p-4">
      <div className="w-full max-w-md">
        {/* Logo y Título */}
        <div className="text-center mb-8">
          <div className="inline-flex items-center justify-center w-20 h-20    rounded-2xl shadow-lg mb-4">
            <span className="material-symbols-outlined text-white text-3xl" > <img src="https://upload.wikimedia.org/wikipedia/commons/8/85/Instituto_Tecnologico_de_Oaxaca_-_original.svg"></img></span>
          </div>
          <h1 className="text-4xl font-black text-text-main mb-2">
            ProeVira
          </h1>
          <p className="text-text-secondary text-lg">
            Enfermedades Epidemiológicas
          </p>
        </div>

        {/* Formulario de Login */}
        <div className="bg-white rounded-2xl shadow-xl p-8 border border-[#dbe2e6]">
          <h2 className="text-2xl font-bold text-text-main mb-6">
            Iniciar Sesión
          </h2>

          {error && (
            <div className="mb-4 p-4 bg-red-50 border border-red-200 rounded-lg flex items-center gap-3">
              <span className="material-symbols-outlined text-red-600">error</span>
              <p className="text-red-800 text-sm">{error}</p>
            </div>
          )}

          <form onSubmit={handleSubmit} className="space-y-4">
            {/* Email */}
            <div>
              <label htmlFor="email" className="block text-sm font-semibold text-text-main mb-2">
                Correo Electrónico
              </label>
              <div className="relative">
                <span className="material-symbols-outlined absolute left-3 top-1/2 -translate-y-1/2 text-text-secondary">
                  mail
                </span>
                <input
                  id="email"
                  type="email"
                  name="email"
                  value={formData.email}
                  onChange={handleChange}
                  placeholder="usuario@ejemplo.com"
                  className="w-full pl-12 pr-4 py-3 border border-[#dbe2e6] rounded-lg focus:outline-none focus:ring-2 focus:ring-primary"
                  disabled={loading}
                />
              </div>
            </div>

            {/* Contraseña */}
            <div>
              <label htmlFor="contrasena" className="block text-sm font-semibold text-text-main mb-2">
                Contraseña
              </label>
              <div className="relative">
                <span className="material-symbols-outlined absolute left-3 top-1/2 -translate-y-1/2 text-text-secondary">
                  lock
                </span>
                <input
                  id="contrasena"
                  type="password"
                  name="contrasena"
                  value={formData.contrasena}
                  onChange={handleChange}
                  placeholder="••••••••"
                  className="w-full pl-12 pr-4 py-3 border border-[#dbe2e6] rounded-lg focus:outline-none focus:ring-2 focus:ring-primary"
                  disabled={loading}
                />
              </div>
            </div>

            {/* Recordar sesión */}
            <div className="flex items-center justify-between">
              <label className="flex items-center gap-2 cursor-pointer">
                <input
                  type="checkbox"
                  className="w-4 h-4 text-primary border-gray-300 rounded focus:ring-2 focus:ring-primary"
                />
                <span className="text-sm text-text-secondary">Recordar sesión</span>
              </label>
              <Link to="#" className="text-sm text-primary hover:underline font-semibold">
                ¿Olvidaste tu contraseña?
              </Link>
            </div>

            {/* Botón de Login */}
            <button
              type="submit"
              disabled={loading}
              className="w-full py-3 bg-primary text-white rounded-lg hover:bg-primary/90 font-bold text-lg shadow-lg disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2 transition-all">
              {loading ? (
                <>
                  <div className="animate-spin rounded-full h-5 w-5 border-b-2 border-white"></div>
                  Iniciando sesión...
                </>
              ) : (
                <>
                  <span className="material-symbols-outlined">login</span>
                  Iniciar Sesión
                </>
              )}
            </button>
          </form>

          {/* Información adicional */}
          <div className="mt-6 pt-6 border-t border-[#dbe2e6]">
            <p className="text-center text-sm text-text-secondary mb-4">
              ¿No tienes una cuenta?
            </p>
            <button className="w-full py-3 bg-white border-2 border-primary text-primary rounded-lg hover:bg-blue-50 font-semibold flex items-center justify-center gap-2 transition-all">
              <span className="material-symbols-outlined">person_add</span>
              Solicitar Acceso
            </button>
          </div>
        </div>

        {/* Footer */}
        <div className="mt-8 text-center">
          <p className="text-sm text-text-secondary">
            © 2025 Sistema de Predicción de Enfermedades
          </p>
          <p className="text-xs text-text-secondary mt-2">
            Gestion de Proyectos de Software - ITO Oaxaca
          </p>
        </div>
      </div>
    </div>
  );
};

export default Login;