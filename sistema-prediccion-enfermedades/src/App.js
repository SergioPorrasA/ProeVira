import React from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import './styles/globals.css';

// Layout
import Layout from './components/layout/Layout';
import Sidebar from './components/layout/Sidebar';

// Pages
import Login from './pages/Login';
import Dashboard from './pages/Dashboard';
import Analisis from './pages/Analisis';
import ModelosPredictivos from './pages/ModelosPredictivos';
import Reportes from './pages/Reportes';
import Configuracion from './pages/Configuracion';
// import Formulario de Riesgo de Brote (si es necesario en alguna ruta)
import RiesgoBroteForm from './pages/RiesgoBroteForm';
import PrediccionAvanzada from './pages/PrediccionAvanzada';

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
                    <Route path="/" element={<Navigate to="/dashboard" replace />} />
                    <Route path="/dashboard" element={<Dashboard />} />
                    <Route path="/analisis" element={<Analisis />} />
                    {/* <Route path="/modelos" element={<ModelosPredictivos />} /> */}
                    <Route path="/modelos" element={<RiesgoBroteForm />} />
                    <Route path="/prediccion-avanzada" element={<PrediccionAvanzada />} />
                    <Route path="/reportes" element={<Reportes />} />
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