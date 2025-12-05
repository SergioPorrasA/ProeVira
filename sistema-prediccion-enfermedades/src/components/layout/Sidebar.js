import React, { useState, useEffect } from 'react';
import { Link, useLocation, useNavigate } from 'react-router-dom';

const Sidebar = () => {
  const location = useLocation();
  const navigate = useNavigate();
  const [usuario, setUsuario] = useState(null);

  useEffect(() => {
    const usuarioData = localStorage.getItem('usuario');
    if (usuarioData) {
      setUsuario(JSON.parse(usuarioData));
    }
  }, []);

  const cerrarSesion = () => {
    localStorage.removeItem('usuario');
    navigate('/login');
  };

  const menuItems = [
    { path: '/prediccion-avanzada', icon: 'query_stats', label: 'Predicción Avanzada' },
    { path: '/modelos', icon: 'psychology', label: 'Predicción Rápida' },
    { path: '/dashboard-predicciones', icon: 'monitoring', label: 'Historial Predicciones' },
    { path: '/monitoreo', icon: 'sensors', label: 'Monitoreo Tiempo Real' },
    { path: '/entrenar-modelos', icon: 'model_training', label: 'Entrenar Modelos' },
    { path: '/alertas', icon: 'notifications_active', label: 'Alertas' },
    { path: '/reportes', icon: 'description', label: 'Reportes' },
    { path: '/configuracion', icon: 'settings', label: 'Configuración' }
  ];

  return (
    <aside className="w-72 bg-white border-r border-[#dbe2e6] flex flex-col">
      {/* Header */}
      <div className="p-6 border-b border-[#dbe2e6]">
        <div className="flex items-center gap-3 mb-2">
          <div className="w-12 h-12 bg-primary rounded-xl flex items-center justify-center shadow-lg">
            <span className="material-symbols-outlined text-white text-3xl"> <img src="https://upload.wikimedia.org/wikipedia/commons/8/85/Instituto_Tecnologico_de_Oaxaca_-_original.svg"></img></span>
          </div>
          <div>
            <h1 className="text-text-main text-xl font-black leading-tight">ProeVira</h1>
            <p className="text-text-secondary text-xs">Sistema de Predicción</p>
          </div>
        </div>
      </div>

      {/* User Info */}
      {usuario && (
        <div className="p-4 border-b border-[#dbe2e6] bg-gradient-to-r from-blue-50 to-purple-50">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 bg-primary rounded-full flex items-center justify-center">
              <span className="material-symbols-outlined text-white">person</span>
            </div>
            <div className="flex-1 min-w-0">
              <p className="text-sm font-bold text-text-main truncate">{usuario.nombre}</p>
              <p className="text-xs text-text-secondary truncate">{usuario.rol}</p>
            </div>
          </div>
        </div>
      )}

      {/* Navigation */}
      <nav className="flex-1 p-4 overflow-y-auto">
        <div className="space-y-1">
          {menuItems.map((item) => {
            const isActive = location.pathname === item.path;
            return (
              <Link
                key={item.path}
                to={item.path}
                className={`flex items-center gap-3 px-4 py-3 rounded-xl transition-all duration-200 ${
                  isActive
                    ? 'bg-primary text-white shadow-lg shadow-primary/30'
                    : 'text-text-main hover:bg-gray-100'
                }`}>
                <span className="material-symbols-outlined text-2xl">
                  {item.icon}
                </span>
                <span className="font-semibold">{item.label}</span>
              </Link>
            );
          })}
        </div>
      </nav>

      {/* Footer con botón de cerrar sesión */}
      <div className="p-4 border-t border-[#dbe2e6]">
        <button
          onClick={cerrarSesion}
          className="w-full flex items-center gap-3 px-4 py-3 rounded-xl text-red-600 hover:bg-red-50 transition-all duration-200 font-semibold">
          <span className="material-symbols-outlined text-2xl">logout</span>
          <span>Cerrar Sesión</span>
        </button>
        <div className="mt-3 text-center">
          <p className="text-xs text-text-secondary">Versión 1.0.0</p>
        </div>
      </div>
    </aside>
  );
};

export default Sidebar;