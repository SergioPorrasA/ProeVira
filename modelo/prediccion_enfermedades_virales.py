import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from sklearn.linear_model import LinearRegression
from sklearn.preprocessing import PolynomialFeatures
from sklearn.metrics import mean_squared_error, r2_score
from datetime import datetime
import warnings
warnings.filterwarnings('ignore')

class PredictorDengue:
    def __init__(self):
        self.modelo_lineal = LinearRegression()
        self.modelo_polinomial = LinearRegression()
        self.caracteristicas_poli = PolynomialFeatures(degree=2)
        
    def cargar_y_preprocesar_datos(self, ruta_archivo):
        """
        Carga y preprocesa los datos del CSV
        """
        # Cargar datos
        df = pd.read_csv(ruta_archivo)
        
        # Imprimir informacion para diagnostico
        print(f"Columnas disponibles: {df.columns.tolist()}")
        print(f"Primeras filas:\n{df.head()}")
        print(f"Total de registros: {len(df)}")
        
        # Convertir fecha a datetime
        df['FECHA'] = pd.to_datetime(df['FECHA'], format='%d/%m/%Y')
        
        # Agrupar por fecha y contar casos
        casos_diarios = df.groupby('FECHA').size().reset_index(name='casos_confirmados')
        
        # Ordenar por fecha
        casos_diarios = casos_diarios.sort_values('FECHA').reset_index(drop=True)
        
        # Crear indice temporal (variable X)
        casos_diarios['X'] = range(1, len(casos_diarios) + 1)
        
        print(f"Casos diarios procesados: {len(casos_diarios)}")
        
        return casos_diarios
    
    def entrenar_modelos(self, df):
        """
        Entrena ambos modelos de regresion
        """
        # Preparar datos
        X = df[['X']].values
        y = df['casos_confirmados'].values
        
        # Entrenar modelo lineal
        self.modelo_lineal.fit(X, y)
        
        # Entrenar modelo polinomial
        X_poli = self.caracteristicas_poli.fit_transform(X)
        self.modelo_polinomial.fit(X_poli, y)
        
        # Generar predicciones de entrenamiento
        df['Prediccion_Lineal'] = self.modelo_lineal.predict(X)
        df['Prediccion_Polinomica'] = self.modelo_polinomial.predict(X_poli)
        
        return df
    
    def evaluar_modelos(self, df):
        """
        Evalua el rendimiento de ambos modelos
        """
        y_real = df['casos_confirmados']
        y_pred_lineal = df['Prediccion_Lineal']
        y_pred_poli = df['Prediccion_Polinomica']
        
        # Metricas para regresion lineal
        mse_lineal = mean_squared_error(y_real, y_pred_lineal)
        r2_lineal = r2_score(y_real, y_pred_lineal)
        
        # Metricas para regresion polinomial
        mse_poli = mean_squared_error(y_real, y_pred_poli)
        r2_poli = r2_score(y_real, y_pred_poli)
        
        print("\n=== EVALUACION DE MODELOS ===")
        print(f"Regresion Lineal - MSE: {mse_lineal:.4f}, R2: {r2_lineal:.4f}")
        print(f"Regresion Polinomial - MSE: {mse_poli:.4f}, R2: {r2_poli:.4f}")
        
        # Calcular errores absolutos
        df['Error_Lineal'] = abs(y_real - y_pred_lineal)
        df['Error_Polinomica'] = abs(y_real - y_pred_poli)
        
        # Crear tabla comparativa
        self.imprimir_tabla_comparativa(df)
        
        return {
            'lineal': {'mse': mse_lineal, 'r2': r2_lineal},
            'polinomial': {'mse': mse_poli, 'r2': r2_poli}
        }
    
    def imprimir_tabla_comparativa(self, df):
        # """
        # Imprime una tabla comparativa de casos reales vs predicciones
        # """
        print("\n" + "="*120)
        print("TABLA COMPARATIVA: CASOS REALES VS PREDICCIONES")
        print("="*120)
        print(f"{'Fecha':<12} {'Casos Reales':<15} {'Pred. Lineal':<15} {'Error Lin.':<12} {'Pred. Polin.':<15} {'Error Polin.':<12}")
        print("-"*120)
        
        # Mostrar primeras 10 filas
        for idx, fila in df.head(10).iterrows():
            print(f"{fila['FECHA'].strftime('%d/%m/%Y'):<12} "
                  f"{fila['casos_confirmados']:<15.0f} "
                  f"{fila['Prediccion_Lineal']:<15.2f} "
                  f"{fila['Error_Lineal']:<12.2f} "
                  f"{fila['Prediccion_Polinomica']:<15.2f} "
                  f"{fila['Error_Polinomica']:<12.2f}")
        
        print("...")
        
        # Mostrar ultimas 10 filas
        for idx, fila in df.tail(10).iterrows():
            print(f"{fila['FECHA'].strftime('%d/%m/%Y'):<12} "
                  f"{fila['casos_confirmados']:<15.0f} "
                  f"{fila['Prediccion_Lineal']:<15.2f} "
                  f"{fila['Error_Lineal']:<12.2f} "
                  f"{fila['Prediccion_Polinomica']:<15.2f} "
                  f"{fila['Error_Polinomica']:<12.2f}")
        
        print("-"*120)
        
        # Resumen estadistico
        print("\nRESUMEN ESTADISTICO:")
        print(f"Error Promedio Lineal: {df['Error_Lineal'].mean():.2f} casos")
        print(f"Error Promedio Polinomial: {df['Error_Polinomica'].mean():.2f} casos")
        print(f"Error Maximo Lineal: {df['Error_Lineal'].max():.2f} casos")
        print(f"Error Maximo Polinomial: {df['Error_Polinomica'].max():.2f} casos")
        
        # Determinar cual modelo es mejor
        if df['Error_Lineal'].mean() < df['Error_Polinomica'].mean():
            print(f"\n>>> La Regresion LINEAL es mas precisa (menor error promedio)")
        else:
            print(f"\n>>> La Regresion POLINOMIAL es mas precisa (menor error promedio)")
        
        print("="*120)
    
    def predecir_futuro(self, ultima_fecha, periodos=90):
        """
        Genera predicciones futuras
        """
        # Obtener el ultimo indice
        ultimo_indice = self.datos_entrenamiento['X'].max()
        
        # Crear fechas futuras
        fechas_futuras = pd.date_range(start=ultima_fecha + pd.Timedelta(days=1), periods=periodos)
        
        # Crear DataFrame para predicciones
        df_futuro = pd.DataFrame({
            'FECHA': fechas_futuras,
            'X': range(ultimo_indice + 1, ultimo_indice + periodos + 1)
        })
        
        # Generar predicciones lineales
        X_futuro = df_futuro[['X']].values
        df_futuro['Prediccion_Lineal'] = self.modelo_lineal.predict(X_futuro)
        
        # Generar predicciones polinomiales
        X_futuro_poli = self.caracteristicas_poli.transform(X_futuro)
        df_futuro['Prediccion_Polinomica'] = self.modelo_polinomial.predict(X_futuro_poli)
        
        return df_futuro
    
    def graficar_resultados(self, datos_entrenamiento, predicciones_futuras=None):
        """
        Genera graficas comparativas
        """
        plt.figure(figsize=(15, 8))
        
        # Graficar datos reales
        plt.plot(datos_entrenamiento['FECHA'], datos_entrenamiento['casos_confirmados'], 
                'bo-', label='Casos Reales', alpha=0.7, markersize=4)
        
        # Graficar predicciones de entrenamiento
        plt.plot(datos_entrenamiento['FECHA'], datos_entrenamiento['Prediccion_Lineal'], 
                'r--', label='Prediccion Lineal (Entrenamiento)', alpha=0.7)
        plt.plot(datos_entrenamiento['FECHA'], datos_entrenamiento['Prediccion_Polinomica'], 
                'g--', label='Prediccion Polinomial (Entrenamiento)', alpha=0.7)
        
        # Graficar predicciones futuras si existen
        if predicciones_futuras is not None:
            plt.plot(predicciones_futuras['FECHA'], predicciones_futuras['Prediccion_Lineal'], 
                    'r-', label='Prediccion Lineal (Futuro)', alpha=0.5)
            plt.plot(predicciones_futuras['FECHA'], predicciones_futuras['Prediccion_Polinomica'], 
                    'g-', label='Prediccion Polinomial (Futuro)', alpha=0.5)
            
            # Linea vertical para separar entrenamiento de prediccion
            max_fecha_entrenamiento = datos_entrenamiento['FECHA'].max()
            plt.axvline(x=max_fecha_entrenamiento, color='gray', linestyle=':', alpha=0.7)
            plt.text(max_fecha_entrenamiento, plt.ylim()[1]*0.9, 'Inicio Prediccion', 
                    rotation=90, ha='right', va='top')
        
        plt.xlabel('Fecha')
        plt.ylabel('Numero de Casos')
        plt.title('Prediccion de Casos de Dengue - Regresion Lineal vs Polinomial')
        plt.legend()
        plt.grid(True, alpha=0.3)
        plt.xticks(rotation=45)
        plt.tight_layout()
        plt.show()
    
    def imprimir_predicciones_futuras(self, df_futuro):
        """
        Imprime una tabla con las predicciones futuras
        """
        print("\n" + "="*100)
        print("PREDICCIONES FUTURAS DE CASOS DE DENGUE")
        print("="*100)
        print(f"{'Fecha':<12} {'Pred. Lineal':<20} {'Pred. Polinomial':<20} {'Diferencia':<15}")
        print("-"*100)
        
        for idx, fila in df_futuro.iterrows():
            diferencia = abs(fila['Prediccion_Lineal'] - fila['Prediccion_Polinomica'])
            print(f"{fila['FECHA'].strftime('%d/%m/%Y'):<12} "
                  f"{fila['Prediccion_Lineal']:<20.2f} "
                  f"{fila['Prediccion_Polinomica']:<20.2f} "
                  f"{diferencia:<15.2f}")
        
        print("-"*100)
        print(f"\nTotal de días predichos: {len(df_futuro)}")
        print(f"Promedio Predicción Lineal: {df_futuro['Prediccion_Lineal'].mean():.2f} casos/día")
        print(f"Promedio Predicción Polinomial: {df_futuro['Prediccion_Polinomica'].mean():.2f} casos/día")
        print(f"Máximo previsto (Lineal): {df_futuro['Prediccion_Lineal'].max():.2f} casos")
        print(f"Máximo previsto (Polinomial): {df_futuro['Prediccion_Polinomica'].max():.2f} casos")
        print(f"Mínimo previsto (Lineal): {df_futuro['Prediccion_Lineal'].min():.2f} casos")
        print(f"Mínimo previsto (Polinomial): {df_futuro['Prediccion_Polinomica'].min():.2f} casos")
        print("="*100)

    def ejecutar_analisis_completo(self, ruta_csv, periodos_prediccion=90):
        """
        Ejecuta el analisis completo
        """
        print("Cargando y preprocesando datos...")
        datos = self.cargar_y_preprocesar_datos(ruta_csv)
        
        print("\nEntrenando modelos...")
        self.datos_entrenamiento = self.entrenar_modelos(datos)
        
        print("\nEvaluando modelos...")
        metricas = self.evaluar_modelos(self.datos_entrenamiento)
        
        print("\nGenerando predicciones futuras...")
        ultima_fecha = self.datos_entrenamiento['FECHA'].max()
        predicciones_futuras = self.predecir_futuro(ultima_fecha, periodos_prediccion)
        
        # Imprimir predicciones futuras
        self.imprimir_predicciones_futuras(predicciones_futuras)
        
        print("\nGenerando graficas...")
        self.graficar_resultados(self.datos_entrenamiento, predicciones_futuras)
        
        # Mostrar resumen de predicciones futuras
        print("\n=== RESUMEN DE PREDICCIONES FUTURAS ===")
        print(f"Periodo de prediccion: {predicciones_futuras['FECHA'].min().strftime('%d/%m/%Y')} a {predicciones_futuras['FECHA'].max().strftime('%d/%m/%Y')}")
        print(f"Casos promedio predichos (Lineal): {predicciones_futuras['Prediccion_Lineal'].mean():.2f}")
        print(f"Casos promedio predichos (Polinomial): {predicciones_futuras['Prediccion_Polinomica'].mean():.2f}")
        
        # Guardar tabla completa en CSV
        tabla_comparativa = self.datos_entrenamiento[['FECHA', 'casos_confirmados', 
                                                'Prediccion_Lineal', 'Error_Lineal',
                                                'Prediccion_Polinomica', 'Error_Polinomica']].copy()
        tabla_comparativa.to_csv('tabla_comparativa_completa.csv', index=False)
        print("\nTabla comparativa completa guardada en: tabla_comparativa_completa.csv")
        
        return {
            'datos_entrenamiento': self.datos_entrenamiento,
            'predicciones_futuras': predicciones_futuras,
            'metricas': metricas
        }

# Funcion principal para ejecutar el analisis
def main():
    """
    Funcion principal para ejecutar el predictor de dengue
    """
    # Inicializar el predictor
    predictor = PredictorDengue()
    
    # Especificar la ruta del archivo CSV
    ruta_csv = r"c:/GDPS-PROEVIRA/ProeVira/modelo/datos_dengue.csv"  # Cambiar a la ruta correcta del archivo CSV
    
    try:
        # Ejecutar analisis completo
        resultados = predictor.ejecutar_analisis_completo(ruta_csv, periodos_prediccion=90)
        
        # Guardar resultados en archivos CSV
        resultados['datos_entrenamiento'].to_csv('resultados_entrenamiento.csv', index=False)
        resultados['predicciones_futuras'].to_csv('predicciones_futuras.csv', index=False)
        
        print("\n[OK] Analisis completado exitosamente!")
        print("Archivos generados:")
        print("   - resultados_entrenamiento.csv")
        print("   - predicciones_futuras.csv")
        print("   - tabla_comparativa_completa.csv")
        
    except FileNotFoundError:
        print(f"[ERROR] No se encontro el archivo {ruta_csv}")
        print("Por favor, asegurate de que el archivo existe y la ruta es correcta.")
    except Exception as e:
        print(f"[ERROR] Error durante el analisis: {str(e)}")
        import traceback
        traceback.print_exc()

# Ejecutar el programa
if __name__ == "__main__":
    main()

