-- =====================================================
-- Script de Base de Datos: proyecto_integrador
-- Sistema de Predicción de Enfermedades Virales (ProeVira)
-- Generado: 2025-12-01
-- =====================================================

DROP DATABASE IF EXISTS proyecto_integrador;
CREATE DATABASE proyecto_integrador CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE proyecto_integrador;

-- =====================================================
-- Tabla: usuario (debe crearse primero por dependencia FK)
-- =====================================================
CREATE TABLE IF NOT EXISTS `usuario` (
  `id_usuario` int NOT NULL AUTO_INCREMENT,
  `nombre` varchar(100) NOT NULL,
  `email` varchar(100) NOT NULL,
  `password` varchar(255) NOT NULL,
  `rol` varchar(50) DEFAULT 'usuario',
  `fecha_creacion` datetime DEFAULT CURRENT_TIMESTAMP,
  `activo` tinyint(1) DEFAULT 1,
  PRIMARY KEY (`id_usuario`),
  UNIQUE KEY `email` (`email`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

-- =====================================================
-- Tabla: region
-- =====================================================
CREATE TABLE IF NOT EXISTS `region` (
  `id_region` int NOT NULL,
  `nombre` varchar(100) NOT NULL,
  `codigo_entidad_inegi` int NOT NULL,
  `poblacion` int DEFAULT 0,
  PRIMARY KEY (`id_region`),
  UNIQUE KEY `codigo_entidad_inegi` (`codigo_entidad_inegi`),
  UNIQUE KEY `uq_nombre_region` (`nombre`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

-- =====================================================
-- Tabla: enfermedad
-- =====================================================
CREATE TABLE IF NOT EXISTS `enfermedad` (
  `id_enfermedad` int NOT NULL AUTO_INCREMENT,
  `nombre` varchar(100) NOT NULL,
  `descripcion` text,
  `estado` varchar(20) DEFAULT NULL,
  `nivel_riesgo` varchar(50) DEFAULT NULL,
  PRIMARY KEY (`id_enfermedad`)
) ENGINE=InnoDB AUTO_INCREMENT=2 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

-- =====================================================
-- Tabla: dato_epidemiologico
-- =====================================================
CREATE TABLE IF NOT EXISTS `dato_epidemiologico` (
  `id_dato` int NOT NULL AUTO_INCREMENT,
  `id_enfermedad` int NOT NULL,
  `id_region` int NOT NULL,
  `fecha_fin_semana` date NOT NULL,
  `casos_confirmados` int NOT NULL,
  `defunciones` int DEFAULT 0,
  `tasa_incidencia` decimal(10,4) NOT NULL,
  `riesgo_brote_target` tinyint(1) NOT NULL,
  `fecha_carga` date DEFAULT NULL,
  `id_usuario_carga` int DEFAULT NULL,
  PRIMARY KEY (`id_dato`),
  UNIQUE KEY `uq_dato_fecha_region` (`id_region`,`fecha_fin_semana`),
  KEY `fk_dato_enfermedad` (`id_enfermedad`),
  KEY `fk_dato_usuario` (`id_usuario_carga`),
  CONSTRAINT `fk_dato_enfermedad` FOREIGN KEY (`id_enfermedad`) REFERENCES `enfermedad` (`id_enfermedad`),
  CONSTRAINT `fk_dato_region` FOREIGN KEY (`id_region`) REFERENCES `region` (`id_region`),
  CONSTRAINT `fk_dato_usuario` FOREIGN KEY (`id_usuario_carga`) REFERENCES `usuario` (`id_usuario`)
) ENGINE=InnoDB AUTO_INCREMENT=19521 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

-- =====================================================
-- Tabla: alerta
-- =====================================================
CREATE TABLE IF NOT EXISTS `alerta` (
  `id_alerta` int NOT NULL AUTO_INCREMENT,
  `id_region` int NOT NULL,
  `id_enfermedad` int NOT NULL,
  `mensaje` text,
  `fecha_alerta` date DEFAULT NULL,
  `estado` varchar(20) DEFAULT NULL,
  `nivel` varchar(50) DEFAULT NULL,
  PRIMARY KEY (`id_alerta`),
  KEY `alerta_ibfk_1` (`id_region`),
  KEY `alerta_ibfk_2` (`id_enfermedad`),
  CONSTRAINT `alerta_ibfk_1` FOREIGN KEY (`id_region`) REFERENCES `region` (`id_region`),
  CONSTRAINT `alerta_ibfk_2` FOREIGN KEY (`id_enfermedad`) REFERENCES `enfermedad` (`id_enfermedad`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

-- =====================================================
-- Índices adicionales para optimización de consultas
-- =====================================================
CREATE INDEX idx_dato_fecha ON dato_epidemiologico(fecha_fin_semana);
CREATE INDEX idx_dato_region_fecha ON dato_epidemiologico(id_region, fecha_fin_semana);
CREATE INDEX idx_dato_casos ON dato_epidemiologico(casos_confirmados);

-- =====================================================
-- Datos: Regiones (32 Estados de México con población CONAPO 2025)
-- =====================================================
INSERT INTO region (id_region, nombre, codigo_entidad_inegi, poblacion) VALUES
  (1, 'Aguascalientes', 1, 1512400),
  (2, 'Baja California', 2, 3968300),
  (3, 'Baja California Sur', 3, 850700),
  (4, 'Campeche', 4, 1011800),
  (5, 'Coahuila de Zaragoza', 5, 3328500),
  (6, 'Colima', 6, 775100),
  (7, 'Chiapas', 7, 6000100),
  (8, 'Chihuahua', 8, 3998500),
  (9, 'Ciudad de México', 9, 9386700),
  (10, 'Durango', 10, 1913400),
  (11, 'Guanajuato', 11, 6555200),
  (12, 'Guerrero', 12, 3724300),
  (13, 'Hidalgo', 13, 3327600),
  (14, 'Jalisco', 14, 8847600),
  (15, 'México', 15, 18016500),
  (16, 'Michoacán de Ocampo', 16, 4975800),
  (17, 'Morelos', 17, 2056000),
  (18, 'Nayarit', 18, 1294800),
  (19, 'Nuevo León', 19, 6231200),
  (20, 'Oaxaca', 20, 4432900),
  (21, 'Puebla', 21, 6886400),
  (22, 'Querétaro', 22, 2603300),
  (23, 'Quintana Roo', 23, 1989500),
  (24, 'San Luis Potosí', 24, 2931400),
  (25, 'Sinaloa', 25, 3274600),
  (26, 'Sonora', 26, 3154100),
  (27, 'Tabasco', 27, 2601900),
  (28, 'Tamaulipas', 28, 3682900),
  (29, 'Tlaxcala', 29, 1421000),
  (30, 'Veracruz de Ignacio de la Llave', 30, 8871300),
  (31, 'Yucatán', 31, 2561900),
  (32, 'Zacatecas', 32, 1698200);

-- =====================================================
-- Datos: Enfermedades
-- =====================================================
INSERT INTO enfermedad (id_enfermedad, nombre, descripcion, estado, nivel_riesgo) VALUES
  (1, 'Dengue', 'Enfermedad viral transmitida por mosquito Aedes aegypti', 'activo', 'alto');

-- =====================================================
-- Usuario administrador por defecto
-- =====================================================
INSERT INTO usuario (nombre, email, password, rol) VALUES
  ('Administrador', 'admin@proevira.com', '$2b$10$hashedpassword', 'admin');

-- =====================================================
-- INFORMACIÓN DEL SISTEMA
-- =====================================================
-- Base de datos: proyecto_integrador
-- Tablas principales:
--   - region: 32 estados de México con población CONAPO 2025
--   - enfermedad: Catálogo de enfermedades (actualmente Dengue)
--   - dato_epidemiologico: Datos semanales agregados por estado
--   - alerta: Sistema de alertas epidemiológicas
--   - usuario: Usuarios del sistema
--
-- Datos cargados:
--   - Período: 2020-01-05 a 2025-11-23 (6 años)
--   - Registros: 9,760 (32 estados × ~305 semanas)
--   - Fuente: Datos Abiertos de Dengue - Gobierno de México
--
-- Modelo de predicción:
--   - Algoritmo: Random Forest Classifier
--   - Precisión: ~85%
--   - Archivos: model.pkl, label_encoder.pkl
--
-- APIs:
--   - Flask (puerto 5001): Predicciones ML
--   - Node.js (puerto 5000): Dashboard y configuración
--
-- Para cargar datos epidemiológicos, usar ETL_LOADER.py
-- =====================================================
