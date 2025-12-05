import React from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import './styles/globals.css';

// Layout
import Layout from './components/layout/Layout';
import Sidebar from './components/layout/Sidebar';

// Pages
import Login from './pages/Login';
import ModelosPredictivos from './pages/ModelosPredictivos';
import Reportes from './pages/Reportes';
import Configuracion from './pages/Configuracion';
import Alertas from './pages/Alertas';
import RiesgoBroteForm from './pages/RiesgoBroteForm';
import PrediccionAvanzada from './pages/PrediccionAvanzada';
import DashboardPredicciones from './pages/DashboardPredicciones';
import MonitoreoTiempoReal from './pages/MonitoreoTiempoReal';
import EntrenamientoModelos from './pages/EntrenamientoModelos';

// Componente para rutas protegidas
const ProtectedRoute = ({ children }) => {
  const usuario = localStorage.getItem('usuario');
  
  if (!usuario) {
    return <Navigate to="/login" replace />;
  }
  
  return children;
};

function App() {
  return (
    <Router>
      <div className="relative flex min-h-screen w-full flex-col bg-background-light font-display">
        <Routes>
          {/* Ruta de Login */}
          <Route path="/login" element={<Login />} />

          {/* Rutas protegidas */}
          <Route
            path="/*"
            element={
              <ProtectedRoute>
                <div className="flex h-screen bg-[#f8f9fb]">
                  <Sidebar />
                  <Routes>
                    <Route path="/" element={<Navigate to="/prediccion-avanzada" replace />} />
                    <Route path="/modelos" element={<RiesgoBroteForm />} />
                    <Route path="/prediccion-avanzada" element={<PrediccionAvanzada />} />
                    <Route path="/dashboard-predicciones" element={<DashboardPredicciones />} />
                    <Route path="/monitoreo" element={<MonitoreoTiempoReal />} />
                    <Route path="/entrenar-modelos" element={<EntrenamientoModelos />} />
                    <Route path="/reportes" element={<Reportes />} />
                    <Route path="/alertas" element={<Alertas />} />
                    <Route path="/configuracion" element={<Configuracion />} />
                  </Routes>
                </div>
              </ProtectedRoute>
            }
          />
        </Routes>
      </div>
    </Router>
  );
}

// ESTA LÍNEA ES CRÍTICA - DEBES EXPORTAR EL COMPONENTE
export default App;