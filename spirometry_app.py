import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import io

# --- Funciones de análisis de espirometría ---
def get_simplified_predicted_values(age, sex, height):
    """
    Función simplificada para obtener valores predichos de espirometría.
    
    NOTA: Esto es solo un ejemplo conceptual. Para una aplicación real,
    debes usar las ecuaciones estandarizadas de la Global Lung Function Initiative (GLI).
    """
    # Ecuaciones de predicción simplificadas (ejemplo)
    # Valores de FVC y FEV1 en litros (L)
    if sex == 'Masculino':
        predicted_fvc = (4.0 - 0.02 * age) + (0.05 * height / 100) # Ajuste por edad y altura
        predicted_fev1 = (3.5 - 0.025 * age) + (0.04 * height / 100)
    else: # Femenino
        predicted_fvc = (3.0 - 0.015 * age) + (0.04 * height / 100)
        predicted_fev1 = (2.8 - 0.02 * age) + (0.035 * height / 100)

    predicted_fev1_fvc_ratio = (predicted_fev1 / predicted_fvc) * 100

    return {
        "FVC_pred": predicted_fvc,
        "FEV1_pred": predicted_fev1,
        "FEV1_FVC_pred": predicted_fev1_fvc_ratio
    }

def calculate_spirometry_parameters(df, patient_info):
    """
    Calcula los parámetros clave y los compara con los valores de referencia.
    """
    if 'tiempo' not in df.columns or 'flujo' not in df.columns or 'volumen' not in df.columns:
        st.error("El archivo CSV debe contener las columnas 'tiempo', 'flujo' y 'volumen'.")
        return None, None

    df['tiempo'] = pd.to_numeric(df['tiempo'], errors='coerce')
    df['flujo'] = pd.to_numeric(df['flujo'], errors='coerce')
    df['volumen'] = pd.to_numeric(df['volumen'], errors='coerce')
    df = df.dropna().sort_values('tiempo').reset_index(drop=True)

    if df.empty:
        st.error("No hay datos válidos después del preprocesamiento.")
        return None, None

    # Cálculos de valores medidos
    fvc_medida = df['volumen'].max()
    fev1_data = df[df['tiempo'] <= 1.0]
    fev1_medida = fev1_data['volumen'].max() if not fev1_data.empty else 0.0
    fev1_fvc_ratio_medida = (fev1_medida / fvc_medida * 100) if fvc_medida > 0 else 0.0
    pef_medido = df['flujo'].max()

    # Obtener valores predichos
    predicted_values = get_simplified_predicted_values(
        patient_info['edad'],
        patient_info['sexo'],
        patient_info['altura']
    )

    # Comparación y determinación del patrón
    fvc_predicho = predicted_values['FVC_pred']
    fev1_predicho = predicted_values['FEV1_pred']
    fev1_fvc_ratio_predicho = predicted_values['FEV1_FVC_pred']

    fvc_percent_predicho = (fvc_medida / fvc_predicho) * 100 if fvc_predicho > 0 else 0
    fev1_percent_predicho = (fev1_medida / fev1_predicho) * 100 if fev1_predicho > 0 else 0

    pattern = "Normal"
    # Límite inferior de la normalidad (LLN)
    # Se utiliza un umbral del 80% como un LLN simplificado para este ejemplo.
    if fev1_fvc_ratio_medida < 70 or fev1_percent_predicho < 80:
        pattern = "Obstructivo"
    elif fvc_percent_predicho < 80:
        pattern = "Restrictivo"

    measured_results = {
        "FVC (L)": round(fvc_medida, 2),
        "FEV1 (L)": round(fev1_medida, 2),
        "FEV1/FVC (%)": round(fev1_fvc_ratio_medida, 2),
        "PEF (L/s)": round(pef_medido, 2),
    }

    comparison_results = {
        "FVC Predicho (L)": round(fvc_predicho, 2),
        "FEV1 Predicho (L)": round(fev1_predicho, 2),
        "FVC (% Predicho)": round(fvc_percent_predicho, 2),
        "FEV1 (% Predicho)": round(fev1_percent_predicho, 2),
        "FEV1/FVC Predicho (%)": round(fev1_fvc_ratio_predicho, 2)
    }

    return measured_results, comparison_results, pattern

# --- Interfaz de Streamlit ---
def main():
    st.title("Aplicación de Espirometría")
    st.subheader("Análisis de Curvas de Flujo-Volumen y Volumen-Tiempo")

    st.sidebar.title("Información del Paciente")
    age = st.sidebar.slider("Edad", 18, 100, 30)
    sex = st.sidebar.selectbox("Sexo", ["Masculino", "Femenino"])
    height = st.sidebar.slider("Altura (cm)", 100, 250, 170)
    uploaded_file = st.sidebar.file_uploader("Sube un archivo CSV de espirometría", type=["csv"])
    
    patient_info = {
        "edad": age,
        "sexo": sex,
        "altura": height
    }

    if uploaded_file is not None:
        try:
            df = pd.read_csv(uploaded_file)
            st.success("✅ Archivo CSV cargado correctamente.")

            st.write("### Datos de la espirometría (Primeras 5 filas)")
            st.dataframe(df.head())

            measured_results, comparison_results, clinical_pattern = calculate_spirometry_parameters(df.copy(), patient_info)

            if measured_results is not None:
                st.write("---")
                st.write("### Resumen de Resultados")
                
                st.write("#### Valores Medidos")
                st.table(pd.DataFrame([measured_results]))

                st.write("#### Comparación con Valores de Referencia")
                st.table(pd.DataFrame([comparison_results]))

                st.info(f"**Diagnóstico Sugerido:** **{clinical_pattern}**")

                st.write("---")
                st.write("### Gráficas de Espirometría")

                fig_vol_time, ax_vol_time = plt.subplots(figsize=(10, 5))
                ax_vol_time.plot(df['tiempo'], df['volumen'], label='Curva Medida', color='blue')
                ax_vol_time.set_xlabel("Tiempo (s)")
                ax_vol_time.set_ylabel("Volumen (L)")
                ax_vol_time.set_title("Curva Volumen-Tiempo")
                ax_vol_time.grid(True)
                st.pyplot(fig_vol_time)

                fig_flow_vol, ax_flow_vol = plt.subplots(figsize=(10, 5))
                ax_flow_vol.plot(df['volumen'], df['flujo'], label='Curva Medida', color='blue')
                ax_flow_vol.set_xlabel("Volumen (L)")
                ax_flow_vol.set_ylabel("Flujo (L/s)")
                ax_flow_vol.set_title("Curva Flujo-Volumen")
                ax_flow_vol.grid(True)
                st.pyplot(fig_flow_vol)

            else:
                st.error("No se pudieron calcular los parámetros de espirometría. Revisa el formato de tus datos.")

        except Exception as e:
            st.error(f"❌ Error al procesar el archivo CSV: {e}")
            st.info("Asegúrate de que el archivo CSV tiene las columnas 'tiempo', 'flujo' y 'volumen'.")

# --- Ejecutar la aplicación ---
if __name__ == "__main__":
    main()